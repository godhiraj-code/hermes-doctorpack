# clean-home

Generated: [SCENARIO_TIMESTAMP]
Hermes home: `[REDACTED_HERMES_HOME]`
Lookback: 24h

## Executive summary

Findings: fail=0, warn=0, unknown=1, ok=6.

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

### OK — enabled plugins configured

- Severity: info
- Confidence: high
- Summary: 1 plugin(s) listed as enabled.

### OK — no recent warning/error evidence found

- Severity: info
- Confidence: medium
- Summary: No recent warning/error lines matched in the inspected log tail.

### UNKNOWN — no user plugin manifests discovered

- Severity: info
- Confidence: high
- Summary: No user plugin directories with plugin.yaml were found. Bundled/pip plugins may still exist.

### OK — no recent plugin warning/error evidence

- Severity: info
- Confidence: medium
- Summary: No recent plugin-related warning/error lines matched.

## Evidence appendix

- `config.yaml`: config file exists

## Difference from built-in Hermes doctor/debug/logs

- Hermes doctor checks install/runtime prerequisites and config basics.
- /debug packages debug artifacts for support-style inspection.
- Logs expose raw runtime history and require manual interpretation.
- Doctorpack correlates config, plugin state, and recent redacted log evidence into conservative findings and a reusable incident postmortem.
