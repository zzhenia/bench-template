# Auto-Note — session notes and auto-close for idle windows

Writes the session note for a convo window that has gone quiet, then closes the
window once it has stayed finished for an hour. Nothing goes unrecorded because
a tab was forgotten, and finished tabs do not pile up.

## What runs, and when

`setup.sh` installs a launchd job, `com.bench.<bench-name>.auto-note`, that runs
`auto_note.py` **every 5 minutes** (macOS only). Each sweep:

1. Reads this bench's transcripts in `~/.claude/projects/<bench path with / as ->/`
   (under the login in `.claude-login` if the bench has one), last 24 h only.
2. **Auto-note.** A session with at least one user message whose last turn is
   older than `default_idle_minutes` (15) gets a note: Claude Haiku via
   `claude -p` writes the text, the script files it in
   `convos/<topic>/YYMMDD-<slug>.md`, dated by when the session went quiet. If a
   note for that date exists it is appended under `#### Auto-note — session idle
   since HH:MM`. A session with no `>>` topic goes to the convo the model picks,
   or `the-bench`.
3. **Auto-close.** A window is closed after `autoclose.idle_minutes` (60) when
   all of these hold: its note is written, nothing has been said since, its last
   turn ended cleanly, and the CPU time on its tty has not moved since the last
   sweep. The script checks the registered CLI pid is still on that tty, then
   sends HUP to the tab's shell, TERM, then KILL, and logs "closed" only when
   every process is gone. Any new activity cancels a pending close. Reopen with
   `claude --resume <session id>` (in the log line).

## How it finds windows

The `UserPromptSubmit` hook (`.claude/scripts/convo_session.sh`) records
`{topic, tty, pid, cwd, last_prompt}` in `~/.claude/bench-sessions/<session_id>.json`
on every prompt of a `>>` convo window, and shows any pending auto-note notice
on the next prompt. Windows without a `>>` topic are never registered, so they
are noted but never closed. Needs `jq` on PATH.

## Where the result shows up

Once, in the window itself: a pink line on its tty, and the same line printed by
the hook on the next prompt. `"banners": true` adds a macOS notification. Full
history in `auto-note.log` here; launchd output in `/tmp/com.bench.<bench-name>.auto-note.log|.err`.

## Settings — `config.json`

| Key | Default | Meaning |
|-----|---------|---------|
| `default_idle_minutes` | 15 | idle time before a note is written |
| `overrides` | `{}` | per-convo note thresholds, key = convo name |
| `min_note_interval_minutes` | 120 | minimum gap before re-noting a session |
| `autoclose.enabled` / `idle_minutes` | true / 60 | close finished windows after this long |
| `enabled` | true | false pauses everything without unloading the job |
| `notifications` / `banners` | true / false | tty + next-prompt line / macOS banner |

## What it does not do

- Never posts to a ticket tool and never commits: `/push` still owns git.
- Gives the model no tools; the script writes the file.
- First run on an empty `state.json` seeds already-idle sessions as done
  instead of writing a backlog. `--backfill` writes them.

## Manual use

```bash
python3 actions/recurring/auto-note/auto_note.py --dry-run   # still calls the model; writes and closes nothing
python3 actions/recurring/auto-note/auto_note.py --force SID # note one session now
python3 actions/recurring/auto-note/auto_note.py --backfill  # first run, for real
```

## Install / remove

`setup.sh` does it. By hand, or to remove (replace `<bench-name>`):

```bash
launchctl unload ~/Library/LaunchAgents/com.bench.<bench-name>.auto-note.plist
rm ~/Library/LaunchAgents/com.bench.<bench-name>.auto-note.plist
```

`state.json`, `auto-note.log`, `.last-run` and the lock are runtime files, ignored by git.
