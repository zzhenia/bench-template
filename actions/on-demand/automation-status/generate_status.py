#!/usr/bin/env python3
"""
Generate a dated markdown snapshot of all scheduled launchd automations.
Writes to assets/YYMMDD-automations.md
"""

import json
import os
import plistlib
import subprocess
import sys
from datetime import datetime
from pathlib import Path

AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
ASSETS_DIR = Path(__file__).parent / "assets"
# Repo root: this script lives at actions/on-demand/automation-status/
REPO_ROOT = str(Path(__file__).resolve().parents[3])

WEEKDAY_NAMES = {0: "Sunday", 1: "Monday", 2: "Tuesday", 3: "Wednesday",
                 4: "Thursday", 5: "Friday", 6: "Saturday"}


def parse_schedule(plist_data):
    interval = plist_data.get("StartCalendarInterval")
    if not interval:
        if plist_data.get("StartInterval"):
            secs = plist_data["StartInterval"]
            return f"Every {secs}s"
        if plist_data.get("RunAtLoad"):
            return "At login"
        return "Unknown"

    entries = interval if isinstance(interval, list) else [interval]
    parts = []
    for e in entries:
        day = WEEKDAY_NAMES.get(e.get("Weekday"), "")
        hour = e.get("Hour", 0)
        minute = e.get("Minute", 0)
        time_str = f"{hour:02d}:{minute:02d}"
        parts.append(f"{day} {time_str}".strip())
    return " and ".join(parts)


def get_launchctl_status(label):
    result = subprocess.run(
        ["launchctl", "list", label],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return "not loaded", None

    info = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            info[k.strip().strip('"')] = v.strip().strip('";')

    pid = info.get("PID", "-")
    exit_code = info.get("LastExitStatus", "?")
    status = "running" if pid != "-" and pid != "0" else "idle"
    return status, exit_code


def tail_log(log_path, n=1):
    p = Path(log_path)
    if not p.exists():
        return ""
    lines = p.read_text().strip().splitlines()
    return lines[-1] if lines else ""


def main():
    date_str = datetime.now().strftime("%y%m%d")
    output_path = ASSETS_DIR / f"{date_str}-automations.md"

    rows = []
    for plist_path in sorted(AGENTS_DIR.glob("*.plist")):
        with open(plist_path, "rb") as f:
            try:
                data = plistlib.load(f)
            except Exception:
                continue

        label = data.get("Label", "")
        # Only include automations whose script path is inside this repo
        args = " ".join(data.get("ProgramArguments", []))
        working_dir = data.get("WorkingDirectory", "")
        if REPO_ROOT not in args and REPO_ROOT not in working_dir:
            continue

        schedule = parse_schedule(data)
        script = " ".join(data.get("ProgramArguments", []))
        status, exit_code = get_launchctl_status(label)
        log_path = data.get("StandardOutPath", "")
        last_log = tail_log(log_path) if log_path else ""

        rows.append({
            "label": label,
            "schedule": schedule,
            "script": script,
            "status": status,
            "exit_code": exit_code or "0",
            "last_log": last_log,
        })

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Automation Status",
        f"**Generated:** {now}",
        "",
        "| Automation | Schedule | Status | Last Exit | Last Log |",
        "|------------|----------|--------|-----------|----------|",
    ]
    for r in rows:
        # Strip common com.xxx. prefix for readability
        label_short = r["label"]
        if "." in label_short:
            parts = label_short.split(".")
            if len(parts) > 2:
                label_short = ".".join(parts[2:])
        log = r["last_log"].replace("|", "\\|")[:80]
        lines.append(
            f"| **{label_short}** | {r['schedule']} | {r['status']} | {r['exit_code']} | {log} |"
        )

    lines += [
        "",
        "## Details",
        "",
    ]
    for r in rows:
        lines += [
            f"### {r['label']}",
            f"- **Schedule:** {r['schedule']}",
            f"- **Script:** `{r['script']}`",
            f"- **Status:** {r['status']} (last exit: {r['exit_code']})",
            f"- **Log:** {r['last_log'] or '(no output yet)'}",
            "",
        ]

    ASSETS_DIR.mkdir(exist_ok=True)
    content = "\n".join(lines)
    output_path.write_text(content)

    # Print to stdout so the dashboard terminal can display results
    print(content)
    print(f"\nWritten: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    main()
