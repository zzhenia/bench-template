---
name: network
description: How the OpenClaw network works — hosts, roster, profiles, siblings, GitHub, Jira, notes, errors go to Olga, crons, memory, red lines. Every agent reads this first.
---

# How the network works

**Whose skill this is: every agent on openclaw-1** — Eva, Kitty, Olga, Videobot, and every
agent spawned from the template. One copy, here (`~/ZV-Bench/skills/network/SKILL.md`).
Read it on your first session and whenever you are unsure who does what. Slack has its
own file: `~/ZV-Bench/skills/slack/SKILL.md`. The rules of who does what, the work-order
shape, and the three rules that bind everyone (Kitty first with problems; every handler
reports back to its requester; nothing stalls) are `~/ZV-Bench/skills/network/RULES.md`,
read right after this file.

## 1. Where you live

- **The box, openclaw-1** (Hetzner, Helsinki) runs the gateway, every agent, Olga and all
  crons. Your workspace is `~/.openclaw/workspace/<your-id>` — a git clone of your
  personality repo (`zzhenia/openclaw-<name>-personality`). Standing files (AGENTS.md,
  SOUL.md, IDENTITY.md, USER.md, HEARTBEAT.md, `skills/`) are tracked; memory, sessions
  and logs are not. A cron pulls every clone every 15 minutes: a pushed commit reaches
  you within 15 minutes, and a dirty tree silently stops your updates — commit and push
  right after any edit.
- **The bench** is `~/ZV-Bench` on the box: Zhenia's workspace repo, pulled every 15
  minutes, push rights. Scripts (`scripts/`), skills (`skills/`), shared code (`lib/`), session
  notes (`convos/`), and the network specs (`convos/openclaw/specs/`) live there. Pull
  before you read (`git -C ~/ZV-Bench pull`).
- **The bench is also the team's memory.** Every conversation Zhenia has had — with any of
  us or with Claude on the Mac — is a note under `convos/`, summarised per topic. Before you
  answer anything about past work, decisions or names you do not know, search it:
  `~/ZV-Bench/scripts/bench-recall.sh <words>`. The rule and the reading order are in
  `~/ZV-Bench/skills/bench-recall/SKILL.md`.
- **Skills live in one place**: `~/ZV-Bench/skills/<name>/SKILL.md` (this file,
  `slack`, `bench-recall`, `calendar`, `formula-daily`, `editorial`,
  `writing`).
  Your own `skills/` folder holds only what is yours;
  for anything shared it holds a pointer, never a copy.
- **Zhenia's Mac is not part of the network.** It is often off. Nothing you do depends
  on it; never SSH to it. Work not pushed from the Mac is invisible to you by design —
  say "not pushed yet", do not go looking.
- **Credentials:** `~/.openclaw/keys.env` (`set -a; . ~/.openclaw/keys.env; set +a`).
  Never print, copy, widen or ask for a credential. A missing one is a capability gap
  for Olga (section 5).

## 2. Who is who

| Agent | Id | Role | Where Zhenia talks to them |
|---|---|---|---|
| Kitty | `kitty` | Ops and admin: bench, Jira, SlipBox, spawning agents, Slack channels | DM, #jira-admin, #spanish-vocab, #sb |
| Eva | `eva` | the writer: scripts, strategy + marketing coaching, social media, editorial | #formula-scripts, #formula-strategy, #social-media, DM |
| Olga | `olga` (gateway agent since 260905; her visits run as a cron) | the medic: every failure, every build request | #openclaw-ops, her DM |
| Zhenia | `U085EGDHTND` | the human; they/them; Bogotá time | — |
| PI Bot | `pi-bot` | IC, PM kitty, Sonnet 5, no Slack app — Asana task manager for Pilot Institute work (create, update, comment, transition); routed by Kitty via sessions_send | #pilot-institute (Kitty posts for it) |
| Job Ad Responder | `job-ad-responder` | IC, PM kitty, Sonnet 5, no Slack app — screens Upwork job posts and invites (routed by gmail-sort) for spam, fit and budget; drafts application materials on ✅ | #job-ad-responder (Kitty posts for it) |

The live roster is `openclaw agents list` and the specs in
`~/ZV-Bench/convos/openclaw/specs/` (one file per agent: jobs, dependencies, checks).

**Profiles.** Every agent is one of three: **admin** (Kitty), **PM** (owns an outcome and
directs ICs) or **IC** (delivers assignments). Your AGENTS.md says which you are and,
for an IC, who your PM is. The profile rules:
`~/ZV-Bench/convos/openclaw/assets/agent-template/profiles/`.

## 3. Talking to another agent — one procedure for every agent, Olga included

**Asking any agent for anything that needs an answer** (work, a fix, a lookup, a check):
```sh
~/ZV-Bench/tools/order new --from <your-id> --to <their-id> --reply <CHANNEL>/<thread_ts> -m "<what you need; done when …>"
```
`--reply` is the Slack thread where someone is waiting for the result (the thread you were
asked in); with nobody waiting in Slack, your own session key (`agent:<your-id>:main`). The
command prints an order id and a message: send that message word for word with
`sessions_send` to `agent:<their-id>:main`. Then tell the asker one line ("Olga has it") and
stop — do not promise to post the result yourself; the order posts it.

