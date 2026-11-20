---
name: update
description: Apply the bench template's new core changes to this bench as one commit. Usage: /update
model: haiku
---

If `personal/overlays/update.md` exists in this bench, read it first; where it differs from the steps below, it wins.

1. Run `bash core/bench-update/update.sh`.
2. Exit 0: reply with what changed in one or two lines. If it printed `RUN_SETUP`, run `bash setup.sh` and say so. Run `git push` if the bench has a remote.
   Lines starting `ENV:` come from `core/env/apply.py` (Cursor, Warp and Claude Code settings). Mention what it set in a few words. For each `ENV: CONFLICT <env>:<key> | here: … | bench: …` line, ask the user in one question per key whether to use the bench value or keep theirs, then run `python3 core/env/apply.py --choose <env>:<key>=bench|mine …` with every answer. The answer is remembered, so the same key is not asked again until the bench value changes.
3. Exit 1: reply with its message, one line.
4. Exit 3 (conflicts): for each listed file, read the conflict markers. Resolve a conflict yourself only when both sides can be kept without choosing between them (separate additions, a rename vs an edit elsewhere). Then `git add` the file and `git commit -m "bench update from template"` (append the CHANGES list), and push.
   If any conflict needs a choice between the user's version and the template's, run `git reset -q --hard HEAD`, and reply: the update was not applied, the files, and per file one line on what each side wants. Ask which to keep.
