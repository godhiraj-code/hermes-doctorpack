import datetime as dt
import json
from pathlib import Path

import pytest

import hermes_doctorpack
from hermes_doctorpack.audit import config_audit, plugin_check, postmortem, redact
from hermes_doctorpack.cli import doctorpack_command


@pytest.mark.parametrize("raw", [
    '{"api_key": "synthetic-private-value"}',
    "password='synthetic private value'",
    "Authorization: Bearer synthetic-private-value",
    "Authorization: Basic synthetic-private-value",
    '{"Authorization": "Bearer synthetic-private-value"}',
    "Bearer synthetic-private-value",
    "github_pat_synthetic_private_value_123456789",
])
def test_quoted_secrets_and_authorization(raw):
    result = redact(raw)
    assert "synthetic" not in result
    assert "[REDACTED]" in result


@pytest.mark.parametrize("raw", [
    json.dumps({"password": 'prefix"synthetic-tail'}),
    json.dumps({"password": r"prefix\synthetic-tail"}),
    "password='prefix''synthetic-tail'",
    'password="unterminated synthetic-tail',
    'password="synthetic-tail\nnext safe log line',
    'password="synthetic-tail' + "\\",
    'password="synthetic-tail' + "\\\nnext safe log line",
    "password='synthetic-tail" + "\\\r\nnext safe log line",
    'password="synthetic-tail' + "\\\r",
    'password="synthetic-tail' + "\\\rnext safe log line",
])
def test_escaped_and_truncated_quoted_values(raw):
    result = redact(raw)
    assert "synthetic-tail" not in result
    assert "[REDACTED]" in result
    if "next safe log line" in raw:
        assert "next safe log line" in result


def test_quoted_redaction_preserves_following_fields():
    raw = json.dumps({"password": 'prefix"synthetic-tail', "status": "healthy"})
    assert '"status": "healthy"' in redact(raw)
    assert json.loads(redact(raw)) == {"password": "[REDACTED]", "status": "healthy"}


@pytest.mark.parametrize("suffix", ["|status=healthy", "&retry=true", "/safe/KEEP"])
def test_quoted_redaction_preserves_adjacent_safe_suffix(tmp_path, suffix):
    raw = '2099-01-01T00:00:00Z ERROR plugin password="synthetic-private"' + suffix
    assert suffix in redact(raw)
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "agent.log").write_text(raw, encoding="utf-8")
    result = config_audit({"hermes_home": str(tmp_path)})
    evidence = next(f for f in result["findings"] if f["id"] == "logs.recent_issues")["evidence"]
    assert suffix in evidence[0]["message"]
    assert "synthetic-private" not in json.dumps(result)


@pytest.fixture
def synthetic_home(tmp_path):
    config = {
        "model": {
            "token=synthetic-key-secret": "private value",
            "authorization": "synthetic-authorization-field",
            "passwd": "synthetic-passwd-field",
            "nested": [{"PWD": "synthetic-pwd-field", "status": "healthy"}],
            "endpoint": "https://example.invalid",
            "context_window": 4096,
        },
        "approvals": {"mode": "token=synthetic-mode-value"},
        "plugins": {
            "enabled": ["doctorpack", "token=synthetic-enabled-value"],
            "disabled": ["token=synthetic-disabled-value"],
        },
    }
    # JSON is also YAML; only synthetic fixtures under pytest's temporary home.
    (tmp_path / "config.yaml").write_text(json.dumps(config), encoding="utf-8")
    logs = tmp_path / "logs"
    logs.mkdir()
    lines = [
        json.dumps({"password": 'prefix"synthetic-quoted-tail', "status": "healthy"}),
        "Authorization: Bearer synthetic-bearer-value",
        "Authorization: Basic synthetic-basic-value",
        "Bearer synthetic-standalone-value",
        "github_pat_synthetic_private_value_123456789",
        'password="synthetic-truncated-tail' + "\\",
        "status=healthy",
    ]
    (logs / "agent.log").write_text(
        "\n".join(f"2099-01-01T00:00:00Z ERROR plugin {line}" for line in lines),
        encoding="utf-8",
    )
    plugin_dir = tmp_path / "plugins" / "token=synthetic-discovered-value"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text("name: example\n", encoding="utf-8")
    return tmp_path


