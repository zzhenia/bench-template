#!/bin/bash
# session-note.sh — Stop hook: prompts Claude to write a session note once per session.
# Uses session_id as a flag so it fires on the first Stop of each session only.

DATE=$(date +%y%m%d)
# Resolve repo root: this script lives at .claude/scripts/
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESEARCH_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

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
CONVOS=$(ls "$RESEARCH_DIR/convos" | grep -v "^Templates$" | sort | tr '\n' ', ' | sed 's/, $//')

# Build the additionalContext using jq for safe JSON encoding
CONTEXT="SESSION NOTE REMINDER (${DATE}):

Please write a session note for this conversation. Follow these steps:

1. IDENTIFY THE CONVO: Based on what we just discussed, determine which folder this session belongs to.
   Available convos: ${CONVOS}

2. IF UNSURE: Ask the user: \"Should I file this into an existing convo (if so, which one), or create a new folder?\"
   If creating new, follow the procedure in master-instructions.md (Creating a new convo folder).

3. CHECK EXISTING NOTE:
   - If convos/<folder>/notes/${DATE}.md does NOT exist → create it from convos/Templates/Convo Template.md
     Replace {{TOPIC}} with the folder name and {{DATE}} with ${DATE}.
   - If it DOES exist → ask the user: \"Today's note already exists in <folder>/notes/${DATE}.md. Should I append to it, or create a new file ${DATE}-02.md?\"
     Then act on their answer.

4. Write the note content based on what was actually discussed this session."

jq -n --arg ctx "$CONTEXT" '{
  hookSpecificOutput: {
    hookEventName: "Stop",
    additionalContext: $ctx
  }
}'
