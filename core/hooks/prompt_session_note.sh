#!/usr/bin/env bash
# Pre-push hook: ensures a session note is written before pushing.
# Blocks the push and asks the agent to run the note action if no note for today exists.
# The note action should create a new note or append to an existing one for today.
#
# Agent-agnostic: the hook output describes the required action in plain terms.

CMD=$(jq -r '.tool_input.command // ""' 2>/dev/null)
echo "$CMD" | grep -qE '^git push' || exit 0

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
TODAY=$(date +%y%m%d)

# Allow if a note for today was already committed in this session
TODAY_COMMITTED=$(git -C "$REPO_ROOT" log --name-only --since="midnight" --format="" 2>/dev/null | grep -E "convos/.+/${TODAY}" || true)
[ -n "$TODAY_COMMITTED" ] && exit 0

# Allow if a note for today is staged (will be part of this push)
TODAY_STAGED=$(git -C "$REPO_ROOT" diff --cached --name-only 2>/dev/null | grep -E "convos/.+/${TODAY}" || true)
[ -n "$TODAY_STAGED" ] && exit 0

# Build context: what files changed recently
CHANGED=$(git -C "$REPO_ROOT" diff --name-only HEAD 2>/dev/null | head -30 || true)
STAGED=$(git -C "$REPO_ROOT" diff --cached --name-only 2>/dev/null | head -30 || true)
ALL=$(printf '%s\n%s' "$CHANGED" "$STAGED" | sort -u | grep -v '^$' | head -30)
FILE_LIST=$(echo "$ALL" | tr '\n' ',' | sed 's/,$//' | tr ',' ', ')

jq -n --arg files "$FILE_LIST" --arg today "$TODAY" '{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": ("Before pushing, run the session note action for this conversation. The note action should check if a note for today (" + $today + ") already exists in the relevant convos/ folder — if it does, append the recent work to it; if not, create a new one. Recent changes in this session: " + $files + ". Once the note is written and staged, push again.")
  },
  "continue": false,
  "stopReason": "Write a session note first (create or append), then push again."
}'
