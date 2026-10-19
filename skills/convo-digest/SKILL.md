---
name: convo-digest
description: Keep a conversation's one-page Confluence digest current — run after any update to a conversation (a work order closed, a note written, a decision landed). Every bot uses it; the page never grows.
---

# Conversation digest — one page, forever

Every conversation in `config/conversations.tsv` has one Confluence page under
**Bench conversations**. It exists for Zhenia: they open it, read for one or two
minutes, know where the conversation stands, then go to Slack and talk to the bot.
It is a **state, not a log**. It is rewritten, never appended to, and it never gets
longer.

## When you run it

The bot that changed the conversation updates the page, in the same turn:

- a work order on that conversation closed (done or not done);
- a session note landed in one of its `convos/` folders;
- a decision was taken in its Slack channel or on a ticket.

Kitty may read the page, but her source is the bench convo (`bench-recall`); she
does not need the page to route work.

Zhenia's trigger: `cf` (or `confluence`) in the conversation's Slack channel, optionally
with what to record (`cf: we dropped the Cursor kit`). The channel-note cron
(`tools/recurring/channel-note/channel_digest.py`, every 2 minutes) rewrites the page
from `draft` plus the channel since the last `cf`, puts it, and replies in the thread with
the link, what it dropped, and what it would rather ask than drop; `cf: keep …` or
`cf: drop …` answers that. No agent turn is involved.

## The three commands

```sh
python3 ~/ZV-Bench/scripts/convo-digest.py <id> draft        # 1. what you rewrite from
python3 ~/ZV-Bench/scripts/convo-digest.py <id> put <file>   # 2. replace the page
python3 ~/ZV-Bench/scripts/convo-digest.py <id> show         # read it back
```

`draft` prints the current page (with its version), the conversation's memory
master, and every note dated since the page last changed. Write the whole new page
to a file, then `put`. `put` validates the shape and the cap and refuses if the page
changed since your `draft` — run `draft` again, never `--force` over someone's edit.

## The shape (validated)

```
## What this is        one or two sentences
## Where it stands     ≤ 5 bullets, newest first, each starts with YYMMDD, ≤ 25 words
## Open                ≤ 5 bullets — decisions pending, work in flight
## Next                ≤ 3 bullets
## Links               Jira epics (key — title), Slack channel, convos/<id>/, owning bot
```

Cap: **2,200 characters** excluding Links. Headings exact, in that order, no H1.

## Rules

- **Rewrite, never append.** Every `put` is the whole page.
- **Newest first; drop the oldest.** A new "Where it stands" line pushes the last one
  off. Something that stopped mattering leaves the page.
- **Keep Zhenia's lines.** They edit the page by hand. Read `draft` first; a line
  you did not write and cannot see a reason to drop stays, reworded only for length.
- **Never paste an artefact.** A report, a file, a ticket comment is a link in
  "Where it stands", not text on the page.
- **Numbers over adjectives.** "27 waitlists, all Eligible" beats "housing is progressing".
- **One page, forever.** If it does not fit under the cap, it is not digest material.

A page that reads like a changelog is the failure mode.
