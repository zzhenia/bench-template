---
name: eval-writing
description: How Evalbot writes evals for work orders — procedure, format, criteria, and Kitty's review process
---

# Eval-Writing — Evalbot's Procedure

Evalbot writes evals for work orders when Kitty orders one, before the work starts, and runs the eval on the result before Kitty accepts it. This document captures Evalbot's eval-writing procedure as of 2026-09-27 (baseline for SkillOpt-Sleep optimization).

## When Evals Are Ordered

Evals are ordered for:
- Builds (a script, an action, a code change)
- Anything that deletes or moves things
- Anything that runs in bulk or touches a live target (YouTube, Drive, Jira, Slack, a cron)
- Whenever Zhenia asks for one

No eval is written for:
- One-line lookups
- Relays
- Single ticket comments
Kitty reads those herself.

## The `Done when:` Opener

Every eval starts with `Done when: <one checkable gate>` (line 1; line 2 after the shebang in `.sh` evals). It is the eval itself, simplified to one line: the target, the number it expects, how it is read. It is the final qualifier; anything else the eval needs (checks, fixtures, safety notes) goes below it.

- Markdown evals: `Done when:` is line 1 of the file.
- Shell evals: the shebang must stay line 1, so `# Done when:` is the first line after it.
- The gate is derived from the eval's own pass condition. If you cannot state it in one line, the eval is not ready.
- The gate is checkable: a reader can tell true from false without judgement. "Works" is not a gate; "exit 0 with 30 rows, none empty" is.
- The same line goes into the work order's `Done when:` (below), so the order and the eval cannot drift apart.
- Model: the official `skill-creator` skill, where every step ends with a checkable gate ("**Done when:** frontmatter matches how the skill will actually be reached").

Start from `TEMPLATE.md` or `TEMPLATE.sh` in this folder.

## Eval Format and Naming

**Shell script evals:**
- Filename: `evals/<TICKET-KEY>.sh`
- Opens with `# Done when:` (line 2, after the shebang)
- One shell line that proves the result
- Exit 0 = pass, Exit 1 = fail
- Can verify against live target

**Markdown evals:**
- Filename: `evals/<TICKET-KEY>.md` (when no shell line can prove it)
- Opens with `Done when:` on line 1
- Rubric with test cases, steps, and pass/fail criteria
- Example: `jira-ticket-quality.md` (10 scored fields, per-field filled criteria)

**Action evals:**
- Filename: `tools/<type>/<name>/eval.md`
- Opens with `Done when:` on line 1
- Test cases with steps and pass/fail criteria
- Separate from `instructions.md`
- Kept by Evalbot, run by Kitty before accepting an order that changed the action

## The Work Order Process

1. **Kitty orders the eval first**, before work starts
2. Evalbot writes the eval and provides the `Done when:` line for the order (the eval's own line 1)
3. The work order includes:
   ```
   Work order <TICKET-KEY> — <title>
   Deliverable: <what exists when this is done>
   Destination: <bench path>
   Deadline: <YYMMDD>
   Done when: check-box: <one shell line, exit 0 = true>   (Evalbot's eval)
   ```
4. Handler completes the work
5. Handler reports done: `… comment <TICKET-KEY> "done — <artefact: path + commit, Drive link, or result>"`
6. **Kitty runs the eval against the real target**
7. If eval fails:
   - Kitty recommissions the handler with the failing line
   - Handler fixes and reports done again
   - At most two recommissions on the same failing line
   - Third failure = stall (escalate to Olga or another owner)
8. No recommissioning needed: Kitty accepts the work

## Eval Safety Boundaries

**Evals run read-only against the live target and never repair anything.** If the eval's target is broken, the eval reports the breakage; it does not fix it.

## Model Calls Inside an Eval

Every `claude -p` call in an eval passes `--model "$(python3 "$BENCH/scripts/bench-profile" model smart)"` (`fast` for a plain yes/no judge). Without `--model` the call runs on the CLI default, the most expensive model, and each sample and judge is a separate session. Run the workdir as `mktemp -d /tmp/<ticket-key-lowercase-no-dash>-eval.XXXXXX` (e.g. `/tmp/oc97-eval.XXXXXX`) so the token audit files the cost under Evalbot and the ticket.

## Eval Examples

### jira-ticket-quality.md (rubric format)
- 10 scored fields (Parent, Summary, Description, Labels, Sprint or backlog, Story points, Due date, Priority, URLs, Assignee)
- Per-field filled criteria (pass/fail, not partial credit)
- Score: `fields_filled / fields_expected`
- Comment shape: `[jira] opened — N/10 fields; missing: <field>, <field>`
- Friday running average over all tickets Jira opened that ISO week

### Shell script eval format
```bash
#!/usr/bin/env bash
# Done when: <one checkable gate>
# Single exit 0/1 check against the real target
exit 0  # pass
# or
exit 1  # fail
```

## Baseline: Current Practice (2026-09-27)

This SKILL.md captures the eval-writing procedure as of the SkillOpt-Sleep trial start. Proposed edits will be gated against held-out test evals to ensure no regression in quality, consistency, or coverage.

---

*Extracted from `~/ZV-Bench/skills/network/RULES.md` §4 (Work orders) and `~/ZV-Bench/convos/openclaw/specs/evalbot.md` (Evalbot's role). No rewording applied.*
