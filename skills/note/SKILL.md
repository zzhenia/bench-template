---
name: note
description: Write a session note for this conversation in the correct convos folder.
model: haiku
---

Write a session note for this conversation. Follow these steps:

1. **Identify the convo folder.**

   **First, scan every user message in this conversation for `>>` at the start of a message.** The pattern is: a message that begins with `>>` (with or without a space after it), followed by the convo name. The convo name is the first word — extract it by taking everything up to the first space, period, comma, or colon, then convert to lowercase kebab-case.

   Examples — all of these are valid:
   - `>> music what are the best ambient artists?` → convo name is `music`
   - `>>music what are the best ambient artists?` → convo name is `music`
   - `>> ice-cream what was popular in 1970?` → convo name is `ice-cream`
   - `>>Kick-off. Give me the to-do list` → convo name is `kick-off`
   - **Aliases:** `autopilot` → `yt-autopilot` (Zhenia's shorthand; `convos/autopilot/` no longer exists — never create it).
   - `>> 2026-taxes how do I file my return?` → convo name is `2026-taxes`
   - `>>Cars how can I buy a car?` → convo name is `cars`

   **If a `>> <name>` marker was found:**
   - The convo name is decided. Do NOT ask the user to confirm, rename, or choose.
   - If `convos/<name>/` exists, use it.
   - If it does NOT exist, **create it immediately**: `mkdir -p convos/<name>/`. Add a row to `bench-index.csv` with `slug` = the name, `type` = `convo`, `convo_folder` = `convos/<name>/`, and leave `jira`/`asana` empty.
   - Then proceed directly to step 2. No questions.

   **If NO `>>` marker was found anywhere in the conversation:**
   - Determine the folder from the session topic. If it clearly matches an existing convo, use it.
   - If it doesn't clearly match, ask the user with these options:
     1. Create a new convo folder (suggest a name based on the session topic)
     2. Use an existing folder (list the closest matches)
   - Do NOT guess or force-attach a note to a convo that isn't clearly relevant.

2. **Get today's date** in YYMMDD format (e.g. 260403).

3. **Choose a short description** — one or two kebab-case words summarising the session topic (e.g. `csv-fix`, `push-command`, `folder-structure`).

4. **Check for an existing note** at `convos/<folder>/YYMMDD-<description>.md` and also any file matching `convos/<folder>/YYMMDD*.md`.
   - If none exists → create `YYMMDD-<description>.md` from `convos/Templates/Convo Template.md`, replacing `{{TOPIC}}` with the folder name and `{{DATE}}` with today's date.
   - If one already exists → ask: "Today's note already exists as `<filename>`. Should I append to it, or create a new file `YYMMDD-<description>-02.md`?" Then act on the answer.
   - **Exception — auto-notes.** If the existing note contains an `#### Auto-note —` section or a `written automatically` HTML comment, it was written by the `auto-note` watcher while the window sat idle. **Append to it without asking**, under a `#### /note — <HH:MM>` heading, and cover anything the auto-note got wrong or missed. Do not create a second file, and do not delete the auto-note section.

5. **Write the note content** — summarise what was actually discussed this session: key decisions, action items, open questions, references used.

6. **Post to ticket — Jira only, never Asana. ALWAYS confirm the target ticket with the user first. NEVER post automatically, even when only one ticket is linked.** Many convos are broad topics that span many different tickets (e.g. `personal-finance`, `colombia-lifestyle`), so a single linked key is NOT a safe default to post to.

   Session notes never post to Asana and this step must never call the Asana API — no search, no lookup, no comment. `bench_ticket.py post` and `bench_ticket.py candidates` are Jira-only. See CLAUDE.md "Asana — Session Notes Never Post Here".

   **ZVC job detection:** If the note filename or content references a 4-digit ZVC job number (e.g. `0017`, `0023`, `0051`), search for the matching ZVC ticket with `python3 tools/on-demand/bench-ticket/bench_ticket.py candidates <job-number>` and include the ZVC result as the **first option** in the ticket list presented to the user. ZVC job notes should typically go to the ZVC ticket (e.g. `ZVC-462`), not the parent convo ticket (e.g. `ZHEN-6245`). Still confirm — don't auto-post.

   **If the slug already has a `jira` value in bench-index.csv:**
   - The `jira` column may hold one key or a **comma-separated list** of keys.
   - First read the linked key(s) with `python3 tools/on-demand/bench-ticket/bench_ticket.py lookup <slug>`. **Do NOT run a bare `post` for a single linked key — it posts immediately with no confirmation.**
   - Present the linked ticket(s) **with their titles** plus a "Skip — don't post" option, and **wait for the user to choose** the ticket relevant to *this* session.
   - Only after the user confirms, post to the chosen ticket with an explicit key: `python3 tools/on-demand/bench-ticket/bench_ticket.py post <slug> <note-file> --key <KEY>`
   - **Relevant ticket not yet in the list:** pass it via `--key <KEY>` — `post` appends it to the slug's comma-separated `jira` list automatically.

   **If the slug has NO linked Jira ticket:**
   - Search for candidates: `python3 tools/on-demand/bench-ticket/bench_ticket.py candidates <slug>`
     This returns JSON with up to 3 Jira results, each with `source`, `key`, and `title`.
   - Present a numbered list to the user showing each candidate's key and title, e.g.:
     ```
     1. [Jira] ZHEN-1234 — Thumbnail workflow improvements
     2. [Jira] ZHEN-5678 — PI design system updates
     3. Skip — don't post to any ticket
     ```
   - **Wait for the user to choose.** Do NOT auto-link or auto-post.
   - If the user picks a ticket, update bench-index.csv with that link (`python3 tools/on-demand/bench-ticket/bench_ticket.py update <slug> --jira <KEY>`), then post the comment.
   - If the user picks "Skip", do not post and move on.

**Naming convention:** Always use `YYMMDD-short-description.md` — never a bare `YYMMDD.md`.
**Memory files:** `_memory-index.md` and `_memory-master.md` inside convo folders are machine-maintained memory files (nightly convo-memory job). NEVER write session content into them, never edit them, and never count them as existing notes when checking for today's note.
**Note location:** Notes go directly in `convos/<folder>/YYMMDD-description.md`. NEVER create or write into `notes/` or `assets/` subfolders inside convo folders. Even if those subfolders already exist, ignore them — always write the note file directly in the convo folder root.
**Ticket comment format:** `bench_ticket.py` posts a brief summary (title + date + file path) to Jira — never the full note body. External ticket comments must be short pointers back to the bench, rendered in rich text (ADF), not Markdown.
**Ticket references:** Every time you mention a Jira ticket in output (tables, lists, or inline), always include the ticket title/summary alongside the key. For example: `ZHEN-6235 — REF workflow redesign`, not just `ZHEN-6235`.
