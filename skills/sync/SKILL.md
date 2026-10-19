---
name: sync
description: Sync the bench with GitHub both ways: commit local work, pull what changed on GitHub, push. No session notes, no tickets. Usage: /sync "optional message"
model: haiku
---

Two-way sync of this repo with GitHub. The git half of `/push`, without session notes or ticket posting.

1. Follow steps 1 to 3 of `skills/push/SKILL.md`: see what changed, stage everything with its three checks, commit. A message passed as an argument is used as-is. Nothing to commit is normal; carry on.
2. Fetch and note what is coming in, before pulling:
   ```bash
   git fetch origin
   git log --oneline HEAD..origin/main
   ```
3. Pull and push, as in steps 4 and 5 of `/push`:
   ```bash
   git pull --rebase origin main
   git push
   ```
   On a rebase conflict, stop and list the conflicting files. If the push is rejected, repeat this step once. Never `--force`.
4. Do not write session notes and do not touch Jira or Asana.

Reply in at most three lines: what came in from GitHub (commit count, plus subjects when 5 or fewer), what went up (commit message and file count, or "nothing to push"), and anything left out of the commit.
