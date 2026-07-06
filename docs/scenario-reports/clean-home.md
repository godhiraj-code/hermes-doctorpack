# Scenario: clean-home

Kind: `config_audit`
Status: `ok`
Findings: fail=0, warn=0, unknown=0, ok=5

## Findings

### OK — config.yaml present

- Severity: info
- Confidence: high
- Summary: Found Hermes config.yaml.
- Evidence:
  - `config.yaml`: config file exists

### OK — approval prompts not obviously disabled

- Severity: info
- Confidence: medium
- Summary: approvals.mode=manual

### OK — secret redaction not disabled

- Severity: info
- Confidence: medium
- Summary: security.redact_secrets is true or omitted/default.

### OK — enabled plugins configured

- Severity: info
- Confidence: high
- Summary: 1 plugin(s) listed as enabled.

### OK — no recent warning/error evidence found

- Severity: info
- Confidence: medium
- Summary: No recent warning/error lines matched in the inspected log tail.
