# plugin-conflict

Generated: [SCENARIO_TIMESTAMP]
Hermes home: `[REDACTED_HERMES_HOME]`
Lookback: 24h

## Executive summary

Findings: fail=0, warn=1, unknown=2, ok=5.

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

### WARN — plugins both enabled and disabled

- Severity: medium
- Confidence: high
- Summary: Some plugins are listed in both plugins.enabled and plugins.disabled; disabled wins and can make tools appear missing.
- Recommendation: Remove each plugin from one list so enablement is unambiguous.

Evidence:
- `config.yaml`: doctorpack

### OK — enabled plugins configured

- Severity: info
- Confidence: high
- Summary: 1 plugin(s) listed as enabled.

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
- `config.yaml`: doctorpack
- `plugins`: doctorpack

## Difference from built-in Hermes doctor/debug/logs

- Hermes doctor checks install/runtime prerequisites and config basics.
- /debug packages debug artifacts for support-style inspection.
- Logs expose raw runtime history and require manual interpretation.
- Doctorpack correlates config, plugin state, and recent redacted log evidence into conservative findings and a reusable incident postmortem.
