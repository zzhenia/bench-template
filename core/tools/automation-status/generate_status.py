#!/usr/bin/env python3
"""
Launchd detail view: every installed launchd job of this bench (see inventory.py for
which ones count), with schedule, launchctl status, last exit and last log line.
Writes state/automation-status/YYMMDD-automations.md at the bench root and prints it.
"""

import plistlib
import subprocess
from datetime import datetime
from pathlib import Path

from inventory import ROOT, load_config, job, job_name, ours

AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
ASSETS_DIR = ROOT / "state" / "automation-status"

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

    cfg = load_config()
    rows = []
    for plist_path in sorted(AGENTS_DIR.glob("*.plist")):
        with open(plist_path, "rb") as f:
            try:
                data = plistlib.load(f)
            except Exception:
                continue

        label = data.get("Label", "")
        if not ours(cfg, label, data):
            continue

        status, exit_code = get_launchctl_status(label)
        log_path = data.get("StandardOutPath", "")
        label_short = job_name(cfg, label)
        rows.append({
            "label": label,
            "label_short": label_short,
            "schedule": parse_schedule(data),
            "script": " ".join(data.get("ProgramArguments", [])),
            "status": status,
            "exit_code": exit_code or "0",
            "last_log": tail_log(log_path) if log_path else "",
            "description": job(cfg, label_short)[0],
        })

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Automation Status",
        f"**Generated:** {now}",
        "",
        "| Automation | Description | Schedule | Status | Last Exit | Last Log |",
        "|------------|-------------|----------|--------|-----------|----------|",
    ]
    for r in rows:
        log = r["last_log"].replace("|", "\\|")[:80]
        lines.append(
            f"| **{r['label_short']}** | {r['description']} | {r['schedule']} | {r['status']} | {r['exit_code']} | {log} |"
        )

    lines += [
        "",
        "## Details",
        "",
    ]
    for r in rows:
        desc_line = f"\n{r['description']}\n" if r['description'] else ""
        lines += [
            f"### {r['label']}",
            desc_line,
            f"- **Schedule:** {r['schedule']}",
            f"- **Script:** `{r['script']}`",
            f"- **Status:** {r['status']} (last exit: {r['exit_code']})",
            f"- **Log:** {r['last_log'] or '(no output yet)'}",
            "",
        ]

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines)
    output_path.write_text(content)

    # Print to stdout so the dashboard terminal can display results
    print(content)
    print(f"\nWritten: {output_path}")
    return str(output_path)


if __name__ == "__main__":
    main()
