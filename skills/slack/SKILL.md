---
name: network-slack
description: How every agent uses Slack — surfaces, fetch the thread before every reply, lost context, reply shape, reactions, failures, incident table. Read before any Slack read or post.
---

# How to use Slack

**Whose skill this is: every agent that talks to Zhenia on Slack** — Eva, Kitty,
Olga, and any agent added later. One copy, here, read from the bench clone on the box
(`~/ZV-Bench/skills/slack/SKILL.md`). A personality file may hold a pointer to
this file and its own channel list; it never holds a second copy of these rules. When a
Slack mistake happens, the fix goes into this file and its incident table, once.

Zhenia's Slack user id is `U085EGDHTND`. Your bot token: `~/.openclaw/openclaw.json` →
`channels.slack.accounts.<your-id>.botToken` (Olga: `SLACK_BOT_TOKEN_OLGA` in
`~/.openclaw/keys.env`). Channel ids per agent: `~/ZV-Bench/convos/openclaw/specs/network.md`.

## 1. Know where you are before you type

You are never handed the channel id or the thread. Get them, every time, from
`session_status(sessionKey="current")` → *Route context* → `active.to`
(`channel:C…` or `user:U…`) and `active.threadId` (the `thread_ts`). Never guess an id
from a memorised list; the list in your AGENTS.md is for sanity-checking only.

Three surfaces, three behaviours:

