# freeze — keep a tab from auto-closing

`freeze.sh` marks a Claude Code tab so the idle auto-close never shuts it. A
mark is `~/.claude/bench-sessions/frozen/<cli pid>` holding the process start
time. The session hook clears it on the next message typed in the tab.

```bash
core/tools/freeze/freeze.sh            # this tab
core/tools/freeze/freeze.sh --all      # every Claude tab in Cursor
core/tools/freeze/freeze.sh --off [PID]
core/tools/freeze/freeze.sh --list
```

`statusline.sh` is the Claude Code status line: the working folder, with a
FROZEN badge in front while the tab is frozen. Point `statusLine.command` in
`~/.claude/settings.json` at it.
