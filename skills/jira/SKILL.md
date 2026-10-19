---
name: jira
description: How to open Jira issues and update Confluence pages on the bench — hierarchy rules, commands, credential handling.
---

# Jira + Confluence

Credentials: `set -a; . ~/.openclaw/keys.env; set +a` (box) or `source config/keys.env`
(bench). Never print or pass on the command line. Variables: `ZV_JIRA_URL`,
`ZV_JIRA_EMAIL`, `ZV_JIRA_API_TOKEN` (falls back to bare `JIRA_*`).

All Jira operations go through `~/ZV-Bench/scripts/jira.sh`. Never use raw curl for Jira.

## Hierarchy — Epic → Task → Sub-task

A child issue never skips a level, and its type is decided by the parent — never chosen
freely.

| Parent type | Child type |
|---|---|
| Epic | Task (never Sub-task) |
| Task or Story | Sub-task |
| Sub-task | refused — nothing nests under a Sub-task |

**Never a lone Sub-task.** If a Task would get only one Sub-task, expand the Task itself
instead. Sub-tasks only when there are two or more. jira.sh does not enforce this rule;
the agent is responsible for checking before creating a Sub-task. When a requester asks
how to file just one Sub-task under a Task, answer in one sentence: expand the Task scope.
Stop there — do not mention Sub-tasks again in that response.

### Commands

```bash
# Anything with a parent — jira.sh picks the type from the parent:
JIRA_AS=<id> STORY_POINTS=<1|2|3|5|8> \
  bash ~/ZV-Bench/scripts/jira.sh create-child <PARENT_KEY> "<summary>" "<desc>"

# Parentless issues only; refuses Sub-task:
JIRA_AS=<id> bash ~/ZV-Bench/scripts/jira.sh create <PROJECT_KEY> "<IssueType>" "<summary>" "<desc>"

# Comment (artefact/checkpoint, prefixed [<your id>]):
bash ~/ZV-Bench/scripts/jira.sh comment <KEY> "<text>"
```

`create-subtask` is a deprecated alias for `create-child`; it now applies the same rule.

To fix a mis-typed issue without losing its key, use `jira.sh reparent <KEY> <NEW_PARENT>`
(bulk-move API; a plain `PUT issuetype` is rejected for Sub-task ↔ standard conversions).

## Opening a ticket — field checklist

Every ticket needs all ten scored fields (`evals/jira-ticket-quality.md`):

1. **Parent** — the conversation's epic (`config/conversations.tsv`). Epic → Task, Task → Sub-task.
2. **Summary** — one line, the deliverable, no ticket keys inside.
3. **Description** — context/reason, what was asked and by whom, what exists, what done means.
   - Any ticket assigned to Zhenia, or whose next step is Zhenia's, opens with "What to
     do": numbered steps Zhenia can follow without reading anything else — where to open
     it, the exact command or click, what success looks like, what to do if it doesn't
     work, what happens after (who verifies and closes). Context goes underneath, at most
     two lines, under "Why". Never an open decision like "Olga to say where" (ZHEN-7270,
     context only, no steps) — decide first, then write the steps.
     ```
     What to do:
     1. Where to open it
     2. The exact command or click
     3. What success looks like
     4. What to do if it doesn't work
     5. What happens after (who verifies and closes)
     ```
4. **Labels** — owner id (the route); `FOR=<id>` when the ticket is a work order for a named agent.
5. **Sprint or backlog** — active ZHEN sprint (board 15) if it fits; otherwise backlog + reason written on the ticket.
6. **Story points** — `STORY_POINTS=<n>` on create/create-child; values: 1, 2, 3, 5, 8.
7. **Due date** — from the request; else sprint end for sprint work; blank only for backlog with no deadline.
8. **Priority** — Medium default; High = blocker; Highest only when Zhenia says so.
9. **URLs** — first URL in `customfield_10081`; extras at the top of the description.
10. **Assignee** — blank (labels are the route); `zhenia` only when the step is Zhenia-only.

## Confluence — fetch before every write

REST v3 base: `https://zvi.atlassian.net/wiki`.
Auth: `(ZV_JIRA_EMAIL, ZV_JIRA_API_TOKEN)` basic auth.

**Always fetch the current page before writing** to get the version number and preserve
any manual edits made since the last automated write.

```bash
# 1. Fetch current body and version:
curl -s -u "$ZV_JIRA_EMAIL:$ZV_JIRA_API_TOKEN" \
  "https://zvi.atlassian.net/wiki/api/v2/pages/<PAGE_ID>?body-format=storage"
# → .version.number  (call it $VER)
# → .body.storage.value  (current content)

# 2. Write with version incremented by 1:
curl -s -u "$ZV_JIRA_EMAIL:$ZV_JIRA_API_TOKEN" \
  -X PUT "https://zvi.atlassian.net/wiki/api/v2/pages/<PAGE_ID>" \
  -H "Content-Type: application/json" \
  -d "{\"id\":\"<PAGE_ID>\",\"status\":\"current\",\"title\":\"<TITLE>\",
       \"body\":{\"representation\":\"storage\",\"value\":\"<STORAGE>\"},
       \"version\":{\"number\":$(( VER + 1 )),\"message\":\"<agent-id>\"}}"
```

For large pages or SOP publishing, use the canonical converter:
`~/ZV-Bench/tools/on-demand/sop-generator/publish_sop_to_confluence.py`.

Preserving edits: read the current body, merge only the section you own (e.g., "Where it
stands"), and PUT the merged result. Never overwrite the whole page from a stale local copy.
