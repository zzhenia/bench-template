#!/bin/bash
# session-note.sh — Stop hook: prompts Claude to write a session note once per session.
# Uses session_id as a flag so it fires on the first Stop of each session only.

DATE=$(date +%y%m%d)
# Resolve the repo root from this script's own location (.claude/scripts/).
# It used to be hardcoded to $HOME/research, a path that has not existed for
# a long time — the `ls` below failed silently and the convo list came out empty.
BENCH_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

# Read stdin JSON (Stop hook provides session_id)
INPUT=$(cat)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"')
FLAG_FILE="/tmp/claude-session-note-${SESSION_ID}.flag"

# Already prompted this session — do nothing
if [ -f "$FLAG_FILE" ]; then
  exit 0
fi

# Mark this session as prompted
touch "$FLAG_FILE"

# Build list of available convo folders (excluding Templates)
CONVOS=$(ls "$BENCH_DIR/convos" 2>/dev/null | grep -v "^Templates$" | grep -v "^~archive$" | sort | tr '\n' ', ' | sed 's/, $//')

# Build the additionalContext using jq for safe JSON encoding
CONTEXT="SESSION NOTE REMINDER (${DATE}):

Please write a session note for this conversation. Follow these steps:

1. IDENTIFY THE CONVO: Based on what we just discussed, determine which folder this session belongs to.
   Available convos: ${CONVOS}

2. IF UNSURE: Ask the user: \"Should I file this into an existing convo (if so, which one), or create a new folder?\"
   If creating new, follow the procedure in master-instructions.md (Creating a new convo folder).

3. CHECK EXISTING NOTE. Notes go directly in convos/<folder>/, never in a notes/ subfolder,
   and are named ${DATE}-<short-description>.md — never a bare ${DATE}.md.
   - If no convos/<folder>/${DATE}*.md exists → create ${DATE}-<short-description>.md from
     convos/Templates/Convo Template.md. Replace {{TOPIC}} with the folder name and {{DATE}} with ${DATE}.
   - If one DOES exist → ask the user: \"Today's note already exists as <filename>. Should I append to it,
     or create a new file ${DATE}-<description>-02.md?\" Then act on their answer.

4. Write the note content based on what was actually discussed this session."

jq -n --arg ctx "$CONTEXT" '{
  hookSpecificOutput: {
    hookEventName: "Stop",
    additionalContext: $ctx
  }
}'
