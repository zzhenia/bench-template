---
name: lookup
description: Where to look, in what order, before answering a question about the user's own facts, documents or past work (an ID, an amount, a date, a decision, "where is X"). Bench first, then this bench's own sources, then general knowledge, marked as such.
---

If `personal/overlays/lookup.md` exists in this bench, read it first; it lists this bench's own sources and how to reach each. Where it differs from the steps below, it wins.

Look before you answer. Stop at the first source that holds the answer.

1. **The bench.** `convos/<topic>/_memory-master.md`, then `_memory-index.md`, then the dated notes, then the rest of the repo (`grep -rn`). A note is a snapshot: give its date, and check the live thing before acting on it.
2. **This bench's other sources**, in the order the overlay lists them (wikis, ticket trackers, email, drives). No overlay: ask the user once where their documents live, and add the answer to `personal/overlays/lookup.md`.
3. **General knowledge**, only after 1 and 2 come up empty, and say that it is.

Rules:

- Never work out a number a document holds (an ID, a tax number, an amount, a reference). Find the document. A derived number looks right and is wrong.
- Say where the answer came from, once, in plain words: a source and a date, not a path.
- Nothing found anywhere: say what you searched, then answer from what you know, marked as such.
