#!/bin/bash
# Freeze a Claude tab so the auto-note watcher never auto-closes it.
#
#   freeze.sh              freeze the tab this runs in (walks up to its `claude`)
#   freeze.sh --pid PID    freeze the Claude CLI with that pid
#   freeze.sh --all        freeze every Claude CLI running in a Cursor tab
#   freeze.sh --off [PID]  unfreeze (this tab, or that pid)
#   freeze.sh --list       show frozen tabs
#
# A freeze is a file ~/.claude/bench-sessions/frozen/<cli pid> holding the
# process start time, so a recycled pid never inherits it. The next message
# typed in the tab removes it (the UserPromptSubmit session hook).

DIR="$HOME/.claude/bench-sessions/frozen"
mkdir -p "$DIR"

started() { ps -o lstart= -p "$1" 2>/dev/null | sed 's/  */ /g;s/^ //;s/ $//'; }

own_cli() {
  local pid=$PPID
  while [ -n "$pid" ] && [ "$pid" -gt 1 ]; do
    case "$(ps -o command= -p "$pid")" in claude*) echo "$pid"; return ;; esac
    pid=$(ps -o ppid= -p "$pid" | tr -d ' ')
  done
}

freeze_pid() {
  local s; s=$(started "$1")
  [ -n "$s" ] || { echo "freeze: no process $1" >&2; return 1; }
  printf '%s\n' "$s" > "$DIR/$1"
  echo "frozen $1 ($(ps -o command= -p "$1" | sed 's/.* -n //'))"
}

case "$1" in
  --all)
    n=0
    for pid in $(ps -axo pid=,command= | awk '$2=="claude"{print $1}'); do
      a=$pid
      for _ in 1 2 3 4 5 6 7 8; do
        a=$(ps -o ppid= -p "$a" | tr -d ' ')
        [ -z "$a" ] || [ "$a" -le 1 ] && break
        case "$(ps -o comm= -p "$a")" in *Cursor*pty-host*) freeze_pid "$pid" && n=$((n+1)); break ;; esac
      done
    done
    echo "$n Cursor tabs frozen" ;;
  --pid) freeze_pid "$2" ;;
  --off)
    pid=${2:-$(own_cli)}
    rm -f "$DIR/$pid" && echo "unfrozen $pid" ;;
  --list)
    for f in "$DIR"/*; do
      [ -f "$f" ] || continue
      pid=$(basename "$f")
      [ "$(started "$pid")" = "$(cat "$f")" ] && echo "$pid $(ps -o command= -p "$pid" | sed 's/.* -n //')" || rm -f "$f"
    done ;;
  *)
    pid=$(own_cli)
    [ -n "$pid" ] || { echo "freeze: no Claude process found above this shell" >&2; exit 1; }
    freeze_pid "$pid" ;;
esac
