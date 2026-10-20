#!/bin/bash
# UserPromptSubmit hook — set the terminal tab title from a `>>` topic.
#
# When a prompt starts with `>> name`, that name becomes the tab title, so a
# window full of Claude sessions is readable at a glance. The topic only appears
# in the first message of a convo, so later prompts leave the title alone.
#
# Deliberately does nothing else. Silent and cheap: no network, no writes.

payload=$(cat)
prompt=$(printf '%s' "$payload" | jq -r '.prompt // .message // .content // empty')

topic=$(printf '%s' "$prompt" | head -1 \
  | sed -n 's/.*>>[[:space:]]*\([a-zA-Z0-9_-]*\).*/\1/p' \
  | tr '[:upper:]' '[:lower:]')

if [ -n "$topic" ]; then
  # stderr is silenced BEFORE the /dev/tty redirect, so a headless run with no
  # controlling terminal fails quietly instead of printing into the hook output.
  printf '\033]0;%s \033\\' "$topic" 2>/dev/null > /dev/tty || true
fi

printf '{"suppressOutput":true}'
