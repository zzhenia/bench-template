---
name: fb
description: Pull the PI website feedback rows ticked "Push to Claude Design" and copy them to the clipboard as a prompt for the Claude Design prototype chat. Usage: /fb [--all]
---

Run `scripts/fb-pull.sh` (add `--all` if the user asks to re-pull already-pushed rows). It fetches the ticked, not-yet-pushed rows from the Railway prototype server (which stamps them as pushed), and puts the list on the clipboard with a one-line instruction. Report the script's one line (count + IDs) and tell Zhenia to paste into the Claude Design prototype chat, then implement → DEPLOY ↑ in the preview. If it prints `0 item(s)`, say so and stop.

Why not let Claude Design fetch the URL itself: its fetch tool returned a stale copy of the list all evening (260903) whatever the path or query, so the clipboard is the reliable hand-off. Never curl `change-requests*.md` for testing — serving it stamps column D.
