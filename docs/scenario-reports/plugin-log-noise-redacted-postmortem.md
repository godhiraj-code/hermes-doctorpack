# plugin-log-noise-redacted

Generated: [SCENARIO_TIMESTAMP]
Hermes home: `[REDACTED_HERMES_HOME]`
Lookback: 24h

## Executive summary

Findings: fail=0, warn=2, unknown=0, ok=5.

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

### WARN — recent warning/error log evidence

- Severity: medium
- Confidence: medium
- Summary: Found 2 recent redacted warning/error line(s) in Hermes logs. This is evidence, not root cause by itself.
- Recommendation: Review timestamps and adjacent log context before declaring a root cause.

Evidence:
- `logs/gateway.log` (2099-01-01T00:00:00+00:00): 2099-01-01T00:00:00Z ERROR plugin doctorpack register_tool failed token=[REDACTED]
- `logs/gateway.log` (2099-01-01T00:00:01+00:00): 2099-01-01T00:00:01Z WARNING gateway retry for user [REDACTED_EMAIL] phone [REDACTED_PHONE]

### OK — user plugins discovered

- Severity: info
- Confidence: high
- Summary: Found 1 user plugin directory/directories with plugin.yaml.

Evidence:
- `plugins`: doctorpack

### WARN — recent plugin log warnings/errors

- Severity: medium
- Confidence: medium
- Summary: Found 1 recent plugin-related warning/error line(s).
- Recommendation: Treat this as triage evidence; inspect adjacent log lines before assigning root cause.

Evidence:
- `logs/gateway.log` (2099-01-01T00:00:00+00:00): 2099-01-01T00:00:00Z ERROR plugin doctorpack register_tool failed token=[REDACTED]

## Evidence appendix

- `config.yaml`: config file exists
- `logs/gateway.log` (2099-01-01T00:00:00+00:00): 2099-01-01T00:00:00Z ERROR plugin doctorpack register_tool failed token=[REDACTED]
- `logs/gateway.log` (2099-01-01T00:00:01+00:00): 2099-01-01T00:00:01Z WARNING gateway retry for user [REDACTED_EMAIL] phone [REDACTED_PHONE]
- `plugins`: doctorpack
- `logs/gateway.log` (2099-01-01T00:00:00+00:00): 2099-01-01T00:00:00Z ERROR plugin doctorpack register_tool failed token=[REDACTED]

## Difference from built-in Hermes doctor/debug/logs

- Hermes doctor checks install/runtime prerequisites and config basics.
- /debug packages debug artifacts for support-style inspection.
- Logs expose raw runtime history and require manual interpretation.
- Doctorpack correlates config, plugin state, and recent redacted log evidence into conservative findings and a reusable incident postmortem.
