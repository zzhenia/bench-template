---
name: freeze
description: Freeze this tab so the idle auto-close never shuts it; the next message unfreezes it. Usage: /freeze (or /freeze all for every Cursor tab)
model: haiku
---

The `UserPromptSubmit` hook normally handles a bare `/freeze` before it reaches
you. If you are reading this, do it yourself, with no questions:

1. Run `freeze.sh` from the first folder that has it: `tools/on-demand/freeze/`,
   `actions/on-demand/freeze/` (bench template), else
   `~/dev/dev-ZV/ZV-Bench/tools/on-demand/freeze/`. Add `--all` when the
   argument is `all`.
2. Reply with one line: `Frozen: this tab will not auto-close. Typing anything unfreezes it.`
   or `Not frozen: <the script's error>`.

Run nothing else.
