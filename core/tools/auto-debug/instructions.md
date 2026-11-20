# auto-debug

Watches a tool's `BUGS.md` and starts Claude Code to fix the bugs listed in it.

```
python3 core/tools/auto-debug/auto_debug.py start <tool-slug>
python3 core/tools/auto-debug/auto_debug.py stop <tool-slug>
python3 core/tools/auto-debug/auto_debug.py status
```

- Tools come from `bench-index.csv` (rows with `type = action`); the slug is
  the `slug` column.
- `start` creates `BUGS.md` in the tool's folder if missing. Each `### ` heading
  is one bug. When the file changes and holds open bugs, a terminal opens (VS
  Code / Cursor, via `osascript`) running `claude` with a prompt to fix every
  bug, strike it through (`~~#N. Title~~ — fixed <time>`) and write a note.
- The watcher stops itself after 30 minutes without a change.
- State: `state/auto-debug/bugfix_mode.json`. Needs macOS and the `claude`
  binary at `~/.local/bin/claude`.
- The coordinator is a background thread: `start` from the CLI only records the
  watch; something long-running (a dashboard importing the module) must keep it
  alive.
