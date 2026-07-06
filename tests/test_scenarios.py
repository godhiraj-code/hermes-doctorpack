import json
from pathlib import Path

from hermes_doctorpack.audit import config_audit, plugin_check, postmortem
from hermes_doctorpack.cli import doctorpack_command


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def ids(result):
    return {f["id"]: f for f in result["findings"]}


def test_clean_home_with_logs_reports_ok_not_warn(tmp_path):
    write(tmp_path / "config.yaml", "approvals:\n  mode: manual\nsecurity:\n  redact_secrets: true\nplugins:\n  enabled:\n    - doctorpack\n  disabled: []\n")
    write(tmp_path / "logs" / "agent.log", "2099-01-01T00:00:00Z INFO normal startup\n")
    result = config_audit({"hermes_home": str(tmp_path), "lookback_hours": 24})
    by_id = ids(result)
    assert result["status"] == "ok"
    assert by_id["logs.recent_issues"]["status"] == "ok"


def test_unsafe_config_redaction_off_and_approvals_off_are_flagged(tmp_path):
    write(tmp_path / "config.yaml", "approvals:\n  mode: off\nsecurity:\n  redact_secrets: false\nplugins:\n  enabled: []\n")
    result = config_audit({"hermes_home": str(tmp_path), "include_logs": False})
    by_id = ids(result)
    assert result["status"] == "fail"
    assert by_id["security.redaction_off"]["status"] == "fail"
    assert by_id["approvals.disabled"]["status"] == "warn"


def test_plugin_enabled_disabled_conflict_is_warn_and_disabled_wins(tmp_path):
    write(tmp_path / "config.yaml", "plugins:\n  enabled:\n    - doctorpack\n  disabled:\n    - doctorpack\n")
    write(tmp_path / "plugins" / "doctorpack" / "plugin.yaml", "name: doctorpack\n")
    audit = config_audit({"hermes_home": str(tmp_path), "include_logs": False})
    check = plugin_check({"hermes_home": str(tmp_path), "plugin_name": "doctorpack"})
    assert ids(audit)["plugins.conflict"]["status"] == "warn"
    assert ids(check)["plugins.target_disabled"]["status"] == "warn"


def test_plugin_not_found_is_unknown_not_failure(tmp_path):
    write(tmp_path / "config.yaml", "plugins:\n  enabled: []\n  disabled: []\n")
    result = plugin_check({"hermes_home": str(tmp_path), "plugin_name": "missing-plugin"})
    by_id = ids(result)
    assert by_id["plugins.target_not_found"]["status"] == "unknown"
    assert result["finding_counts"]["fail"] == 0


def test_timestamp_less_tail_log_warning_is_medium_confidence(tmp_path):
    write(tmp_path / "config.yaml", "approvals:\n  mode: manual\nsecurity:\n  redact_secrets: true\n")
    write(tmp_path / "logs" / "gateway.log", "WARNING gateway timeout while retrying delivery\n")
    result = config_audit({"hermes_home": str(tmp_path), "lookback_hours": 1})
    finding = ids(result)["logs.recent_issues"]
    assert finding["status"] == "warn"
    assert finding["evidence"][0]["timestamp"] is None
    assert finding["evidence"][0]["confidence"] == "medium"


def test_plugin_log_scan_focuses_plugin_related_evidence(tmp_path):
    write(tmp_path / "config.yaml", "plugins:\n  enabled:\n    - doctorpack\n")
    write(tmp_path / "logs" / "gateway.log", "2099-01-01T00:00:00Z ERROR generic gateway failed\n2099-01-01T00:00:01Z ERROR plugin doctorpack register_tool failed\n")
    result = plugin_check({"hermes_home": str(tmp_path), "plugin_name": "doctorpack", "lookback_hours": 24})
    evidence = ids(result)["plugins.log_evidence"]["evidence"]
    dumped = json.dumps(evidence)
    assert "register_tool failed" in dumped
    assert "generic gateway failed" not in dumped


def test_postmortem_report_redacts_secrets_and_honors_max_evidence(tmp_path):
    write(tmp_path / "config.yaml", "approvals:\n  mode: manual\nsecurity:\n  redact_secrets: true\nplugins:\n  enabled:\n    - doctorpack\n")
    write(tmp_path / "logs" / "agent.log", "\n".join([
        "2099-01-01T00:00:00Z ERROR token=super-secret failed",
        "2099-01-01T00:00:01Z WARNING plugin doctorpack retry api_key=another-secret",
        "2099-01-01T00:00:02Z ERROR password=bad failed",
    ]))
    result = postmortem({"hermes_home": str(tmp_path), "output_dir": str(tmp_path / "reports"), "incident_title": "Secret Leak Test", "max_evidence": 1})
    text = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "super-secret" not in text
    assert "another-secret" not in text
    assert "password=bad" not in text
    assert "[REDACTED]" in text
    assert result["evidence_count"] == 1


def test_slash_command_parses_quoted_incident_title(tmp_path):
    out_dir = tmp_path / "reports"
    write(tmp_path / "config.yaml", "approvals:\n  mode: manual\nsecurity:\n  redact_secrets: true\n")
    output = doctorpack_command(f'postmortem --hermes-home "{tmp_path}" --output-dir "{out_dir}" --incident-title "Gateway Delivery Timeout"')
    assert "Doctorpack postmortem status:" in output
    assert "gateway-delivery-timeout" in output.lower()
    assert list(out_dir.glob("*gateway-delivery-timeout.md"))
