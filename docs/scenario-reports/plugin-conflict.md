# Scenario: plugin-conflict

Kind: `plugin_check`
Status: `warn`
Findings: fail=0, warn=1, unknown=1, ok=1

## Findings

### OK — user plugins discovered

- Severity: info
- Confidence: high
- Summary: Found 1 user plugin directory/directories with plugin.yaml.
- Evidence:
  - `plugins`: doctorpack

### WARN — doctorpack disabled

- Severity: medium
- Confidence: high
- Summary: doctorpack is explicitly listed under plugins.disabled; it will not load.
- Recommendation: Run hermes plugins enable doctorpack or edit config.yaml.

### UNKNOWN — no recent plugin warning/error evidence

- Severity: info
- Confidence: medium
- Summary: No recent plugin-related warning/error lines matched.