def _tool_args(home):
    return {
        "hermes_home": str(home),
        "plugin_name": "token=synthetic-target-value",
        "incident_title": "token=synthetic-incident-value",
        "output_dir": str(home / "reports"),
    }


def _assert_safe_result(result):
    # Inspect the entire JSON response, not only the evidence collection.
    assert "synthetic-" not in json.dumps(result)
    assert "synthetic_private" not in json.dumps(result)
    assert result["success"] is True
    assert "healthy" in json.dumps(result)
    if result["kind"] == "config_audit":
        model = result["config_view_redacted"]["model"]
        assert model["token=[REDACTED]"] == "[REDACTED]"
        assert model["authorization"] == "[REDACTED]"
        assert model["passwd"] == "[REDACTED]"
        assert model["nested"] == [{"PWD": "[REDACTED]", "status": "healthy"}]
        assert model["endpoint"] == "https://example.invalid"
        assert model["context_window"] == 4096
    if result["kind"] == "plugin_check":
        assert "doctorpack" in result["enabled"]
    if result["kind"] == "postmortem":
        report = Path(result["report_path"])
        assert report.is_file()
        text = report.read_text(encoding="utf-8")
        assert "synthetic-" not in text
        assert "synthetic_private" not in text
        assert "healthy" in text


@pytest.mark.parametrize("diagnostic", [config_audit, plugin_check, postmortem])
def test_diagnostics_redact_entire_results(synthetic_home, diagnostic):
    _assert_safe_result(diagnostic(_tool_args(synthetic_home)))


class ToolContext:
    """Capture public handlers for output regression tests, not catalog validation."""

    def __init__(self):
        self.handlers = {}

    def register_tool(self, **kwargs):
        self.handlers[kwargs["name"]] = kwargs["handler"]

    def register_command(self, *args, **kwargs):
        pass

    def register_cli_command(self, **kwargs):
        pass


@pytest.fixture
def registered_handlers():
    context = ToolContext()
    hermes_doctorpack.register(context)
    return context.handlers


@pytest.mark.parametrize("name", ["config_audit", "plugin_check", "postmortem"])
def test_registered_handlers_redact_entire_json(synthetic_home, registered_handlers, name, monkeypatch):
    args = _tool_args(synthetic_home)
    if name == "postmortem":
        monkeypatch.setattr(hermes_doctorpack, "discover_hermes_home", lambda: synthetic_home)
        args = {"incident_title": args["incident_title"]}
    raw = registered_handlers[f"doctorpack_{name}"](args)
    assert "synthetic-" not in raw
    assert "synthetic_private" not in raw
    _assert_safe_result(json.loads(raw))


@pytest.mark.parametrize("target", ["enabled", "disabled", "discovered", "missing"])
def test_plugin_target_findings_are_redacted(synthetic_home, target):
    name = f"token=synthetic-{target}-value"
    result = plugin_check({"hermes_home": str(synthetic_home), "plugin_name": name})
    assert "synthetic-" not in json.dumps(result)
    assert any(f["id"].startswith("plugins.target_") for f in result["findings"])


@pytest.mark.parametrize("name", ["config_audit", "plugin_check", "postmortem"])
def test_registered_error_json_redacts_parser_snippets(tmp_path, registered_handlers, name, monkeypatch):
    (tmp_path / "config.yaml").write_text(
        'model:\n  authorization: "synthetic-parser-value\n', encoding="utf-8",
    )
    args = _tool_args(tmp_path)
    if name == "postmortem":
        monkeypatch.setattr(hermes_doctorpack, "discover_hermes_home", lambda: tmp_path)
        args = {"incident_title": args["incident_title"]}
    raw = registered_handlers[f"doctorpack_{name}"](args)
    assert "synthetic-parser-value" not in raw
    result = json.loads(raw)
    assert result["success"] is False
    assert result["error"] == "doctorpack_internal_error"
    assert "[REDACTED]" in result["message"]


