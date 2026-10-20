#!/bin/bash
# UserPromptSubmit hook. Three cheap jobs:
#   1. When a prompt starts with `>> name`, set the terminal tab title to it.
#   2. Register the session in ~/.claude/bench-sessions/<session_id>.json
#      (topic, tty, pid, cwd, last_prompt) so auto-note knows which convo the
#      window belongs to, which tty to write to, and when it was last used.
#      The topic only appears in the first `>>` message; later prompts keep it.
#   3. Show any pending auto-note notice, so a note written while the window was
#      idle is visible the moment you type again.

REG_DIR="$HOME/.claude/bench-sessions"
mkdir -p "$REG_DIR"

payload=$(cat)
session_id=$(printf '%s' "$payload" | jq -r '.session_id // empty')
cwd=$(printf '%s' "$payload" | jq -r '.cwd // empty')
prompt=$(printf '%s' "$payload" | jq -r '.prompt // .message // .content // empty')

topic=$(printf '%s' "$prompt" | head -1 \
  | sed -n 's/.*>>[[:space:]]*\([a-zA-Z0-9_-]*\).*/\1/p' \
  | tr '[:upper:]' '[:lower:]')

if [ -n "$topic" ]; then
  # stderr is silenced BEFORE the /dev/tty redirect, so a headless run with no
  # controlling terminal fails quietly instead of printing into the hook output.
  printf '\033]0;%s \033\\' "$topic" 2>/dev/null > /dev/tty || true
fi

# ── register ───────────────────────────────────────────────────────────────
if [ -n "$session_id" ]; then
  reg="$REG_DIR/$session_id.json"

  # Hooks run with no controlling terminal, so ask the CLI process
  # ($CLAUDE_PID) for its tty; $$ is the fallback for hosts that give hooks one.
  tty_dev=$(ps -o tty= -p "${CLAUDE_PID:-$$}" 2>/dev/null | tr -d '[:space:]')
  if [ -z "$tty_dev" ] || [ "$tty_dev" = "??" ]; then
    tty_dev=$(ps -o tty= -p $$ 2>/dev/null | tr -d '[:space:]')
  fi
  tty_path=""
  if [ -n "$tty_dev" ] && [ "$tty_dev" != "??" ] && [ -w "/dev/$tty_dev" ]; then
    tty_path="/dev/$tty_dev"
  fi

  prev_topic=""
  [ -f "$reg" ] && prev_topic=$(jq -r '.topic // empty' "$reg" 2>/dev/null)
  [ -z "$topic" ] && topic="$prev_topic"

  # Only convo windows get registered: headless `claude -p` runs (auto-note's
  # own model calls among them) fire this hook too.
  [ -z "$topic" ] && { printf '{"suppressOutput":true}'; exit 0; }

  # The CLI pid too: tty numbers get recycled, so auto-note checks this exact
  # pid is still on that tty before writing to it or closing it.
  jq -n --arg t "$topic" --arg tty "$tty_path" --arg cwd "$cwd" \
        --arg sid "$session_id" --arg ts "$(date +%s)" \
        --arg pid "${CLAUDE_PID:-}" \
    '{session_id:$sid, topic:$t, tty:$tty, pid:($pid|tonumber? // null),
      cwd:$cwd, last_prompt:($ts|tonumber)}' \
    > "$reg" 2>/dev/null || true
fi

# ── drain pending notice ───────────────────────────────────────────────────
# systemMessage is printed in the terminal (what you see); additionalContext
# tells Claude a note already exists, so /note appends instead of starting over.
notice="$REG_DIR/$session_id.notice"
if [ -n "$session_id" ] && [ -f "$notice" ]; then
  body=$(cat "$notice")
  rm -f "$notice"
  jq -n --arg c "$body" \
    '{systemMessage:$c,
      hookSpecificOutput:{hookEventName:"UserPromptSubmit", additionalContext:$c}}'
  exit 0
fi

printf '{"suppressOutput":true}'
