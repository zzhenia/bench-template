---
name: push
description: Stage all changes, commit with an auto-generated message based on the diff, and push to remote. Usage: /push "optional message"
---

Stage all changes and push to remote. Follow these steps:

1. Run `git diff --cached`, `git diff`, and `git status` to understand what has changed.
2. If a commit message was passed as an argument, use it exactly. Otherwise write a concise one-line message (imperative mood, under 72 characters) based on the diff.
3. Run:
   ```bash
   git add -A && git commit -m "<message>" && git push
   ```
4. **Create session notes.** From the diff, identify which `convos/` folders are involved. For each relevant folder, create or append a session note following all rules in the `/note` command (YYMMDD-short-description.md, Convo Template, check for existing note today first). Files outside `convos/` do not automatically require a note — only create one if the change is clearly tied to a tracked conversation.

5. **Post to tickets.** For each note written, run:
   ```bash
   python3 actions/on-demand/bench-ticket/bench_ticket.py post <slug> <note-file>
   ```
   where `<slug>` matches the convo/action folder name in `bench-index.csv`. Relay any "no ticket found" proposals to the user.

After running, report: commit message used, push success/failure, note files created, tickets posted.
