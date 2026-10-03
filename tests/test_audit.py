import json
import pytest
from pathlib import Path

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
def test_redaction_covers_quoted_secrets_and_authorization(raw):
    result = redact(raw)
    assert "synthetic" not in result
    assert "[REDACTED]" in result


@pytest.mark.parametrize("raw", [
    json.dumps({"password": 'prefix"synthetic-tail'}),
    json.dumps({"password": r"prefix\synthetic-tail"}),
    "password='prefix''synthetic-tail'",
    'password="unterminated synthetic-tail',
    'password="synthetic-tail\nnext safe log line',
])
def test_redaction_consumes_escaped_and_truncated_quoted_values(raw):
    result = redact(raw)
    assert "synthetic-tail" not in result
    assert "[REDACTED]" in result


def test_quoted_redaction_preserves_following_log_fields():
    raw = json.dumps({"password": 'prefix"synthetic-tail', "status": "healthy"})
    assert '"status": "healthy"' in redact(raw)


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_redacts_secrets_email_phone_and_url_credentials():
    raw = "api_key: sk-abcdefghijklmnopqrstuv user=a@example.com phone +1-415-555-0137 url=https://user:pass@example.com/x"
    out = redact(raw)
    assert "sk-" not in out
    assert "a@example.com" not in out
    assert "415-555" not in out
    assert "user:pass" not in out
    assert "[REDACTED" in out


def test_redaction_preserves_iso_timestamps():
    raw = "2026-07-06T10:54:04.590000+00:00 ERROR something failed"
    out = redact(raw)
    assert "2026-07-06T10:54:04" in out


def test_missing_config_is_unknown_not_fail(tmp_path):
    result = config_audit({"hermes_home": str(tmp_path), "include_logs": False})
    by_id = {f["id"]: f for f in result["findings"]}
    assert by_id["config.present"]["status"] == "unknown"
    assert result["finding_counts"]["fail"] == 0


def test_old_timestamped_log_error_does_not_create_recent_warning(tmp_path):
    write(tmp_path / "config.yaml", "security:\n  redact_secrets: true\napprovals:\n  mode: manual\n")
    write(tmp_path / "logs" / "agent.log", "2020-01-01T00:00:00Z ERROR ancient failure\n")
    result = config_audit({"hermes_home": str(tmp_path), "lookback_hours": 1, "include_logs": True})
    finding = {f["id"]: f for f in result["findings"]}["logs.recent_issues"]
    assert finding["status"] == "ok"
    assert "ancient" not in json.dumps(finding)


def test_recent_log_secret_is_redacted_in_evidence(tmp_path):
    write(tmp_path / "config.yaml", "security:\n  redact_secrets: true\napprovals:\n  mode: manual\n")
    write(tmp_path / "logs" / "agent.log", "2099-01-01T00:00:00Z ERROR token=super-secret-token failed\n")
    result = config_audit({"hermes_home": str(tmp_path), "lookback_hours": 24, "include_logs": True})
    dumped = json.dumps(result)
    assert "super-secret-token" not in dumped
    assert "[REDACTED]" in dumped


def test_plugin_installed_but_not_enabled_is_warn_not_fail(tmp_path):
    write(tmp_path / "config.yaml", "plugins:\n  enabled: []\n  disabled: []\n")
    write(tmp_path / "plugins" / "doctorpack" / "plugin.yaml", "name: doctorpack\n")
    result = plugin_check({"hermes_home": str(tmp_path), "plugin_name": "doctorpack"})
    by_id = {f["id"]: f for f in result["findings"]}
    assert by_id["plugins.target_not_enabled"]["status"] == "warn"
    assert result["finding_counts"]["fail"] == 0


def test_redaction_disabled_is_direct_fail(tmp_path):
    write(tmp_path / "config.yaml", "security:\n  redact_secrets: false\n")
    result = config_audit({"hermes_home": str(tmp_path), "include_logs": False})
    by_id = {f["id"]: f for f in result["findings"]}
    assert by_id["security.redaction_off"]["status"] == "fail"


def test_postmortem_writes_markdown_report(tmp_path):
    write(tmp_path / "config.yaml", "security:\n  redact_secrets: true\napprovals:\n  mode: manual\n")
    out_dir = tmp_path / "reports"
    result = postmortem({"hermes_home": str(tmp_path), "output_dir": str(out_dir), "incident_title": "Test Incident"})
    report = Path(result["report_path"])
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Test Incident" in text
    assert "[REDACTED_HERMES_HOME]" in text
    assert str(tmp_path) not in text
    assert "Difference from built-in Hermes doctor/debug/logs" in text
