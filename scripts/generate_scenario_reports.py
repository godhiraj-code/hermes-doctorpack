"""Generate sanitized Doctorpack scenario reports for manual QA/docs.

This script uses temporary fake HERMES_HOME directories. It does not read the
user's real Hermes logs/config and does not call the network.
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hermes_doctorpack.audit import config_audit, plugin_check, postmortem

OUT = ROOT / "docs" / "scenario-reports"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def render_summary(name: str, result: dict) -> str:
    counts = result["finding_counts"]
    lines = [
        f"# Scenario: {name}",
        "",
        f"Kind: `{result['kind']}`",
        f"Status: `{result['status']}`",
        f"Findings: fail={counts['fail']}, warn={counts['warn']}, unknown={counts['unknown']}, ok={counts['ok']}",
        "",
        "## Findings",
        "",
    ]
    for finding in result["findings"]:
        lines.extend([
            f"### {finding['status'].upper()} — {finding['title']}",
            "",
            f"- Severity: {finding['severity']}",
            f"- Confidence: {finding['confidence']}",
            f"- Summary: {finding['summary']}",
        ])
        if finding.get("recommendation"):
            lines.append(f"- Recommendation: {finding['recommendation']}")
        if finding.get("evidence"):
            lines.append("- Evidence:")
            for e in finding["evidence"][:3]:
                ts = f" ({e['timestamp']})" if e.get("timestamp") else ""
                lines.append(f"  - `{e['source']}`{ts}: {e['message']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_scenarios(base: Path):
    clean = base / "clean-home"
    write(clean / "config.yaml", "approvals:\n  mode: manual\nsecurity:\n  redact_secrets: true\nplugins:\n  enabled:\n    - doctorpack\n  disabled: []\n")
    write(clean / "logs" / "agent.log", "2099-01-01T00:00:00Z INFO startup complete\n")

    unsafe = base / "unsafe-config"
    write(unsafe / "config.yaml", "approvals:\n  mode: off\nsecurity:\n  redact_secrets: false\nplugins:\n  enabled: []\n")

    plugin_missing = base / "plugin-installed-not-enabled"
    write(plugin_missing / "config.yaml", "plugins:\n  enabled: []\n  disabled: []\n")
    write(plugin_missing / "plugins" / "doctorpack" / "plugin.yaml", "name: doctorpack\n")

    conflict = base / "plugin-conflict"
    write(conflict / "config.yaml", "plugins:\n  enabled:\n    - doctorpack\n  disabled:\n    - doctorpack\n")
    write(conflict / "plugins" / "doctorpack" / "plugin.yaml", "name: doctorpack\n")

    logs = base / "plugin-log-noise-redacted"
    write(logs / "config.yaml", "approvals:\n  mode: manual\nsecurity:\n  redact_secrets: true\nplugins:\n  enabled:\n    - doctorpack\n")
    write(logs / "plugins" / "doctorpack" / "plugin.yaml", "name: doctorpack\n")
    write(logs / "logs" / "gateway.log", "\n".join([
        "2099-01-01T00:00:00Z ERROR plugin doctorpack register_tool failed token=secret-token",
        "2099-01-01T00:00:01Z WARNING gateway retry for user alice@example.com phone +1-415-555-0137",
    ]))
    return {
        "clean-home": clean,
        "unsafe-config": unsafe,
        "plugin-installed-not-enabled": plugin_missing,
        "plugin-conflict": conflict,
        "plugin-log-noise-redacted": logs,
    }


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="doctorpack-scenarios-") as td:
        scenarios = build_scenarios(Path(td))
        index = ["# Doctorpack scenario QA reports", "", "Generated from temporary fake Hermes homes. No real local Hermes logs are included.", ""]
        for name, home in scenarios.items():
            if name == "plugin-installed-not-enabled":
                result = plugin_check({"hermes_home": str(home), "plugin_name": "doctorpack"})
                summary = render_summary(name, result)
            elif name == "plugin-conflict":
                result = plugin_check({"hermes_home": str(home), "plugin_name": "doctorpack"})
                summary = render_summary(name, result)
            else:
                result = config_audit({"hermes_home": str(home), "lookback_hours": 24})
                summary = render_summary(name, result)
            summary_path = OUT / f"{name}.md"
            summary_path.write_text(summary, encoding="utf-8")
            pm = postmortem({"hermes_home": str(home), "output_dir": str(OUT), "incident_title": name, "lookback_hours": 24})
            generated = Path(pm["report_path"])
            deterministic = OUT / f"{name}-postmortem.md"
            text = generated.read_text(encoding="utf-8")
            text = re.sub(r"^Generated: .*$", "Generated: [SCENARIO_TIMESTAMP]", text, flags=re.MULTILINE)
            deterministic.write_text(text, encoding="utf-8")
            generated.unlink()
            index.append(f"- [{name}]({summary_path.name}) — status `{result['status']}`; postmortem `{deterministic.name}`")
        (OUT / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print(f"Wrote scenario reports to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
