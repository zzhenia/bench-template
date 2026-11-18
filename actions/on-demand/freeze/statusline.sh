#!/bin/bash
# Claude Code status line: the working folder in blue; a frozen tab
# (actions/on-demand/freeze) gets a cyan "FROZEN" line in front of it.
dir=$(jq -r '.workspace.current_dir // .cwd')
pid=$PPID
while [ -n "$pid" ] && [ "$pid" -gt 1 ]; do
  case "$(ps -o command= -p "$pid")" in claude*) break ;; esac
  pid=$(ps -o ppid= -p "$pid" | tr -d ' ')
done
f="$HOME/.claude/bench-sessions/frozen/$pid"
if [ -f "$f" ] && [ "$(ps -o lstart= -p "$pid" | sed 's/  */ /g;s/^ //;s/ $//')" = "$(cat "$f")" ]; then
  printf '\033[30;46m ❄ FROZEN · will not auto-close \033[0m '
fi
printf '\033[34m%s\033[0m' "$dir"
