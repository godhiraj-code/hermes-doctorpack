import json
from pathlib import Path
import shlex
import sys
import types

import pytest

import hermes_doctorpack
from hermes_doctorpack.audit import discover_hermes_home


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


@pytest.fixture
def active_home(tmp_path, monkeypatch):
    home = tmp_path / "profile"
    home.mkdir()
    constants = types.ModuleType("hermes_constants")
    constants.get_hermes_home = lambda: home
    monkeypatch.setitem(sys.modules, "hermes_constants", constants)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "launch-home"))
    return home


def _postmortem_handler():
    ctx = FakeContext()
    hermes_doctorpack.register(ctx)
    return ctx.tools["doctorpack_postmortem"]["handler"]


@pytest.mark.parametrize("key", ["output_dir", "hermes_home", "unexpected"])
@pytest.mark.parametrize("value", ["outside", "../outside"])
def test_model_postmortem_rejects_path_and_unknown_arguments(active_home, tmp_path, key, value):
    outside = tmp_path / "outside"
    requested = str(outside) if value == "outside" else str(active_home / value)
    result = json.loads(_postmortem_handler()({key: requested}))
    assert result["success"] is False
    assert not outside.exists()
    assert not (active_home / "doctorpack").exists()


def test_model_postmortem_writes_only_to_active_profile(active_home, tmp_path):
    args = {"incident_title": "Safe incident", "lookback_hours": 24, "max_evidence": 5}
    result = json.loads(_postmortem_handler()(args))
    assert result["success"] is True
    report = Path(result["report_path"])
    assert report.parent == active_home / "doctorpack" / "reports"
    assert report.is_file()
    assert not (tmp_path / "launch-home").exists()
    assert args == {"incident_title": "Safe incident", "lookback_hours": 24, "max_evidence": 5}


@pytest.mark.parametrize("args", [[], ["invalid"], "invalid"])
def test_model_postmortem_requires_an_argument_object(active_home, args):
    result = json.loads(_postmortem_handler()(args))
    assert result["success"] is False
    assert not (active_home / "doctorpack").exists()


@pytest.mark.parametrize("component", ["doctorpack", "reports"])
def test_model_postmortem_refuses_symlinked_report_directories(active_home, tmp_path, component):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = active_home / "doctorpack"
    if component == "reports":
        link.mkdir()
        link = link / "reports"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Directory symlinks unavailable: {exc}")
    result = json.loads(_postmortem_handler()({"incident_title": "Safe incident"}))
    assert result["success"] is False
    assert list(outside.iterdir()) == []


def test_model_postmortem_schema_excludes_paths():
    ctx = FakeContext()
    hermes_doctorpack.register(ctx)
    parameters = ctx.tools["doctorpack_postmortem"]["schema"]["parameters"]
    assert "output_dir" not in parameters["properties"]
    assert "hermes_home" not in parameters["properties"]
    assert parameters["additionalProperties"] is False


def test_profile_home_precedes_launch_environment(active_home):
    assert discover_hermes_home() == active_home


def test_standalone_home_falls_back_to_environment(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "hermes_constants", None)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "standalone"))
    assert discover_hermes_home() == tmp_path / "standalone"


def test_user_cli_and_slash_keep_explicit_home_and_output(active_home, tmp_path):
    ctx = FakeContext()
    hermes_doctorpack.register(ctx)
    explicit_home = tmp_path / "selected-home"
    explicit_home.mkdir()
    for surface, output_name in [(ctx.commands["doctorpack"]["handler"], "slash-output"),
                                 (ctx.cli["doctorpack"]["handler_fn"], "cli-output")]:
        output = tmp_path / output_name
        command = shlex.join(["postmortem", "--hermes-home", str(explicit_home),
                              "--output-dir", str(output), "--json"])
        result = json.loads(surface(command))
        assert result["success"] is True
        assert Path(result["report_path"]).parent == output
        assert Path(result["report_path"]).is_file()
        assert result["hermes_home"] == str(explicit_home)
    assert not (active_home / "doctorpack").exists()
