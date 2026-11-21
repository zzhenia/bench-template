---
name: e
description: Done with this window — write the session note now and close the tab. Usage: /e
model: haiku
---

If `personal/overlays/e.md` exists in this bench, read it first; where it differs from the steps below, it wins.

The user is finished with this terminal window. Do these steps in order, with no
questions and no confirmation prompts.

1. **Write the session note** the way `/note` does: read `core/skills/note/SKILL.md`
   and follow its steps 1–5 (find the `>>` convo, today's date, the file, the
   content). Three differences:
   - Never ask about the folder. With no `>>` marker, use the closest existing
     convo; if none clearly fits, use `convos/the-bench/`.
   - If today's note already exists, append under `#### /e — HH:MM` without
     asking.
   - Skip step 6 entirely: no ticket lookup, no candidates search, no posting.
   If the conversation has fewer than 3 real user messages, write nothing.

2. **Record the note** so the auto-note watcher and the launcher do not write a
   second one:

   ```bash
   python3 core/tools/auto-note/auto_note.py --mark <note-path>
   ```

   (With nothing written, skip this.)

3. **Reply with one line and nothing else:** `Note: <note-path> (not committed)`
   or `Nothing to note.` If the overlay names a close word for this bench's
   terminal launcher, add it as a second, last line on its own; the launcher
   turns it into `/exit`. Without one, the user types `/exit`.
