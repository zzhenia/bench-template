---
name: shortcuts
description: Command shortcuts Zhenia types — sb (SlipBox note), nr (new REF reference), cint (compile intros), jt (open a Jira ticket). Load whenever a message opens with a two- to four-letter code, upper or lower case, with or without a colon, in any Slack channel, DM or bench session, before treating the letters as a name, a person or a missing skill.
---

# Command shortcuts

A message that opens with a short letter code is a command; the rest of the message is
its argument. `JT: enable openprose skill` and `jt enable openprose skill` both mean "open
a Jira ticket for: enable openprose skill". Case does not matter. The letters are never a
person, a roster name or a skill folder. This table is the only list; Kitty's
`reference/ref-and-slipbox.md` holds the how for the ones she runs.

| Code | Means | Owner |
|---|---|---|
| `jt` | open a Jira ticket for what follows | **Jirabot** (`convos/openclaw/specs/jira.md`): files it at once with what the message gives, gaps marked TBD, and replies with key + title; no question before filing — the questions come afterwards, as one comment on the open ticket. Parent = the channel's epic in `config/conversations.tsv`; no epic for the channel → parent ZHEN-5505 — ZV admin, with the channel named on the ticket. Reply with key + title. |
| `sb` | write a SlipBox note from what follows (a quote, a link, a thought) | **REFbot**: `scripts/slipbox-write.py`. Every message in #sb is an `sb`. |
| `nr` | new reference: a Task in the REF Jira project, summary `Author - Year - Title` | **REFbot**: `scripts/jira-gate.sh create REF …` after the `ref-management` duplicate check. |
| `cint` | compile book intros for the next batch of Review books, or for the REF keys given | **REFbot**: `cint [REF-keys]`. |
| `rf` | single reference lookup: search for a free copy of one REF ticket | **REFbot**: `python3 ~/ZV-Bench/scripts/ref-find.py one <KEY>`. Status outcomes: **found** (PDF in all-pdfs, ticket Format pdf + Review), **not_found** (stays in Find), **quarantined** (unreadable text gate, file in ref_processing), **skipped** (source down or other transient error). Retry on skipped → files Olga's inbox immediately (do not delay). Reply with result and ticket link. |
| `rfs` | monthly free-copy sweep: search all Find-status tickets for available sources | **REFbot**: checks if `~/.openclaw/ref-find.lock` exists (if so, sweep already running — reply "sweep in progress, check back tomorrow"); otherwise runs detached `setsid nohup flock ~/.openclaw/ref-find.lock python3 ~/ZV-Bench/scripts/ref-find.py run` to completion across multiple days respecting rate limits (OpenAlex 100/day, arXiv 3s). Posts one summary line to #refadmin when done, or if stalled >24h files Olga's inbox with status log. Owner replies "sweep started" immediately. |

**Only one agent relays a shortcut, ever — never every agent present.** A shortcut is
not addressed to anyone, so without this rule every agent in the channel or thread treats
it as theirs to act on. On 260919 a single `jt` in #openclaw-ops (Kitty and Olga both
present) produced two separate `sessions_send` calls to Jirabot and two tickets
(ZHEN-6900/6901) for one line from Zhenia — in a channel with N agents that is N wasted
relays, not two. Jirabot's own dedup check (`convos/openclaw/specs/jira.md`, added the
same day) is a safety net for when this rule is missed, not the fix. The fix is upstream:
**the relayer is the channel's `bot` column in `config/conversations.tsv`** (e.g. channel
`openclaw` → Kitty). A channel not in that table — #openclaw-ops, a DM — defaults to
Kitty, unless the message names another agent directly. Every agent that is *not* the
relayer for that channel does nothing with the shortcut: no `sessions_send`, no reply, no
dedup check of its own — exactly as if the message were not addressed to it.

The Jirabot is live (260916): the relayer hands a `jt` verbatim to `agent:jira:main` by
`sessions_send` and tells Zhenia "Jira has it". Until the REFbot is spawned, Kitty runs
`sb`, `nr` and `cint` herself (RULES.md §2; the how is in her
`reference/ref-and-slipbox.md`). The owner replies in the same thread with the result:
ticket key + title, note name, or the extracts folder. On the Mac, Claude Code runs `jt`
itself with `scripts/jira.sh create-child` under the same parent rule.

Single-word triggers with their own rules stay where they are: `note` (channel-note job),
`cf` (convo digest), `ghost` (Formula Daily), `medium` (editorial), and the slash commands
(`/note`, `/push`, `/ask`, …).

## When the code is not in the table

Do not search the bench for a file by that name and do not look it up on the web. Ask
Zhenia one line — "`XY` — what does it stand for?" — then add the row here in the same
turn (`git -C ~/ZV-Bench pull`, edit, commit, push) so it exists for everyone next time.
A shortcut is defined once, on the bench, never in a personality repo or a channel.
