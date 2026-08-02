# The Bench — Master Instructions for Claude

This file is the operating guide for Claude Code in your bench workspace. Read it at the start of every session.

---

## Your Name

Your name is stored in `config/keys.env` under `BENCH_OWNER`. Read this value at the start of each session and use it when personalizing output (e.g. the Actions Dashboard title, greetings). If it's empty, address the user generically.

---

## What This Workspace Is

Your bench is a unified personal knowledge workspace that combines:
- **Claude Code** (terminal AI with persistent context)
- **VS Code** (editing environment)
- **Obsidian** (visual note-linking and search across the entire folder)
- **GitHub** (private version control)

---

## Top-Level Structure

```
your-bench/
├── master-instructions.md   ← this file (master guide)
├── bench-index.csv          ← single source of truth for actions, convos, and tickets
├── setup.sh                 ← first-run setup script
├── actions/                 ← repeatable tasks Claude executes
├── config/                  ← API keys and environment config
└── convos/                  ← ongoing topics and session notes
```

---

## actions/

Each folder is a **repeatable, parameterized task** — the Claude equivalent of a custom GPT.

**Schema:**
```
actions/<action-name>/
├── assets/            ← source material (PDFs, screenshots, text)
├── instructions.md    ← the prompt/procedure Claude follows
├── eval.md            ← evaluation checklist (test cases, pass/fail criteria)
└── BUGS.md            ← known bugs and issues
```

**How to use:** Drop reference material into `assets/`, then invoke the action by asking Claude to follow `instructions.md` in that folder.

**Action matching rule:** Before responding to any task, check whether the request matches an existing action in `actions/`. If it does, read and follow that action's `instructions.md` before producing any output. Do not rely on general knowledge or freeform generation when a dedicated action exists — the instructions file is the source of truth for tone, format, and content rules.

**Current actions:** See `bench-index.csv` (rows where `type = action` or `type = both`).

**When creating a new action**, always do all four:
1. Create the action folder under `actions/on-demand/` or `actions/recurring/`.
2. Write an `eval.md` with test cases covering the action's core functionality, edge cases, and expected behavior. Each test should have steps and pass/fail criteria. Also create a `BUGS.md` (can start empty with just a heading).
3. Add a row to `bench-index.csv`.
4. Add an entry to the `ACTIONS` list in `actions/on-demand/actions-dashboard/server.py` — the dashboard is the comprehensive catalogue of everything built on this bench.

---

## convos/

Each folder is an **ongoing topic** with persistent context across sessions.

**Schema:**
```
convos/<topic-name>/
├── YYMMDD-short-description.md   ← session notes live directly here (Layer 0 — the log)
├── YYMMDD-another-topic.md
├── _memory-index.md              ← Layer 1 — detailed memory with [YYMMDD] citations (machine-maintained)
└── _memory-master.md             ← Layer 2 — compact wake summary, ~60 lines (machine-maintained)
```

**How to use:** At the start of a session, read `_memory-master.md` plus any notes dated after its `through YYMMDD` watermark (line 2 of the master). If no master exists, read the latest note(s). Write a new dated note at the end of each session summarizing decisions made.

### Memory compression (Layer 1/2)

Convo folders with 5+ notes get OptMem-style three-layer memory, maintained by the nightly `convo-memory` job (`actions/recurring/convo-memory/`, Claude Haiku, 02:30):

- **Layer 0 (log):** dated session notes — written by `/note` as always, never deleted or edited by the pipeline
- **Layer 1 (index):** `_memory-index.md` — every fact/decision as a `- [YYMMDD]` bullet citing its source note; only grows, never loses evidence
- **Layer 2 (wake):** `_memory-master.md` — compact summary regenerated from the index, capped at ~60 lines regardless of note count

Rules: never hand-edit `_memory-*.md` files; never write session content into them. Details: `actions/recurring/convo-memory/instructions.md`.

**Session note naming convention:** `YYMMDD-short-description.md` — date followed by one or two kebab-case words describing the session topic (e.g. `260405-csv-fix.md`, `260403-folder-structure.md`)

