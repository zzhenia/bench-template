#!/usr/bin/env python3
"""
Auto Debug — watches BUGS.md files and launches Claude to fix them.

Extracted from actions-dashboard. Can be imported by the dashboard server
or used standalone via CLI:

    python3 auto_debug.py start <action_id>
    python3 auto_debug.py stop <action_id>
    python3 auto_debug.py status
"""

import json
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path

BASE = Path(os.environ.get("BENCH_ROOT") or Path(__file__).resolve().parents[3])  # bench root

STATUS_FILE = BASE / "state" / "auto-debug" / "bugfix_mode.json"
IDLE_TIMEOUT = 30 * 60  # auto-disable after 30 min of no changes
# Native install location; the model and endpoint come from the active AI profile.
CLAUDE_BIN = Path.home() / ".local" / "bin" / "claude"
VSCODE_BIN = Path("/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code")

_lock = threading.Lock()
_thread = None  # single coordinator thread
_stop_event = threading.Event()
_pids = {}  # action_id → pid of running claude process

# Will be set by the dashboard when importing, or loaded from bench-index.csv
_actions = None


def _get_actions():
    """Return the actions list — from dashboard if imported, else from bench-index.csv."""
    global _actions
    if _actions is not None:
        return _actions
    # Fallback: load from bench-index.csv
    actions = []
    csv_path = BASE / "bench-index.csv"
    if csv_path.exists():
        import csv
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("type") == "action" and row.get("convo_folder"):
                    folder = row.get("convo_folder", "").rstrip("/")
                    # Map convo_folder to actual action folder
                    action_folder = folder.replace("convos/", "tools/on-demand/", 1) if folder.startswith("convos/") else ""
                    actions.append({
                        "id": row.get("slug", ""),
                        "name": row.get("slug", ""),
                        "folder": action_folder or folder,
                    })
    _actions = actions
    return actions


def set_actions(actions_list):
    """Set the actions list (called by dashboard server on import)."""
    global _actions
    _actions = actions_list


def read_status():
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text())
        except Exception:
            pass
    return {}


def write_status(data):
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(data, indent=2))


def action_folder(action_id):
    """Return the filesystem path for an action's folder."""
    action = next((a for a in _get_actions() if a["id"] == action_id), None)
    if not action or not action.get("folder"):
        return None
    return BASE / action["folder"]


def bugs_path(action_id):
    folder = action_folder(action_id)
    return folder / "BUGS.md" if folder else None


def ensure_bugs_file(action_id):
    """Create BUGS.md if it doesn't exist. Return the path."""
    path = bugs_path(action_id)
    if not path:
        return None
    if not path.exists():
        action = next((a for a in _get_actions() if a["id"] == action_id), None)
        name = action["name"] if action else action_id
        path.write_text(
            f"# {name} — Bug List\n\n"
            f"**Created:** {time.strftime('%Y-%m-%d')}\n\n---\n\n"
            "<!-- Add bugs below. Each ### heading is one bug. -->\n"
        )
    return path


