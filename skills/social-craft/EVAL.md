# Social Craft Eval — Draft Scoring Checklist

**Purpose:** Scored eval checklist for Eva to run against every Writer draft before it reaches Zhenia. Gate: 80%. Below gate, return failed items to Writer for another pass — never deliver to Zhenia below 80%.

**Score:** passed items / applicable items × 100. If item doesn't apply to the draft (e.g., question rule for Formula Daily blog post), exclude from denominator.

---

## 24-item checklist (Pass/Fail per item)

**Machine-writing patterns banned (from VOICE.md tells):**

1. ✓/✗ **No announced insight opener** — "Here's what I learned", "The thing nobody tells you", "Then I realised", "The insight that made it click", "The part to get right"
2. ✓/✗ **No contrast pivot** — "It's not X, it's Y" / "Not just X but Y" / "Don't just X" / "X isn't the problem, Y is"
3. ✓/✗ **No tidy triplet, no paired-word ending, no repeated em-dash asides** — "capture, process, review" when two are true; "clarity and consistency" paired endings; em-dash aside used 3+ times in one paragraph (use parens instead)
4. ✓/✗ **No summary close** — "In the end", "Ultimately", "The takeaway", restatement of opening, closing line that praises the reader's question
5. ✓/✗ **No undersized landing** — final sentence carries the weight of what precedes it (not a short wisdom-y sentence, not isolated small words after buildup)
6. ✓/✗ **No label opener** — short 1-3 word tags OR longer lead-ins ending in colon ("Honest answer:", "Quick take:", "Where it aims is your 61%:")
7. ✓/✗ **No oblique tail clause** — second clause must not point at an unstated premise through vague referents ("what they know", "that", "it"); it must restate the first clause more plainly or add one concrete new point, and every referent must name something already said
8. ✓/✗ **Dense opener has lead-in** (Shorts/LI/X/Reddit/FD openers — skip for long-form) — if the first sentence packs jargon or assumed context the viewer lacks, one short plain sentence precedes it; the dense sentence continues unchanged

**Permanently banned phrases (from VOICE.md):**

9. ✓/✗ **None of these phrases present:** "In conclusion", "It is important to note", "That being said", "Furthermore", "Moreover", "Additionally" as an opener, "crucial/vital role", "game changer", "leverage", "unlock", "streamline", "dive into", "in today's fast-paced world", "hot take", "no fluff", "whether you're a X or a Y", "silently failing" / "fails silently" / "silent failure", "earns its keep" / "earn its keep", "the part to get right" / "the thing to get right", emoji inside a sentence

**Core rules (from social-craft skill + VOICE.md):**

10. ✓/✗ **First line starts at the content** — no throat-clearing, no restating their question
11. ✓/✗ **At least one concrete detail** — plugin name, number, date, specific moment (not "many users find...")
12. ✓/✗ **No sentence over ~25 words** — roughly 25 words is ceiling
13. ✓/✗ **Not three sentences of the same length in a row** — vary length on purpose
14. ✓/✗ **One claim only** — everything either supports it or goes
15. ✓/✗ **Evidence is Zhenia's own practice** — "I ran PARA for eight months and abandoned it because..." not "Many users find that..."
16. ✓/✗ **No hedging** — no "perhaps", "it could be argued", or similar uncertainty language
17. ✓/✗ **No pitch, no unsolicited Formula link** — link only if they asked for exactly that thing, mention only, not a pitch
18. ✓/✗ **No speaking for community, no flattery of question, no apology for length** — answer the person, not the audience
19. ✓/✗ **Length fits the platform** — Reddit 60–150 words (unless question demands more), LinkedIn comment 40–80, LinkedIn post <200, X one thought
20. ✓/✗ **Ends with exactly one open, specific, unanswered, non-survey question** — (skip for Formula Daily/blog) Uses something from their post; not answerable with yes/no/number; not rhetorical; not "Thoughts?", "What do you think?", "Anyone else?"

**Fact-checking (from VOICE.md):**

21. ✓/✗ **Named author/book/study/stat fact-checked** — if draft cites a name, number, or specific work, verify against a real source
22. ✓/✗ **Spelling matches what Zhenia pasted** — never "correct" British to American or vice versa; match whatever they used
23. ✓/✗ **No two-part summary sentence** — no sentence of the form 'A [thing] that does X is the one that Y'; especially forbidden as the second sentence of a comment where it sums up the first
24. ✓/✗ **Stand-alone clarity** — every sentence makes sense without the source Daily; joining sentences (no-staccato, two-part rules) must keep the connecting step; banned: pronoun with no referent, ', and' that changes subject, definition wedged mid-sentence, A-so-C with B cut; if the join loses logic, use two full sentences

---

## Scoring

Count passed items: `P`  
Count applicable items (exclude rules that don't apply, e.g., question rule for blog): `A`  
Score: `(P / A) × 100`

**Gate:** 80%

- **≥80%:** Pass. Send to Zhenia.
- **<80%:** Fail. Return list of failed items to Writer for another pass. Do not send to Zhenia.

---

## How to use (Pass 2 step in social-craft skill)

Eva runs this checklist against every Writer draft:

1. Open `social-craft/EVAL.md`
2. Go through each of the 24 items, mark ✓ (pass) or ✗ (fail)
3. Calculate score: (passed / applicable) × 100
4. If ≥80%: send to Zhenia
5. If <80%: reply to Writer with the list of failed items only (do not send the draft itself to Zhenia)

Example reply to Writer (score 75%, 15/20 passed):

> Score: 75% (below 80% gate)
> Failed items:
> - Item 3: Tidy triplet detected ("tool, workflow, system")
> - Item 11: No concrete detail beyond plugin names
> - Item 12: One sentence is 31 words
> - Item 20: Closing question is "What's your take?" (survey question)
> 
> Please revise and resubmit.

---

## References

- **VOICE.md:** ~/ZV-Bench/skills/writing/VOICE.md (five tells, permanently banned phrases)
- **social-craft/SKILL.md:** Pass 2 step where this eval runs
- **CRAFT.md:** ~/ZV-Bench/skills/writing/CRAFT.md (structural library, Miller StoryBrand)
