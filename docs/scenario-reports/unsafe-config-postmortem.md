# unsafe-config

Generated: [SCENARIO_TIMESTAMP]
Hermes home: `[REDACTED_HERMES_HOME]`
Lookback: 24h

## Executive summary

Findings: fail=1, warn=1, unknown=4, ok=1.

This report is evidence-backed. `unknown` means Doctorpack lacked evidence; it is not treated as healthy or broken.

## Findings

### OK — config.yaml present

- Severity: info
- Confidence: high
- Summary: Found Hermes config.yaml.

Evidence:
- `config.yaml`: config file exists

### WARN — approval prompts disabled

- Severity: high
- Confidence: high
- Summary: approvals.mode appears to disable command approval prompts.
- Recommendation: Use manual or smart approval mode unless this is an isolated throwaway environment.

Evidence:
- `config.yaml`: approvals.mode=false

### FAIL — secret redaction disabled

- Severity: critical
- Confidence: high
- Summary: security.redact_secrets is false; tool output/log context may expose secrets to the model.
- Recommendation: Re-enable secret redaction before normal use.

Evidence:
- `config.yaml`: security.redact_secrets=false

### UNKNOWN — no enabled plugins configured

- Severity: low
- Confidence: medium
- Summary: No plugins.enabled list was found. This is fine unless you expected a plugin to load.

### UNKNOWN — logs unavailable

- Severity: info
- Confidence: medium
- Summary: No Hermes log files were found, so runtime health cannot be inferred from logs.

### UNKNOWN — no user plugin manifests discovered

- Severity: info
- Confidence: high
- Summary: No user plugin directories with plugin.yaml were found. Bundled/pip plugins may still exist.

### UNKNOWN — no recent plugin warning/error evidence

- Severity: info
- Confidence: medium
- Summary: No recent plugin-related warning/error lines matched.

## Evidence appendix

- `config.yaml`: config file exists
- `config.yaml`: approvals.mode=false
- `config.yaml`: security.redact_secrets=false

## Difference from built-in Hermes doctor/debug/logs

- Hermes doctor checks install/runtime prerequisites and config basics.
- /debug packages debug artifacts for support-style inspection.
- Logs expose raw runtime history and require manual interpretation.
- Doctorpack correlates config, plugin state, and recent redacted log evidence into conservative findings and a reusable incident postmortem.
