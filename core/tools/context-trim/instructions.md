# context-trim

A Claude Code mod. After each turn in a session inside this bench (or in a
`bench_dirs` entry) it reads the conversation's token count. Past
`threshold_tokens` a band appears above the prompt:

- `1` writes the session note (`core/tools/auto-note`, same writer as the idle
  sweep), clears the conversation in the same window and resumes with `>><topic>`.
  Messages typed while the note is written are held and sent after the resume line.
- `2` asks again `snooze_tokens` later.
- `3` arms the restart: once the turn has ended and no background command or
  subagent is still running, it waits for your next message, so the last answer
  stays on screen. That message is held, `1` runs, and it is sent on after the
  resume line. Slash commands and messages with images pass through without
  firing it. While queued or armed, `1` restarts now, `2` cancels.

A failed note is retried `max_attempts` times, `retry_seconds` apart, then the band
shows one red line with the log path; `1` restarts without a note, `2` keeps going.
A held message is sent either way.

Settings: defaults in `config.json` here; a bench overrides any key in
`config/context-trim.json`:

| Key | Default | Meaning |
|-----|---------|---------|
| `threshold_tokens` | 100000 | when the band first appears |
| `snooze_tokens` | 25000 | how much later "not now" asks again |
| `max_attempts` / `retry_seconds` | 3 / 30 | note retries |
| `python` | `/usr/bin/python3` | interpreter for `auto_note.py` |
| `bench_dirs` | `[]` | other bench paths (absolute) whose sessions also get the band |

Loaded in every session through `CLAUDE_CODE_PLUGIN_DIRS` in
`~/.claude/settings.json` (and any other login's settings), pointing at
`<bench>/core/tools/context-trim`. Tests: `claude plugin test core/tools/context-trim`.
