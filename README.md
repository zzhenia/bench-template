# The Bench

A personal knowledge and automation workspace built on Claude Code, Obsidian, and GitHub.

Each team member runs their own bench — a private repo where Claude Code has persistent context, session notes are tracked as markdown, and repeatable tasks live as versioned actions.

---

## Prerequisites

- [Claude Code](https://claude.ai/code) (CLI)
- **[Warp](https://warp.dev)** or **[Cursor](https://cursor.com)** — the two
  supported hosts. Pick either; you can run both.
- [Obsidian](https://obsidian.md) (optional — for note linking and search)
- Python 3.10+
- A GitHub account

API integrations (Jira, Asana, Toggl) are optional — the bench works without them. `setup.sh` asks which project-management tool you use (`jira`, `asana` or `none`) and saves it as `PM_TOOL` in `config/bench.env`; with `none` there is no ticket step.

> **On supported environments.** The bench runs in any terminal — Terminal.app,
> iTerm, ssh — and every action works there. What Warp and Cursor add is the
> environment layer: a project picker, a Claude session that starts named and
> coloured, and a one-word command to open a project in its own window. Those
> two are the only hosts with a setup kit and the only ones we fix bugs for.
> VS Code, Zed and JetBrains are unsupported.

---

## Quick start

**1. Create your bench from this template**

Click **"Use this template"** on GitHub → name it (e.g. `my-bench`) → set it to Private → click **Create repository**.

**2. Clone it**

```bash
mkdir -p ~/dev && cd ~/dev
git clone https://github.com/your-username/my-bench.git
```

Then open the folder in your host:

- **Cursor** — `cursor ~/dev/my-bench`, or **File → Open Folder**. You should
  see the bench files (`.claude`, `actions`, `config`, `convos`, …) at the root
  of the sidebar, not nested inside a subfolder.
- **Warp** — `cd ~/dev/my-bench`. The Project Explorer roots itself at the
  nearest git toplevel, so it follows automatically.

**3. Run setup**

In a terminal at the repo root (in Cursor: ``Ctrl+` ``):

```bash
chmod +x setup.sh && ./setup.sh
```

This copies `config/keys.env.template` → `config/keys.env`. Fill in your API keys before running any actions.

**4. Enter your name**

During setup you'll be asked: *"Hello! How shall I call you?"* — your name is saved in `config/keys.env` as `BENCH_OWNER` and appears in the Actions Dashboard header (e.g. "Ben's Actions Dashboard"). You can change it anytime by editing `config/keys.env`.

**5. Open in Claude Code**

In Cursor, install the **Claude Code** extension from the Extensions panel
(search "Claude Code" by Anthropic). In Warp, nothing to install. Either way:

```bash
claude .
```

Claude reads `CLAUDE.md` and `master-instructions.md` at the start of each
session. Your commands (`/note`, `/push`, `/status`, `/ai`) are ready immediately.

**6. Optional — install the environment layer**

This is what makes a bench feel like a bench rather than a folder: a project
picker on every new tab, `wp` / `cw` to open a project in its own window, and a
Claude session that starts already named after the project.

- Warp: `config/warp/README.md` → *Apply on a new machine*
- Cursor: `config/cursor/README.md` → *Apply on a new machine*

Both install the same `~/.zshrc` block, so doing one first makes the other short.

---

## Getting started checklist

Once setup is complete, work through these to get familiar with your bench:

- [ ] **Review the Getting Started checklist** — you're reading it now!
- [ ] **Enter your name** — run `./setup.sh` and answer the welcome prompt (or edit `BENCH_OWNER` in `config/keys.env` directly)
- [ ] **Pick a bench colour** — `./setup.sh` asks (red, blue, green, yellow, purple, orange, pink, cyan). It colours the Cursor window, with a dark and a light variant that follow the system, and the Claude session. Switch later with `python3 scripts/bench-colour.py <colour>`
- [ ] **Create your first note** — start a conversation with Claude, then run `/note` to save a session note to a convo folder
- [ ] **Create your first action** — copy `actions/on-demand/meeting-minutes/` to a new folder, rename it, and edit `instructions.md`
- [ ] **Open the Actions Dashboard** — run `bash actions/on-demand/actions-dashboard/run.sh` and visit http://localhost:7391 to see your actions listed
- [ ] **Review bench-index.csv** — open it to see how actions, convos, and tickets are tracked in one place

---

## Structure

```
your-bench/
├── master-instructions.md   ← Claude's operating guide for this bench
├── bench-index.csv          ← index of all actions and convos + ticket links
├── CLAUDE.md                ← always-loaded operating rules
├── config/
│   ├── bench.env            ← non-secret settings (PM_TOOL, BENCH_COLOR)
│   ├── keys.env.template    ← copy to keys.env and fill in your API keys
│   ├── warp/                ← Warp setup kit (zshrc block, wp, tab configs)
│   └── cursor/              ← Cursor setup kit (cw, per-project folderOpen tasks)
├── scripts/                 ← shared utilities (jira.sh, …)
├── actions/
│   ├── on-demand/           ← manually triggered actions
│   │   ├── actions-dashboard/  ← local web dashboard (http://localhost:7391)
│   │   ├── bench-ticket/    ← ticket lookup + comment posting utility
│   │   ├── automation-status/  ← snapshot of scheduled automations
│   │   └── meeting-minutes/ ← example action (copy to create your own)
│   ├── recurring/           ← scheduled actions (launchd / cron)
│   │   ├── auto-note/       ← notes idle convo windows, closes them after 60 min
│   │   ├── context-trim/    ← past a token limit, offers a note + clean restart
│   │   ├── convo-memory/    ← nightly memory compression (three-layer OptMem)
│   │   ├── python-repin/    ← keeps jobs on a Homebrew Python that has their libraries
│   │   ├── brew-check/      ← tests and repairs the Homebrew tools jobs call
│   │   └── weekly-check-ins/
│   └── ~archive/
├── convos/
│   ├── Templates/           ← Convo Template.md for new conversations
│   └── ~archive/
└── .claude/
    ├── commands/            ← /note  /push  /status  /ai  /eod  /bugs  /dashboard  /nb
    ├── hooks/               ← response-length budget (600 chars of prose)
    ├── scripts/
    └── skills/
```

---

## Core concepts

### Actions
Repeatable tasks Claude executes on your behalf. Each lives in its own folder with an `instructions.md` and an `assets/` folder for input files.

- **On-demand:** run manually (`/status`, ad-hoc research, file processing)
- **Recurring:** scheduled via launchd (macOS) or cron

To add an action: copy `actions/on-demand/meeting-minutes/` as a starting point, rename it, and edit `instructions.md`.

### Convos
Ongoing research topics with persistent context across sessions. Each session ends with a dated note (`YYMMDD-short-description.md`) written by `/note`.

To start a new convo, begin your message with `>> name`:

```
>> music what are the best ambient artists for 2026?
```

Claude will answer your question. When you run `/note`, it automatically creates `convos/music/` (if it doesn't exist) and writes the session note there. No manual folder creation needed.

To continue an existing convo, use the same `>> name` to restore context from previous notes.

### Commands

| Command | What it does |
|---------|-------------|
| `/note` | Writes a session note to the active convo folder; offers to post to the linked ticket |
| `/push` | Commits and pushes all changes; creates notes; offers to post to linked tickets |
| `/status` | Runs automation-status and shows a snapshot of scheduled jobs |
| `/ai` | Processes all `@ai` inline annotations in a file |
| `/dashboard` | Opens the Actions Dashboard in your browser (starts it if not running) |
| `/dashboard stop` | Stops the dashboard |
| `/dashboard restart` | Restarts the dashboard |
| `/eod` | End-of-day wrap-up — note, commit, push, stop services |
| `/bugs` | Records bugs to carry into the next session |
| `/nb` | Unwraps hard-wrapped text (clipboard, inline text, or a file) |

### Bench Index (`bench-index.csv`)

Tracks every action and convo with their linked Jira/Asana tickets. When you add a new action or convo, add a row. The ticket workflow in `/note` and `/push` reads from this file.

Links are added by hand — nothing searches for or auto-links tickets, and posting only goes to a ticket already linked here:
```bash
python3 actions/on-demand/bench-ticket/bench_ticket.py update <slug> --jira PROJ-123
python3 actions/on-demand/bench-ticket/bench_ticket.py update <slug> --asana 1201234567890
```

---

## Actions Dashboard

A local web interface that lists all your actions from `bench-index.csv`.

```bash
bash actions/on-demand/actions-dashboard/run.sh
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
Standardized `script/` folder with `setup`, `bootstrap`, `test`, `server` etc. Same instinct: one repo, consistent conventions, all operations as named scripts. The bench's `actions/on-demand/` and `actions/recurring/` structure follows this pattern.

**Dotfiles repos**
The dotfiles community does something adjacent — a versioned, portable personal environment. Usually stops at config/tooling though, not cross-API automation.

**Personal data warehouses**
A smaller niche: people running dbt + Airbyte locally to pipe Toggl, Strava, and finance data into Postgres for personal analytics. Overlaps with Toggl + Sheets integrations.

**Self-hosted automation (n8n, Activepieces)**
The no-code/low-code crowd uses these for the same multi-system glue. More visual, less programmable, no git history or Claude integration.

**The gap most people hit**
The common failure mode in all these is the registry problem — no single source of truth for "what project maps to what ticket in what system." `bench-index.csv` solves exactly that. Most people end up with duplicated bookmarks, copy-pasted IDs, and no automation because of it.

The closest conceptual match overall is **internal developer platforms (IDPs)** — applied personally. The bench is platform engineering for an org of one.