def _coordinator():
    """Single background thread: polls all active watchers every 5 seconds."""
    while not _stop_event.is_set():
        if _stop_event.wait(5):
            return

        with _lock:
            all_status = read_status()

        now = time.time()
        changed = False

        for action_id, info in list(all_status.items()):
            if not isinstance(info, dict) or not info.get("active"):
                continue

            bp = bugs_path(action_id)
            if not bp:
                continue

            info["last_check"] = time.strftime("%Y-%m-%dT%H:%M:%S")

            # Auto-timeout: disable if no changes for IDLE_TIMEOUT
            last_activity = info.get("last_activity", info.get("started_at", now))
            if now - last_activity > IDLE_TIMEOUT:
                info["active"] = False
                info["state"] = "timeout"
                info["message"] = "Auto-disabled (30 min idle)"
                ts = time.strftime("%H:%M")
                info.setdefault("log", []).append(f"[{ts}] Auto-disabled after idle timeout")
                info["log"] = info["log"][-20:]
                changed = True
                continue

            if not bp.exists():
                info["state"] = "watching"
                info["message"] = "No BUGS.md yet"
                changed = True
                continue

            current_mtime = bp.stat().st_mtime
            mtime_changed = current_mtime > info.get("last_mtime", 0)

            if not mtime_changed:
                if info["state"] in ("fixing", "launched"):
                    pid_file = Path(tempfile.gettempdir()) / f"bugfix_{action_id}_watcher.pid"
                    watcher_alive = False
                    if pid_file.exists():
                        try:
                            pid = int(pid_file.read_text().strip())
                            os.kill(pid, 0)
                            watcher_alive = True
                        except (ValueError, ProcessLookupError, PermissionError):
                            pid_file.unlink(missing_ok=True)
                    if not watcher_alive:
                        ts = time.strftime("%H:%M")
                        info.setdefault("log", []).append(f"[{ts}] Watcher terminal lost, resetting to watching")
                        info["log"] = info["log"][-20:]
                        info["state"] = "watching"
                        info["message"] = "Watcher lost — waiting for BUGS.md change"
                else:
                    info["state"] = "watching"
                    info["message"] = "No changes"
                changed = True
                continue

            # File changed — check if it has actionable content
            content = bp.read_text().strip()
            lines = content.splitlines()
            skip_prefixes = ("#", "---", "**", "<!--")
            actionable = [
                l for l in lines
                if l.strip()
                and "~~" not in l
                and not any(l.strip().startswith(p) for p in skip_prefixes)
            ]
            info["last_mtime"] = current_mtime
            info["last_activity"] = now

            if not actionable:
                info["state"] = "watching"
                info["message"] = "All bugs fixed" if lines else "No bugs listed"
                changed = True
                continue

            if info["state"] == "launched":
                watcher_alive = False
                pid_file = Path(tempfile.gettempdir()) / f"bugfix_{action_id}_watcher.pid"
                if pid_file.exists():
                    try:
                        pid = int(pid_file.read_text().strip())
                        os.kill(pid, 0)
                        watcher_alive = True
                    except (ValueError, ProcessLookupError, PermissionError):
                        pid_file.unlink(missing_ok=True)
                if watcher_alive:
                    info["message"] = f"Claude running ({len(actionable)} line(s) of bugs remaining)"
                    changed = True
                    continue
                ts = time.strftime("%H:%M")
                info.setdefault("log", []).append(f"[{ts}] Watcher terminal lost, re-launching")
                info["log"] = info["log"][-20:]
                info["state"] = "watching"

            # Launch claude in Terminal
            info["state"] = "fixing"
            info["message"] = "Bug(s) found — starting Claude..."
            ts = time.strftime("%H:%M")
            info.setdefault("log", []).append(f"[{ts}] Bug(s) detected, starting fix run")
            info["log"] = info["log"][-20:]
            changed = True

            with _lock:
                write_status(all_status)

            _run_claude(action_id, bp, info)
            if info["state"] == "fixing":
                info["state"] = "launched"
                info["message"] = "Claude running in Terminal"
            changed = True

        if changed:
            with _lock:
                write_status(all_status)


def _write_watcher_script(action_id):
    """Write a persistent watcher script that runs in VS Code terminal."""
    af = action_folder(action_id) or BASE
    tmp = Path(tempfile.gettempdir())
    script_path = tmp / f"bugfix_{action_id}_watcher.sh"
    trigger_path = tmp / f"bugfix_{action_id}.trigger"
    prompt_path = tmp / f"bugfix_{action_id}.prompt"

    script_path.write_text(
        f'#!/bin/bash\n'
        f'# Bug Fix Terminal: {action_id}\n'
        f'cd "{BASE}"\n'
        f'echo "\\033[1;36m=== Bug Fix Mode: {action_id} ===\\033[0m"\n'
        f'echo "Watching for triggers..."\n'
        f'echo ""\n'
        f'TRIGGER="{trigger_path}"\n'
        f'PROMPT_FILE="{prompt_path}"\n'
        f'while true; do\n'
        f'  if [ -f "$TRIGGER" ]; then\n'
        f'    rm -f "$TRIGGER"\n'
        f'    echo "\\033[1;33m--- Starting fix run ---\\033[0m"\n'
        f'    [ -f "{BASE}/scripts/bench-profile" ] && eval "$(python3 "{BASE}/scripts/bench-profile" env)"\n'
        f'    "{CLAUDE_BIN}" --max-turns 50 "$(cat "$PROMPT_FILE")" &\n'
        f'    CLAUDE_PID=$!\n'
        f'    wait $CLAUDE_PID 2>/dev/null\n'
        f'    echo ""\n'
        f'    echo "\\033[1;32m--- Fix run complete. Waiting for next trigger... ---\\033[0m"\n'
        f'    echo ""\n'
        f'  fi\n'
        f'  sleep 2\n'
        f'done\n',
    )
    script_path.chmod(0o755)
    return script_path, trigger_path, prompt_path


