---
name: note
description: Write a session note for this conversation in the correct convos folder.
---

Write a session note for this conversation. Follow these steps:

1. **Identify the convo folder.**

   **First, scan every user message in this conversation for `>>` at the start of a message.** The pattern is: a message that begins with `>>` (with or without a space after it), followed by the convo name. The convo name is the first word — extract it by taking everything up to the first space, period, comma, or colon, then convert to lowercase kebab-case.

   Examples — all of these are valid:
   - `>> music what are the best ambient artists?` → convo name is `music`
   - `>>music what are the best ambient artists?` → convo name is `music`
   - `>> ice-cream what was popular in 1970?` → convo name is `ice-cream`
   - `>>Kick-off. Give me the to-do list` → convo name is `kick-off`
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

5. **Write the note content** — summarise what was actually discussed this session: key decisions, action items, open questions, references used.

6. **Post to ticket.** Look up the slug matching the active convo/action in `bench-index.csv`:
   - Run: `python3 actions/on-demand/bench-ticket/bench_ticket.py post <slug> <note-file>`
   - The script posts the note as a comment to the linked Jira and/or Asana ticket.
   - If no ticket is found, the script searches automatically; if still none, it prints a proposal — relay that to the user.

**Naming convention:** Always use `YYMMDD-short-description.md` — never a bare `YYMMDD.md`.
**Note location:** Notes go directly in `convos/<folder>/YYMMDD-description.md`. NEVER create or write into `notes/` or `assets/` subfolders inside convo folders. Even if those subfolders already exist, ignore them — always write the note file directly in the convo folder root.
**Jira comment format:** One sentence summarising the session + the note file path. Never paste the full note body manually — `bench_ticket.py` handles formatting.
