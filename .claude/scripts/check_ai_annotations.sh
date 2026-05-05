#!/usr/bin/env bash
# PostToolUse/Read hook: checks if the file just opened has @ai annotations.
# If so, injects a soft reminder into Claude's context so it can mention them.
#
# Agent-agnostic: any AI agent that reads this output should honour it.

FILE=$(jq -r '.tool_input.file_path // ""' 2>/dev/null)
[ -z "$FILE" ] && exit 0
[ -f "$FILE" ] || exit 0

# Skip .claude/ files (command docs that reference @ai by design)
echo "$FILE" | grep -q '\.claude/' && exit 0

MATCHES=$(grep -n '@ai ' "$FILE" 2>/dev/null || true)
[ -z "$MATCHES" ] && exit 0

COUNT=$(echo "$MATCHES" | wc -l | tr -d ' ')

jq -n --arg file "$FILE" --arg count "$COUNT" --arg matches "$MATCHES" '{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": ("Note: this file has " + $count + " unprocessed @ai instruction(s). Mention this to the user and offer to run /ai when it seems relevant.\n\nAnnotations found:\n" + $matches)
  }
}'