# The Bench

A personal knowledge and automation workspace built on an agent CLI (Claude Code or Codex), Obsidian, and GitHub.

Each team member runs their own bench — a private repo where the agent has persistent context, session notes are tracked as markdown, and repeatable tasks live as versioned actions.

---

## Free and paid

**Free (this template):** everything in this repo, run from your own CLI with no
limitation. Every tool, skill, command and scheduled job listed below is included.

**Paid:** the desktop app and agentic capability. Nothing in the free bench depends on it.

---

## Prerequisites

- An agent CLI: [Claude Code](https://claude.ai/code) or [Codex](https://github.com/openai/codex).
  Claude Code reads `CLAUDE.md`; Codex reads `AGENTS.md`, which carries the same rules.
- Any editor or IDE with a terminal, or a terminal on its own
- [Obsidian](https://obsidian.md) (optional, for note linking and search)
- Python 3.10+
- A GitHub account

API integrations (Jira, Asana, Toggl) are optional; the bench works without them. `setup.sh` asks which project-management tool you use (`jira`, `asana` or `none`) and saves it as `PM_TOOL` in `config/bench.env`; with `none` there is no ticket step.

---

## Quick start

**1. Create your bench from this template**

Click **"Use this template"** on GitHub → name it (e.g. `my-bench`) → set it to Private → click **Create repository**.

**2. Clone it**

```bash
mkdir -p ~/dev && cd ~/dev
git clone https://github.com/your-username/my-bench.git
```

Open the folder in your editor, or `cd ~/dev/my-bench` in a terminal. The bench
files (`.claude`, `actions`, `config`, `convos`, …) should sit at the root, not
inside a subfolder.

**3. Run setup**

In a terminal at the repo root:

```bash
chmod +x setup.sh && ./setup.sh
```

This copies `config/keys.env.template` → `config/keys.env`. Fill in your API keys before running any actions.

**4. Enter your name**

During setup you'll be asked: *"Hello! How shall I call you?"* Your name is saved in `config/keys.env` as `BENCH_OWNER` and appears in the Actions Dashboard header (e.g. "Ben's Actions Dashboard"). Change it anytime by editing `config/keys.env`.

**5. Start your agent**

```bash
claude .     # or: codex
```

The agent reads the bench rules and `master-instructions.md` at the start of
each session. Your commands (`/note`, `/push`, `/status`, `/ai`) are ready immediately.

**6. Optional: install the startup layer**

This is what makes a bench feel like a bench rather than a folder. It is one
`~/.zshrc` block (`core/shell/bench.zsh`); the setup notes are in the
READMEs under `config/`. Once installed, every new terminal tab in the bench runs
this sequence:

1. **Pick a conversation.** The tab opens on a numbered list of your most
   recently used convos. Press a number or type a name; `r` opens a project
   menu, `s`, a blank line or 30 s of silence gives a plain shell, and `bench`
   brings the menu back any time.
2. **Colour change.** The agent session starts named after the convo and gets a
   random session colour, so tabs are easy to tell apart. The `>>name` first
   message is staged, unsent, and costs nothing until you press Enter.
3. **Automatic notes.** After 15 minutes of quiet, `auto-note` writes the session
   note into the convo folder for you. `/note` still writes one on demand.
4. **Closing windows.** A tab whose note is written and that has stayed idle for
   60 minutes is closed for you. `/e` writes the note and closes the tab now;
   `claude --resume <id>` reopens any closed session.

---

## Getting started checklist

Once setup is complete, work through these to get familiar with your bench:

- [ ] **Review the Getting Started checklist** — you're reading it now!
- [ ] **Enter your name** — run `./setup.sh` and answer the welcome prompt (or edit `BENCH_OWNER` in `config/keys.env` directly)
- [ ] **Pick a bench colour** — `./setup.sh` asks (red, blue, green, yellow, purple, orange, pink, cyan). It colours the editor window, with a dark and a light variant that follow the system, and the agent session. Switch later with `python3 scripts/bench-colour.py <colour>`
- [ ] **Create your first note** — start a conversation with Claude, then run `/note` to save a session note to a convo folder
- [ ] **Create your first action** — copy `tools/on-demand/meeting-minutes/` to a new folder, rename it, and edit `instructions.md`
- [ ] **Open the Actions Dashboard** — run `bash tools/on-demand/actions-dashboard/run.sh` and visit http://localhost:7391 to see your actions listed
- [ ] **Review bench-index.csv** — open it to see how actions, convos, and tickets are tracked in one place

---

## Structure

```
your-bench/
├── master-instructions.md   ← read first: what the bench is, where things live, where to look
├── CLAUDE.md                ← always-loaded operating rules
├── AGENTS.md                ← the same rules for Codex (link to CLAUDE.md)
├── bench-index.csv          ← index of all actions and convos + ticket links
├── core/                    ← shared by every bench, arrives with /update; never edit
│   ├── skills/  tools/      ← shared skills and tools (auto-note, convo-memory, freeze, …)
│   ├── hooks/  shell/  env/ ← Claude Code hooks, terminal layer, Warp/Cursor/Claude settings
│   ├── bench-update/        ← the daily check and /update
│   └── rules.md
├── personal/
│   ├── skills/              ← your own skills, one folder each
│   └── overlays/            ← your changes to a core skill (<skill>.md)
├── skills/                  ← links only, into core/skills and personal/skills
├── config/
│   ├── bench.env            ← non-secret settings (PM_TOOL, BENCH_COLOR)
│   ├── keys.env.template    ← copy to keys.env and fill in your API keys
│   └── warp/                ← your Warp tab configs
├── scripts/                 ← shared utilities (jira.sh, …)
├── tools/
│   ├── on-demand/           ← your manually triggered actions (meeting-minutes: example to copy)
│   ├── recurring/           ← your scheduled actions
│   └── ~archive/
├── convos/
│   ├── Templates/           ← Convo Template.md for new conversations
│   └── ~archive/
└── .claude/                 ← settings.json, commands/ (/dashboard), hooks/, skills → ../skills
```

---

## Core concepts

### Actions
Repeatable tasks Claude executes on your behalf. Each lives in its own folder with an `instructions.md` and an `assets/` folder for input files.

- **On-demand:** run manually (`/status`, ad-hoc research, file processing)
- **Recurring:** scheduled via launchd (macOS) or cron

To add an action: copy `tools/on-demand/meeting-minutes/` as a starting point, rename it, and edit `instructions.md`.

### Convos
Ongoing research topics with persistent context across sessions. Each session ends with a dated note (`YYMMDD-short-description.md`) written by `/note`.

To start a new convo, begin your message with `>> name`:

```
>> music what are the best ambient artists for 2026?
```

Claude will answer your question. When you run `/note`, it automatically creates `convos/music/` (if it doesn't exist) and writes the session note there. No manual folder creation needed.

To continue an existing convo, use the same `>> name` to restore context from previous notes.

### Default tools and skills

All of these ship with the free bench.

| Command / skill | What it does |
|---------|-------------|
| `/note` | Writes a session note to the active convo folder; offers to post to the linked ticket |
| `/push` | Commits and pushes all changes; creates notes; offers to post to linked tickets |
| `/sync` | Commits local work, pulls what changed on GitHub, pushes. No notes, no tickets |
| `/e` | Writes the session note now and closes the tab |
| `/eod` | End-of-day wrap-up: note, commit, push, stop services |
| `/bugs` | Records bugs to carry into the next session |
| `/status` | Shows a snapshot of the scheduled jobs |
| `/ai` | Processes all `@ai` inline annotations in a file |
| `/nb` | Unwraps hard-wrapped text (clipboard, inline text, or a file) |
| `/atl` | Redoes the last answer at half the length |
| `/dashboard` | Opens the Actions Dashboard (`stop`, `restart` to manage it) |
| `toggl` | Reading and writing Toggl time entries within the free-plan rate limit |
| `lookup` | Where to look, in order, before answering about your own facts or past work |

Every shared skill and tool lives in `core/` (`core/skills/`, `core/tools/`) and
arrives with `/update`; `skills/` holds only links to them and to your own
skills in `personal/skills/`. Your own tools go in `tools/on-demand/` (example to
copy: `meeting-minutes`; `actions-dashboard`) and `tools/recurring/`
(`weekly-check-ins`).

### Bench Index (`bench-index.csv`)

Tracks every action and convo with their linked Jira/Asana tickets. When you add a new action or convo, add a row. The ticket workflow in `/note` and `/push` reads from this file.

Links are added by hand — nothing searches for or auto-links tickets, and posting only goes to a ticket already linked here:
```bash
python3 core/tools/bench-ticket/bench_ticket.py update <slug> --jira PROJ-123
python3 core/tools/bench-ticket/bench_ticket.py update <slug> --asana 1201234567890
```

---

## Actions Dashboard

A local web interface that lists all your actions from `bench-index.csv`.

```bash
bash tools/on-demand/actions-dashboard/run.sh
```

This opens http://localhost:7391 in your browser automatically.

---

## Adding API integrations

Edit `config/keys.env` (never commit this file) with the keys for the tool `PM_TOOL` names:

```
JIRA_URL=https://your-workspace.atlassian.net
JIRA_EMAIL=you@example.com
JIRA_API_TOKEN=your-token

ASANA_PAT=your-pat

ANTHROPIC_API_KEY=your-key
```

Get a Jira API token at: https://id.atlassian.com/manage-profile/security/api-tokens  
Get an Asana PAT at: https://app.asana.com/0/my-apps

If this bench runs on its own Anthropic account, put that login's `CLAUDE_CONFIG_DIR` path (e.g. `~/.claude-work`) in a `.claude-login` file at the bench root. Background jobs like `convo-memory` and `auto-note` then use that login; without the file they use your default one.

---

## Git workflow

Each bench is a private GitHub repo. Commit regularly:

```bash
/push "describe what changed"
```

Or let Claude generate the commit message automatically with just `/push`.

---

## Prior art and analogous frameworks

The bench sits in a space that several communities have approached differently:

**Personal Operating Systems (Notion/Airtable)**
The most common version — a "Life OS" with linked databases across projects, tasks, and notes. Same instinct as the bench (central registry, cross-system linking), but no-code and no automation layer.

**Scripts to Rule Them All** (GitHub's pattern)
Standardized `script/` folder with `setup`, `bootstrap`, `test`, `server` etc. Same instinct: one repo, consistent conventions, all operations as named scripts. The bench's `tools/on-demand/` and `tools/recurring/` structure follows this pattern.

**Dotfiles repos**
The dotfiles community does something adjacent — a versioned, portable personal environment. Usually stops at config/tooling though, not cross-API automation.

**Personal data warehouses**
A smaller niche: people running dbt + Airbyte locally to pipe Toggl, Strava, and finance data into Postgres for personal analytics. Overlaps with Toggl + Sheets integrations.

**Self-hosted automation (n8n, Activepieces)**
The no-code/low-code crowd uses these for the same multi-system glue. More visual, less programmable, no git history or Claude integration.

**The gap most people hit**
The common failure mode in all these is the registry problem — no single source of truth for "what project maps to what ticket in what system." `bench-index.csv` solves exactly that. Most people end up with duplicated bookmarks, copy-pasted IDs, and no automation because of it.

The closest conceptual match overall is **internal developer platforms (IDPs)** — applied personally. The bench is platform engineering for an org of one.
