# Script Craft Library

Two books sit behind your scriptwriting the way STRATEGY.md's twelve sit behind your strategy coaching. They are not new rules — `yt-autopilot/instructions.md` and `retro-findings-master.md` still outrank everything here. These are the *why* underneath those rules, so that when a script is flat you can name what is missing instead of guessing.

**The notes below are your working knowledge.** Normal script work never needs the PDF open. Go to the PDF when Zhenia asks a question that needs the full argument, or when you are diagnosing a structural problem the notes don't cover. Read chapters, not books.

## Access

Both live in `ref-db-main/all-pdfs` (`1EKyBT1pobCN8Wug6TrDq57jT_Ee7NyVn`), shared with the service account — same folder and same method as the strategy library (TOOLS.md → Strategy library access).

| Book | Drive file ID | REF ticket |
|---|---|---|
| Miller — Building a StoryBrand (2017) | `19Whkp1SQNLeD3Ro6mSBXNdq-8gqRRDA-` | [REF-6796](https://zvi.atlassian.net/browse/REF-6796) · Find |
| Edwards — Copywriting Secrets (2019) | `17G0COiUv1PIv7tT9U_7xj8tsgoPlqSrN` | [REF-5681](https://zvi.atlassian.net/browse/REF-5681) · Read |

```bash
python3 ~/ZV-Bench/scripts/gdrive-read.py read 19Whkp1SQNLeD3Ro6mSBXNdq-8gqRRDA- > /tmp/storybrand.pdf
pdftotext -f 60 -l 70 /tmp/storybrand.pdf -   # pull the pages you need, not the whole book
```

Neither book has printed page numbers you can trust, so **cite the actual PDF page** when you quote (`Miller, Building a StoryBrand, PDF p. 62`). Page numbers below are PDF pages in these exact files.

---

## Miller — Building a StoryBrand (2017)

The book's claim: customers don't buy the best product, they buy the one whose message they can understand with the least effort. Everything else follows from that.

**SB7, story in a nutshell (p. 26).** A CHARACTER who wants something encounters a PROBLEM before they can get it. At the peak of their despair a GUIDE steps in, gives them a PLAN, and CALLS THEM TO ACTION. That action helps them avoid FAILURE and ends in a SUCCESS.

**The three questions (p. 28).** At no point should a viewer be unable to answer: what does the hero want, who or what opposes them, what does their life look like if they do or don't get it. Miller's threshold is the first fifteen to twenty minutes of a film. Ours is the first thirty seconds. A cold open that leaves one of the three unanswered is the structural version of a retention cliff.

**The grunt test (p. 30).** Could someone answer in five seconds: what is this, how does it make my life better, what do I do next. Applied to a video: title + thumbnail + first line. Applied to a description: first two lines above the fold.

**Give the problem a villain (p. 60–62).** Personify the obstacle and position the product as the weapon against it. Formula's villains are already there and usually unnamed: tool sprawl, the note you can never find again, the system that works until Wednesday. Name one per video, and only one.

**Three levels of problem (p. 62–64).** External is the tangible thing (my notes are a mess). Internal is the frustration it causes (I feel disorganised and slightly ashamed). Philosophical is why it's *wrong* (people shouldn't have to fight their own tools to think clearly). Miller's line: companies sell solutions to external problems, but people buy solutions to internal ones. Practically — the title sells the external, the hook lands the internal, the close touches the philosophical. Scripts that only ever operate at the external level are the ones that feel like documentation.

**Be the guide, never the hero (p. 77).** The viewer is the hero. Zhenia is Yoda, not Luke. Every "here's how I built my system" beat must resolve into "here's how you build yours" or it inverts the roles.

**Guides need empathy plus authority (p. 78–80).** Empathy: "we understand how it feels to…", "like you, we're frustrated by…". Authority is competence, not bragging, and Miller lists four cheap ways to show it — testimonials (three, not twenty), statistics, awards, logos. Ours: real numbers, a screen recording of the thing actually working, the retro that says what failed.

**A plan removes risk.** Viewers need to see the steps between where they are and the result. Three or four named steps beat a comprehensive one.

**Two calls to action (p. 96–100).** Direct (buy, subscribe, register) and transitional (a free thing that on-ramps: PDF, template, webinar). Every video should carry one of each. Formula Commons is a textbook transitional CTA — it stakes territory, creates reciprocity, and positions the guide. Miller's observation is worth pinning: in thousands of clients he never met anybody who *oversold*; nearly everyone's CTA falls softer than a whisper.

**Stakes (p. 106–108).** If there is nothing to lose, there is no story. Kahneman's loss aversion — people are two to three times more motivated to avoid a loss than to achieve an equivalent gain. But fear is salt in the recipe: too much and viewers block it out, too little and nothing moves. One line of stakes, placed before the payoff, not a doom-laden intro.

**Success, and closing the loop (p. 118–122).** Show where you're taking them. Miller's three resolutions: status/power, self-realisation or acceptance, transcendence (being part of something bigger). "If we don't tell people where we're taking them, they won't follow."

**Identity transformation (p. 126–129).** Beyond the result, who does the viewer get to *become*? Formula's answer is roughly: the person whose systems just work, who thinks clearly in public, who understands the why before the how. That identity should be visible in the last thirty seconds of every long-form video.

**How to use it.** Before drafting, write the seven lines out for the video — one sentence each. If any line is blank or generic, the brief isn't finished and the script will drift. It costs five minutes and it is the fastest structural diagnosis you have.

---

## Edwards — Copywriting Secrets (2019)

Blunter, tactical, aimed at direct response. Where Miller gives structure, Edwards gives the sentence-level moves. Thirty-one "secrets"; the ones that matter for scripts:

**#3 — Nobody buys without a reason why (p. 39–41).** Ten reasons people buy: make money, save money, save time, avoid effort, escape mental or physical pain, get more comfort, better health/hygiene, gain praise, feel more loved, raise status. Edwards keeps the first five memorised. Every video promise should hang on one *named* why — "save time" and "escape pain" are usually Formula's, and they are different videos.

**#4 and #13 — It's about them, never you (p. 48, p. 142).** Count the *you*s against the *I*s in a draft. A Formula script is allowed first person when the story earns it, but the ratio should be lopsided toward the viewer.

**#6 — The headline is the most important piece of copy you write (p. 65).** Ogilvy: five times as many people read the headline as the body. Title and thumbnail are the headline; the first spoken line is the second headline. Spend disproportionate time there and treat it as its own draft, not the byproduct of finishing the script.

**#8 — F.R.E.D., your avatar (p. 87–89).** Know the words he uses, and "enter the conversation already going on inside his head". Concretely: pull phrasing from comments, Reddit threads and search queries rather than inventing how a viewer would describe the problem. If the hook uses our vocabulary instead of theirs, it doesn't land.

**#9 — Bullets (p. 107–110).** Bullets exist to build curiosity, not to inform; 3–12 at a time; and the classic failure is listing features instead of benefits. In a script this is the "here's what you'll be able to do" beat — the point where most drafts slip into specs.

**#10 — Emotion sells, logic justifies (p. 116).** Give the viewer the emotional reason to act *and* the logical one to defend the decision afterwards. Missing either loses a different half of the audience.

**#15 — Three formulas that never fail (p. 157–163).** All three work at any length — a twenty-page letter, a one-minute VSL, a ten-minute talk, and therefore a thirty-second cold open:
1. **Problem / Agitate / Solve.** Agitate is the magic and the step everyone skips. State the problem, make it *hurt*, then solve it.
2. **"If you want X, Y and Z, then do this."** Desire-led rather than pain-led. The right shape when the video is aspirational, not remedial.
3. **Before / After / Bridge.** Where they are, where they could be, the bridge across. This is the natural spine for a workflow or tutorial video.

**#19 and #30 — Originality is overrated; keep a swipe file (p. 205, p. 309).** Rearrangement beats invention. The competitor research files in each `(NNNN)` folder are already a swipe file — mine them for structure, never for phrasing.

**#20 — Stories make them thirsty; copy tells them where to buy a drink (p. 211–213).** The distinction to hold: a story's job is to create want, the CTA's job is to convert it. A video full of stories and no ask converts nothing; a video full of asks and no story earns none.

**#21 — Love me or hate me, there's no money in the middle (p. 221).** Take a position. Formula's "why before how" is a position; softening it into "here are some options" is how a script becomes forgettable.

**#29 — You can't catch fish without a hook (p. 301–303).** A hook is an angle that induces *curiosity*, and nothing else — it is not there to sell, convince or convert. Edwards separates it from the USP: the USP is what makes the product different ("our three-minute video fixes 90% of long-drive problems"); the hook is the lightning-fast story about that difference ("one-legged golfer outdrives Tiger Woods"). Most weak Formula hooks are USPs wearing a hook's clothes — accurate, unsurprising, no curiosity gap.

**#31 — Polish (p. 314).** Editing is a separate pass, after the draft, never during.

**How to use it.** After the structural pass (StoryBrand), run the copy pass: is there a named why (#3), is the hook curiosity rather than claim (#29), which of the three formulas is the spine (#15), does the ask actually get made (#20).

---

## The opening — 28 questions

The beginning of the first paragraph of a blog post, online article or video script answers as many of these as it can. Not all 28, but as many as possible.

1. What is the single most important thing the reader should learn from this text?
2. What in it would make the reader read a passage aloud to a friend?
3. What surprised you while gathering the material?
4. Is there a short story that captures the essence of the text?
5. Do I have an image that reveals the essence of the text?
6. What is the conflict?
7. How will what I am writing about affect my readers? (An answer to "So what?")
8. What actually happened?
9. Why would anyone read this text? (Another answer to "So what?")
10. Do you have a metaphor that captures the essence of the text?
11. Where does it take place?
12. What VOICE is the story told in?
13. Does the story have a FACE?
14. Where are the points of tension in the story?
15. Do you have a quote that expresses the essence of the story?
16. Which elements of the story connect to each other, and how?
17. What is the structure of the text?
18. Which key questions does the text answer?
19. What form best tells the story? (Interview, report, captioned photo, infographic, video and so on.)
20. Do I have one or two specific details that reveal why the story matters?
21. What is the backstory?
22. What problems do you need to solve in writing the text?
23. From which point of view is the story best told?
24. What is the central event of the text?
25. What is MY opinion of this story?
26. Should I tell this story at all?
27. Why did this story happen?
28. What is the sequence of events?

## The kicker

Two sentences, three at most: where the viewer downloads the thing (link in the description) and the one next video to watch, by title with its (NNNN). No callback to the opening, no comment prompt, no lead magnet line, no restated thesis.

## Opening and kicker are their own tasks

Eva orders the opening and the kicker from Writer as two separate tasks, apart from the body. Each delivery of a finished piece to Zhenia ends with a reminder to look over the opening and the kicker.

---

## Precedence

1. `yt-autopilot/instructions.md` — the scriptwriting source of truth. Always wins.
2. `retro-findings-master.md` — Formula's own measured retention evidence. Beats any book, because it is this channel's data.
3. These two books — craft depth and diagnostic vocabulary for when 1 and 2 don't explain why a script is flat.

If a book's advice contradicts a retro finding, the retro finding wins and it is worth saying so out loud to Zhenia. Direct-response copy is written for people who chose to open a sales letter; a YouTube viewer is one click from leaving. The retention data is the correction.

Cite the book and concept when you coach ("Edwards calls this agitating — the hook states the problem but never makes it hurt"), so Zhenia can read deeper. Never update the REF tickets without their explicit approval.
