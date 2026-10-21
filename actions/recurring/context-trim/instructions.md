# context-trim

A Claude Code mod. After each turn in a session inside this bench it reads the
conversation's token count. Past `threshold_tokens` a band appears above the prompt:

- `1` writes the session note (auto-note, same writer as the idle sweep), clears the
  conversation in the same window and resumes with `>><topic>`.
- `2` asks again `snooze_tokens` later.

A failed note is retried `max_attempts` times, `retry_seconds` apart, then the band
shows one red line with the log path; `1` restarts without a note, `2` keeps going.

Settings: `config.json`. Loaded in every session through `CLAUDE_CODE_PLUGIN_DIRS`
in `~/.claude/settings.json` (added by `setup.sh`; the band only shows in sessions
inside this bench). Tests: `claude plugin test actions/recurring/context-trim`.
