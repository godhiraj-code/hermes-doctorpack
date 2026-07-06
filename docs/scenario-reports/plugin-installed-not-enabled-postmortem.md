# plugin-installed-not-enabled

Generated: [SCENARIO_TIMESTAMP]
Hermes home: `[REDACTED_HERMES_HOME]`
Lookback: 24h

## Executive summary

Findings: fail=0, warn=0, unknown=3, ok=4.

This report is evidence-backed. `unknown` means Doctorpack lacked evidence; it is not treated as healthy or broken.

## Findings

### OK — config.yaml present

- Severity: info
- Confidence: high
- Summary: Found Hermes config.yaml.

Evidence:
- `config.yaml`: config file exists

### OK — approval prompts not obviously disabled

- Severity: info
- Confidence: medium
- Summary: approvals.mode=manual

### OK — secret redaction not disabled

- Severity: info
- Confidence: medium
- Summary: security.redact_secrets is true or omitted/default.

### UNKNOWN — no enabled plugins configured

- Severity: low
- Confidence: medium
- Summary: No plugins.enabled list was found. This is fine unless you expected a plugin to load.

### UNKNOWN — logs unavailable

- Severity: info
- Confidence: medium
- Summary: No Hermes log files were found, so runtime health cannot be inferred from logs.

### OK — user plugins discovered

- Severity: info
- Confidence: high
- Summary: Found 1 user plugin directory/directories with plugin.yaml.

Evidence:
- `plugins`: doctorpack

### UNKNOWN — no recent plugin warning/error evidence

- Severity: info
- Confidence: medium
- Summary: No recent plugin-related warning/error lines matched.

## Evidence appendix

- `config.yaml`: config file exists
- `plugins`: doctorpack

## Difference from built-in Hermes doctor/debug/logs

- Hermes doctor checks install/runtime prerequisites and config basics.
- /debug packages debug artifacts for support-style inspection.
- Logs expose raw runtime history and require manual interpretation.
- Doctorpack correlates config, plugin state, and recent redacted log evidence into conservative findings and a reusable incident postmortem.
