# automation-status — what runs on this bench

- `inventory.py` writes `AUTOMATIONS.md` at the bench root: every scheduled job,
  where and when it runs, whether it calls a model or posts to Slack, and its
  7-day cost when a usage ledger is configured.
- `generate_status.py` (or `status.sh`) is the launchd detail view: launchctl
  status, last exit and last log line, written to
  `state/automation-status/YYMMDD-automations.md`.

Jobs are found on their own: launchd plists labelled `com.bench.<BENCH_SLUG>.*`
or whose program sits inside the bench, and `core/tools/*/schedule.plist`
templates that are not installed yet (listed as "not installed").

## Settings

`config/bench.env`: `BENCH_SLUG` (the launchd label part, shared with
`core/bin/install-schedules.sh`).

`config/automation-status.json`, all keys optional:

- `launchd_prefixes` — extra label prefixes that count as this bench's jobs.
- `jobs` — `{name: {desc, ledger_op, ledger_host ("mac" or a remote), slack}}`.
- `usage_ledger` — path of the local bench_ai usage ledger (SQLite).
- `prices` — `{model: [usd per M input, usd per M output]}` overrides.
- `remotes` — other machines over SSH: `{where, kind: "openclaw" | "launchd",
  ssh: "user@host", key, services_regex, label_regex, timezone_label,
  unreachable_note, empty_note}`.

`config/ai-profile.json`, if present, names the model each agent runs on.
