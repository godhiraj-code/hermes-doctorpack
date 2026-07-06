"""Tool schemas for Hermes Doctorpack."""

_COMMON_PROPS = {
    "hermes_home": {
        "type": "string",
        "description": "Optional Hermes home directory to inspect. Defaults to active HERMES_HOME or standard Hermes home.",
    },
    "lookback_hours": {
        "type": "integer",
        "minimum": 1,
        "maximum": 168,
        "description": "How far back recent log evidence should count. Default 24.",
    },
}

CONFIG_AUDIT_SCHEMA = {
    "name": "doctorpack_config_audit",
    "description": (
        "Audit local Hermes configuration, profile, approval, gateway, cron, MCP, and recent logs. "
        "Returns redacted evidence-backed findings with ok/warn/fail/unknown states. "
        "Use when Hermes seems misconfigured, unsafe, or unreliable."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            **_COMMON_PROPS,
            "include_logs": {
                "type": "boolean",
                "description": "Include redacted recent agent/gateway/error log evidence. Default true.",
            },
        },
    },
}

PLUGIN_CHECK_SCHEMA = {
    "name": "doctorpack_plugin_check",
    "description": (
        "Inspect Hermes plugin configuration and recent plugin-related logs. "
        "Use when a plugin is installed but not loading, tools are missing, or plugin errors are suspected."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            **_COMMON_PROPS,
            "plugin_name": {
                "type": "string",
                "description": "Optional plugin name to focus on, e.g. doctorpack.",
            },
        },
    },
}

POSTMORTEM_SCHEMA = {
    "name": "doctorpack_postmortem",
    "description": (
        "Create a local redacted incident postmortem from Hermes logs/config evidence. "
        "Writes a Markdown report and returns the report path plus structured findings."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            **_COMMON_PROPS,
            "incident_title": {
                "type": "string",
                "description": "Short incident title. Default: Hermes diagnostic incident.",
            },
            "output_dir": {
                "type": "string",
                "description": "Directory where the Markdown report should be written. Defaults to HERMES_HOME/doctorpack/reports.",
            },
            "max_evidence": {
                "type": "integer",
                "minimum": 1,
                "maximum": 50,
                "description": "Maximum redacted evidence snippets to include. Default 20.",
            },
        },
    },
}
