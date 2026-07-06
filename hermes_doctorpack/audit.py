"""Core diagnostics for Hermes Doctorpack.

Design rule: never turn missing evidence into a hard failure. Findings are
explicitly statused as ok/warn/fail/unknown with confidence and source evidence.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import platform
import re
import socket
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

try:  # Hermes already depends on PyYAML, but keep a fallback for tests/minimal envs.
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password|passwd|pwd|bearer|authorization)(\s*[:=]\s*)([^\s'\"{},;]+)"),
    re.compile(r"(?i)(sk-[A-Za-z0-9_\-]{20,})"),
    re.compile(r"(?i)(xox[baprs]-[A-Za-z0-9\-]{20,})"),
    re.compile(r"(?i)(gh[pousr]_[A-Za-z0-9_]{20,})"),
    re.compile(r"(?i)(AIza[0-9A-Za-z_\-]{20,})"),
    re.compile(r"(?i)(https?://)([^\s/@:]+):([^\s/@]+)@"),
)
# Conservative phone redaction: avoid eating ISO timestamps / log prefixes. This catches
# common 10-digit phone shapes; it deliberately does not try to redact every possible
# international number because over-redacting timestamps destroys diagnostic evidence.
PHONE_RE = re.compile(r"(?<![\w:])(?:\+?\d{1,3}[- .])?(?:\(?\d{3}\)?[- .]\d{3}[- .]\d{4})(?!\w)")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(
    r"(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?(?:Z|[+-]\d{2}:?\d{2})?)"
)

ERROR_WORDS = ("error", "exception", "traceback", "failed", "failure", "unauthorized", "forbidden")
WARN_WORDS = ("warning", "warn", "deprecated", "retry", "rate limit", "timeout")
PLUGIN_WORDS = ("plugin", "plugins", "register_tool", "register_command")
GATEWAY_WORDS = ("gateway", "discord", "telegram", "whatsapp", "slack", "matrix", "delivery")


@dataclass
class Evidence:
    source: str
    message: str
    timestamp: str | None = None
    confidence: str = "medium"


@dataclass
class Finding:
    id: str
    title: str
    status: str
    severity: str
    confidence: str
    summary: str
    evidence: list[Evidence] = field(default_factory=list)
    recommendation: str = ""


def redact(text: Any) -> str:
    """Redact secrets and common direct identifiers from arbitrary text."""
    out = str(text)
    out = ANSI_RE.sub("", out)
    for pat in SECRET_PATTERNS:
        def repl(match: re.Match[str]) -> str:
            if match.re.pattern.startswith("(?i)(https?"):
                return f"{match.group(1)}[REDACTED]@"
            if len(match.groups()) >= 3:
                return f"{match.group(1)}{match.group(2)}[REDACTED]"
            return "[REDACTED]"
        out = pat.sub(repl, out)
    out = EMAIL_RE.sub("[REDACTED_EMAIL]", out)
    out = PHONE_RE.sub("[REDACTED_PHONE]", out)
    return out


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _parse_ts(line: str) -> dt.datetime | None:
    m = TS_RE.search(line)
    if not m:
        return None
    raw = m.group("ts").replace(" ", "T").replace(",", ".")
    try:
        if raw.endswith("Z"):
            return dt.datetime.fromisoformat(raw[:-1] + "+00:00")
        parsed = dt.datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.datetime.now().astimezone().tzinfo)
        return parsed.astimezone(dt.timezone.utc)
    except ValueError:
        return None


def _is_recent(line: str, cutoff: dt.datetime) -> bool:
    parsed = _parse_ts(line)
    if parsed is None:
        return True  # timestamp-less recent tail evidence is weak but still visible
    return parsed >= cutoff


def _rel(path: Path, home: Path) -> str:
    try:
        return str(path.relative_to(home)).replace("\\", "/")
    except Exception:
        return str(path)


def discover_hermes_home(explicit: str | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("HERMES_HOME")
    if env:
        return Path(env).expanduser().resolve()
    try:
        from hermes_constants import get_hermes_home  # type: ignore
        return Path(get_hermes_home()).expanduser().resolve()
    except Exception:
        pass
    if platform.system().lower() == "windows":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / "hermes"
    return Path.home() / ".hermes"


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    if yaml is not None:
        data = yaml.safe_load(text) or {}
        return data if isinstance(data, dict) else {}
    # intentionally tiny fallback: enough for simple top-level test fixtures
    out: dict[str, Any] = {}
    for line in text.splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"\'')
    return out


def _tail_lines(path: Path, max_bytes: int = 256_000, max_lines: int = 500) -> list[str]:
    if not path.exists() or not path.is_file():
        return []
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            if size > max_bytes:
                fh.seek(max(0, size - max_bytes))
            data = fh.read(max_bytes)
        return data.decode("utf-8", errors="replace").splitlines()[-max_lines:]
    except OSError:
        return []


def _log_paths(home: Path) -> list[Path]:
    candidates = [
        home / "logs" / "agent.log",
        home / "logs" / "gateway.log",
        home / "logs" / "errors.log",
        home / "agent.log",
        home / "gateway.log",
        home / "errors.log",
    ]
    return [p for p in candidates if p.exists()]


def _scan_logs(home: Path, *, lookback_hours: int, focus_words: Iterable[str] = ()) -> list[Evidence]:
    cutoff = _now_utc() - dt.timedelta(hours=lookback_hours)
    focus = tuple(w.lower() for w in focus_words)
    evidence: list[Evidence] = []
    for path in _log_paths(home):
        for line in _tail_lines(path):
            low = line.lower()
            if focus and not any(w in low for w in focus):
                continue
            if not _is_recent(line, cutoff):
                continue
            if any(w in low for w in ERROR_WORDS + WARN_WORDS):
                ts = _parse_ts(line)
                evidence.append(
                    Evidence(
                        source=_rel(path, home),
                        message=redact(line)[:600],
                        timestamp=ts.isoformat() if ts else None,
                        confidence="high" if ts else "medium",
                    )
                )
    return evidence[:50]


def _finding(
    id: str,
    title: str,
    status: str,
    severity: str,
    confidence: str,
    summary: str,
    evidence: list[Evidence] | None = None,
    recommendation: str = "",
) -> Finding:
    return Finding(id, title, status, severity, confidence, summary, evidence or [], recommendation)


def _safe_config_view(cfg: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "approvals", "agent", "model", "plugins", "gateway", "mcp_servers", "cron", "tools", "toolsets",
        "terminal", "memory", "privacy", "security", "tts", "stt", "delegation", "moa",
    }
    return {k: _redact_obj(v) for k, v in cfg.items() if k in allowed}


def _redact_obj(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if re.search(r"(?i)(key|token|secret|password|client_secret|webhook)", str(k)):
                out[k] = "[REDACTED]"
            else:
                out[k] = _redact_obj(v)
        return out
    if isinstance(obj, list):
        return [_redact_obj(x) for x in obj]
    if isinstance(obj, str):
        return redact(obj)
    return obj


def _enabled_plugins(cfg: dict[str, Any]) -> tuple[list[str], list[str]]:
    plugins = cfg.get("plugins") or {}
    enabled = plugins.get("enabled") or []
    disabled = plugins.get("disabled") or []
    return list(enabled) if isinstance(enabled, list) else [], list(disabled) if isinstance(disabled, list) else []


def config_audit(args: dict[str, Any]) -> dict[str, Any]:
    home = discover_hermes_home(args.get("hermes_home"))
    lookback = int(args.get("lookback_hours") or 24)
    include_logs = bool(args.get("include_logs", True))
    cfg_path = home / "config.yaml"
    cfg = _load_yaml(cfg_path)
    findings: list[Finding] = []

    if cfg_path.exists():
        findings.append(_finding(
            "config.present", "config.yaml present", "ok", "info", "high",
            "Found Hermes config.yaml.", [Evidence(_rel(cfg_path, home), "config file exists", confidence="high")]
        ))
    else:
        findings.append(_finding(
            "config.present", "config.yaml missing", "unknown", "medium", "high",
            "No config.yaml was found at the inspected Hermes home; cannot audit config-specific risks.",
            [Evidence(str(cfg_path), "file not found", confidence="high")],
            "Verify HERMES_HOME or pass hermes_home explicitly."
        ))

    approvals = ((cfg.get("approvals") or {}) if isinstance(cfg.get("approvals"), dict) else {})
    mode = str(approvals.get("mode", "manual")).lower()
    if mode in {"off", "none", "false"}:
        findings.append(_finding(
            "approvals.disabled", "approval prompts disabled", "warn", "high", "high",
            "approvals.mode appears to disable command approval prompts.",
            [Evidence(_rel(cfg_path, home), f"approvals.mode={redact(mode)}", confidence="high")],
            "Use manual or smart approval mode unless this is an isolated throwaway environment."
        ))
    elif cfg:
        findings.append(_finding("approvals.enabled", "approval prompts not obviously disabled", "ok", "info", "medium", f"approvals.mode={mode or 'default/manual'}"))

    security = cfg.get("security") if isinstance(cfg.get("security"), dict) else {}
    redaction = security.get("redact_secrets", True) if isinstance(security, dict) else True
    if redaction is False:
        findings.append(_finding(
            "security.redaction_off", "secret redaction disabled", "fail", "critical", "high",
            "security.redact_secrets is false; tool output/log context may expose secrets to the model.",
            [Evidence(_rel(cfg_path, home), "security.redact_secrets=false", confidence="high")],
            "Re-enable secret redaction before normal use."
        ))
    elif cfg:
        findings.append(_finding("security.redaction_on", "secret redaction not disabled", "ok", "info", "medium", "security.redact_secrets is true or omitted/default."))

    enabled, disabled = _enabled_plugins(cfg)
    both = sorted(set(enabled) & set(disabled))
    if both:
        findings.append(_finding(
            "plugins.conflict", "plugins both enabled and disabled", "warn", "medium", "high",
            "Some plugins are listed in both plugins.enabled and plugins.disabled; disabled wins and can make tools appear missing.",
            [Evidence(_rel(cfg_path, home), ", ".join(redact(x) for x in both), confidence="high")],
            "Remove each plugin from one list so enablement is unambiguous."
        ))

    if enabled:
        findings.append(_finding("plugins.enabled", "enabled plugins configured", "ok", "info", "high", f"{len(enabled)} plugin(s) listed as enabled."))
    else:
        findings.append(_finding("plugins.enabled", "no enabled plugins configured", "unknown", "low", "medium", "No plugins.enabled list was found. This is fine unless you expected a plugin to load."))

    if include_logs:
        evidence = _scan_logs(home, lookback_hours=lookback)
        if evidence:
            findings.append(_finding(
                "logs.recent_issues", "recent warning/error log evidence", "warn", "medium", "medium",
                f"Found {len(evidence)} recent redacted warning/error line(s) in Hermes logs. This is evidence, not root cause by itself.",
                evidence[:20],
                "Review timestamps and adjacent log context before declaring a root cause."
            ))
        else:
            status = "ok" if _log_paths(home) else "unknown"
            findings.append(_finding(
                "logs.recent_issues", "no recent warning/error evidence found" if status == "ok" else "logs unavailable",
                status, "info", "medium",
                "No recent warning/error lines matched in the inspected log tail." if status == "ok" else "No Hermes log files were found, so runtime health cannot be inferred from logs.",
            ))

    return _result("config_audit", home, findings, extra={"config_view_redacted": _safe_config_view(cfg)})


def plugin_check(args: dict[str, Any]) -> dict[str, Any]:
    home = discover_hermes_home(args.get("hermes_home"))
    lookback = int(args.get("lookback_hours") or 24)
    plugin_name = str(args.get("plugin_name") or "").strip().lower()
    cfg = _load_yaml(home / "config.yaml")
    enabled, disabled = _enabled_plugins(cfg)
    findings: list[Finding] = []

    user_plugins = home / "plugins"
    discovered: list[str] = []
    if user_plugins.exists():
        for manifest in user_plugins.glob("*/plugin.yaml"):
            discovered.append(manifest.parent.name)
    if discovered:
        findings.append(_finding(
            "plugins.discovered_user", "user plugins discovered", "ok", "info", "high",
            f"Found {len(discovered)} user plugin directory/directories with plugin.yaml.",
            [Evidence(_rel(user_plugins, home), ", ".join(sorted(redact(x) for x in discovered))[:500], confidence="high")]
        ))
    else:
        findings.append(_finding(
            "plugins.discovered_user", "no user plugin manifests discovered", "unknown", "info", "high",
            "No user plugin directories with plugin.yaml were found. Bundled/pip plugins may still exist."
        ))

    if plugin_name:
        in_enabled = plugin_name in {x.lower() for x in enabled}
        in_disabled = plugin_name in {x.lower() for x in disabled}
        in_user = plugin_name in {x.lower() for x in discovered}
        if in_disabled:
            findings.append(_finding(
                "plugins.target_disabled", f"{plugin_name} disabled", "warn", "medium", "high",
                f"{plugin_name} is explicitly listed under plugins.disabled; it will not load.",
                recommendation=f"Run hermes plugins enable {plugin_name} or edit config.yaml."
            ))
        elif in_enabled:
            findings.append(_finding("plugins.target_enabled", f"{plugin_name} enabled", "ok", "info", "high", f"{plugin_name} is listed under plugins.enabled."))
        elif in_user:
            findings.append(_finding(
                "plugins.target_not_enabled", f"{plugin_name} installed but not enabled", "warn", "medium", "high",
                f"{plugin_name} appears installed in user plugins but is not listed under plugins.enabled.",
                recommendation=f"Run hermes plugins enable {plugin_name}."
            ))
        else:
            findings.append(_finding(
                "plugins.target_not_found", f"{plugin_name} not found", "unknown", "medium", "medium",
                f"{plugin_name} was not found in user plugin manifests or config lists. It may be bundled or pip-installed; run hermes plugins list for authoritative discovery."
            ))

    evidence = _scan_logs(home, lookback_hours=lookback, focus_words=PLUGIN_WORDS)
    if evidence:
        findings.append(_finding(
            "plugins.log_evidence", "recent plugin log warnings/errors", "warn", "medium", "medium",
            f"Found {len(evidence)} recent plugin-related warning/error line(s).",
            evidence[:20],
            "Treat this as triage evidence; inspect adjacent log lines before assigning root cause."
        ))
    else:
        findings.append(_finding("plugins.log_evidence", "no recent plugin warning/error evidence", "ok" if _log_paths(home) else "unknown", "info", "medium", "No recent plugin-related warning/error lines matched."))

    return _result("plugin_check", home, findings, extra={"enabled": enabled, "disabled": disabled, "discovered_user_plugins": sorted(discovered)})


def postmortem(args: dict[str, Any]) -> dict[str, Any]:
    home = discover_hermes_home(args.get("hermes_home"))
    lookback = int(args.get("lookback_hours") or 24)
    max_evidence = int(args.get("max_evidence") or 20)
    title = str(args.get("incident_title") or "Hermes diagnostic incident").strip()
    output_dir = Path(args.get("output_dir") or (home / "doctorpack" / "reports")).expanduser()

    audit = config_audit({"hermes_home": str(home), "lookback_hours": lookback, "include_logs": True})
    plugins = plugin_check({"hermes_home": str(home), "lookback_hours": lookback})
    findings = [_finding_from_dict(x) for x in audit["findings"] + plugins["findings"]]
    evidence: list[Evidence] = []
    for f in findings:
        evidence.extend(f.evidence)
    evidence = evidence[:max_evidence]

    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = _now_utc().strftime("%Y%m%d-%H%M%S")
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", title.lower()).strip("-")[:60] or "incident"
    report_path = output_dir / f"{stamp}-{safe_name}.md"
    report_path.write_text(_render_report(title, home, lookback, findings, evidence), encoding="utf-8")

    out = _result("postmortem", home, findings, extra={"report_path": str(report_path), "evidence_count": len(evidence)})
    out["message"] = "Redacted postmortem report written."
    return out


def _finding_from_dict(data: dict[str, Any]) -> Finding:
    ev = [Evidence(**e) for e in data.get("evidence", [])]
    return Finding(
        id=data["id"], title=data["title"], status=data["status"], severity=data["severity"],
        confidence=data["confidence"], summary=data["summary"], evidence=ev,
        recommendation=data.get("recommendation", ""),
    )


def _result(kind: str, home: Path, findings: list[Finding], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    counts: dict[str, int] = {"ok": 0, "warn": 0, "fail": 0, "unknown": 0}
    for f in findings:
        counts[f.status] = counts.get(f.status, 0) + 1
    overall = "fail" if counts.get("fail") else "warn" if counts.get("warn") else "unknown" if counts.get("unknown") and not counts.get("ok") else "ok"
    payload = {
        "success": True,
        "kind": kind,
        "status": overall,
        "generated_at": _now_utc().isoformat(),
        "host": {"system": platform.system(), "python": sys.version.split()[0], "hostname": redact(socket.gethostname())},
        "hermes_home": str(home),
        "finding_counts": counts,
        "findings": [asdict(f) for f in findings],
        "guarantees": [
            "local-first: no network calls are made",
            "secret/PII redaction is applied before returning evidence",
            "missing evidence is reported as unknown, not fail",
            "log matches are triage evidence, not automatic root-cause claims",
        ],
    }
    if extra:
        payload.update(extra)
    return payload


def _render_report(title: str, home: Path, lookback: int, findings: list[Finding], evidence: list[Evidence]) -> str:
    counts: dict[str, int] = {"ok": 0, "warn": 0, "fail": 0, "unknown": 0}
    for f in findings:
        counts[f.status] = counts.get(f.status, 0) + 1
    lines = [
        f"# {redact(title)}",
        "",
        f"Generated: {_now_utc().isoformat()}",
        "Hermes home: `[REDACTED_HERMES_HOME]`",
        f"Lookback: {lookback}h",
        "",
        "## Executive summary",
        "",
        f"Findings: fail={counts['fail']}, warn={counts['warn']}, unknown={counts['unknown']}, ok={counts['ok']}.",
        "",
        "This report is evidence-backed. `unknown` means Doctorpack lacked evidence; it is not treated as healthy or broken.",
        "",
        "## Findings",
        "",
    ]
    for f in findings:
        lines.extend([
            f"### {f.status.upper()} — {redact(f.title)}",
            "",
            f"- Severity: {f.severity}",
            f"- Confidence: {f.confidence}",
            f"- Summary: {redact(f.summary)}",
        ])
        if f.recommendation:
            lines.append(f"- Recommendation: {redact(f.recommendation)}")
        lines.append("")
        if f.evidence:
            lines.append("Evidence:")
            for e in f.evidence[:5]:
                ts = f" ({e.timestamp})" if e.timestamp else ""
                lines.append(f"- `{redact(e.source)}`{ts}: {redact(e.message)}")
            lines.append("")
    lines.extend(["## Evidence appendix", ""])
    if not evidence:
        lines.append("No log/config evidence snippets were available.")
    for e in evidence:
        ts = f" ({e.timestamp})" if e.timestamp else ""
        lines.append(f"- `{redact(e.source)}`{ts}: {redact(e.message)}")
    lines.extend([
        "",
        "## Difference from built-in Hermes doctor/debug/logs",
        "",
        "- Hermes doctor checks install/runtime prerequisites and config basics.",
        "- /debug packages debug artifacts for support-style inspection.",
        "- Logs expose raw runtime history and require manual interpretation.",
        "- Doctorpack correlates config, plugin state, and recent redacted log evidence into conservative findings and a reusable incident postmortem.",
    ])
    return "\n".join(lines) + "\n"


__all__ = ["config_audit", "plugin_check", "postmortem", "redact", "discover_hermes_home"]
