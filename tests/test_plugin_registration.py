import json

import hermes_doctorpack


class FakeContext:
    def __init__(self):
        self.tools = {}
        self.commands = {}
        self.cli = {}

    def register_tool(self, **kwargs):
        self.tools[kwargs["name"]] = kwargs

    def register_command(self, name, handler, description="", args_hint=""):
        self.commands[name] = {"handler": handler, "description": description, "args_hint": args_hint}

    def register_cli_command(self, **kwargs):
        self.cli[kwargs["name"]] = kwargs


def test_register_exposes_tools_command_and_cli():
    ctx = FakeContext()
    hermes_doctorpack.register(ctx)
    assert set(ctx.tools) == {"doctorpack_config_audit", "doctorpack_plugin_check", "doctorpack_postmortem"}
    assert "doctorpack" in ctx.commands
    assert "doctorpack" in ctx.cli


def test_tool_handler_returns_json_string(tmp_path):
    ctx = FakeContext()
    hermes_doctorpack.register(ctx)
    handler = ctx.tools["doctorpack_config_audit"]["handler"]
    raw = handler({"hermes_home": str(tmp_path), "include_logs": False})
    parsed = json.loads(raw)
    assert parsed["success"] is True
    assert parsed["kind"] == "config_audit"
