# Scenario: plugin-log-noise-redacted

Kind: `config_audit`
Status: `warn`
Findings: fail=0, warn=1, unknown=0, ok=4

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

### WARN — recent warning/error log evidence

- Severity: medium
- Confidence: medium
- Summary: Found 2 recent redacted warning/error line(s) in Hermes logs. This is evidence, not root cause by itself.
- Recommendation: Review timestamps and adjacent log context before declaring a root cause.
- Evidence:
  - `logs/gateway.log` (2099-01-01T00:00:00+00:00): 2099-01-01T00:00:00Z ERROR plugin doctorpack register_tool failed token=[REDACTED]
  - `logs/gateway.log` (2099-01-01T00:00:01+00:00): 2099-01-01T00:00:01Z WARNING gateway retry for user [REDACTED_EMAIL] phone [REDACTED_PHONE]
