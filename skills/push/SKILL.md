---
name: push
description: Commit all finished work in the repo and push to remote. Usage: /push "optional message" (add --mine to stage only this session's files)
model: haiku
---

Commit **everything that's finished and unpushed** and push to remote. Follow these steps:

1. Run `git diff --cached`, `git diff`, and `git status` to understand what has changed. Expect to see changes you did not make — that is normal and they go in too.
2. If a commit message was passed as an argument, use it exactly. Otherwise write a message from the diff: a one-line summary (imperative mood, under 72 characters), plus a short body naming each workstream in the commit when it spans several. Describing what you staged is ordinary bookkeeping — never treat it as a reason to narrow the commit, and never raise it with the user as a tradeoff.
3. **Stage everything**, then commit — before pulling, since `git pull --rebase` refuses to run with uncommitted changes.

   > Bench work lives in independent folders (`tools/`, `convos/`), so a commit spanning several of them never entangles a revert. Withholding finished work has a real cost: it stays unpushed and un-backed-up until someone remembers it. Do not split commits by which session produced the change.

   ```bash
   git add -A
   git diff --cached --name-only
   ```

   Three things to check before committing:
   - **Runtime and generated artifacts** don't belong in git even when untracked and finished — logs, rolling state backups, caches. If something large and machine-written shows up untracked, exclude it (`git add -A -- . ':!<path>'`) and offer to add a `.gitignore` rule. Note that already-tracked machine-maintained files (`_memory-index.md`, `_memory-master.md`, `bench-index.csv`, action `state.json`) DO get committed — they are versioned on purpose.
   - **Credential-shaped paths** (`*token*`, `*key*`, `*secret*`, `.env`) — check contents and confirm with the user before they reach the remote. Prose mentioning a variable name is fine; an actual value is not.
   - **Broken partial commits** — if a staged file imports something from a file you'd be leaving out, include that file too.

   If the user passes `--mine`, stage only the files this session changed, by explicit path.

   ```bash
   git commit -m "<message>"
   ```
   If there is nothing of yours to commit, skip this step and continue (a pull + push may still be needed to sync earlier commits).
4. **Pull before pushing** to integrate any commits from other machines (e.g., the OpenClaw laptop). A plain `git push` never overwrites the remote — without this step it would simply be rejected if the branch is behind:
   ```bash
   git fetch origin && git pull --rebase origin "$(git branch --show-current)"
   ```
   Do NOT swallow errors. If the rebase reports conflicts, STOP, report the conflicting files to the user, and resolve them before continuing — do not proceed to push with an unfinished rebase.
5. **Push:**
   ```bash
   git push
   ```
   If the push is still rejected (the remote moved again between fetch and push), repeat steps 4–5 once. Never use `--force`.
6. **Create session notes.** From the diff, identify which `convos/` folders are involved. For each relevant folder, create or append a session note following all rules in the `/note` command (YYMMDD-short-description.md, Convo Template, check for existing note today first). Files outside `convos/` do not automatically require a note — only create one if the change is clearly tied to a tracked conversation.

7. **Post to tickets — Jira only, never Asana.** For each note written:
   - Look up the slug in `bench-index.csv` using `bench_ticket.py lookup <slug>`.
   - If a Jira ticket is linked, **show the user** the ticket key, the comment that would be posted, and **ask for confirmation** before posting. Do NOT post automatically.
   - Only after the user confirms, run:
     ```bash
     python3 tools/on-demand/bench-ticket/bench_ticket.py post <slug> <note-file>
     ```
     This is Jira-only and never touches the Asana API. See CLAUDE.md "Asana — Session Notes Never Post Here".
   - If no ticket is found, inform the user — do not search or auto-link tickets.

After running, report: commit message used, how many files were staged, **anything deliberately left out and why** (should normally be nothing but runtime artifacts), push success/failure, note files created, tickets posted.

**Ticket references:** Every time you mention a Jira ticket in output (tables, lists, or inline), always include the ticket title/summary alongside the key. For example: `ZHEN-6235 — REF workflow redesign`, not just `ZHEN-6235`.