def test_masked_mapping_keys_preserve_all_values_and_safe_neighbor_keys(tmp_path):
    routes = {
        "synthetic-one@example.invalid": {"status": "healthy"},
        "synthetic-two@example.invalid": {"status": "degraded"},
        "[REDACTED_EMAIL]": {"status": "safe-original"},
        "[REDACTED_EMAIL] (2)": {"status": "safe-suffix"},
    }
    (tmp_path / "config.yaml").write_text(json.dumps({"gateway": {"routes": routes}}), encoding="utf-8")
    # This traverses both the config view and complete-result redaction passes.
    result = config_audit({"hermes_home": str(tmp_path), "include_logs": False})
    safe_routes = result["config_view_redacted"]["gateway"]["routes"]
    assert len(safe_routes) == len(routes)
    assert {value["status"] for value in safe_routes.values()} == {
        "healthy", "degraded", "safe-original", "safe-suffix",
    }
    assert safe_routes["[REDACTED_EMAIL]"] == routes["[REDACTED_EMAIL]"]
    assert safe_routes["[REDACTED_EMAIL] (2)"] == routes["[REDACTED_EMAIL] (2)"]
    assert "synthetic-" not in json.dumps(result)


def test_redacted_titles_never_overwrite_an_existing_report(tmp_path, monkeypatch):
    now = dt.datetime(2026, 10, 11, 12, 0, tzinfo=dt.timezone.utc)
    monkeypatch.setattr("hermes_doctorpack.audit._now_utc", lambda: now)
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "agent.log").write_text("ERROR first safe incident", encoding="utf-8")
    first = postmortem({"hermes_home": str(tmp_path), "incident_title": "Gateway token=synthetic-first"})
    first_text = Path(first["report_path"]).read_text(encoding="utf-8")
    (logs / "agent.log").write_text("ERROR second safe incident", encoding="utf-8")
    second = postmortem({"hermes_home": str(tmp_path), "incident_title": "Gateway token=synthetic-second"})
    assert first["report_path"] != second["report_path"]
    assert Path(first["report_path"]).read_text(encoding="utf-8") == first_text
    assert "first safe incident" in first_text
    assert "second safe incident" in Path(second["report_path"]).read_text(encoding="utf-8")
    assert "synthetic-" not in json.dumps([first, second])
    assert first["report_path_redacted"] is False


def test_masked_report_directory_returns_usable_filename(tmp_path):
    output_dir = tmp_path / "synthetic-person@example.invalid"
    result = postmortem({"hermes_home": str(tmp_path), "output_dir": str(output_dir)})
    assert result["report_path_redacted"] is True
    assert "synthetic-person" not in json.dumps(result)
    assert Path(result["report_filename"]).name == result["report_filename"]
    assert (output_dir / result["report_filename"]).is_file()
    summary = doctorpack_command(
        f'postmortem --hermes-home "{tmp_path}" --output-dir "{output_dir}"'
    )
    assert "Report filename:" in summary
    assert "selected output directory" in summary
    assert "synthetic-person" not in summary


@pytest.mark.parametrize("title", ["sk abcdefghijklmnopqrstuv", "Incident 415/555/0137"])
def test_normalized_report_filename_remains_usable(tmp_path, title):
    output_dir = tmp_path / "reports"
    result = postmortem({"hermes_home": str(tmp_path), "output_dir": str(output_dir), "incident_title": title})
    assert result["report_path_redacted"] is False
    assert Path(result["report_path"]).is_file()
    assert (output_dir / result["report_filename"]).is_file()
