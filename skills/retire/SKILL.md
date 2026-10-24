---
name: retire
description: Set this Cursor tab aside — move it into the left tab group, where it waits for its auto-note and auto-close. Usage: /retire
model: haiku
---

Zhenia is done with this tab for now but wants it to close on its own. Do these
steps with no questions.

1. Run:

   ```bash
   tools/on-demand/retire/retire.sh
   ```

   It moves this session's Cursor tab into the first (left) tab group.

2. Reply with one line and nothing else:
   - Success: `Retired: note after 15 min idle, tab closes after 3 h.`
   - Failure: `Not moved: <the script's error>`.

Write no note, run nothing else, and send nothing after that line: any new
activity restarts the idle clock.
