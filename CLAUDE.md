# The Bench — Claude Code Operating Instructions

Read `master-instructions.md` for the full workspace guide. The rules below are
the most critical and apply to every session.

Everything here is the distributed default. Your own bench will grow rules this
file doesn't have — add them here, not in a comment somewhere.

---

## Response Length — Short by Default

Every message stays **under 600 characters of prose** (fenced code and tables
you were asked for don't count). This is the default, not a ceiling to aim at.

- Applies to **every** message, including ones sent mid-turn before more tool
  calls. The `response-length-budget.py` Stop hook only checks the last message
  of a turn, so mid-turn messages are on you.
- Lead with the outcome. Keep numbers, file paths, and anything needing a decision.
- No section headers, bold labels, or summary tables in a chat reply unless asked.
- Cut recaps of what the user already knows and caveats about caveats.
- Detail goes in the session note, which they can open. Not the terminal.
- Longer is allowed only when the user asks for detail, or asks for a document,
  draft, or comparison as the deliverable itself.

Tune the budget with `RESPONSE_BUDGET_CHARS`; `RESPONSE_BUDGET_OFF=1` disables
it for a session. See `.claude/hooks/response-length-budget.py`.

---

## Pronouns

Record the bench owner's pronouns here and use them everywhere. Until you know
them, use **they/them** — never guess from a name.

---

## Supported Environments — Warp and Cursor Only

The bench is **supported in exactly two places: Warp and Cursor.** Nothing else
is a supported host, and no environment-specific work should be built for one.

- **Warp** — the terminal. Setup kit: `config/warp/`, documented in its README.
- **Cursor** — the editor. Setup kit: `config/cursor/`, documented in its README.
- **A plain terminal** (Terminal.app, iTerm, ssh) runs Claude Code fine and every
  action still works. What it does *not* get is the environment layer: no project
  picker, no auto-launched named session, no `wp`/`cw`. That is expected, not a
  bug — do not "fix" it, and do not add a third setup kit for it.
- **VS Code, Zed, JetBrains, and anything else** are unsupported.

**Warp and Cursor rules are deliberately different, because the two hosts are
different.** Never copy a rule across without checking it still earns its place:

| Concern | Warp | Cursor |
|---|---|---|
| Open a project in its own window | `wp <name>` — needs `warp://…?new_window=true` because the Project Explorer root is derived from cwd and cannot be set | `cw <name>` — `cursor <dir>` is the whole mechanism; the explorer root *is* the folder |
| Run something on window open | `~/.warp/tab_configs/*.toml` → `commands` | `<repo>/.vscode/tasks.json` → `runOn: folderOpen` |
| Per-project colour | tab config `color` | **none** — tried and rejected; don't add it back without deciding to |
| Toggle the file tree | `Cmd+/` (custom binding) | `Cmd+B` (built in) |
| File preview | n/a — a terminal has no preview pane | `workbench.editorAssociations` opens `.md`/`.csv` rendered |

Both hosts share one shell layer (`bench_claude_named`, `bench`, `bench_menu_once` in
`~/.zshrc`, canonical copy `config/warp/zshrc-picker.zsh`). When you change it,
check both arms — the guards that stop a double Claude launch differ per host
(`bench_warp_tab_config_here` on Warp, `BENCH_NO_MENU=1` in the task on Cursor).

---

## Action Matching Rule

Before responding to any task, check whether the request matches an existing
action in `actions/`. If it does, **read that action's `instructions.md` before
producing any output**. Do not rely on general knowledge or freeform generation
when a dedicated action exists — the instructions file is the source of truth
for tone, format, and content rules.

Current actions: see `bench-index.csv` (rows where `type = action` or `type = both`).

---

## The >> Topic Convention

When a user message starts with `>>` followed by a name, that is a **convo topic
declaration**. Extract the convo name (first word after `>>`, lowercased,
kebab-case).

Before doing anything else:

1. Check if `convos/<name>/` exists. If so, use the **layered read path**:
   - If `convos/<name>/_memory-master.md` exists: read it, extract the
     `through YYMMDD` watermark from line 2, then read only the notes dated
     **after** that watermark. Drill into `_memory-index.md` when a question
     needs detail behind a master line; open a raw note `[YYMMDD]` only as a
     last resort.
   - If no `_memory-master.md` exists: read all notes in the folder.
2. Check if `actions/on-demand/<name>/` or `actions/recurring/<name>/` exists —
   if so, read its `instructions.md`.
3. Then respond using that context.

`_memory-index.md` and `_memory-master.md` are machine-maintained (nightly
`convo-memory` job). Never hand-edit them and never write session content into
them — session notes remain separate dated files.

---

## Ticket References

Every time you mention a Jira or Asana ticket — in tables, lists, session notes,
`/note` output, `/push` output, or inline — always include the ticket title
alongside the key. If you don't know the title, fetch it before displaying.

- Correct: `PROJ-6099 — Create a weekly report app`
- Wrong: `PROJ-6099`

---

## Jira Hierarchy — Epic → Task → Sub-task, Never Skip a Level

**A child issue never skips a hierarchy level, and its work type is decided by
its parent's type — never chosen freely.**

- Parent is an **Epic** → the child is a **Task**. Never a Sub-task. There is no
  exception, no "small enough to be a subtask" case.
- Parent is a **Task** or **Story** → the child is a **Sub-task**.
- Parent is a **Sub-task** → refused. Nothing nests under a Sub-task.

Enforced in `scripts/jira.sh`:

- `jira.sh create-child <PARENT_KEY> "<summary>" ["<desc>"]` — reads the parent
  and picks the type itself. **Use this for anything with a parent.** Do not
  pass a type.
- `jira.sh create <PROJECT> "<Type>" …` — parentless issues only; refuses `Sub-task`.
- `create-subtask` is a deprecated alias for `create-child` and applies the same rule.

To fix an existing mis-typed issue **without losing its key**, use the Jira bulk-move
API (a plain `PUT issuetype` is rejected for sub-task ↔ standard conversions):

```bash
POST /rest/api/3/bulk/issues/move
{"sendBulkNotification": false,
 "targetToSourcesMapping": {"<PROJECT>,<typeId>,<parentNumericId>": {
   "inferClassificationDefaults": true, "inferFieldDefaults": true,
   "inferStatusDefaults": true, "inferSubtaskTypeDefault": true,
   "issueIdsOrKeys": ["<KEY>"]}}}
```

---

## Ticket Posting — Confirmation Required

**NEVER post a comment to any Jira or Asana ticket without explicit user
confirmation.** This applies everywhere: `/note`, `/push`, manual posting. Even
when a slug has only one linked ticket, present the target (key + title) plus a
"Skip" option and wait for the user to choose. Use `bench_ticket.py lookup`
(never a bare `post`) to read linked tickets without triggering a post.

---

## API Keys and Credentials

All API keys and service credentials live in **`config/keys.env`**. Before
calling any external service (Jira, Asana, Toggl, Confluence, Slack, Google
Sheets, etc.), **source this file first** (`source config/keys.env`). Never
assume credentials are missing — check `config/keys.env` before reporting an
auth error. `config/keys.env` is gitignored and must never be committed.

---

## APIs Over MCPs

Always **prioritize direct API calls** (via `curl`, `requests`, or existing
scripts in the codebase) over MCP integrations. Only fall back to an MCP tool if
no API is available or the API cannot accomplish the task. Most services used on
a bench have credentials in `config/keys.env` and should be called directly.

---

## Building Automations — No Next-Day Surprises

The recurring failure mode on a bench: we build something, it looks finished,
and the next day it breaks for a reason that was never discussed. The cause is
almost always an operating condition nobody asked about — how often it runs,
what it depends on, what happens when that dependency is down.

**Before writing code** for any automation (new one, or a change to an existing
one), ask these as a short numbered list in ONE message, and wait:

1. **Trigger and cadence** — what makes it run? How soon after the input arrives
   is a result expected? ("within minutes" and "sometime tomorrow" are
   completely different builds.)
2. **Dependencies** — what has to be running or reachable (network up, git
   remote, API creds, another machine)? What should happen when one is down —
   retry, skip, or shout?
3. **Failure visibility** — where does the owner find out it broke? A log file
   nobody opens does not count as visibility.
4. **Ownership** — which steps are the human's and which are automated?

Never infer these from the surrounding code. If an existing piece already sets
one (a plist schedule, an existing retry), **read it and state it back** rather
than assuming it matches what the owner expects.

**When reporting the build as done**, always state in plain language: what runs,
when it runs, what it produces, and how a failure shows up. Any internal noun
(worker, queue, relay, cron label) gets a one-line gloss the first time it
appears in chat. The owner does not read the code — a report they can't verify
is not a report.

---

## Session Note

After any meaningful session, write a dated note in the relevant `convos/`
folder. Use `/note` to trigger this.