**Current convos:** See `bench-index.csv` (rows where `type = convo` or `type = both`).

### The >> topic convention

When a user message starts with `>>` (with or without a space after it) followed by a name, this is a **convo topic declaration**. The first word after `>>` is the convo name for this session. Extract it by taking everything up to the first space, period, comma, or colon, then convert to lowercase kebab-case. The name can be any string.

**When you see this pattern, follow these steps IN ORDER before doing anything else:**

1. Extract the convo name (first word after `>>`, lowercased, kebab-case).
2. Check if `convos/<name>/` exists.
3. **If the folder exists: read its memory before responding.** The user is continuing an existing conversation — the memory contains the context you need. Use the layered read path:
   - If `_memory-master.md` exists: read it, extract the `through YYMMDD` watermark from line 2, and read only notes dated **after** the watermark. Drill into `_memory-index.md` when the question needs detail behind a master line; open a raw note `[YYMMDD]` as a last resort.
   - If no `_memory-master.md` exists: read all notes (small folder).
4. If the folder does not exist: this is a new topic. Answer the question normally — the folder will be created when `/note` runs.
5. This session belongs to convo `<name>`. Remember it for when `/note` is run.

**IMPORTANT:** The `>>` marker means this is a bench conversation topic, not a coding question. Even if the topic seems unrelated to software engineering (lamps, music, cars, taxes), treat it as a legitimate convo. Read the notes and respond helpfully.

**Examples:**
- `>> music what are the best ambient artists?` → convo is `music`
- `>>music what are the best ambient artists?` → convo is `music`
- `>>Kick-off. Give me the to-do list` → convo is `kick-off`
- `>>lamps advise on options two and three?` → convo is `lamps`, read `convos/lamps/*.md` first

---

### Creating a new convo folder

When a conversation doesn't clearly belong to an existing folder, ask: *"Should I file this into an existing convo, or create a new one?"*

If creating a new convo:

1. Name the folder in kebab-case (e.g. `learning-spanish`).
2. Create the folder under `convos/`. Notes go directly inside it — no subfolders needed.
3. Add a row to `bench-index.csv`:
   - `slug` = folder name
   - `type` = `convo`
   - Leave `jira` and `asana` empty for now

---

## Bench Index

`bench-index.csv` (bench root) is the single source of truth for all actions and convos, and their linked tickets.

### Columns

| Column | Values | Meaning |
|---|---|---|
| `slug` | kebab-case string | Unique identifier — matches the folder name |
| `type` | `action` / `convo` / `both` | Whether it lives in `actions/`, `convos/`, or both |
| `convo_folder` | path or empty | Relative path to the convo folder |
| `action_folder` | path or empty | Relative path to the action folder |
| `jira` | ticket key or empty | e.g. `PROJ-42` |
| `asana` | task GID or empty | Asana task ID (numeric) |

Items where `type = both` share a single row.

### Linking external integrations (Jira, Asana, etc.)

**Never add a Jira ticket, Asana task, or any other external integration to `bench-index.csv` without explicit user confirmation.** When a new action or convo is created, leave the `jira`, `asana`, and other integration columns empty. If `bench_ticket.py` proposes a match, relay the proposal to the user and wait for approval before writing it to the index. The same applies when updating existing rows with new ticket links.

### Ticket workflow (run at every `/note` and `/push`)

1. **Look up the slug** in `bench-index.csv` for the active convo/action.
2. **If a ticket exists** — post a brief comment using `bench_ticket.py` (title + date + file path only — never the full note body). Comments on external systems (Jira/Asana) must be short pointers back to the bench, rendered in rich text (ADF for Jira, HTML for Asana), not Markdown.
3. **If no ticket exists** — the script searches Jira+Asana automatically; if still none, it proposes creation. **Do not auto-link** — relay the proposal to the user and wait for confirmation.
4. Only update `bench-index.csv` with a new ticket key/GID after the user confirms the link.

---

## Git Workflow

- Branch: `main`
- Commit after significant changes: `git add . && git commit -m "description"`
- Push: `git push`
- `.gitignore` excludes: `.obsidian/`, `.DS_Store`, `config/keys.env`

