---
name: eval-writing
description: Write an eval for a piece of work before it starts, then run it on the result before accepting it — when to write one, the Done-when opener, format, naming, the accept/redo loop.
---

If `personal/overlays/eval-writing.md` exists in this bench, read it first; where it differs from the steps below, it wins.

# Eval writing

An eval is written before the work starts and run on the result before the work is accepted.

## When to write one

Write an eval for:
- Builds (a script, a tool, a code change)
- Anything that deletes or moves things
- Anything that runs in bulk or touches a live target (a video channel, a drive, a ticket tracker, a chat workspace, a scheduled job)
- Whenever the user asks for one

No eval for one-line lookups, relays or single ticket comments; the reviewer reads those directly.

## The `Done when:` opener

Every eval starts with `Done when: <one checkable gate>`: the target, the number it expects, how it is read.

- Markdown evals: line 1 of the file.
- Shell evals: the shebang stays line 1, so `# Done when:` is line 2.
- The gate comes from the eval's own pass condition. If it does not fit one line, the eval is not ready.
- The gate is checkable without judgement. "Works" is not a gate; "exit 0 with 30 rows, none empty" is.
- The same line goes into the work request's `Done when:`, so the request and the eval cannot drift apart.

Start from `TEMPLATE.md` or `TEMPLATE.sh` in this folder.

## Format and naming

**Shell evals** — `evals/<TICKET-KEY>.sh`: `# Done when:` on line 2, a check against the real target, exit 0 = pass, exit 1 = fail.

**Markdown evals** — `evals/<TICKET-KEY>.md`, when no shell line can prove it: `Done when:` on line 1, then test cases with steps and pass/fail criteria.

**Tool evals** — `tools/<type>/<name>/eval.md`, kept apart from `instructions.md`: `Done when:` on line 1, test cases with steps and pass/fail criteria. Run before accepting any change to that tool.

## The loop

1. The eval is written first, and its `Done when:` line goes into the work request:
   ```
   Work <TICKET-KEY> — <title>
   Deliverable: <what exists when this is done>
   Destination: <path>
   Deadline: <YYMMDD>
   Done when: <the eval's line 1>
   ```
2. The work is done and reported with the artefact (path + commit, link, or result).
3. The reviewer runs the eval against the real target, never against the summary.
4. On a fail, the work goes back with the failing line. At most two redos on the same line; a third fail is escalated.
5. On a pass, the work is accepted. Passing evals stay in `evals/` as the record.

## Safety

Evals run read-only against the live target and never repair anything. A broken target is reported, not fixed.

## Model calls inside an eval

Every `claude -p` call in an eval passes `--model` explicitly (a cheaper model for a plain yes/no judge). Without it the call runs on the CLI default, and every sample and judge is a separate session. Put the work folder in `mktemp -d`.
