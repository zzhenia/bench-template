#!/bin/bash
# UserPromptSubmit hook.
#
# Three jobs, all cheap:
#   1. Extract a `>>` topic from the prompt and set the terminal tab title.
#   2. Register this session in ~/.claude/bench-sessions/<session_id>.json so the
#      auto-note watcher knows which convo the window belongs to and which tty to
#      shout into. The topic only appears in the first `>>` message, so later
#      prompts keep whatever was recorded before.
#   3. Drain any pending auto-note notice into the conversation, so a note written
#      while the window was idle is visible the moment the user types again — the
#      tty write the watcher does can be wiped by the next TUI redraw, this can't.

# Bench root: core/hooks/ (or the .claude/scripts/ link to it) is two levels down.
ROOT="${BENCH_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
REG_DIR="$HOME/.claude/bench-sessions"
mkdir -p "$REG_DIR"

payload=$(cat)
session_id=$(printf '%s' "$payload" | jq -r '.session_id // empty')
cwd=$(printf '%s' "$payload" | jq -r '.cwd // empty')
prompt=$(printf '%s' "$payload" | jq -r '.prompt // .message // .content // empty')

# ── freeze (261117) ────────────────────────────────────────────────────────
# `/freeze` (or `/*`) marks this tab so the auto-note watcher never auto-closes it, and
# is blocked here so it reaches no model and leaves the idle clock alone. Any
# other message unfreezes the tab. core/tools/freeze/freeze.sh owns the mark.
if [ -n "${CLAUDE_PID:-}" ]; then
  if printf '%s' "$prompt" | grep -qE '^[[:space:]]*/(freeze|\*)[[:space:]]*$'; then
    freeze="$ROOT/core/tools/freeze/freeze.sh"
    if out=$(bash "$freeze" --pid "$CLAUDE_PID" 2>&1); then
      reason="Frozen: this tab will not auto-close. Typing anything unfreezes it."
    else
      reason="Not frozen: $out"
    fi
    jq -n --arg r "$reason" '{decision:"block", reason:$r}'
    exit 0
  fi
  rm -f "$HOME/.claude/bench-sessions/frozen/$CLAUDE_PID"
fi

topic=$(printf '%s' "$prompt" | head -1 \
  | sed -n 's/.*>>[[:space:]]*\([a-zA-Z0-9_-]*\).*/\1/p' \
  | tr '[:upper:]' '[:lower:]')

if [ -n "$topic" ]; then
  # stderr is silenced BEFORE the /dev/tty redirect so a missing controlling
  # terminal (headless run) fails quietly instead of printing into the hook output.
  printf '\033]0;%s \033\\' "$topic" 2>/dev/null > /dev/tty || true
fi

# ── register ───────────────────────────────────────────────────────────────
if [ -n "$session_id" ]; then
  reg="$REG_DIR/$session_id.json"

  # The window the user is typing in. Ask the CLI process, not this one: Claude
  # Code runs hooks with no controlling terminal, so `ps -o tty= -p $$` always
  # answers "??" and every registry entry was written with tty:"" — which is
  # why the watcher had never once managed a live line and always fell back to
  # "no tty registered … notice file only". $CLAUDE_PID is the CLI's own pid and
  # does have one. Under `convo`/`zv_claude_named` that is expect's slave pty,
  # which relays to the real terminal, so the write lands either way. $$ stays
  # as the fallback for any host that does give hooks a tty.
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

  # Only convo windows get registered. Headless `claude -p` runs (the auto-note
  # watcher's own calls, among others) fire this hook too and would otherwise
  # litter the registry with topicless entries.
  [ -z "$topic" ] && { printf '{"suppressOutput":true}'; exit 0; }

  # pid of the CLI too (260826): ttys numbers get recycled, so the watcher
  # checks this exact pid is still on that tty before writing a pink line.
  jq -n --arg t "$topic" --arg tty "$tty_path" --arg cwd "$cwd" \
        --arg sid "$session_id" --arg ts "$(date +%s)" \
        --arg pid "${CLAUDE_PID:-}" \
    '{session_id:$sid, topic:$t, tty:$tty, pid:($pid|tonumber? // null),
      cwd:$cwd, last_prompt:($ts|tonumber)}' \
    > "$reg" 2>/dev/null || true
fi

# ── drain pending notice ───────────────────────────────────────────────────
# Two channels on purpose, because they have different audiences:
#   systemMessage      — printed in the terminal, the way /note's own output is.
#                        This is the bit the user actually sees. Added 260823;
#                        before that the drain was additionalContext only, which
#                        goes into Claude's context and is invisible to a human,
#                        so an auto-note had no visible surface at all.
#   additionalContext  — tells Claude a note already exists for this session, so
#                        it appends rather than starting a second one.
# The notice is already a single ASCII line ("[auto-note] 67m idle: appended to
# convos/... (not committed, not posted to a ticket)."), so it is used verbatim.
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
