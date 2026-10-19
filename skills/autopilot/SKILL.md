---
name: autopilot
description: Start, stop, or restart the YT Autopilot app (http://localhost:8001).
model: haiku
---

Manage the YT Autopilot server via launchd (`com.zvi.yt-autopilot`). The argument can be `start`, `stop`, `restart`, or `reset`. If no argument is given, open the app in the browser — starting it first if it's not already running.

The plist lives at `~/Library/LaunchAgents/com.zvi.yt-autopilot.plist`.

**Port check (run for ALL commands including bare `/autopilot`):**

```bash
lsof -ti:8001
```

If a process is found, check whether it belongs to THIS repo:

```bash
lsof -i:8001 | grep LISTEN
```

If the server.py path does NOT contain `yt-autopilot`, tell the user and ask before stopping it.

---

**Commands:**

### (no argument) — open the app

1. Run the port check above.
2. If the app is already running, just open the browser: `open http://localhost:8001`
3. If nothing is running on 8001, run start, then open the browser.

### start

1. Run the port check above.
2. If already running, say "YT Autopilot is already running" and open the browser.
3. Otherwise, start via launchd:

```bash
launchctl load -w ~/Library/LaunchAgents/com.zvi.yt-autopilot.plist 2>/dev/null
launchctl kickstart gui/$(id -u)/com.zvi.yt-autopilot
```

4. Wait 2 seconds, then verify it started (`lsof -ti:8001`).
5. Open the browser: `open http://localhost:8001`

### stop

1. Run the port check above.
2. Stop via launchd (prevents auto-restart):

```bash
launchctl unload -w ~/Library/LaunchAgents/com.zvi.yt-autopilot.plist 2>/dev/null
```

3. If port 8001 is still occupied (orphan process), kill it: `kill $(lsof -ti:8001) 2>/dev/null`
4. Confirm it stopped.

### restart

1. Run stop.
2. Then run start.

### reset

1. Run stop.
2. Delete the state file: `rm -f tools/on-demand/yt-autopilot/app/state.json`
3. Then run start. This will regenerate the default state with the sample project.

---

After running, report what happened (e.g. "YT Autopilot started at http://localhost:8001", "Stopped", "Restarted", "Reset and restarted").
