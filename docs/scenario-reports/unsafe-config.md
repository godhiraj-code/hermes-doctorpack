# Scenario: unsafe-config

Kind: `config_audit`
Status: `fail`
Findings: fail=1, warn=1, unknown=2, ok=1

## Findings

### OK — config.yaml present

- Severity: info
- Confidence: high
- Summary: Found Hermes config.yaml.
- Evidence:
  - `config.yaml`: config file exists

### WARN — approval prompts disabled

- Severity: high
- Confidence: high
- Summary: approvals.mode appears to disable command approval prompts.
- Recommendation: Use manual or smart approval mode unless this is an isolated throwaway environment.
- Evidence:
  - `config.yaml`: approvals.mode=false

### FAIL — secret redaction disabled

- Severity: critical
- Confidence: high
- Summary: security.redact_secrets is false; tool output/log context may expose secrets to the model.
- Recommendation: Re-enable secret redaction before normal use.
- Evidence:
  - `config.yaml`: security.redact_secrets=false

### UNKNOWN — no enabled plugins configured

- Severity: low
- Confidence: medium
- Summary: No plugins.enabled list was found. This is fine unless you expected a plugin to load.

### UNKNOWN — logs unavailable

- Severity: info
- Confidence: medium
- Summary: No Hermes log files were found, so runtime health cannot be inferred from logs.
