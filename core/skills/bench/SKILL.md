---
name: bench
description: List every skill and tool on this bench with a plain explanation of what each does, for someone new to the bench. Usage: /bench, or /bench <word> to filter.
---

If `personal/overlays/bench.md` exists in this bench, read it first; where it differs from the steps below, it wins.

1. Run `bash core/bin/catalog.sh`. Each row is `kind <TAB> name <TAB> where <TAB> description`:
   - kind: `skill` (typed as `/name` or picked up by Claude when the request fits), `tool` (a script Claude runs for you), `job` (runs on a schedule by itself).
   - where: `core` (every bench has it) or `bench` (this bench only).
2. If arguments follow `/bench`, keep only rows whose name or description matches them.
3. Reply with three short lists — **Skills**, **Tools**, **Scheduled jobs** — sorted by name. One line each: the name (skills as `/name`), then what it does in plain words for a newcomer: what you get, not how it works. Rewrite descriptions that are internal or vague; leave out trigger lists, file paths and ticket keys. Mark this-bench-only items with "(this bench)".
4. A row with an empty description: open that item's SKILL.md or instructions.md and write the line from it.
5. End with one line: "Ask about any of them, e.g. 'what does /note do?'"

This reply may run past the usual length limit; it is the list the user asked for. No other commentary.
