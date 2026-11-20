---
name: status
description: Show the current status of all scheduled bench automations.
model: haiku
---

If `personal/overlays/status.md` exists in this bench, read it first; where it differs from the steps below, it wins.

Run the automation inventory and display the result.

1. Run:
   ```bash
   python3 core/tools/automation-status/inventory.py
   ```
   It regenerates `AUTOMATIONS.md` at the bench root: every scheduled job, where and when it runs, model calls, Slack posts, 7-day cost, what it does.
2. Read `AUTOMATIONS.md` and show the table inline.
3. For the launchd detail view (last run status, log tails) run `python3 core/tools/automation-status/generate_status.py` and show the file it writes (`state/automation-status/YYMMDD-automations.md`).