| Surface | What arrives | How you behave |
|---|---|---|
| DM with Zhenia | everything | answer everything, in the thread it came in |
| Channel where you receive every message (Kitty in #spanish-vocab, #sb; Eva in #formula-*, #social-media) | everything | answer what is addressed to you or is your job there; stay silent on the rest; one reply per message. In a capture channel (#spanish-vocab, #sb) nothing is addressed to you: the one-line ack is the whole reply |
| Mention-gated channel (Kitty in #jira-admin, #openclaw-ops; Olga in every conversation channel) | only @mentions and threads you are already in | answer only when mentioned; nothing else in that channel is yours |

#openclaw-ops is Olga's channel: Zhenia talks to Olga there. No other agent answers a
message there unless @mentioned by name.

## 1b. Who is being spoken to — decide this before you read the message

**One owner per channel. Non-owners: NO_REPLY without composing.** Every channel has
exactly one owner (`specs/network.md`, Slack channels table). If you are not the owner
and you were not @mentioned (`explicitly_mentioned_bot: false`), send `NO_REPLY` — as the
entire turn, without drafting a response first. You are not on this channel by accident;
the owner is covering it. Never compose a reply when you are not addressed.

Zhenia never has to name the owner: a message with no @mention is for the owner and nobody else.
The envelope says who was addressed — `explicitly_mentioned_bot`, `mentioned_user_ids`,
`mention_source` and `sender.is_bot` in the `Conversation info` block. Read those first.

| The message | Channel owner | Anyone else who received it |
|---|---|---|
| no mention | answers | `NO_REPLY` |
| @mentions you (`explicitly_mentioned_bot: true`) | answers | answers, in a thread under Zhenia's message; the owner stays silent |
| @mentions another agent (`mentioned_user_ids` names a sibling, not you) | `NO_REPLY` | `NO_REPLY` |
| written by a sibling agent (`sender.is_bot: true`) | `NO_REPLY` | `NO_REPLY` |

- **A mention is a native `@name` (`<@U…>`) and nothing else.** Your name in a sentence
  is not a mention (gateway policy `channels.slack.mentionPatterns.mode = deny`, 260916).
  Only Zhenia addresses agents on Slack; a sibling reaches you through `sessions_send` or
  your inbox, never by writing your name in a channel.
- **"Not addressed to me" is never a message.** When the turn is not yours, the entire
  output is `NO_REPLY` — no sentence before it, no reasoning after it. Anything before
  `NO_REPLY` is delivered (260916, Olga posted "Still Kitty and Zhenia going back and
  forth — not addressed to me" into #refadmin).
- **Knowing the answer does not make it yours.** Zhenia writing `@Olga` in #refadmin means
  Olga answers and Kitty says nothing — in Kitty's own channel, even when Kitty could help
  (260916, Kitty answered a message addressed to Olga two minutes before Olga did). If
  Zhenia says something is another agent's territory *without* @mentioning them, that is a
  handoff: file it to that agent's inbox and reply in one line saying so.
- **Olga in a conversation channel:** Zhenia never talks to her there by default. She
  answers only when Zhenia @mentions her (technical help on something that came up), in a
  thread under that message, and stays in that thread until it ends. Kitty is silent for
  the whole thread.
- **Thread carry-over yields to a channel's unconditional owner.** `requireMention: true`
  gates fresh top-level messages, but Slack's `implicitMentions.threadParticipation`
  (default `true`, only overridable per account — not per channel) still wakes a
  mention-gated agent on every later message in a thread it once replied in, no fresh
  mention needed. In #openclaw-ops that collides with Olga's unconditional read of every
  message: a thread where Kitty answered once, then goes quiet, still wakes Kitty on
  Zhenia's next unrelated ask in the same thread — same message, two independent turns
  (260919, ZHEN-6900/6901: two near-duplicate tickets for one "JT …" ask). The fix has to
  be at reply time, since the gateway wakes both regardless: in #openclaw-ops, thread
  participation is never standing on its own — `NO_REPLY` unless the message carries a
  fresh @mention or is a sibling handoff (§1b above). Olga already covers everything else
  there.

## 2. Read the thread before every reply — you cannot see your own earlier replies

The thread history the gateway hands you **excludes your own earlier replies**
(ZHEN-6418, upstream bug). Every thread therefore looks as if Zhenia's earlier messages
went unanswered. Re-answering them is the failure mode (260825, Fred explained the same
thing twice; 260803, Kitty duplicated notes). So, before every reply in a thread:

```sh
bash ~/.openclaw/scripts/slack-thread.sh <your-id> <channel-id from active.to> <thread_ts from active.threadId>
```

(`eva`, `kitty`, `videobot`, `olga`; source copy `~/ZV-Bench/scripts/slack-thread.sh`.)
The delegated `message(action="read")` tool does **not** work for this, even inside a
live thread.

**`reply_to_id` in a message envelope is the same thing as a thread parent ts.** That
is how a threaded reply arrives in a DM (there is no `active.threadId` there), and the
parent's content is NOT in your turn — only the pointer is. Run `slack-thread.sh
<your-id> <channel> <that reply_to_id>` first; the ROOT line it prints is the message
being replied to. Common case: Zhenia rating a morning book post with a short reply
("Review, low") — without the fetch it reads as a fresh request about something else
(260910, Kitty answered a book rating as a code-review request, ZHEN-6742). Then:

- Answer **only the newest unanswered message**. If a question already has your reply
  above it, it is answered.
- **A top-level message from Zhenia in a channel is a reply to your last message there.**
  Zhenia answers your posts at top level as often as in a thread. Run
  `slack-dm.sh <you> 30 <channel>` (section 2b) and read their message against your last
  line in that channel. If that message carried several items (two tickets, three books)
  and their reply does not name one, do not take the first: name the items in one line
  and ask which. Never ask "where did that happen?" — that is a question about your
  tooling (260916, Kitty answered about REF-1548 when Zhenia meant REF-1575, then asked
  them to point at it).
- **An attached screenshot is the pointer.** A picture of one of your messages says
  "this one": it names the working object. Read it before replying (section 5b).
- A reply from Zhenia in a thread is a reply to **your last message in that thread**,
  not to a file or conversation elsewhere. "The draft above", "add this to the package",
  "my previous response" = content one message up. Never invent a missing object.
- **Pin your working object.** Name the thing you are working on (slug, title, URL) in
  every message, so their reply can never be misread as being about something else.
- If a reply genuinely does not fit your last message, quote the one candidate you think
  they mean and ask ONE yes/no. Never redirect the work onto a guess (260823, Eva edited
  an already-published post).
- Zhenia pasting their own draft ("my reply to X: …") is a **handoff**: return a
  polished, post-ready version in their voice (`~/ZV-Bench/skills/writing/VOICE.md`),
  draft first in a code block, at most two lines of comment after. Never just discuss it.

## 2b. Read the DM before every top-level reply — your own messages are invisible to you

Any outgoing message you sent — regardless of whether it came from a cron job,
a heartbeat, a main session, or anywhere else — may be missing from your in-session
history (OpenClaw gateway bug, ZHEN-6677). This includes messages sent seconds ago.
**You will not notice it is missing.** You will have some other context that seems to
fit, and you will answer about the wrong thing. (260908: Kitty was asked "Could you list
those four?" — the four Spanish captures from Kitty's 14:22 message. Kitty couldn't see
that message, guessed the question was about the three Jira tickets from the 13:32
burndown, and answered about tickets.)

**Before every top-level reply in your DM channel**, run:

```sh
bash ~/.openclaw/scripts/slack-dm.sh <your-id>            # your DM with Zhenia, last 30
bash ~/.openclaw/scripts/slack-dm.sh <your-id> 50          # more
bash ~/.openclaw/scripts/slack-dm.sh <your-id> 30 <channel-id>   # a channel instead
```

(`eva`, `kitty`, `videobot`, `olga`; source copy `~/ZV-Bench/scripts/slack-dm.sh`.)
It uses your own token, finds your own DM, and marks the lines you sent as `YOU` —
including the cron and heartbeat ones your session never saw. Find the message Zhenia is
replying to by matching their message to the most recent `YOU` line before it. If
Zhenia's message is in a thread, also run `slack-thread.sh` on that thread (section 2).

**Never guess what a reply is about.** If Zhenia's message contains a reference ("those
four", "that ticket", "my previous"), the thing it refers to is in the DM history — read
it first, then answer. Never say "I don't have context", redirect to another agent, or
guess from your in-session memory without reading first.

**Never assert that you did or did not write something in Slack from in-session memory
alone.** Before ANY claim about your own past messages — especially a denial — run
`slack-dm.sh <your-id> 30 <channel>` or `slack-thread.sh <your-id> <channel> <thread_ts>`
and read the actual history. Your Slack identity posts from many sessions (crons,
heartbeats, other channels routing follow-ups) and those messages can be invisible to your
current session. If Zhenia says you wrote something, the default assumption is that you
did and your context is missing it; a denial without a history fetch is forbidden (260918,
ZHEN-6892).

## 2c. Scheduled messages read the conversation before they are written

A heartbeat or cron report (production check, sprint burndown, morning books, digest,
CMO check-in — anything sent on a schedule) runs in a **fresh, isolated session**: it
has never seen your DM with Zhenia, the channel it posts to, or what Zhenia decided
yesterday. Left alone it reports the durable record (sheet, Jira, tracker) as if nothing
had been said since — and repeats a question Zhenia already answered. (260906: Zhenia
told Eva in the DM "no work yet on 0062", 0062 on hold; the 260907 and 260908 production
checks both flagged 0062 as urgent and asked whether the publish date had moved. Zhenia:
"otherwise, it's a bit useless".)

**Before composing any scheduled message, read the surface it goes to** — same command
as 2b, wider window:

```sh
bash ~/.openclaw/scripts/slack-dm.sh <your-id> 40               # scheduled DM to Zhenia
bash ~/.openclaw/scripts/slack-dm.sh <your-id> 40 <channel-id>  # scheduled channel post
```

Then, and only then, write the message. What you are looking for, newest first:

1. **Decisions Zhenia stated** about anything your report covers — on hold, cancelled,
   date moved, done, "do not ask again", a strategy shift. They win over the sheet or
   Jira. Report the item as Zhenia left it ("0062 on hold since Sep 6 — nothing to do")
   and never re-flag it as stale, late or blocked.
2. **Answers to questions your last report asked** (the `YOU` lines are your earlier
   reports). Act on them; do not ask again.
3. **Questions you asked that got no answer.** Ask once more at most, in different
   words, then stop — an unanswered question is a decision, not a gap.
4. **What your last report already said.** Say only what changed since; if nothing
   changed and the job requires a message, one line saying so.

If the read fails (Slack error, script missing), send the report anyway from the durable
record and add one line "(could not read our DM first)" — Zhenia never gets a missing
report because a lookup failed. This section is the rule; it is also wired in as step 0
of the jobs that send Zhenia a scheduled report (Eva's production-check and its
`production-coordinator.md`, Kitty's burndown and morning-book jobs, 260908). A new
scheduled job that messages Zhenia gets the same first line.

**Record decisions where the schedule reads them.** When Zhenia tells you something in
chat that a scheduled report depends on (a hold, a date, a rating), write it into the
durable place the job reads *in the same turn* — tracker Notes row, the Jira ticket,
the job's state file — dated. The DM read above catches what was said in the DM; the
durable record catches what was said in a channel or a thread the job will not read.

## 2d. The 'stop' message — corrections and do-overs

A message that is ONLY `stop` / `wait` / `hold` / `espera` (one word, nothing else) means
Zhenia wants to correct or replace the earlier message you were about to act on. Do not
act on the earlier message.

**Your reply:** one line exactly: `"Stopped. Send the corrected version when ready."`

**If the earlier turn already acted** (created a calendar event, wrote a file, posted to a channel),
say exactly what was done in that same reply so Zhenia can undo it. Example:
`"Stopped. I'd already created the calendar event 'Dentist' for Oct 1. Delete it or send the corrected version when ready."`

**Before acting on any Zhenia message in section 2 (thread or DM), fetch the full thread first.**
If a newer Zhenia message corrects or replaces the one you are about to act on, act on the
newest version only. A deleted message is never acted on.

## 3. Lost context — one lookup pass, then one question

Your session gets compacted; earlier detail disappears. That is your problem, never
Zhenia's. When they say "that job", "the digest", "the ticket", "the script" and you
cannot place it, you get **one lookup pass before you may ask**:

0. A short letter code at the start of the message (`sb`, `nr`, `JT:`) is a command
   shortcut, not a name — `~/ZV-Bench/skills/shortcuts/SKILL.md` has the table.
1. The thread and the recent history of the surface you are on, with the fetch above —
   and the other likely surface (a channel discussion often precedes a DM ask).
2. Your own workspace files (Eva: STRATEGY.md, MARKETING-COACH.md, the job's Drive
   folder, digest outputs; Kitty: bench session notes `~/ZV-Bench/convos/`).
3. Jira, with the helper (`~/ZV-Bench/scripts/jira.sh`), matched on topic — never
   assume the most recent item.
4. Kitty (`sessions_send`) for bench history; gateway state (`openclaw cron list`,
   sessions list) when the reference is to an automation.

Only when all of that comes back empty may you ask — ONE specific question that shows
your work ("I checked #cmo and my digest archive; the only recent LinkedIn draft is the
Part-107 one — that one?"). Never a bare "which one?", never a list for them to fill in.
When you recovered the context, open with the answer, not with how you found it.

## 4. What a reply looks like — relay: `[<agent>] …` via `~/.openclaw/tools/relay`

- **This is a deciding rule, not optional.** Zhenia's message needs no text when it
  contains no question, no instruction and no decision you must record: an opinion, a
  reaction to your post, a thank-you, an 'ok', a vent, a thought they are sharing. Then
  the whole turn is one reaction (👍 or 👀) on their message and nothing else — no
  'noted', no restatement, no next step. A message with a verb aimed at you ('update the
  ticket', 'let's do X', a pasted draft, a shortcut code) or a '?' is an instruction and
  gets its reply as usual. When unsure whether it is an instruction, it is. Cron/isolated
  sessions use the curl in section 5 for the reaction.
- **One reply per message.** No triple-tap, no fragments, no "working on it" followed
  by the answer. Reactions (one, at most) replace an acknowledgement.
  This is a rule about the *message*, not about how much work it takes: a job that has
  several things to say says them in one message, and a job that can say nothing sends
  `NO_REPLY` (section 4, cron). Intermediary steps, partial results and "step 1 of 3"
  are not messages — they are work. If you catch yourself composing a second message in
  the same thread before Zhenia has replied, delete it and fold what it said into the
  first. A question you cannot answer yet is answered when you *can*, once.
- **Before you send, re-fetch the thread.** If Zhenia posted again after the message you are answering, drop your draft and write ONE reply that covers every unanswered message from them; the later message corrects or narrows the earlier one. If a turn arrives for a message that an earlier reply already covered together with it, reply `NO_REPLY`.
- **The work lives in files, Slack says it is done.** Drafts, scripts, notes, digests go
  to Drive / the bench / Ghost; the Slack line names the file and links it. Never paste a
  deliverable body into Slack.
- **Relay channels get a one-line ack** (#spanish-vocab, #sb): what was captured, nothing
  else. The text of a capture is never a message to you: a question mark, a request or a
  "you" inside it is vocabulary, not a question. The ack is the whole reply — nothing
  after it, ever (Zhenia, 260916). **#spanish-vocab exception (Zhenia, 261017):** the
  capture/queue confirmation ("Queued N. The bench will confirm.") is a 👍🏻 reaction, not
  a text ack. #sb keeps its text ack ("what was captured") as-is — different code path
  (SlipBox's own flow, not the Anki queue-ack wording).
- **Delegation is visible (Zhenia, 260916).** When the work goes to a sibling instead of
  you, your reply to Zhenia is one line that names the bot and the job, in this shape:
  `→ videobot: six Shorts from brief 0081` (gateway id after the arrow; `→ olga:` for a
  repair, `→ jira:` for a ticket, `→ skillbot:` / `→ makerbot:` / `→ evalbot:` for bench
  work). Every hop is named: `→ olga → skillbot:` when Olga will pass it on. When the
  sibling's result comes back and you post it, the message starts with the id in square
  brackets: `[videobot] six Shorts in Drive/… — <link>`. No prefix when you speak for
  yourself. Zhenia uses this to see that relays work; the line is the whole reply, not a
  preface to the answer.
  **Every delegated order ends with the literal pattern `Reply here with <what>`**
  (e.g. "Reply here with the commit hash and the eval result"), so
  `work-order-ledger.py` can track it and relay the sibling's report into the thread once
  it lands. Once the ledger has relayed that report, the delegator posts no second
  confirmation message, no further confirmation at all — the ledger's relay is it.
  
  **Relay tool:** To post a message from your agent directly to a channel or thread, use
  `~/.openclaw/tools/relay --from-id <agent-id> --channel "#channel" --text "message"`.
  The tool adds the `[<agent-id>] ` prefix, validates through the ZHEN-6949 message gate,
  and posts under Kitty's token. Use `--thread <message-ts>` instead of `--channel` for
  thread replies. Unknown agent IDs are rejected; the gate enforces length and content
  rules (no error narration, no permission requests inline).
- **A promise to report back is a timer, not a hope (Zhenia, 261012: "you always say you're going to follow up or confirm things, but you never do") — scoped to work you do directly, with no order sent to a sibling.** Every reply that says "I'll post / confirm / send it when done" about work you are doing yourself creates, in the same turn, an `automations` one-shot (`schedule.kind: "at"`, about 20 min out, `sessionTarget: "current"`) that names each promised item and how to verify it. That run checks the live state itself, then posts the result with its link, or re-sends the dropped order and schedules the next check. Delete the timer if the result was posted first. No timer = don't promise; finish the work in the turn instead. **When the promise depends on an order sent to a sibling instead**, this timer does not apply: `work-order-ledger.py` (the work order ledger) tracks that order and relays the sibling's report into the thread when it lands — do not also create an automations timer for it.
- **A turn started by a sibling's `sessions_send` report never reaches Slack on its own.**
  That turn's final composed text goes back to the sibling that sent the report, not to
  the Slack thread or channel. Anything from that turn that must reach Slack — e.g. a
  verification correction after checking a sibling's claim — is posted with the `message` tool in that same turn, not left as the turn's final text; a later turn is too late.
  **Never say a message was posted to Slack unless the `message` tool itself returned a
  result for it in that turn.** A composed final answer, on its own, is not a post.
- **No narration of your machinery.** Nothing about tools, scripts, permissions, sessions
  or retries reaches Zhenia. If a sentence describes your own plumbing rather than their
  question, delete it.
- **Write nothing between tool calls, full stop (ZHEN-7139).** With `streaming.mode: off`
  (260904 upgrade), every line of text your turn writes between tool calls — not just lines
  about your own machinery — is joined to your final answer and delivered as one message.
  This is not a content filter you can satisfy by staying on-topic: any commentary at all
  ("Let me check X", "Found Y, now Z") leaks through, makes the reply long enough to trip
  the message gate, and can itself get pattern-matched as step-narration and block the whole
  send. The only reliable fix is mechanical: output no text at all until your final answer
  is ready to send, then send only that.
- **Acknowledge with 👀, never with words (Zhenia, 261017; recurrence of ZHEN-7139).** A
  multi-step turn (several tool calls, a build, a relay) still goes out as one message when
  you finally compose it — but that one message must be the answer only. Don't let status
  lines ("Done — …", "Now committing…", "Pushed (…). Now routing…", "Now replying to
  Zhenia.", "Delivered. Summary: …") become part of what you compose, even as the lead-up
  to a real summary at the end. If the work is seen and started, that's the 👀 reaction —
  nothing else — not a sentence saying so. Compose once, at the very end, and that
  composition is the whole reply.
- **Cron / isolated sessions:** your final message is delivered verbatim as the job's
  output. If the job cannot complete, the entire final message is exactly `NO_REPLY` and
  nothing is delivered. Errors go to Olga (section 6).
- **Formatting is Slack mrkdwn, not Markdown:** `*bold*` with single asterisks,
  `_italic_`, `` `code` ``, fenced blocks for anything pasted, `<url|text>` for links, no
  `#` headings, no tables (use short lines).
- **Message gate limit — count before sending.** A chat reply to Zhenia is **at most 350
  characters AND at most 3 sentences** (both rules apply). Not counted: fenced code blocks
  and a URL on its own line. An inline URL or `<url|text>` link counts toward the limit. A
  sentence is any `.`, `!`, or `?` followed by a space or line break — so "e.g. " counts as
  one. Over the limit, the message is deleted (not trimmed), so Zhenia gets nothing and a
  rewrite costs a second full response. Count first: `python3 ~/ZV-Bench/tools/recurring/message-gate/gate.py check -`
  on your draft. Content that doesn't fit goes in a file, Drive doc or ticket; the reply
  is one line with the link. **Exempt from the length rule:** replies to Zhenia's messages
  that open with `ghost`, `medium`, `reddit` or `linkedin` (the post is output, not chat).
  All other gate rules still apply to those replies.
- **Never open by restating, summarising or agreeing with Zhenia's message** (Zhenia,
  261014). They know what they said. The first sentence is your own content — the
  answer, the decision, the objection. Delete any lead-in of the form "Agree with…",
  "That flips it…", "So you want…", "Good point about…".
- **Short answer first.** Lead with the direct answer or decision in 1–3 sentences (or
  one line). No front-loaded full explanation, drafts, reasoning, or fix write-ups unless
  Zhenia explicitly asks for detail. If more is warranted, wait for them to ask in a
  follow-up, then give it all.
- **Humour:** subtle, positive, never sarcastic, never at the expense of the task.

## 4b. Abort a run in progress

To stop a run that is already in progress on the box, Zhenia types a message with **a
leading space** before the `/stop`: ` /stop` (not `/stop`). Slack's message parser
blocks a bare `/stop` command, so the space is required. The gateway will confirm the abort.

This is different from sending the word "stop" alone (section 2d), which asks you to
correct a message you have not yet acted on.

## 5. Reactions

- **A message that needs no text (§4) gets only the reaction — nothing else, ever.**
- React like a person: one emoji when you saw something and need not reply (👍 ✅ 👀).
  One reaction per message, maximum. Never a reaction plus a reply that says the same.
- **Live conversation:** the `react` tool action works.
- **Cron / isolated session:** the `react` tool fails ("requires the exact current
  conversation"). Use the Web API right after sending, with the message `ts`:

  ```sh
  curl -s -X POST https://slack.com/api/reactions.add -H "Authorization: Bearer $TOKEN" \
    -d channel=<channel_id> -d timestamp=<msg_ts> -d name=<emoji>
  ```
- **Reading reactions** (Kitty's book jobs): `reactions.get?channel=…&timestamp=…&full=true`,
  and look for the emoji whose `users` contains `U085EGDHTND`.
- **A text reply beats a reaction.** Zhenia overrides any emoji by replying in the thread
  under that specific message ("Medium, review"); the emoji set stays small on purpose, so
  a job that reads reactions also reads `conversations.replies` on the same `ts` and
  applies the text when there is one. Never nag for a reaction that a text reply already
  answered (260916; build tracked as ZHEN-6841 — Book rating pipeline: text-reply override
  instead of more emoji reactions).

## 5b. Files Zhenia attaches

The gateway's `message(action=download-file)` only works inside the exact turn that
carries the attachment; from a nested run, a cron job or a later reply it says
"requires the exact current conversation and account" (260910, ZHEN-6737). That is not a
reason to tell Zhenia the file is out of reach — your own bot can fetch it:
```sh
~/.openclaw/tools/slack-file <you> <file-id or permalink> [--out PATH] [--pad 20]
```
Prints where it saved the file (`--json` to parse). `--pad N` puts an image on a white
background with N px of border, which is what "white background with a border" means.
`file_not_found` means the bot is not in that channel — say which channel and ask for it
to be re-attached where you are. For a Formula Daily post, the Ghost side is
`daily_draft.py --date <D> image <file>` (formula-daily skill, step 3).

## 6. When Slack breaks

Retry once, silently. If it still fails, file it with Olga — one file
`~/.openclaw/medic/inbox/<you>-<YYYYmmdd-HHMMSS>.md` with `agent:`, `doing:`, the exact
`command:` and the verbatim `error:` — and then **answer Zhenia from what you can see**:
the message in front of you plus anything quoted in it. If the answer truly depends on
what you cannot see, ask one plain question about the content, never about your tooling.
Zhenia never hears "I can't pull the thread", "let me try another way", or that a
sibling is down (siblings: `sessions_send` is asynchronous — silence inside your turn is
not failure; resend once next turn, then Olga).

## 7. Olga

Same rules, live plumbing. Olga is a gateway agent (since 260905): Zhenia's messages to
her DM `D0BUWR40KAN` and to #openclaw-ops reach her as live turns and she answers in the
same thread. The old `medic.sh slack-inbox` poller is retired — its crontab line must stay
absent (specs/olga.md asserts it; do not put it back).

Her only open surfaces are Zhenia: `dmPolicy: "allowlist"` with `allowFrom: ["U085EGDHTND"]`
(her DM), and #openclaw-ops. Anywhere else she speaks only when Zhenia @mentions her
(section 1b). Every other group channel she sits in — she is a member of
the conversation channels only to run Slack admin actions Kitty's token cannot — is
mention-gated: account `requireMention: true`, with
`channels.C0BUQJULML3.requireMention: false` for her own channel. Do not set the account
`requireMention` back to `false` and do not add `"*"` to `allowFrom`: that hands every
channel message to a live olga session and Zhenia gets duplicate answers (260914, §8).

## 8. Incidents — what broke, and the rule that came out of it

| Date | What happened | Rule / fix |
|---|---|---|
| 260620 | Every config write restarted the gateway; Slack does not replay messages received while disconnected | batch config changes; expect a lost message after a restart |
| 260623 | A DM session wedged with a dangling tool call (API 400) | `/new` in Slack resets the session; compact, do not archive, Slack session keys |
| 260630–260714 | Thread sessions started with no parent context | `channels.slack.thread.inheritParent: true`, `historyScope: thread` (narrowed from `channel` 260822) |
| 260728 | Bot messages invisible in thread context | `contextVisibility: all`, `allowBots: true` |
| 260730–260816 | Thread history excludes the agent's own replies (ZHEN-6418) | `slack-thread.sh` before every thread reply (section 2) |
| 260802 | Streaming edits corrupted replies | `streaming.mode: off` gateway-wide |
| 260803 | Kitty re-answered a thread and wrote duplicate notes | answer only the newest unanswered message; `slipbox-write.py` refuses title collisions |
| 260816 | An agent went deaf in a channel | two layers must both be on: Slack app Event Subscriptions (`message.channels`, `message.groups`) *and* the account's `groupPolicy`/`requireMention` |
| 260823 | Reply read as being about the wrong object; a published post got edited | pin the working object; one yes/no before redirecting (section 2) |
| 260825 | Fred explained the same thing twice in one thread | section 2 |
| 260904 | "Working / Completed / Bash — failed" cards and leaked thinking reached Zhenia after the 2026.8.2 upgrade | `streaming.mode: off`, `nativeTaskCards: false`; never narrate tooling |
| 260904 | Agents told Zhenia they could not fetch a thread | section 6: answer from what you see, file with Olga |
| 260910 | Zhenia asked three times for an attached diagram to go into a post; Fred said it was out of reach (download-file refused from a nested run) | section 5b: `slack-file <you> <file-id>`, then `daily_draft.py image` |
| 260905 | Kitty answered every message in #openclaw-ops (meant for Olga) | Kitty mention-only there (`accounts.kitty.channels.C0BUQJULML3.requireMention`); Olga polls her own surfaces |
| 260908 | Kitty answered "Could you list those four?" with Jira tickets instead of Spanish vocab captures — the 14:22 captures message was invisible, the 13:32 burndown was Kitty's last known context | `slack-dm.sh` before every top-level DM reply, not just when you notice confusion (section 2b) |
| 260908 | Eva's production check flagged 0062 as urgent two days running after Zhenia had put it on hold in the same DM — the heartbeat runs in a fresh session and never read the conversation (ZHEN-6709) | `slack-dm.sh <id> 40` before every scheduled message; decisions in chat go into the durable record the job reads (section 2c) |
| 260913 | Zhenia got three replies to one request and asked for the rule to be enforced for every agent: "Too much text, respond once instead of 3 times" | Section 4: one reply per message — one message per job run, intermediary steps are never messages; a repeated/duplicate notification is a pipeline bug to fix at the source, not something to say in Slack |
| 260917 | Zhenia asked Eva for one extra check in `social-craft`; Eva edited the skill file and pushed it herself, in two messages that narrated the rebase and push | a skill file is Skillbot's even when the subject is writing: `→ kitty → skillbot:` one line, the result relayed as `[skillbot] …` — RULES §3; section 4, delegation is visible, no narration |
| 260916 | Zhenia posted two Spanish sentences with the target words bolded in #spanish-vocab; Kitty queued them, then answered the sentences' question about a Slack artefact library | a capture's text is never a message to the agent; the ack is the whole reply — section 5, relay channels |
| 260916 | Kitty wrote "once Olga's looked at it" in #refadmin; the gateway's default mention pattern matched the name, ran a live Olga turn, and Olga posted "not addressed to me" into Kitty's channel | native @mentions only: `channels.slack.mentionPatterns.mode = deny`; `NO_REPLY` is the whole message (§1b) |
| 260916 | Zhenia @mentioned Olga in #refadmin; Kitty answered first because it is her channel | a message @mentioning a sibling is not yours, even in your own channel (§1b) |
| 260916 | Zhenia's top-level reply to a two-item reminder was taken as being about the first item; Kitty asked them to point at where the text response happened | top-level reply = reply to your last message there; several items → name them and ask which; text reply beats reaction (§2, §5) |
| 260914 | Olga answered in #jira and re-verified Kitty's ticket confirmations (three near-identical blocks) — her account had `groupPolicy: "open"` + `requireMention: false` and no channel map, so the gateway routed every message in every channel she's a member of to a live olga turn | Olga is mention-gated everywhere except her own surfaces: account `requireMention: true`, `channels.C0BUQJULML3.requireMention: false` (§7) |
| 260918 | Kitty's #calendar-email session posted 'the Enterprise damage claim (#24327274)' into #personal-finance; the gateway recorded it as a zero-token delivery-mirror (invisible to that session); Zhenia referenced it a minute later; Kitty denied authorship from in-session memory, contradicted by its own visible message four lines up; Zhenia sent a screenshot | Never assert that you did or did not write something in Slack from in-session memory. Before ANY claim about your own past messages — especially a denial — run `slack-dm.sh` or `slack-thread.sh` and read the actual history. If Zhenia says you wrote something, the default is that you did and your context is missing it; a denial without a history fetch is forbidden (§2b, ZHEN-6892) |
| 260919 | One "JT …" ask in #openclaw-ops filed two near-duplicate tickets (ZHEN-6900, ZHEN-6901) — Olga's unconditional channel read and Kitty's `implicitMentions.threadParticipation` (thread carry-over from an earlier reply, no fresh mention) both fired on the same message; Kitty's `requireMention: true` there never applied because thread carry-over bypasses it | thread participation is never standing in #openclaw-ops on its own — §1b; `threadParticipation` has no per-channel override (account-wide only), so this is a reply-time rule, not a config fix, unless Zhenia wants the account-wide toggle (ZHEN-6903) |
| 261001 | Zhenia sent a dentist appointment message to Kitty by mistake, then typed `stop`; Kitty created the calendar event anyway because agents on the CLI backend cannot read a mid-run message until the turn is complete | ZHEN-7085: messages that are only `stop` / `wait` / `hold` / `espera` mean "correct/replace the earlier message" — do not act on it (§2d). To abort a run already in progress, Zhenia types ` /stop` (leading space; bare `/stop` is blocked by Slack). See also §4b |
| 261012 | Kitty promised the Crónica ES/EN PDF (261010) and many "I'll confirm"s that depended on a bot's report arriving; the PDF was never posted | Every "I'll confirm" gets an automations follow-up timer in the same turn (§4) |
| 261013 | Eva sent two replies 4 s apart — one per message — when Zhenia sent a follow-up correction while Eva was still composing (Zhenia: "if I send you a second message while you are still working on the answer on the first one, you need to stop composing the first message and consider both of my messages together … often I send a follow-up message to correct or narrow down my initial message") | Before you send, re-fetch the thread; if Zhenia posted again, drop your draft and write ONE reply covering every unanswered message; the later message corrects or narrows the earlier one (§4) |
| 261014 | In #formula-lf (23:23) Eva and Kitty both opened with a paragraph rephrasing Zhenia's message; Zhenia: "The first paragraph is always rephrasing my message. I don't need that." | First sentence is your own content, never a restatement (§4) |
| 261015 | Zhenia: "whenever my comment on Slack does not require an answer, for example it does not contain a question, the agent simply replies with an acknowledgement reaction instead of generating a response." | no question/instruction/decision → one reaction, no text (§4, §5) |
| 261017 | Kitty's DM carried in-between narration as part of the composed reply itself ("Done — …", "Now committing…", "Pushed (…). Now routing…", "Now replying to Zhenia.") ahead of the real summary — ZHEN-7139 closed without this actually fixed. Zhenia: use the 👀 reaction to show a request was seen, not narration text | §4: compose once, at the end, and that composition is the whole reply — no status lines, ever; 👀 is the entire acknowledgment (ZHEN-7139 reopened) |
| 261017 | Kitty's #spanish-vocab capture ack said "Queued N. The bench will confirm." as text; Zhenia wants a 👍🏻 reaction there instead | relay-channel ack in #spanish-vocab is a reaction (👍🏻), not text — §4 |
| 261019 | Kitty's "Verified — REF-7291 …" final text ran in a turn started by REFbot's `sessions_send` report, so it went back to REFbot, never to Slack — happened twice | §4: a sibling-report turn's final text never reaches Slack on its own; post with the `message` tool in that same turn; never claim a post without a `message`-tool result. Fixed alongside commit `09b678a2` / `work-order-ledger.py` (OC-131) |
