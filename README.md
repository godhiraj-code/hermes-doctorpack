# hermes-doctorpack

Local-first diagnostics, safety audit, plugin checks, and incident postmortems for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

Doctorpack is intentionally **not** a replacement for `hermes doctor`, `/debug`, or raw logs:

| Built-in surface | What it does | What Doctorpack adds |
| --- | --- | --- |
| `hermes doctor` | Checks install/config prerequisites and basic runtime dependencies. | Correlates config, plugin state, and recent log evidence into conservative findings. |
| `/debug` | Packages debug artifacts for support/troubleshooting. | Produces a redacted incident postmortem with severity, confidence, and recommendations. |
| `agent.log` / `gateway.log` | Raw runtime history. | Parses only recent redacted evidence; never treats a log keyword as root cause by itself. |
| `hermes plugins list` | Shows plugin discovery/enabled state. | Flags conflicts, disabled target plugins, and plugin-related log evidence. |

## Security model

- Local-first: no network calls.
- Read-only by default except `doctorpack_postmortem`, which writes a Markdown report to `HERMES_HOME/doctorpack/reports` or a user-supplied output directory.
- Secret and PII redaction before returning evidence.
- Missing logs/config are `unknown`, not `fail`.
- Log matches are evidence, not proof. Findings carry `status`, `severity`, and `confidence`.
- Stdlib-first runtime; PyYAML is used for config parsing.

## Plugin tools

- `doctorpack_config_audit` — audit config, approval/security/plugin posture, and recent logs.
- `doctorpack_plugin_check` — inspect plugin manifests/config state and plugin log evidence.
- `doctorpack_postmortem` — generate a redacted Markdown incident report.

## Install as a Hermes plugin

Directory install during development:

```bash
mkdir -p ~/.hermes/plugins
cp -R hermes-doctorpack ~/.hermes/plugins/doctorpack
hermes plugins enable doctorpack
```

Pip distribution later:

```bash
pip install hermes-doctorpack
```

## Standalone CLI smoke use

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

## MVP scope

This first version focuses on the high-signal wedge:

1. config audit
2. plugin check
3. postmortem report

Gateway/MCP/cron-specific deep checks can layer on later after the first artifact is dogfooded and shared.