**Answering an order** (a message that starts `Order o-…`): do the work, then — done or not
done — run the line it ends with:
```sh
~/ZV-Bench/tools/order done <id> -m "<result, with the commit, file, ticket or link>"
~/ZV-Bench/tools/order done <id> --not-done -m "<why, and what would unblock it>"
```
That posts "[<Your name>] <result>" in the asker's thread (or wakes the asking session). Do
not post the result anywhere yourself and do not `sessions_send` it back.

No `order done` after 30 min → the order is re-sent to you once; 2 h later it goes to Olga
(to Kitty when Olga is the silent one). This is automatic; nobody chases by hand.

Plain `sessions_send` (no order) only for messages that need no answer: a hand-back, an FYI.
Always the **full session key** `agent:<id>:main` — never a bare label. Never tell Zhenia a
sibling is down.

## 4. GitHub, Jira, notes, files

- **GitHub:** the box's key `~/.ssh/id_ed25519` pushes to ZV-Bench and the personality
  repos. Commit messages say what changed and why, in one line, as yourself
  (`Kitty: …`, `Eva: …`). Never force-push, never rewrite history, never delete a repo.
- **Jira** (`zvi.atlassian.net`): only through `~/ZV-Bench/scripts/jira.sh`, never raw
  `fetch`/curl. Every issue has a parent — Epic → Task → Sub-task, never skipping a level;
  `jira.sh create-child <PARENT> "<summary>"` picks the type. Always show a ticket as key
  **and title**. Never comment on a ticket without Zhenia naming it.
  `jira.sh get <KEY>` returns a fixed field set (summary, issuetype, parent, status) —
  priority and custom fields (e.g. customfield_10290) read back None/missing even right
  after a write that stuck. That is the wrong read, not a failed write. To verify a
  priority or custom-field write, use `jira.sh search "key = <KEY>" 1 "priority,customfield_10290"`
  (or whatever fields you wrote) instead (Kitty, ZHEN-6774, 260911).
- **Every `jira.sh` call is `JIRA_AS=<your-id> jira.sh …`.** There is one Jira account for
  the whole network, `openclaw`; no agent has a seat and nothing is ever assigned to you. Your
  id goes on as a label — that is the route: `jira.sh mine` lists your tickets, hand-backs find
  you, and `jira.sh comment` signs `[<your-id>]`. A ticket comes to you as a Slack ping with
  its key; you answer on the ticket (checkpoint and done comments) and ping back — the full
  shape is `~/ZV-Bench/skills/network/RULES.md` §4.
- **Answer where you were asked; nothing goes through Kitty for relay** (Zhenia, 2026-09-14:
  every relayed message is two model turns). A question in your channel gets your answer in
  that thread. `sessions_send` to Kitty only for the two cases below: a ticket request, or a
  stall you cannot clear. Never forward a message so that Kitty can answer it.
- **A short letter code at the start of a message is a command shortcut** — `sb`, `nr`,
  `cint`, `JT: …` ("open a Jira ticket for …"). The table is
  `~/ZV-Bench/skills/shortcuts/SKILL.md`; read it before treating the letters as a name or
  a missing skill.
- **Work or a ticket Zhenia asks for becomes a ticket request to Jira, never a ticket you
  open.** Only Jira, the Jirabot (`agent:jira:main`, live since 260916), opens tickets
  (RULES.md §4), ticket-first: it files at once and asks afterwards. (1) Hand it to Jira by
  `sessions_send` to `agent:jira:main` — never by a post in a channel; Jira is not in Slack —
  with Zhenia's words verbatim, the thread link and what you already know; tell Zhenia one
  line ("Jira has it"); post the key and title in the thread when it comes back; no key
  within 30 minutes → re-send once, say so, and tell Kitty; (2) for every piece only Olga can do — a tool, a package,
  an access, a script on the box — an order to Olga (section 3); (3) carry on with what
  does not depend on Olga. (4) Needs Zhenia's decision or hands? `jira.sh assign <KEY> zhenia` and one
  line in the thread saying what you need. (5) Done → `jira.sh transition <KEY> Testing`
  and the one-line result in the thread. Reply to Zhenia's ask with the key and title, once.
- **Session notes:** when Zhenia says `/note`, write a bench-style note with
  `bash ~/ZV-Bench/scripts/oc-note.sh <your-id> <convo> <slug>` (it pulls, writes
  `convos/<convo>/YYMMDD-<slug>.md`, commits, pushes). Never touch `_memory-*.md` files.
  Not in a conversation channel (`config/conversations.tsv`): there, a message that is only
  `note` belongs to the channel-note job on the box, which writes the note and posts
  `:memo: Note saved: …`. Do nothing with either — no reply, no reaction, no `oc-note.sh`.
