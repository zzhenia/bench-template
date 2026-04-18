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

**Option A — VS Code UI:**

1. Open VS Code → click **Clone Git Repository** on the Welcome tab
2. Your GitHub repos appear in the dropdown — click your new bench repo
3. Pick a folder to save it in, then click **Open** when VS Code asks

**Option B — Terminal:**

Open a terminal and navigate to where you want the repo to live, then clone:

```bash
cd ~/dev
git clone https://github.com/your-username/my-bench.git
```

Then open VS Code → **File → Open Folder** → select the `my-bench` folder.

Either way, you should see the bench files (`.claude`, `actions`, `config`, `convos`, etc.) at the root of the sidebar — not nested inside a subfolder.

**3. Run setup**

In the VS Code integrated terminal (`Ctrl+`` ` or `Cmd+`` `):

```bash
chmod +x setup.sh && ./setup.sh
```

This copies `config/keys.env.template` → `config/keys.env`. Fill in your API keys before running any actions.

**4. Enter your name**

During setup you'll be asked: *"Hello! How shall I call you?"* — your name is saved in `config/keys.env` as `BENCH_OWNER` and appears in the Actions Dashboard header (e.g. "Ben's Actions Dashboard"). You can change it anytime by editing `config/keys.env`.

**5. Open in Claude Code**

Install the **Claude Code** extension from the VS Code Extensions panel (search "Claude Code" by Anthropic). Once installed, open the integrated terminal and run:

```bash
claude .
```

Claude will read `master-instructions.md` at the start of each session. Your commands (`/note`, `/push`, `/status`, `/ai`) are ready immediately.

---

## Getting started checklist

Once setup is complete, work through these to get familiar with your bench:

- [ ] **Review the Getting Started checklist** — you're reading it now!
- [ ] **Enter your name** — run `./setup.sh` and answer the welcome prompt (or edit `BENCH_OWNER` in `config/keys.env` directly)
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
├── config/
│   └── keys.env.template    ← copy to keys.env and fill in your API keys
├── actions/
│   ├── on-demand/           ← manually triggered actions
│   │   ├── actions-dashboard/  ← local web dashboard (http://localhost:7391)
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

To start a new convo, begin your message with `>> name`:

```
>> music what are the best ambient artists for 2026?
```

Claude will answer your question. When you run `/note`, it automatically creates `convos/music/` (if it doesn't exist) and writes the session note there. No manual folder creation needed.

To continue an existing convo, use the same `>> name` to restore context from previous notes.

### Commands

| Command | What it does |
|---------|-------------|
| `/note` | Writes a session note to the active convo folder; posts to linked ticket |
| `/push` | Commits and pushes all changes; creates notes; posts to tickets |
| `/status` | Runs automation-status and shows a snapshot of scheduled jobs |
| `/ai` | Processes all `@ai` inline annotations in a file |
| `/dashboard` | Opens the Actions Dashboard in your browser (starts it if not running) |
| `/dashboard stop` | Stops the dashboard |
| `/dashboard restart` | Restarts the dashboard |

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
bash actions/on-demand/actions-dashboard/run.sh
```

This opens http://localhost:7391 in your browser automatically.

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
