---
name: note
description: Write a session note for this conversation in the correct convos folder.
---

Write a session note for this conversation. Follow these steps:

1. **Identify the convo folder.**

   **If `@<name>` was used in the conversation:**
   - The `@` marker declares the convo topic. The name after `@` IS the folder name. Do not ask the user to confirm or rename it.
   - Look for a folder under `convos/` that matches the name exactly (case-insensitive).
   - If an exact match exists (e.g. `@music` → `convos/music/`), use it.
   - If NO exact match exists, the topic is new. **Immediately create the folder** `convos/<name>/` (kebab-case) without asking. Add a row to `bench-index.csv` with `slug` = folder name, `type` = `convo`, `convo_folder` = `convos/<name>/`, and leave `jira`/`asana` empty. Then proceed to write the note.
   - Do NOT ask "what should I name it?" — the `@` marker already provided the name.
   - Do NOT fall back to a "closest" unrelated folder. `@music` does NOT match `the-bench`.

   **If no `@` marker was used:**
   - Determine the folder from the session topic. If it clearly matches an existing convo, use it.
   - If it doesn't clearly match, ask the user with these options:
     1. Create a new convo folder (suggest a name based on the session topic)
     2. Use an existing folder (list the closest matches)
   - Do NOT guess or force-attach a note to a convo that isn't clearly relevant. Always offer the "create new" option when the topic is new.

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