---

## Claude Operating Rules

1. **Read before acting.** At the start of a topic session, read the convo folder's `_memory-master.md` plus notes newer than its watermark (or the latest notes if no master exists) before responding.
2. **Write session notes.** After meaningful sessions, create a dated note directly in the convo folder summarizing decisions, context, and next steps.
3. **Don't alter sub-folder file names.** Keep the standard `instructions.md` files inside `actions/` folders only. The root guide is `master-instructions.md`.
4. **assets/ is for action inputs only.** Drop source material (PDFs, screenshots, CSVs, text) into the action's `assets/` folder — never commit credentials or sensitive personal data. Convo folders do not have assets subfolders.
5. **Keep commits clean.** Commit after meaningful milestones, not every file save.

---

## Writing Style

These rules apply to all produced writing: notes, SOPs, briefs, articles, descriptions, generated content. They do not apply to code, commit messages, or casual conversation unless the output is meant to be read as prose.

### Voice and Tone

- Write like you speak, but don't be cheesy. Natural, direct, confident.
- Use American English.
- Use the active voice. Passive voice makes writing ambiguous and hard to follow. Aim for active 90% of the time.
- Avoid first-person ("I," "me," "myself") when writing on behalf of an organization or producing reference material. "We" is acceptable; rephrasing to remove the pronoun entirely is better.
- Be authoritative. Don't hedge. If you're unsure, research until you are sure. Drop phrases like "It is said that…", "This is possibly…", "Studies show…" (cite the study instead).
- Put yourself in the position of someone encountering the topic for the first time. Spell out acronyms on first use (unless universally known, like GPS). Don't assume shared context.

### Structure

- Don't bury the lead. The most relevant information belongs in the opening section. Keep introductions under 100 words.
- Keep paragraphs to 2-4 sentences. Keep sentences around 25 words or fewer. Use single spaces.
- For anything longer than ~800 words, include a short bullet-point summary after the introduction.
- Use bullet points, tables, and bolding where they make information easier to scan. Bold sparingly.
- Add relevant hyperlinks when referencing specific information.
- Conclusions should land one or two key takeaways, then point the reader somewhere next.

### Rhythm and Flow

- Vary sentence length. A mix of short, medium, and long sentences creates a rhythm that keeps the reader moving. Five short sentences in a row become monotonous; one long sentence surrounded by short ones has impact.
- Create a "slippery slope": each sentence should pull the reader into the next. Ask questions, then answer them. Build small journeys within sections. Use visual metaphors and concrete examples to hold attention.
- If you think an article, paragraph, sentence, or word is too long, it is.

### Banned Phrases

Avoid these unless there is genuinely no better alternative:

"In conclusion", "Not only X, but also Y", "It is important to note that", "That being said", "Ultimately", "Furthermore", "Moreover", "Additionally", "For instance", "For example", "This means that", "In other words", "In summary", "As previously mentioned", "Crucial role", "Play a crucial role", "Vital role", "Whether you're a [X] or a [Y]", "Significant", "Important", "Essential", "Beneficial", "Solution", "Impactful", "Enhance", "Efficient", "Optimize", "Challenges", "Increased efficiency", "Crucial", "Lucrative", "Ensures"

### Punctuation

- Minimize em dashes; default to parentheses instead.
- Use AP-style title capitalization for headings.

### AI Usage

- AI is a tool, not a crutch. Use it for outlines, prompts, proofreading, and explanation. Never copy-paste generated text wholesale. Rewrite, reshape, and own the output.
- Always verify facts that come from AI. It cannot be trusted as a fact-checker.

### Quality Checks

Run produced writing through these (or their equivalents) before considering it done:

1. **Hemingway Editor** (or similar) — aim for 6th to 8th grade readability. Avoid red and green highlights; use yellow sparingly.
2. **Grammarly** (or similar) — catch grammar issues, but understand every suggestion before accepting it. Dismiss the ones that make the sentence sound unnatural.
3. **Capitalize My Title** (AP style) — for headings and titles.
