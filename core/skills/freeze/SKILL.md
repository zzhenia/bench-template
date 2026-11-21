---
name: freeze
description: Freeze this tab so the idle auto-close never shuts it; the next message unfreezes it. Usage: /freeze (or /freeze all for every Cursor tab)
model: haiku
---

If `personal/overlays/freeze.md` exists in this bench, read it first; where it differs from the steps below, it wins.

The `UserPromptSubmit` hook normally handles a bare `/freeze` before it reaches
you. If you are reading this, do it yourself, with no questions:

1. Run `core/tools/freeze/freeze.sh`. Add `--all` when the argument is
   `all`.
2. Reply with one line: `Frozen: this tab will not auto-close. Typing anything unfreezes it.`
   or `Not frozen: <the script's error>`.

Run nothing else.
