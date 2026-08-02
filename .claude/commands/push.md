---
name: push
description: Stage this session's changes, commit with an auto-generated message based on the diff, and push to remote. Usage: /push "optional message" (add --all to stage everything)
---

Stage **this session's** changes and push to remote. Follow these steps:

1. Run `git diff --cached`, `git diff`, and `git status` to understand what has changed. Expect to see changes you did not make — see step 3.
2. If a commit message was passed as an argument, use it exactly. Otherwise write a concise one-line message (imperative mood, under 72 characters) based on the diff.
3. **Stage ONLY the files this session changed**, then commit — before pulling, since `git pull --rebase` refuses to run with uncommitted changes.

   > **Never use `git add -A` or `git add .`** More than one Claude session is often open on a repo at the same time. `git add -A` sweeps the other session's half-finished work into your commit under an unrelated message, which makes history misleading and hard to revert.

   - Work out which files **you** created or edited in this conversation, and stage them by explicit path:
     ```bash
     git add -- <path1> <path2> ...
     ```
   - Verify the staged set is exactly what you intended — not a superset:
     ```bash
     git diff --cached --name-only
     ```
   - Anything else in `git status` belongs to another session or to the user. **Leave it unstaged**, and list it in your final report so they know it was skipped and why.
   - If you genuinely cannot tell whether a modified file is yours, **ask** rather than assume. Machine-maintained files (`_memory-index.md`, `_memory-master.md`, `trigger.log`, `state.json`) are almost never yours.
   - Only when the user explicitly asks to push everything — `/push --all`, or "commit everything" in their own words — may you use `git add -A`.
   - Before committing, glance at the staged paths for anything credential-shaped (`*token*`, `*key*`, `*secret*`, `.env`). If something looks sensitive, check its contents and confirm with the user before it goes to the remote.

   ```bash
   git commit -m "<message>"
   ```
   If there is nothing of yours to commit, skip this step and continue (a pull + push may still be needed to sync earlier commits).
4. **Pull before pushing** to integrate commits from other machines. A plain `git push` never overwrites the remote — without this it would simply be rejected if the branch is behind:
   ```bash
   git fetch origin && git pull --rebase origin "$(git branch --show-current)"
   ```
   Do NOT swallow errors. If the rebase reports conflicts, STOP, report the conflicting files to the user, and resolve them before continuing — do not push with an unfinished rebase.
5. **Push:**
   ```bash
   git push
   ```
   If the push is rejected because the remote moved again, repeat steps 4–5 once. Never use `--force`.
6. **Create session notes.** From the diff, identify which `convos/` folders are involved. For each relevant folder, create or append a session note following all rules in the `/note` command (YYMMDD-short-description.md, Convo Template, check for existing note today first). Files outside `convos/` do not automatically require a note — only create one if the change is clearly tied to a tracked conversation.

7. **Post to tickets.** For each note written, run:
   ```bash
   python3 actions/on-demand/bench-ticket/bench_ticket.py post <slug> <note-file>
   ```
   where `<slug>` matches the convo/action folder name in `bench-index.csv`. Relay any "no ticket found" proposals to the user.

After running, report: commit message used, **which files were staged**, **which changed files were deliberately left unstaged** (and that they belong to another session or the user), push success/failure, note files created, tickets posted.

**Ticket references:** Every time you mention a Jira or Asana ticket in output (tables, lists, or inline), always include the ticket title/summary alongside the key. For example: `ZHEN-6235 — REF workflow redesign`, not just `ZHEN-6235`.
