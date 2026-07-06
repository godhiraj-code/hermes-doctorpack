# Sample: Hermes gateway/plugin incident

Generated: 2026-07-06T12:06:12Z
Hermes home: `[REDACTED_HOME]`
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
- Summary: Found recent redacted warning/error line(s) in Hermes logs. This is evidence, not root cause by itself.
- Recommendation: Review timestamps and adjacent log context before declaring a root cause.

Evidence:
- `logs/agent.log` (2026-07-06T11:25:41Z): 2026-07-06 16:55:41 WARNING hermes.lint.lsp: lsp[pyright] spawn/initialize failed: OSError: [WinError 193] %1 is not a valid Win32 application
- `logs/agent.log` (2026-07-06T11:29:44Z): 2026-07-06 16:59:44 WARNING hindsight.embedded: Daemon for profile 'hermes' is no longer responsive, restarting...

### OK — user plugins discovered

- Severity: info
- Confidence: high
- Summary: Found user plugin directory/directories with plugin.yaml.

Evidence:
- `plugins`: doctorpack

### WARN — recent plugin log warnings/errors

- Severity: medium
- Confidence: medium
- Summary: Found recent plugin-related warning/error line(s).
- Recommendation: Treat this as triage evidence; inspect adjacent log lines before assigning root cause.

Evidence:
- `logs/gateway.log` (2026-07-06T05:56:47Z): WARNING hermes_plugins.whatsapp_platform.adapter: [Whatsapp] WhatsApp is enabled but not paired. Run `hermes whatsapp` to pair, or disable WhatsApp.

## Evidence appendix

All evidence above is intentionally redacted and bounded. Doctorpack does not upload logs or call the network.

## Difference from built-in Hermes doctor/debug/logs

- Hermes doctor checks install/runtime prerequisites and config basics.
- `/debug` packages debug artifacts for support-style inspection.
- Logs expose raw runtime history and require manual interpretation.
- Doctorpack correlates config, plugin state, and recent redacted log evidence into conservative findings and a reusable incident postmortem.
