# bench-ticket — link session notes to tickets

`bench_ticket.py` reads and writes the ticket columns (`jira`, `asana`) of
`bench-index.csv` and posts short session-note comments. Used by the `note`,
`push` and `bugs` skills. Needs `requests`.

```bash
python3 core/tools/bench-ticket/bench_ticket.py lookup <slug>           # linked tickets, with titles
python3 core/tools/bench-ticket/bench_ticket.py candidates <query>      # up to 3 matches, JSON, read-only
python3 core/tools/bench-ticket/bench_ticket.py post <slug> <note> --key <KEY>
python3 core/tools/bench-ticket/bench_ticket.py update <slug> --jira <KEY>
```

`post` sends a brief comment (title, date, first topics, file path), never the
note body: ADF on Jira, HTML on Asana. It always needs `--key`; skills confirm
the ticket with the user before running it.

## Settings

`config/bench.env`:

- `PM_TOOL` — `jira`, `asana` or `none`. Only that tool's API is called; empty
  or `none` makes every command a no-op.
- `TICKET_AUTOLINK` — `yes` lets `post --key` link a key that is not on the slug
  yet (appended to its comma-separated list). Default: refuse.

`config/keys.env`: `JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, optional
`JIRA_PROJECT_KEYS` (comma-separated, narrows `candidates`); or `ASANA_PAT` and
`ASANA_WORKSPACE_GID`.
