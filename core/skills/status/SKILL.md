---
name: status
description: Show the current status of all scheduled bench automations.
model: haiku
---

If `personal/overlays/status.md` exists in this bench, read it first; where it differs from the steps below, it wins.

Run the automation status script and display the result.

1. Run:
   ```bash
   python3 tools/on-demand/automation-status/generate_status.py
   ```
2. The script writes a dated markdown snapshot to `tools/on-demand/automation-status/assets/YYMMDD-automations.md`.
3. Read that file and display its contents inline — show both the summary table and the Details section.
4. Report the output file path at the end.