def _run_claude(action_id, bp, info):
    """Launch or trigger claude in a reusable VS Code terminal."""
    ts = time.strftime("%H:%M")
    af = action_folder(action_id) or BASE
    action = next((a for a in _get_actions() if a["id"] == action_id), None)
    action_name = action["name"] if action else action_id

    # Find the convo folder for this action (if it has one)
    convo_path = ""
    if action and action.get("convo"):
        convo_dir = BASE / Path(action["convo"]).parent
        if convo_dir.exists():
            convo_path = str(convo_dir)

    try:
        local_time = time.strftime("%Y-%m-%d %H:%M")
        convo_context = ""
        if convo_path:
            convo_context = (
                f"Before starting, read the .md files in {convo_path} "
                "to understand recent session context and decisions. "
            )
        prompt = (
            f"Read the file {bp} and fix every bug listed in it. "
            f"{convo_context}"
            "Work through them top to bottom. For each bug: "
            "1) Read the referenced source files. "
            "2) Implement the fix. "
            "3) IMPORTANT: After fixing, edit BUGS.md and replace the bug's "
            "### heading and body with a single line: "
            f"'- ~~#N. Title~~ — fixed {local_time}'. "
            "Do not skip any bugs. If something is unclear, ask me — "
            "I can see this terminal and will answer. "
            "Do not re-fix bugs already marked as fixed (lines with ~~). "
            "CRITICAL: After you finish fixing ALL bugs, re-read BUGS.md "
            "and verify that EVERY bug you fixed is marked with ~~strikethrough~~. "
            "If any fixed bug is still unmarked, edit BUGS.md to mark it now. "
            "Then run /note to write a session note."
        )

        script_path, trigger_path, prompt_path = _write_watcher_script(action_id)
        prompt_path.write_text(prompt)

        # Check if the watcher terminal is already running
        watcher_running = False
        pid_file = Path(tempfile.gettempdir()) / f"bugfix_{action_id}_watcher.pid"
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                os.kill(pid, 0)
                watcher_running = True
            except (ValueError, ProcessLookupError, PermissionError):
                pid_file.unlink(missing_ok=True)

        if not watcher_running:
            # First time — open a new VS Code terminal with the watcher script
            script_path.write_text(
                f'#!/bin/bash\n'
                f'echo $$ > "{pid_file}"\n'
                f'trap "rm -f \\"{pid_file}\\"" EXIT\n'
                f'cd "{BASE}"\n'
                f'echo "\\033[1;36m=== Bug Fix Mode: {action_name} ===\\033[0m"\n'
                f'echo "Watching for triggers..."\n'
                f'echo ""\n'
                f'TRIGGER="{trigger_path}"\n'
                f'PROMPT_FILE="{prompt_path}"\n'
                f'while true; do\n'
                f'  if [ -f "$TRIGGER" ]; then\n'
                f'    rm -f "$TRIGGER"\n'
                f'    echo "\\033[1;33m--- Starting fix run ---\\033[0m"\n'
                f'    [ -f "{BASE}/scripts/bench-profile" ] && eval "$(python3 "{BASE}/scripts/bench-profile" env)"\n'
                f'    "{CLAUDE_BIN}" --max-turns 50 "$(cat "$PROMPT_FILE")" &\n'
                f'    CLAUDE_PID=$!\n'
                f'    wait $CLAUDE_PID 2>/dev/null\n'
                f'    echo ""\n'
                f'    echo "\\033[1;32m--- Fix run complete. Waiting for next trigger... ---\\033[0m"\n'
                f'    echo ""\n'
                f'  fi\n'
                f'  sleep 2\n'
                f'done\n',
            )
            script_path.chmod(0o755)

            shell_cmd = f'bash "{script_path}"'
            subprocess.run(["pbcopy"], input=shell_cmd.encode(), timeout=5)

            # Use `code --reuse-window` to focus the correct VS Code window
            # (the one with this repo open) before creating the terminal.
            bridge_script = (
                f'"{VSCODE_BIN}" --reuse-window "{BASE}" && '
                'osascript -e \''
                'delay 1.0\n'
                'tell application "System Events" to tell process "Code"\n'
                '  click menu item "New Terminal" of menu "Terminal" of menu bar 1\n'
                '  delay 1.0\n'
                '  keystroke "v" using {command down}\n'
                '  delay 0.3\n'
                '  keystroke return\n'
                'end tell\' && exit'
            )
            escaped_bridge = bridge_script.replace("\\", "\\\\").replace('"', '\\"')
            result = subprocess.run(
                ["osascript", "-e",
                 f'tell application "Terminal"\n'
                 f'  do script "{escaped_bridge}"\n'
                 f'end tell'],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                raise RuntimeError(f"osascript failed: {result.stderr.strip()}")

            info["log"].append(f"[{ts}] Opened Terminal for {action_name}")
        else:
            info["log"].append(f"[{ts}] Triggered existing terminal for {action_name}")

        trigger_path.write_text("go")

        info["state"] = "fixing"
        info["message"] = "Claude running in Terminal"
        info["last_activity"] = time.time()

    except Exception as ex:
        info["state"] = "error"
        info["message"] = str(ex)[:200]
        info["log"].append(f"[{ts}] Error: {str(ex)[:100]}")

    info["log"] = info["log"][-20:]


def ensure_coordinator():
    """Start the coordinator thread if not already running."""
    global _thread
    with _lock:
        if _thread and _thread.is_alive():
            return
        _stop_event.clear()
        _thread = threading.Thread(target=_coordinator, daemon=True)
        _thread.start()


def start(action_id):
    action = next((a for a in _get_actions() if a["id"] == action_id), None)
    if not action or not action.get("folder"):
        return {"ok": False, "error": "Action has no folder"}

    ensure_bugs_file(action_id)

    with _lock:
        all_status = read_status()
        all_status[action_id] = {
            "active": True,
            "state": "watching",
            "started_at": time.time(),
            "last_activity": time.time(),
            "last_mtime": 0,
            "last_check": None,
            "message": "Watching for BUGS.md changes",
            "pid": None,
            "log": all_status.get(action_id, {}).get("log", [])[-20:],
        }
        write_status(all_status)

    ensure_coordinator()
    return {"ok": True}


def stop(action_id):
    with _lock:
        all_status = read_status()
        info = all_status.get(action_id, {})
        info["active"] = False
        info["state"] = "idle"
        info["message"] = "Stopped"
        pid = info.get("pid")
        if pid:
            try:
                os.kill(pid, 15)
            except (ProcessLookupError, PermissionError):
                pass
        info["pid"] = None
        _pids.pop(action_id, None)
        all_status[action_id] = info
        write_status(all_status)
    return {"ok": True}


# ── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: auto_debug.py {start|stop|status} [action_id]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "status":
        status = read_status()
        for aid, info in status.items():
            state = info.get("state", "unknown")
            active = info.get("active", False)
            msg = info.get("message", "")
            print(f"  {aid}: active={active}, state={state} — {msg}")
        if not status:
            print("  (no actions tracked)")
    elif cmd in ("start", "stop") and len(sys.argv) >= 3:
        action_id = sys.argv[2]
        result = start(action_id) if cmd == "start" else stop(action_id)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: auto_debug.py {start|stop|status} [action_id]")
        sys.exit(1)
