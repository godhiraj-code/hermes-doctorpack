"""Hermes Doctorpack plugin registration."""

from __future__ import annotations

import json
from typing import Any

from .audit import config_audit, plugin_check, postmortem
from .schemas import CONFIG_AUDIT_SCHEMA, PLUGIN_CHECK_SCHEMA, POSTMORTEM_SCHEMA


def _json_handler(fn):
    def _handle(args: dict[str, Any] | None = None, **kwargs: Any) -> str:
        del kwargs
        try:
            return json.dumps(fn(args or {}), ensure_ascii=False, indent=2)
        except Exception as exc:  # defensive: tool handlers must not throw into Hermes loop
            return json.dumps(
                {
                    "success": False,
                    "status": "error",
                    "error": "doctorpack_internal_error",
                    "message": str(exc),
                },
                ensure_ascii=False,
            )

    return _handle


def _handle_slash(raw_args: str = "") -> str:
    from .cli import doctorpack_command

    return doctorpack_command(raw_args)


def register(ctx) -> None:
    """Register Doctorpack tools, slash command, and CLI command."""
    from .cli import doctorpack_command, register_cli

    ctx.register_tool(
        name="doctorpack_config_audit",
        toolset="doctorpack",
        schema=CONFIG_AUDIT_SCHEMA,
        handler=_json_handler(config_audit),
        description="Audit local Hermes config/log safety with redacted evidence.",
        emoji="🩺",
    )
    ctx.register_tool(
        name="doctorpack_plugin_check",
        toolset="doctorpack",
        schema=PLUGIN_CHECK_SCHEMA,
        handler=_json_handler(plugin_check),
        description="Inspect Hermes plugin enablement and recent plugin log errors.",
        emoji="🔌",
    )
    ctx.register_tool(
        name="doctorpack_postmortem",
        toolset="doctorpack",
        schema=POSTMORTEM_SCHEMA,
        handler=_json_handler(postmortem),
        description="Generate a local redacted Hermes incident postmortem report.",
        emoji="📋",
    )
    ctx.register_command(
        "doctorpack",
        handler=_handle_slash,
        description="Run local Hermes diagnostics and redacted postmortem checks.",
        args_hint="scan|plugins|postmortem",
    )
    ctx.register_cli_command(
        name="doctorpack",
        help="Hermes Doctorpack diagnostics",
        setup_fn=register_cli,
        handler_fn=doctorpack_command,
        description="Local-first diagnostics, safety audit, and postmortems for Hermes Agent.",
    )
