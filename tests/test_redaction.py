import json
from pathlib import Path

import pytest

import hermes_doctorpack
from hermes_doctorpack.audit import config_audit, plugin_check, postmortem, redact


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
def test_registered_handlers_redact_entire_json(synthetic_home, registered_handlers, name):
    raw = registered_handlers[f"doctorpack_{name}"](_tool_args(synthetic_home))
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
def test_registered_error_json_redacts_parser_snippets(tmp_path, registered_handlers, name):
    (tmp_path / "config.yaml").write_text(
        'model:\n  authorization: "synthetic-parser-value\n', encoding="utf-8",
    )
    raw = registered_handlers[f"doctorpack_{name}"](_tool_args(tmp_path))
    assert "synthetic-parser-value" not in raw
    result = json.loads(raw)
    assert result["success"] is False
    assert result["error"] == "doctorpack_internal_error"
    assert "[REDACTED]" in result["message"]
