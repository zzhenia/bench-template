---
name: status
description: Show the current status of all scheduled bench automations.
model: haiku
---

Regenerate the living inventory of every scheduled job (Mac, openclaw-1, the old laptop)
and show it.

1. Run:
   ```bash
   python3 tools/on-demand/automation-status/inventory.py
   ```
2. It writes `AUTOMATIONS.md` at the bench root (one row per job: where, when, calls a
   model, posts to Slack, cost over the last 7 days, what it does). Auto-push regenerates
   the same file nightly.
3. Read `AUTOMATIONS.md` and display the table inline.
4. For the launchd-only detail view (last run status, log tails) run
   `python3 tools/on-demand/automation-status/generate_status.py` and show its file.
