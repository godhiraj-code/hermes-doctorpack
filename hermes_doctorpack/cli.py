"""CLI and slash-command helpers for Doctorpack."""

from __future__ import annotations

import argparse
import json
import shlex
from typing import Any

from .audit import config_audit, plugin_check, postmortem


def register_cli(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("subcommand", nargs="?", default="scan", choices=["scan", "plugins", "postmortem"])
    parser.add_argument("--hermes-home", default=None)
    parser.add_argument("--lookback-hours", type=int, default=24)
    parser.add_argument("--incident-title", default="Hermes diagnostic incident")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--plugin-name", default=None)
    parser.add_argument("--json", action="store_true", help="Emit raw JSON instead of summary text")


def _run(ns: argparse.Namespace) -> dict[str, Any]:
    args = {"hermes_home": ns.hermes_home, "lookback_hours": ns.lookback_hours}
    if ns.subcommand == "plugins":
        if ns.plugin_name:
            args["plugin_name"] = ns.plugin_name
        return plugin_check(args)
    if ns.subcommand == "postmortem":
        args.update({"incident_title": ns.incident_title, "output_dir": ns.output_dir})
        return postmortem(args)
    return config_audit({**args, "include_logs": True})


def _summarize(result: dict[str, Any]) -> str:
    counts = result.get("finding_counts") or {}
    lines = [
        f"Doctorpack {result.get('kind')} status: {result.get('status')}",
        f"Hermes home: {result.get('hermes_home')}",
        f"Findings: fail={counts.get('fail', 0)} warn={counts.get('warn', 0)} unknown={counts.get('unknown', 0)} ok={counts.get('ok', 0)}",
    ]
    if result.get("report_path"):
        lines.append(f"Report: {result['report_path']}")
    lines.append("")
    for f in result.get("findings", [])[:12]:
        lines.append(f"[{f['status']}] {f['title']} — {f['summary']}")
        if f.get("recommendation"):
            lines.append(f"  fix: {f['recommendation']}")
    return "\n".join(lines)


def doctorpack_command(raw_args: str | argparse.Namespace = "") -> str:
    if isinstance(raw_args, argparse.Namespace):
        result = _run(raw_args)
        return json.dumps(result, indent=2, ensure_ascii=False) if getattr(raw_args, "json", False) else _summarize(result)

    try:
        argv = shlex.split(str(raw_args or ""))
    except ValueError as exc:
        return f"Usage: /doctorpack [scan|plugins|postmortem] [--lookback-hours N]\nParse error: {exc}"
    parser = argparse.ArgumentParser(prog="doctorpack", add_help=False)
    register_cli(parser)
    try:
        ns = parser.parse_args(argv)
    except SystemExit:
        return "Usage: /doctorpack [scan|plugins|postmortem] [--lookback-hours N]"
    result = _run(ns)
    return json.dumps(result, indent=2, ensure_ascii=False) if ns.json else _summarize(result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hermes-doctorpack")
    register_cli(parser)
    ns = parser.parse_args(argv)
    print(doctorpack_command(ns))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
