---
name: dashboard
description: Start, stop, or restart the Actions Dashboard (http://localhost:7391).
model: haiku
---

Manage the Actions Dashboard. The argument can be `start`, `stop`, or `restart`. If no argument is given, default to `start`.

The dashboard is `actions/on-demand/actions-dashboard/server.py`, launched by `run.sh` in the same folder. It serves whichever bench started it, on port 7391.

---

### start (default when no argument)

1. If something is already listening on 7391 (`lsof -ti:7391`), stop it first so THIS repo's dashboard takes the port.
2. Start it in the background from the repo root:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
nohup bash "$REPO_ROOT/actions/on-demand/actions-dashboard/run.sh" > /tmp/actions-dashboard.log 2>&1 &
```

3. Wait 2 seconds, then verify it started: `lsof -ti:7391`. If not, show the tail of `/tmp/actions-dashboard.log`.
4. The server opens the browser itself. Report: "Dashboard started at http://localhost:7391 (serving [repo name])"

### stop

1. Stop whatever is serving the port:

```bash
lsof -ti:7391 | xargs kill 2>/dev/null
```

2. Confirm it stopped.

### restart

1. Run stop, then run start.

---

After running, report what happened (e.g. "Dashboard started at http://localhost:7391", "Dashboard stopped", "Dashboard restarted").
