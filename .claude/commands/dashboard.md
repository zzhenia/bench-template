---
name: dashboard
description: Start, stop, or restart the Actions Dashboard (http://localhost:7391).
---

Manage the Actions Dashboard. The argument should be one of: `start`, `stop`, `restart`. If no argument is given, default to `start`.

**Commands:**

- **start** — Launch the dashboard server in the background and open http://localhost:7391 in the browser. Before starting, check if port 7391 is already in use (`lsof -ti:7391`). If it is, tell the user the dashboard is already running and open the browser.
- **stop** — Find the process on port 7391 (`lsof -ti:7391`) and kill it. Confirm it stopped.
- **restart** — Stop the dashboard (if running), then start it again.

**How to start the server in the background:**

```bash
nohup python3 actions/on-demand/actions-dashboard/server.py > /dev/null 2>&1 &
```

Then open the browser:

```bash
open http://localhost:7391
```

**How to stop:**

```bash
lsof -ti:7391 | xargs kill 2>/dev/null
```

After running the command, report what happened (e.g. "Dashboard started at http://localhost:7391" or "Dashboard stopped").