- **Deliverables are files, not chat.** Drafts and documents go to the job's Drive
  folder (`gdrive-write.py`), notes to the bench, posts to Ghost; Slack gets one line
  with the name and the link.
- **Google Calendar:** availability, event lookup, scheduling, or access diagnosis uses
  `~/ZV-Bench/skills/calendar/SKILL.md` and the existing `scripts/gcal.sh` helper.
  Calendar is personal admin work owned by Kitty; Olga diagnoses capability failures,
  not ordinary Calendar requests. Do not claim there is no integration before running
  the skill's metadata-only access check.
- Never post to Asana, send email, publish, or spend money. Gmail is draft-only.
  **Exception (pi-bot):** pi-bot posts to Asana via `~/.openclaw/tools/asana` for task automation (create, update, comment, delete); the tool reads ASANA_PAT + ASANA_WORKSPACE_GID from keys.env and never prints credentials.
- **Web search: two of them, and the built-in one gives up first.** The `web_search`
  tool is the keyless DuckDuckGo plugin. It answers the first query or two, then serves
  a bot-detection challenge and everything after it in that turn comes back empty — it
  does not say it is blocked, it just returns nothing. When that happens, or whenever
  you need more than a couple of queries in a row, use the box's paid Brave key instead:
  `~/.openclaw/tools/websearch "<query>" [--site reddit.com] [--days N] [--num N]`
  (JSON, every result with a real link; `--help` for the rest). Verified 260909 on five
  consecutive queries that DuckDuckGo had refused. Do not report "I could not find
  anything" from a challenged DuckDuckGo — that is a blocked tool, not an empty web.
- **Reading a Reddit thread.** reddit.com answers this box with 403 — the page, the
  `.json`, `old.reddit`, all of it — so `web_fetch` on a reddit link never works and
  search only ever gives you the title. To get the post body and its comments:
  `~/.openclaw/tools/reddit-read <permalink or post id> [--json] [--comments N]`
  (verified 260910, ZHEN-6734). It waits out Reddit's one-request-per-24-seconds limit
  by itself, so a call may take ~25s; it carries no vote counts.

## 5. When something breaks — retry once, then Olga, never Zhenia

A tool fails, SSH refuses, a cron errors, a scope is missing, a package is absent: retry
once, the same way. If it fails again, send Olga an order (section 3) and carry on with
whatever part still works. `--reply` is the thread you were working in, or your own
session key in a cron or isolated session. Put the four facts in `-m`:

```
doing: <one line — what you were trying to do, for whom>
command: <exact command or tool call>
error: <verbatim>
```

- A missing tool or access is `error: capability gap — <what you need>`. Olga builds it.
- An engineering request from Zhenia ("fix the website", "this script is wrong") is
  `error: request — <their words verbatim>`; you reply exactly "Sent to Olga."
- Zhenia hears nothing about the error from you. In a cron or isolated session, if the
  job cannot complete, your entire final message is exactly `NO_REPLY`.
- Olga's answer arrives through the order. Fixed → verify it yourself, finish the task.
  Blocked → work without it. One failure, at most two reports (`second time` in `doing:`),
  never a third.
- Never work around infrastructure yourself: no editing crons, config, tokens or your
  standing files to dodge an error.
- **If you cannot run `order` yourself** (your exec is down, no shell): `sessions_send` the
  same lines to `agent:kitty:main` — "order this from Olga" — and carry on.
- **When Zhenia asks "did you report to Olga?"**: one line — "Yes, ZHEN-xxxx — <title>" if
  you know the key, otherwise "Sent to Olga." Nothing about nodes, exec, inboxes, Kitty,
  retries or what you are checking. A second message on the same question is a failure
  (Eva, 260905: three lines of plumbing after one question).

## 6. Crons and heartbeats

- Exact timing, isolation, a cheaper model, delivery straight to a channel → a cron
  (`openclaw cron add --agent <id> --session isolated --model … --to … --message …`).
  Shell-only jobs use `--command`, not code-mode scripts.
- Batched, conversational, drift-tolerant checks → `HEARTBEAT.md`. Keep it small; an
  empty or comments-only file means no heartbeat calls (ICs keep it empty).
- Every cron's final message is delivered verbatim; `NO_REPLY` delivers nothing.
- Every cron you own is listed in your spec (`convos/openclaw/specs/<id>.md`). A cron
  not in the spec does not exist.

## 7. Memory and standing files

You wake fresh each session. `memory/YYYY-MM-DD.md` for the day, `MEMORY.md` for what
lasts (main session only, never in shared contexts). Lessons go into the relevant skill
or your AGENTS.md "Local notes" section — and if the lesson is about Slack or the
network, into the shared skill instead, once, for everyone. Write it down; mental notes
do not survive.

## 8. Red lines

No exfiltration of private data. No destructive commands without asking. Inspect before
changing any config or scheduler; merge, do not replace. `trash` over `rm`. Anything that
leaves the machine (email, post, publish, payment) is Zhenia's decision unless your
AGENTS.md grants it explicitly.
