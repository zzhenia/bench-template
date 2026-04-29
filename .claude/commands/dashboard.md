---
name: dashboard
description: Start, stop, or restart the Actions Dashboard (http://localhost:7391).
---

Manage the Actions Dashboard. The argument can be `start`, `stop`, or `restart`. If no argument is given, default to `start`.

The dashboard is managed by a launchd service (`com.zvi.actions-dashboard`) defined in `~/Library/LaunchAgents/com.zvi.actions-dashboard.plist`. The service has `KeepAlive` enabled, so it auto-restarts.

**For ALL commands**, always claim the dashboard for THIS repo by updating the launchd plist. This ensures whichever bench runs `/dashboard` gets ownership.

---

### start (default when no argument)

1. Update the plist to point to this repo's server.py:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
PLIST=~/Library/LaunchAgents/com.zvi.actions-dashboard.plist
SERVER="$REPO_ROOT/actions/on-demand/actions-dashboard/server.py"
```

Use `sed` to replace the server.py path and log paths in the plist so they point to `$REPO_ROOT/actions/on-demand/actions-dashboard/`.

2. Unload and reload the launchd service:

```bash
launchctl unload "$PLIST" 2>/dev/null
lsof -ti:7391 | xargs kill -9 2>/dev/null
sleep 1
launchctl load "$PLIST"
```

3. Wait 2 seconds, then verify it started: `lsof -ti:7391`
4. Open the browser: `open http://localhost:7391`
5. Report: "Dashboard started at http://localhost:7391 (serving [repo name])"

### stop

1. Unload the launchd service:

```bash
launchctl unload ~/Library/LaunchAgents/com.zvi.actions-dashboard.plist 2>/dev/null
lsof -ti:7391 | xargs kill -9 2>/dev/null
```

2. Confirm it stopped.

### restart

1. Run stop, then run start.

---

After running, report what happened (e.g. "Dashboard started at http://localhost:7391", "Dashboard stopped", "Dashboard restarted").
