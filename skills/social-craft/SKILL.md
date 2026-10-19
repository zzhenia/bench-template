---
name: social-craft
description: Passes every public draft under Zhenia's name goes through — voice, banned machine-writing patterns, and one open question at the end of every social draft.
---

# Social craft passes

**Whose skill this is: any agent drafting text Zhenia will publish** — Eva on
Reddit and LinkedIn today, whoever runs a platform tomorrow. The procedure does
not change with the agent.

Two shared files carry the substance, both in the bench clone on this box:

- `~/ZV-Bench/skills/writing/VOICE.md` — how anything published as Zhenia
  sounds, and the machine-writing patterns that are banned. **Read it before you
  draft.**
- `~/ZV-Bench/skills/writing/CRAFT.md` — the structural library (Miller's
  StoryBrand, Edwards' Copywriting Secrets). Eva runs it over scripts; here it is
  the same books and the same moves on a shorter canvas.

This skill is the procedure. Those files are the substance. Nothing you draft for
a platform skips it — digest drafts included.

## Pass 1 — before drafting

Answer these in your head, one line each. If you cannot answer the first two, you
do not have enough of the thread to draft.

- **Who is asking, and what do they actually want?** The literal question, not the
  topic. A person deciding between two plugins is not asking for a PKM philosophy.
- **What does Zhenia know here that nobody else in the thread does?** That is the
  whole reason to reply. If the answer is "nothing specific", the honest draft is
  short or there is no draft.
- **One claim.** Name it. Everything in the draft either supports it or goes.
- **Which villain?** (CRAFT.md, Miller) — tool sprawl, the note you can't find
  again, the system that works until Wednesday. One, named plainly, never three.
- **Formula's spine** — Problem/Agitate/Solve, or Before/After/Bridge, or a plain
  answer. Most comments are a plain answer, and that is correct.

## Pass 2 — after drafting, before it reaches Slack

**Use `social-craft/EVAL.md`** — scored 24-item checklist. Eva runs this against every draft.

1. Open `~/ZV-Bench/skills/social-craft/EVAL.md`
2. Go through each of the 24 items; mark ✓ (pass) or ✗ (fail)
3. Calculate score: (passed items / applicable items) × 100
   - Skip items that don't apply to the draft (e.g., question rule for blog posts)
4. **Gate: 80% minimum**
   - **≥80%:** Pass to Zhenia
   - **<80%:** Return to Writer with the list of failed items only; do not send to Zhenia

**Quick reference (full details in EVAL.md):**
- **Ban sweep.** Read VOICE.md's banned machine-writing patterns: announced insight, contrast pivot, tidy triplet, summary close, undersized landing, label opener, oblique tail clause. Cut the frames.
- **Permanently banned phrases:** Check for "In conclusion", "It is important to note", "Furthermore", "leverage", "unlock", "game changer", etc. (full list in EVAL.md item 9)
- **Core rules:** First line at content, concrete detail, ~25 word ceiling per sentence, one claim, evidence from Zhenia's practice (not "many users"), no hedging, no pitch
- **Length:** Reddit 60–150 words (unless question demands more), LinkedIn comment 40–80, LinkedIn post <200, X one thought
- **Closing question** (skip for blog/Formula Daily): open, specific, genuinely unanswered, not a survey
- **Spelling:** Never "correct" British to American or vice versa; match what Zhenia pasted
- **Fact-check:** Named author/book/study/stat verified against real sources
- **First mention:** any real person named → 1–2 word descriptor before their name (Writing SKILL.md, Voice and Tone); name alone after that
- **Dense opener** (Shorts/LI/X/Reddit/FD openers — skip for long-form): if the first sentence packs jargon or assumed context, add one short plain sentence before it; see VOICE.md (Lead-in before a dense opener) and SF pass below

## Every post ends with an open question (Zhenia, 260904)

**The last line of every public draft is one open question.** Reddit and LinkedIn
comments, LinkedIn/X/Bluesky posts, audience posts — all of them. No exceptions
for short drafts.

What counts:

- **Open.** It cannot be answered with yes, no, or a number.
- **Specific to them.** It uses something from their post — their tool, their
  workflow, the constraint they named. A stranger reading the thread should be
  able to tell the question was written for that person.
- **One.** Two questions is an interview, and people answer neither.
- **Genuinely unanswered.** If the draft already answers it, it is rhetorical.
  Rhetorical questions are banned outright.
- **Not a prompt for praise** and not a survey ("Thoughts?", "What do you think?",
  "Anyone else?", "Curious to hear your take", "How do you handle this?" as a
  standalone). Those are the failure mode, not the rule being satisfied.

Good: *"When your daily note fills up mid-afternoon, where does the overflow
go — a new note, or the next day's?"*
Bad: *"What's your take on daily notes?"*

The blog is different: Formula Daily posts keep their sign-off and no question
is added. This rule is for social only.

## SF (shorts) pass

**The loop (shorts).** Open on one concrete image or idea (a place, an object, a moment, a question) and make the last line before the CTA come back to it, so the short closes where it started. Example FD26-038: it opens on the idea lost at the bus stop and ends on the bus-stop ideas being worth forgetting. Use it whenever the opening has an image the ending can return to naturally; don't force it when there isn't one.

**No glued sentences.** Each sentence carries one thought a listener can follow on a single hearing; never join the first half of one idea to the second half of another with 'and', 'so', 'because' or 'which'. Fuller and plain beats compressed.

Distinct from the oblique tail clause (VOICE.md): glued = two half-ideas joined into one sentence; oblique tail = second clause refers to an unstated premise via vague referents.

**Stand-alone clarity: every sentence must make sense to a reader who never saw the source Daily. Joining sentences (no-staccato, two-part rules) must never drop the step that connects them. Banned: a pronoun with no clear referent, a clause bolted on with ', and' that changes subject, a definition wedged mid-sentence, A-so-C with B cut. If the join loses the logic, use two full sentences.**

Must-FAIL: "Business professor Sophie Leroy called it attention residue in a 2009 paper, the part of your mind that stays on the task you just left, and I run into it most days." (definition wedged mid-sentence; ', and' changes subject)

This qualifies, not contradicts, the no-staccato and two-part rules: joining is permitted when the connection is kept; it is forbidden when the join hides the logic.

## The three command words: fix, ghost, medium

A message from Zhenia that **starts with one of these words** is a command about the text
that follows (or the text pasted earlier in the thread). It is never a question to answer
and never an invitation to discuss the content.

| Word | Means | Reply |
|---|---|---|
| **fix** | Commission Writer to edit the text (Zhenia, 260914 — never do the line edit yourself): grammar, rhythm, machine tells, length the same or shorter. Keep every point Zhenia made. Do not answer it, do not reply to the person it is addressed to, do not add a claim. Fact-check any named claim before it goes back | the fixed text as plain chat text, nothing else — never a code block (Zhenia, 260914: plain text reads better in Slack); one line after it only if you added the closing question |
| **ghost** | Build and schedule the Formula Daily post from it — `formula-daily` skill | the post's `preview_url` + `edit_url` |
| **medium** | Draft it on Medium — `editorial` skill (`medium publish` = live) | the draft link |

"fix" at the start of a message means the text is Zhenia's own draft, wherever it will be
posted. Treating it as a Reddit thread to respond to is the failure mode.

## When Zhenia pastes their own draft back ("fix")

Zhenia's words outrank every rule here. `sessions_send` the paste to Writer
(`agent:writer:main`, or a job slug if the thread already has one) with: fix
grammar, rhythm and the machine tells, keep every point they made, do not add a
claim of your own, same length or shorter. Review what comes back against
VOICE.md, fact-check any named claim it contains with a real `web_search`, and
return the whole thing as plain chat text, ready to paste — never wrapped in a
code block (Zhenia, 260914). If their draft has no
closing question, add one in their register — that is the one addition you are
allowed to make, and say in a single line after the block that you added it.
