---
name: bugs
description: Record a list of bugs to carry into the next session.
---

Capture bugs discovered during this session that can't be fixed now, and write them to the correct convo folder for the next session.

The user's message after `/bugs` contains everything you need: the convo marker (`>> name`), bug descriptions, and possibly screenshots. Process all of it.

## Procedure

### 1. Identify the convo folder

Scan the user's message (the arguments passed with `/bugs`) and the full conversation for `>>` at the start of a line or message. Extract the convo name (first word after `>>`, kebab-case).

- If found: use `convos/<name>/`. Create the folder + bench-index row if it doesn't exist.
- If NOT found: determine from session topic. If it clearly matches an existing convo, use it. If ambiguous, ask.

### 2. Collect the bugs

The user's message after `/bugs` contains the bug descriptions. They may include:
- Inline text descriptions of each bug
- Screenshots showing the issue
- References to specific files, functions, or UI elements

Extract every distinct bug from the user's message. For each one:
- Give it a short, descriptive title
- Write a description paragraph with enough detail to start fixing next session
- If a screenshot was attached, describe what it shows and reference the relevant visual evidence in the bug description
- Include file paths, function names, or UI locations when mentioned or inferable

If the user's message is vague or you need clarification, ask — but in most cases the message will contain everything needed.

### 3. Write the bugs file

**Filename:** `convos/<folder>/YYMMDD_BUGS.md` (e.g. `convos/goal-updater/260424_BUGS.md`)

Use today's date in YYMMDD format. If a bugs file for today already exists, ask whether to overwrite or append.

**Format — follow this template exactly:**

```markdown
# [Topic] — Bug List

<!-- @ai Process all items in this bug list as priority at the start of the next session. Work through them top to bottom, fixing each one before moving to the next. -->

**Created:** YYYY-MM-DD
**Status:** Open — carry into next session

---

### 1. [Short bug title]
[Description — enough context to reproduce or understand the issue. Include file names, function names, or UI locations where relevant. If a screenshot was provided, describe what it shows.]

### 2. [Short bug title]
[Description]

...
```

Key rules:
- The `@ai` comment at the top is essential — it tells the next session to process these bugs automatically.
- The `[Topic]` in the heading should match the convo/project name (e.g. "YT Autopilot", "Goal Updater").
- Number each bug sequentially.
- Each bug gets a `###` heading with a short descriptive title.
- The description paragraph should have enough detail to start fixing without needing to re-discover the issue. Include specific file paths, function names, UI element names, or error messages when known.
- When screenshots were provided, reference what they show — the actual images won't be in the markdown, so the text must stand alone.
- Keep descriptions factual and concise — no speculation about fixes unless the user provides one.

### 4. Confirm

After writing the file, show the user:

> Wrote X bugs to `convos/<folder>/YYMMDD_BUGS.md`:
> 1. [Bug title]
> 2. [Bug title]
> ...
>
> These will be picked up automatically at the start of the next session via the `@ai` annotation.

### 5. Post to ticket (if applicable)

Look up the slug in `bench-index.csv` and post a brief comment:

```bash
python3 actions/on-demand/bench-ticket/bench_ticket.py post <slug> <bugs-file>
```

If no ticket is found, skip silently — this step is optional.
