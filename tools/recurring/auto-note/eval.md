# Auto-Note — Eval Cases

## 1. Note on idle
- Open a `>> test` window, exchange one message, wait past `default_idle_minutes`.
- PASS: within one sweep `convos/test/YYMMDD-<slug>.md` exists, a pink line appears in the window, and the next prompt prints the same line.

## 2. Append, not overwrite
- Same convo, same date, a second idle session.
- PASS: the existing note gains an `#### Auto-note` section; nothing above it changes.

## 3. Auto-close
- Leave the window from case 1 untouched for `autoclose.idle_minutes`.
- PASS: the tab closes; the log shows `closed <topic>` and a `claude --resume` id.

## 4. Cancel on activity
- Type in a window that is ready to close, before the next sweep.
- PASS: the window stays open; the log shows `autoclose cancelled` if it was pending.

## 5. Safety
- PASS: a window with no `>>` topic, a window still running a tool, and a window whose note was never written are never closed.
- PASS: `--dry-run` writes no note, no state, and closes nothing.
