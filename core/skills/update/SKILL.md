---
name: update
description: Apply the bench template's new core changes to this bench as one commit. Usage: /update
model: haiku
---

If `personal/overlays/update.md` exists in this bench, read it first; where it differs from the steps below, it wins.

1. Run `bash core/bench-update/update.sh`.
2. Exit 0: reply with what changed in one or two lines. If it printed `RUN_SETUP`, run `bash setup.sh` and say so. Run `git push` if the bench has a remote.
3. Exit 1: reply with its message, one line.
4. Exit 3 (conflicts): for each listed file, read the conflict markers. Resolve a conflict yourself only when both sides can be kept without choosing between them (separate additions, a rename vs an edit elsewhere). Then `git add` the file and `git commit -m "bench update from template"` (append the CHANGES list), and push.
   If any conflict needs a choice between the user's version and the template's, run `git reset -q --hard HEAD`, and reply: the update was not applied, the files, and per file one line on what each side wants. Ask which to keep.
