# The Bench

A personal knowledge and automation workspace built on Claude Code, Obsidian, and GitHub.

Each team member runs their own bench — a private repo where Claude Code has persistent context, session notes are tracked as markdown, and repeatable tasks live as versioned actions.

---

## Prerequisites

- [Claude Code](https://claude.ai/code) (CLI)
- [Obsidian](https://obsidian.md) (optional — for note linking and search)
- [VS Code](https://code.visualstudio.com) (optional)
- Python 3.10+
- A GitHub account

API integrations (Jira, Asana, Toggl) are optional — the bench works without them.

---

## Quick start

**1. Create your bench from this template**

Click **"Use this template"** on GitHub → name it (e.g. `my-bench`) → set it to Private → click **Create repository**.

**2. Clone and open in VS Code**

1. Open VS Code → click **Clone Git Repository** on the Welcome tab
2. Your GitHub repos appear in the dropdown — click your new bench repo
3. Pick a folder to save it in (e.g. your home folder or a `dev/` folder)
4. Click **Open** when VS Code asks

You should see the bench files (`.claude`, `actions`, `config`, `convos`, etc.) at the root of the sidebar — not nested inside a subfolder.

> **Tip:** If your repos don't appear in the dropdown, paste the clone URL instead: `https://github.com/your-username/my-bench.git` (copy it from the green **Code** button on your repo's GitHub page).

**3. Run setup**

In the VS Code integrated terminal (`Ctrl+`` ` or `Cmd+`` `):

```bash
chmod +x setup.sh && ./setup.sh
```

This copies `config/keys.env.template` → `config/keys.env`. Fill in your API keys before running any actions.

**4. Open in Claude Code**

Install the **Claude Code** extension from the VS Code Extensions panel (search "Claude Code" by Anthropic). Once installed, open the integrated terminal and run:

```bash
claude .
```

Claude will read `master-instructions.md` at the start of each session. Your commands (`/note`, `/push`, `/status`, `/ai`) are ready immediately.

---

## Structure

```
your-bench/
├── master-instructions.md   ← Claude's operating guide for this bench
├── bench-index.csv          ← index of all actions and convos + ticket links
├── config/
│   └── keys.env.template    ← copy to keys.env and fill in your API keys
├── actions/
│   ├── dashboard/           ← local web dashboard (http://localhost:7391)
│   ├── on-demand/           ← manually triggered actions
│   │   ├── bench-ticket/    ← ticket lookup + comment posting utility
│   │   ├── automation-status/  ← snapshot of scheduled automations
│   │   └── meeting-minutes/ ← example action (copy to create your own)
│   ├── recurring/           ← scheduled actions (launchd / cron)
│   │   └── weekly-check-ins/
│   └── ~archive/
├── convos/
│   ├── Templates/           ← Convo Template.md for new conversations
│   └── ~archive/
└── .claude/
    ├── commands/            ← /note  /push  /status  /ai
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

To start a new convo: create a folder under `convos/`, ask Claude to begin working, run `/note` at the end.

### Commands

| Command | What it does |
|---------|-------------|
| `/note` | Writes a session note to the active convo folder; posts to linked ticket |
| `/push` | Commits and pushes all changes; creates notes; posts to tickets |
| `/status` | Runs automation-status and shows a snapshot of scheduled jobs |
| `/ai` | Processes all `@ai` inline annotations in a file |

### Bench Index (`bench-index.csv`)

Tracks every action and convo with their linked Jira/Asana tickets. When you add a new action or convo, add a row. The ticket workflow in `/note` and `/push` reads from this file.

To add a ticket manually:
```bash
python3 actions/on-demand/bench-ticket/bench_ticket.py update <slug> --jira PROJ-123
```

To search for an existing ticket automatically:
```bash
python3 actions/on-demand/bench-ticket/bench_ticket.py search <slug>
```

---

## Actions Dashboard

A local web interface that lists all your actions from `bench-index.csv`.

```bash
python3 actions/dashboard/server.py
```

Then open http://localhost:7391.

---

## Adding API integrations

Edit `config/keys.env` (never commit this file):

```
JIRA_URL=https://your-workspace.atlassian.net
JIRA_EMAIL=you@example.com
JIRA_API_TOKEN=your-token
JIRA_PROJECT_KEYS=PROJ

ASANA_PAT=your-pat
ASANA_WORKSPACE_GID=your-workspace-gid

ANTHROPIC_API_KEY=your-key
```

Get a Jira API token at: https://id.atlassian.com/manage-profile/security/api-tokens  
Get an Asana PAT at: https://app.asana.com/0/my-apps

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
