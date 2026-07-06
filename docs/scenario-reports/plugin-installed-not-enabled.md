# Scenario: plugin-installed-not-enabled

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

### WARN — doctorpack installed but not enabled

- Severity: medium
- Confidence: high
- Summary: doctorpack appears installed in user plugins but is not listed under plugins.enabled.
- Recommendation: Run hermes plugins enable doctorpack.

### UNKNOWN — no recent plugin warning/error evidence

- Severity: info
- Confidence: medium
- Summary: No recent plugin-related warning/error lines matched.
