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
└── instructions.md  ← the prompt/procedure Claude follows
```

**How to use:** Drop reference material into `assets/`, then invoke the action by asking Claude to follow `instructions.md` in that folder.

**Current actions:** See `bench-index.csv` (rows where `type = action` or `type = both`).

---

## convos/

Each folder is an **ongoing topic** with persistent context across sessions.

**Schema:**
```
convos/<topic-name>/
├── YYMMDD-short-description.md   ← session notes live directly here
├── YYMMDD-another-topic.md
└── ...
```

**How to use:** At the start of a session, read the latest note(s) in the convo folder (they carry the standing context). Write a new dated note at the end of each session summarizing decisions made.

**Session note naming convention:** `YYMMDD-short-description.md` — date followed by one or two kebab-case words describing the session topic (e.g. `260405-csv-fix.md`, `260403-folder-structure.md`)

**Current convos:** See `bench-index.csv` (rows where `type = convo` or `type = both`).

### The @topic convention

**IMPORTANT:** When a user message starts with `@word` or `@hyphenated-word` followed by a space (e.g. `@music`, `@ice-cream`, `@faa-rules`), this is a **convo topic declaration**, NOT a file reference. The word after `@` is the convo name for this session.

**When you see this pattern:**
1. Acknowledge the topic internally — this session belongs to convo `<name>`.
2. Answer the user's question normally.
3. When `/note` is run later, use `<name>` as the convo folder. If `convos/<name>/` doesn't exist, create it.

**Examples:**
- `@music what are the best ambient artists?` → convo is `music`, answer the question about ambient artists
- `@cars how can I buy a car in 2026?` → convo is `cars`, answer the question about buying cars
- `@faa-rules tell me about drone regulations` → convo is `faa-rules`, answer about drone regulations

**Do NOT** interpret the `@` as a file reference, code symbol, or resource lookup. In this workspace, `@word` at the start of a message always means "this conversation is about [word]."

If the convo folder exists, read the latest notes to restore context before responding. If it doesn't exist yet, just answer the question — the folder will be created when `/note` runs.

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

### Ticket workflow (run at every `/note` and `/push`)

1. **Look up the slug** in `bench-index.csv` for the active convo/action.
2. **If a ticket exists** — post the session note as a comment using `bench_ticket.py`.
3. **If no ticket exists** — the script searches Jira+Asana automatically; if still none, it proposes creation.
4. Always update `bench-index.csv` after adding a new ticket key/GID.

---

## Git Workflow

- Branch: `main`
- Commit after significant changes: `git add . && git commit -m "description"`
- Push: `git push`
- `.gitignore` excludes: `.obsidian/`, `.DS_Store`, `config/keys.env`

---

## Claude Operating Rules

1. **Read before acting.** At the start of a topic session, read the latest notes in the convo folder before responding.
2. **Write session notes.** After meaningful sessions, create a dated note directly in the convo folder summarizing decisions, context, and next steps.
3. **Don't alter sub-folder file names.** Keep the standard `instructions.md` files inside `actions/` folders only. The root guide is `master-instructions.md`.
4. **assets/ is for action inputs only.** Drop source material (PDFs, screenshots, CSVs, text) into the action's `assets/` folder — never commit credentials or sensitive personal data. Convo folders do not have assets subfolders.
5. **Keep commits clean.** Commit after meaningful milestones, not every file save.
