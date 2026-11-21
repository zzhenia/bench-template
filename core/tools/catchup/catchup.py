#!/usr/bin/env python3
"""Catch-up: list convos with notes since the last run, open one Cursor terminal tab per pick.

  catchup.py list               numbered convos whose notes changed since the last run
  catchup.py open <briefs-dir>  one Cursor tab per <slug>.md brief (first line "title: ..."),
                                then records this run as the last one
  catchup.py mark               record a run without opening anything

Each tab is opened with Ctrl+Shift+` in Cursor, so Cursor needs Accessibility permission and
must be frontmost; the tab's shell then launches its queued brief itself.
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

BENCH = Path(__file__).resolve().parents[3]
CONVOS = BENCH / "convos"
STATE = BENCH / "state" / "catchup" / "state.json"
NOTE = re.compile(r"^\d{6}-.+\.md$")


def queue_dir():
    """The folder a new Cursor terminal claims its oldest entry from on its first prompt
    (bench_menu_once in core/shell/bench.zsh), so nothing is typed into the shell. The shell
    exports BENCH_CATCHUP_QUEUE; outside it, this bench's config/bench.env, then the default."""
    q = os.environ.get("BENCH_CATCHUP_QUEUE", "")
    if not q:
        try:
            for line in (BENCH / "config" / "bench.env").read_text().splitlines():
                if line.startswith("BENCH_CATCHUP_QUEUE="):
                    q = line.split("=", 1)[1].strip()
        except OSError:
            pass
    return Path(q or "~/.bench-catchup").expanduser()


QUEUE = queue_dir()


def last_run():
    try:
        return datetime.fromisoformat(json.loads(STATE.read_text())["last_run"])
    except (OSError, ValueError, KeyError):
        return datetime.now() - timedelta(days=1)


def mark():
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({"last_run": datetime.now().isoformat(timespec="seconds")}) + "\n")


def cmd_list():
    since = last_run()
    rows = []
    for d in CONVOS.iterdir():
        if not d.is_dir():
            continue
        notes = [p for p in d.rglob("*.md") if NOTE.match(p.name)
                 and datetime.fromtimestamp(p.stat().st_mtime) > since]
        if notes:
            notes.sort(key=lambda p: p.stat().st_mtime)
            rows.append((notes[-1].stat().st_mtime, d.name, notes))
    rows.sort(reverse=True)
    print(f"since {since:%Y-%m-%d %H:%M}")
    for i, (_, name, notes) in enumerate(rows, 1):
        print(f"{i:2d}  {name}")
        for p in notes:
            print(f"      {p.relative_to(BENCH)}")


def frontmost():
    r = subprocess.run(["osascript", "-e", 'tell application "System Events" to get name of '
                        'first process whose frontmost is true'], capture_output=True, text=True)
    return r.stdout.strip()


def open_tab():
    subprocess.run(["osascript", "-e", 'tell application "Cursor" to activate'], check=True)
    # With several Cursor windows open, bring this bench's window forward (its title ends
    # with the bench folder name) so the new tab opens there. Best effort.
    subprocess.run(["osascript", "-e", 'tell application "System Events" to tell process "Cursor" '
                    f'to perform action "AXRaise" of (first window whose name ends with "{BENCH.name}")'],
                   capture_output=True)
    time.sleep(0.8)
    # The keystroke lands on whatever has focus; never send it to another app.
    if "Cursor" not in frontmost():
        return "Cursor is not frontmost"
    r = subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "`" '
                        'using {control down, shift down}'], capture_output=True, text=True)
    return r.stderr.strip() or None


def cmd_open(briefs, ai):
    files = sorted(Path(briefs).glob("*.md"))
    if not files:
        sys.exit(f"no briefs in {briefs}")
    QUEUE.mkdir(exist_ok=True)
    failed = []
    for f in files:
        lines = f.read_text().splitlines()
        if not lines or not lines[0].startswith("title:"):
            failed.append(f"{f.stem}: first line must be 'title: ...'")
            continue
        title = lines[0].split(":", 1)[1].strip()
        prompt = f.with_suffix(".prompt")
        prompt.write_text("\n".join(lines[1:]).strip() + "\n")
        entry = QUEUE / f"{time.time():.3f}.tab"
        entry.write_text(f"{title}\n{ai}\n{prompt}\n")
        err = open_tab()
        for _ in range(20):
            if not entry.exists():
                break
            time.sleep(0.5)
        if err or entry.exists():
            entry.unlink(missing_ok=True)
            failed.append(f"{title}: {err or 'the new tab did not pick it up within 10 s'}")
            break
        print(f"opened  {title}")
        time.sleep(2)
    for line in failed:
        print(f"FAILED  {line}")
    mark()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    args = sys.argv[1:]
    ai = os.environ.get("CATCHUP_AI", "claude")
    if args[:1] == ["list"]:
        cmd_list()
    elif args[:1] == ["open"] and len(args) == 2:
        cmd_open(args[1], ai)
    elif args[:1] == ["mark"]:
        mark()
    else:
        sys.exit(__doc__)
