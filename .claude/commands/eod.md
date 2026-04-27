---
name: eod
description: End-of-day wrap-up — save progress, create session note, document next steps, and stop any running services.
---

The user is ending their working day. Perform these steps quickly and without asking questions:

1. **Stop running services.** Kill any app servers started during this session:
   ```bash
   kill $(lsof -ti:8001) 2>/dev/null   # YT Autopilot
   kill $(lsof -ti:7391) 2>/dev/null   # Actions Dashboard
   ```

2. **Create/update the session note.** Use the `/note` workflow — determine the convo folder from the conversation context, write a session note summarising:
   - What was built or changed this session
   - Key decisions made
   - Current state (what works, what's broken)
   - Blockers or open questions
   - What to do next (prioritised)

3. **Update memory.** If the session involved a significant project, update or create a memory file in the memory directory with the current status so the next conversation can pick up immediately.

4. **Post to ticket.** Run `bench_ticket.py post` to push the note to the linked Jira/Asana ticket (if any).

5. **Commit and push.** Stage all changes, create a commit with a message summarising the session's work, and push to the remote. Use the `/push` workflow — auto-generate the commit message from the diff.

6. **Report.** Tell the user:
   - What was saved and where
   - What to reference tomorrow to resume (`/note`, memory file, plan file if applicable)
   - A one-line summary of where things stand

Do NOT ask the user any questions — make reasonable choices for all decisions (convo folder, note filename, etc.). The goal is a fast, clean exit.
