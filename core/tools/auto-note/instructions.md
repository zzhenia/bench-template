# Auto-Note — session notes and auto-close for idle windows

Writes the session note for a convo window that has gone quiet, then closes the
window once it has stayed finished. Nothing goes unrecorded because a tab was
forgotten, and finished tabs do not pile up.

## What runs, and when

A launchd job (template `schedule.plist`, installed by
`core/bin/install-schedules.sh` as `com.bench.<bench-slug>.auto-note`) runs
`auto_note.py` **every 5 minutes** (macOS only). Each sweep:

1. Reads the transcripts of this bench (and of any `other_benches`) in
   `<login>/projects/<bench path with non-alphanumerics as ->/`, for the default
   login `~/.claude`, each bench's own login (`.claude-login`) and
   `$CLAUDE_CONFIG_DIR`; last `lookback_hours` only.
2. **Auto-note.** A session with at least one user message whose last real turn
   is older than its idle threshold gets a note: the model writes the text, the
   script files it in `convos/<topic>/YYMMDD-<slug>.md`, dated by when the
   session went quiet. If a note for that date exists it is appended under
   `#### Auto-note — session idle since HH:MM`. The declared `>>` topic is the
   default; the model may move a session that drifted, but only to a convo that
   already exists. A session with no `>>` topic goes where the model picks, or
   `undeclared_topic`. A note goes to whichever bench holds that convo folder.
3. **Auto-close.** A window is closed after `autoclose.idle_minutes` when all of
   these hold: its note is written, nothing has been said since, its last turn
   ended cleanly (or it is past twice the limit), and the CPU time on its tty
   has not moved since the last sweep. HUP to the tab's shell, then TERM, then
   KILL, and "closed" is logged only when every process is gone. Reopen with
   `claude --resume <session id>` (in the log line).
4. **Idle shell tabs.** A terminal tab with only an idle login shell closes after
   `autoclose.shell_idle_minutes`.
5. **Frozen tabs.** `/freeze` exempts a tab from auto-close until the next
   message typed there (`~/.claude/bench-sessions/frozen/<cli pid>`, holding the
   CLI's start time so a recycled pid never inherits it).

## How it finds windows

The `UserPromptSubmit` hook (`core/hooks/convo_session.sh`) records
`{topic, tty, pid, cwd, last_prompt}` in `~/.claude/bench-sessions/<session_id>.json`
on every prompt of a `>>` convo window, and shows any pending notice on the next
prompt. A window without a `>>` topic is found through the CLI's own session file
(`<config>/sessions/<pid>.json`) once its note is on file. Entries older than 7
days are pruned.

## Closing a window yourself: `/exit` and `/e`

- A bench's terminal launcher can run `auto_note.py --exit <cli pid>` when Claude
  exits: the note is written right there (when at least
  `exit_min_msgs_threshold` messages came since the last one), one line says where
  it went, and the registry entries are cleared. Exit code 1 means the note
  failed and the tab should stay open.
- `/e` (`core/skills/e`): Claude writes the note itself and runs
  `auto_note.py --mark <path>` so nothing writes a second one.

## Where the result shows up

Once, in the window itself: a pink line on its tty, and the same line printed by
the hook on the next prompt (`systemMessage`, also passed as context so Claude
appends rather than writing a second note). `"banners": true` adds a macOS
notification. Both text channels are ASCII only. Full history:
`state/auto-note/auto-note.log`; launchd output in `/tmp/<label>.log|.err`.
`state/auto-note/.last-run` is touched every sweep.

## Settings — `config/auto-note.json`

All keys are optional.

| Key | Default | Meaning |
|-----|---------|---------|
| `default_idle_minutes` | 60 | idle time before a note is written |
| `overrides` | `{}` | per-convo note thresholds, key = convo name |
| `min_note_interval_minutes` | 120 | minimum gap before re-noting a session |
| `lookback_hours` | 24 | transcripts older than this are ignored |
| `max_transcript_chars` | 60000 | transcript text sent to the model |
| `exit_min_msgs_threshold` | 2 | `--exit` writes a fresh note after this many new messages |
| `autoclose.enabled` / `idle_minutes` | true / 60 | close finished windows after this long |
| `autoclose.shell_idle_minutes` | 240 | close idle plain-shell tabs after this long |
| `enabled` | true | false pauses everything without unloading the job |
| `notifications` / `banners` | true / true | tty + next-prompt line / macOS banner |
| `other_benches` | `[]` | paths of other benches whose sessions this watcher notes |
| `topic_aliases` | `{}` | shorthand topic -> real convo folder |
| `undeclared_topic` | `the-bench` | folder for a session with no topic |
| `model` | `haiku` | model for `claude -p` (unused when the bench has `lib/bench_ai.py`) |

The model call uses the bench's AI profile (`lib/bench_ai.py`, operation
`notes`) when the bench has one, otherwise `claude -p` on the session's bench
login. Runtime files (`state.json`, log, lock, `.last-run`) live in
`state/auto-note/`.

## What it does not do

- Never posts to a ticket tool and never commits.
- Gives the model no tools; the script writes the file.
- First run on an empty `state.json` seeds already-idle sessions as done instead
  of writing a backlog. `--backfill` writes them.

## Manual use

```bash
python3 core/tools/auto-note/auto_note.py --dry-run   # still calls the model; writes and closes nothing
python3 core/tools/auto-note/auto_note.py --force SID # note one session now
python3 core/tools/auto-note/auto_note.py --backfill  # first run, for real
python3 core/tools/auto-note/auto_note.py --exit PID  # what a launcher runs on /exit
python3 core/tools/auto-note/auto_note.py --mark PATH # what /e runs after writing PATH
```

## Dependencies

`jq` on PATH for the hook; the `claude` CLI (or the bench's AI profile); network.
A failed model call is retried once, then reported to the window and left for
the next sweep.
