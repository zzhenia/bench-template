---
name: e
description: Done with this window — write the session note now and close the tab. Usage: /e
model: haiku
---

Zhenia is finished with this terminal window. Do these steps in order, with no
questions and no confirmation prompts.

1. **Write the session note** the way `/note` does: read `skills/note/SKILL.md`
   and follow its steps 1–5 (find the `>>` convo, today's date, the file, the
   content). Three differences:
   - Never ask about the folder. With no `>>` marker, use the closest existing
     convo; if none clearly fits, use `convos/the-bench/`.
   - If today's note already exists, append under `#### /e — HH:MM` without
     asking.
   - Skip step 6 entirely: no Jira lookup, no candidates search, no posting.
   If the conversation has fewer than 3 real user messages, write nothing.

2. **Record the note** so the auto-note watcher and the launcher do not write a
   second one:

   ```bash
   python3 tools/recurring/auto-note/auto_note.py --mark <note-path>
   ```

   (With nothing written, skip this.)

3. **Reply with two lines and nothing else.** First line: `Note: <note-path>
   (not committed)` or `Nothing to note.` Last line: the single word `ZVBYE`.
   The terminal launcher watches the output for that word and turns it into
   `/exit`; the tab closes on its own. If the tab is still open after a few
   seconds, Zhenia types `/exit`.
