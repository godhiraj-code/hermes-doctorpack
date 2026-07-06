# hermes-doctorpack

Local-first diagnostics, plugin health checks, safety signals, and incident postmortems for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

Doctorpack is for the moment when Hermes is technically running, but something around plugins, gateway delivery, config, cron/MCP noise, or logs feels wrong and raw logs are too noisy to interpret quickly.

It turns local Hermes evidence into conservative, redacted findings:

```text
Doctorpack config_audit status: warn
Hermes home: C:\Users\you\AppData\Local\hermes
Findings: fail=0 warn=1 unknown=0 ok=4

[ok] config.yaml present — Found Hermes config.yaml.
[ok] approval prompts not obviously disabled — approvals.mode=manual
[ok] secret redaction not disabled — security.redact_secrets is true or omitted/default.
[ok] enabled plugins configured — 1 plugin(s) listed as enabled.
[warn] recent warning/error log evidence — Found recent redacted warning/error line(s) in Hermes logs. This is evidence, not root cause by itself.
  fix: Review timestamps and adjacent log context before declaring a root cause.
```

## Why this is useful

Hermes users often debug from several disconnected surfaces:

- `config.yaml`
- `hermes plugins list`
- `agent.log`
- `gateway.log`
- `errors.log`
- plugin enable/disable state
- approval/security settings

Doctorpack correlates those into a small report with:

- `ok` / `warn` / `fail` / `unknown` status
- severity
- confidence
- redacted evidence snippets
- concrete recommendation
- local Markdown postmortem output

The important design choice: **missing evidence is `unknown`, not `fail`; log keywords are evidence, not root cause.** This keeps it useful without creating scary fake diagnostics.

## Example report

A sanitized sample report is included here:

- [`docs/sample-report.md`](docs/sample-report.md)

Postmortem reports look like this:

```md
# Sample: Hermes gateway/plugin incident

## Executive summary

Findings: fail=0, warn=2, unknown=0, ok=5.

This report is evidence-backed. `unknown` means Doctorpack lacked evidence; it is not treated as healthy or broken.

### WARN — recent plugin log warnings/errors

- Severity: medium
- Confidence: medium
- Summary: Found recent plugin-related warning/error line(s).
- Recommendation: Treat this as triage evidence; inspect adjacent log lines before assigning root cause.

Evidence:
- `logs/gateway.log`: WARNING hermes_plugins.whatsapp_platform.adapter: [Whatsapp] WhatsApp is enabled but not paired.
```

## What it does

### `doctorpack_config_audit`

Audits the local Hermes home for:

- config presence
- approval mode risk, e.g. approval prompts disabled
- secret redaction state
- plugin enabled/disabled conflicts
- recent warning/error evidence from `agent.log`, `gateway.log`, and `errors.log`

### `doctorpack_plugin_check`

Inspects plugin state for:

- user plugin directories with `plugin.yaml`
- target plugin enabled/disabled/not-enabled status
- plugin-related warning/error evidence in recent logs

### `doctorpack_postmortem`

Writes a local Markdown incident report to:

```text
HERMES_HOME/doctorpack/reports/
```

The report includes summary, findings, evidence, recommendations, and a short explanation of how Doctorpack differs from built-in Hermes diagnostics.

## How it is different from Hermes doctor, debug, and logs

| Built-in surface | What it does | What Doctorpack adds |
| --- | --- | --- |
| `hermes doctor` | Checks install/config prerequisites and basic runtime dependencies. | Correlates config, plugin state, and recent log evidence into conservative findings. |
| `/debug` | Packages debug artifacts for support/troubleshooting. | Produces a redacted incident postmortem with severity, confidence, and recommendations. |
| `agent.log` / `gateway.log` | Raw runtime history. | Parses only recent redacted evidence; never treats a log keyword as root cause by itself. |
| `hermes plugins list` | Shows plugin discovery/enabled state. | Flags conflicts, disabled target plugins, installed-but-not-enabled plugins, and plugin-related log evidence. |

Doctorpack does not replace those surfaces. It sits on top of them as a local triage/reporting layer.

## Security model

- Local-first: no network calls.
- Read-only by default except `doctorpack_postmortem`, which writes a Markdown report locally.
- Secret and common PII redaction before returning evidence.
- Bounded log reads; it tails recent log content instead of loading everything.
- Missing logs/config are `unknown`, not `fail`.
- Log matches are evidence, not proof.
- Tool handlers return JSON and catch internal exceptions instead of crashing the agent loop.
- No telemetry, no upload, no external service dependency.

Review generated reports before sharing them publicly. Pattern-based redaction is useful, not magic.

## Install / distribute

### Option A — GitHub install as a user plugin

Use this today:

```bash
git clone https://github.com/godhiraj-code/hermes-doctorpack.git
mkdir -p ~/.hermes/plugins
cp -R hermes-doctorpack ~/.hermes/plugins/doctorpack
hermes plugins enable doctorpack
```

Restart Hermes or start a new session after enabling.

On Windows native Hermes home, copy to:

```text
C:\Users\<you>\AppData\Local\hermes\plugins\doctorpack
```

Then enable:

```bash
hermes plugins enable doctorpack
```

### Option B — install from Git URL with pip

This is useful once users want package-style installs:

```bash
pip install git+https://github.com/godhiraj-code/hermes-doctorpack.git
```

The package exposes a Hermes plugin entry point:

```toml
[project.entry-points."hermes_agent.plugins"]
doctorpack = "hermes_doctorpack"
```

### Option C — future PyPI release

Once the plugin has a few dogfood runs and feedback from Hermes users:

```bash
pip install hermes-doctorpack
```

This repo is already structured for that; publishing to PyPI is intentionally not done yet.

## Usage

From a Hermes session after enabling the plugin:

```text
/doctorpack scan
/doctorpack plugins --plugin-name doctorpack
/doctorpack postmortem --incident-title "Gateway delivery issue"
```

Standalone CLI smoke use:

```bash
python -m hermes_doctorpack.cli scan --hermes-home /path/to/hermes/home
python -m hermes_doctorpack.cli plugins --plugin-name doctorpack
python -m hermes_doctorpack.cli postmortem --incident-title "Gateway failed to send"
```

## False-report guardrails

Doctorpack deliberately avoids false certainty:

- Old timestamped log errors outside `lookback_hours` do not count.
- Timestamp-less tail lines are included only as medium-confidence evidence.
- No config file means `unknown`, not broken.
- No logs means `unknown`, not healthy.
- A keyword like `error` produces triage evidence, not a root-cause claim.
- Config checks only hard-fail on direct evidence such as `security.redact_secrets: false`.
- Plugin not found in user plugin folders can be `unknown` because bundled/pip plugins may exist elsewhere.

## Verification

Current test suite covers:

- secret/email/phone/credential URL redaction
- timestamp preservation during redaction
- missing config returns `unknown`, not `fail`
- old timestamped log errors do not produce recent warnings
- recent log secrets are redacted in evidence
- installed-but-not-enabled plugin is `warn`, not `fail`
- `security.redact_secrets: false` is a direct `fail`
- postmortem Markdown report generation
- Hermes plugin registration for tools, slash command, and CLI command
- tool handler returns valid JSON

Run locally:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Expected result:

```text
..........                                                               [100%]
```

## MVP scope

This first version focuses on the high-signal wedge:

1. config audit
2. plugin check
3. postmortem report

Gateway/MCP/cron-specific deep checks can layer on later after the first artifact is dogfooded and shared.
