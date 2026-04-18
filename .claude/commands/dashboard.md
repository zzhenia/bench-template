---
name: dashboard
description: Start, stop, or restart the Actions Dashboard (http://localhost:7391).
---

Manage the Actions Dashboard. The argument can be `start`, `stop`, or `restart`. If no argument is given, open the dashboard in the browser — starting it first if it's not already running.

**Port conflict check (run this for ALL commands including bare `/dashboard`):**

Before any action, check if port 7391 is already in use:

```bash
lsof -ti:7391
```

If a process is found, check whether it belongs to THIS repo or a different one:

```bash
lsof -i:7391 | grep LISTEN
```

Look at the command path in the output. If the server.py path does NOT contain this repo's directory, tell the user:

> "There's already a dashboard running from a different bench: [path]. Should I stop it and start the dashboard for this repo instead?"

Wait for the user's answer before proceeding. If it DOES belong to this repo, treat it as "already running."

---

**Commands:**

### (no argument) — open the dashboard

1. Run the port conflict check above.
2. If the dashboard is already running for this repo, just open the browser: `open http://localhost:7391`
3. If nothing is running on 7391, start the server then open the browser.

### start

1. Run the port conflict check above.
2. If already running for this repo, say "Dashboard is already running" and open the browser.
3. Otherwise, start the server in the background:

```bash
nohup python3 actions/on-demand/actions-dashboard/server.py > /dev/null 2>&1 &
```

4. Wait 1 second, then verify it started (`lsof -ti:7391`).
5. Open the browser: `open http://localhost:7391`

### stop

1. Run the port conflict check above (warn if it belongs to a different repo).
2. Kill the process: `lsof -ti:7391 | xargs kill 2>/dev/null`
3. Confirm it stopped.

### restart

1. Run stop (with the conflict check).
2. Then run start.

---

After running, report what happened (e.g. "Dashboard started at http://localhost:7391", "Dashboard stopped", "Dashboard restarted").
