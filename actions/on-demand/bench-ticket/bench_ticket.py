#!/usr/bin/env python3
"""
bench_ticket.py — Bench Index ticket utility.

Commands:
  lookup <slug>               Print the slug's linked ticket(s) for PM_TOOL.
  post   <slug> <note-file> --key KEY
                              Post a brief note comment to KEY. KEY must
                              already be linked to the slug in bench-index.csv
                              (the `jira` or `asana` column, comma-separated
                              for several) — nothing is searched or auto-linked.
  update <slug> [--jira KEY] [--asana GID]
                              Manually write ticket refs into bench-index.csv.

The tool comes from PM_TOOL in config/bench.env (jira | asana | none, set by
setup.sh). With none, there is no ticket step and every command is a no-op.
Credentials come from config/keys.env.
"""

import argparse
import base64
import csv
import json
import os
import sys
from pathlib import Path

import requests

# ── Paths ────────────────────────────────────────────────────────────────────

BENCH_ROOT = Path(__file__).resolve().parents[3]
INDEX_FILE = BENCH_ROOT / "bench-index.csv"
KEYS_FILE  = BENCH_ROOT / "config" / "keys.env"
BENCH_FILE = BENCH_ROOT / "config" / "bench.env"

# ── Config loading ───────────────────────────────────────────────────────────

def load_keys(path: Path = KEYS_FILE) -> dict:
    keys = {}
    if not path.exists():
        return keys
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                keys[k.strip()] = v.strip()
    return keys

def jira_configured(keys: dict) -> bool:
    return all(keys.get(k) for k in ("JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_URL"))

def asana_configured(keys: dict) -> bool:
    return bool(keys.get("ASANA_PAT"))

def pm_tool() -> str:
    """jira | asana | none — from config/bench.env. Empty or unknown means none."""
    tool = load_keys(BENCH_FILE).get("PM_TOOL", "").strip().lower()
    return tool if tool in ("jira", "asana") else "none"

# ── CSV helpers ──────────────────────────────────────────────────────────────

def read_index() -> list[dict]:
    with open(INDEX_FILE, newline="") as f:
        return list(csv.DictReader(f))

def write_index(rows: list[dict]):
    fields = ["slug", "type", "convo_folder", "action_folder", "jira", "asana"]
    with open(INDEX_FILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def find_row(slug: str) -> dict | None:
    for row in read_index():
        if row["slug"] == slug:
            return row
    return None

def update_row(slug: str, jira: str = "", asana: str = ""):
    rows = read_index()
    for row in rows:
        if row["slug"] == slug:
            if jira:
                row["jira"] = jira
            if asana:
                row["asana"] = asana
    write_index(rows)

# ── Jira helpers ─────────────────────────────────────────────────────────────

def jira_headers(keys: dict) -> dict:
    creds = base64.b64encode(
        f"{keys['JIRA_EMAIL']}:{keys['JIRA_API_TOKEN']}".encode()
    ).decode()
    return {"Authorization": f"Basic {creds}", "Content-Type": "application/json"}

def _build_adf_from_lines(body: str) -> dict:
    """Convert a multi-line comment into Atlassian Document Format (ADF).

    First line becomes bold, remaining lines become normal paragraphs.
    """
    lines = body.split("\n")
    content = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if i == 0:
            # Bold header line
            content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": line, "marks": [{"type": "strong"}]}],
            })
        else:
            content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": line}],
            })
    return {"version": 1, "type": "doc", "content": content}


def jira_get_summary(base_url: str, key: str, headers: dict) -> str:
    """Fetch the summary (title) of a Jira issue."""
    r = requests.get(
        f"{base_url}/rest/api/3/issue/{key}?fields=summary",
        headers=headers,
    )
    if r.ok:
        return r.json().get("fields", {}).get("summary", "")
    return ""

def jira_post_comment(base_url: str, key: str, body: str, headers: dict):
    """Post a rich-text (ADF) comment to a Jira issue."""
    adf_body = _build_adf_from_lines(body)
    r = requests.post(
        f"{base_url}/rest/api/3/issue/{key}/comment",
        headers=headers,
        json={"body": adf_body},
    )
    r.raise_for_status()

# ── Asana helpers ────────────────────────────────────────────────────────────

ASANA_API = "https://app.asana.com/api/1.0"

def asana_headers(keys: dict) -> dict:
    return {"Authorization": f"Bearer {keys['ASANA_PAT']}", "Accept": "application/json"}

def asana_post_comment(task_gid: str, body: str, headers: dict):
    """Post a rich-text (HTML) comment to an Asana task."""
    lines = body.split("\n")
    html_parts = []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if i == 0:
            html_parts.append(f"<strong>{line}</strong>")
        else:
            html_parts.append(line)
    html_body = "\n".join(html_parts)
    post_headers = {**headers, "Content-Type": "application/json"}
    r = requests.post(
        f"{ASANA_API}/tasks/{task_gid}/stories",
        headers=post_headers,
        json={"data": {"html_text": f"<body>{html_body}</body>"}},
    )
    r.raise_for_status()

# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_lookup(slug: str):
    row = find_row(slug)
    if not row:
        print(f"Slug '{slug}' not found in bench-index.csv")
        sys.exit(1)
    tool = pm_tool()
    if tool == "none":
        print("PM_TOOL=none — no ticket step on this bench.")
        return
    refs = [k.strip() for k in row.get(tool, "").split(",") if k.strip()]
    keys = load_keys()
    if tool == "jira" and refs and jira_configured(keys):
        jh = jira_headers(keys)
        refs = [f"{k} — {jira_get_summary(keys['JIRA_URL'], k, jh)}".rstrip(" —") for k in refs]
    print(f"slug:   {row['slug']}")
    print(f"{tool}:  {', '.join(refs) if refs else '(none linked)'}")


def _build_brief_comment(note_path: Path) -> str:
    """Build a descriptive summary from the note file for external ticket comments.

    Extracts the title, date, and discussion topics to produce a 2-3 sentence
    summary that gives context without requiring the reader to open the file.
    """
    text = note_path.read_text().strip()
    lines = text.splitlines()

    # Extract title from first heading line (# Title)
    title = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped.lstrip("# ").strip()
            break
        if stripped and not stripped.startswith("---") and not stripped.startswith("**"):
            title = stripped
            break

    # Extract date if present
    date_str = ""
    for line in lines:
        if line.strip().startswith("**Date:**"):
            date_str = line.strip().replace("**Date:**", "").strip()
            break

    # Extract discussion topics — collect bullet points or text under that heading
    topics = []
    in_topics = False
    for line in lines:
        stripped = line.strip()
        if "Discussion Topics" in stripped:
            in_topics = True
            continue
        if in_topics:
            if stripped.startswith("####") or stripped.startswith("# "):
                break  # hit next section
            if stripped.startswith("<!--"):
                continue
            if stripped.startswith("- "):
                topics.append(stripped.lstrip("- ").strip())
            elif stripped and not stripped.startswith("<!--"):
                topics.append(stripped)

    # Build relative path from bench root
    try:
        rel_path = note_path.resolve().relative_to(BENCH_ROOT)
    except ValueError:
        rel_path = note_path.name

    # Build summary: title + date header, then topic sentences, then file ref
    header = f"Session note: {title}"
    if date_str:
        header += f" ({date_str})"

    if topics:
        # Take first 3 topics, strip trailing periods, then join with ". "
        cleaned = [t.rstrip(".") for t in topics[:3]]
        summary_text = ". ".join(cleaned) + "."
        comment = f"{header}\n{summary_text}\nSee: {rel_path}"
    else:
        comment = f"{header}\nSee: {rel_path}"
    return comment


def cmd_post(slug: str, note_file: str, key: str = ""):
    note_path = Path(note_file)
    if not note_path.exists():
        print(f"Note file not found: {note_file}")
        sys.exit(1)
    body = _build_brief_comment(note_path)

    tool = pm_tool()
    if tool == "none":
        print("PM_TOOL=none — no ticket step on this bench.")
        return

    keys = load_keys()
    if not (jira_configured(keys) if tool == "jira" else asana_configured(keys)):
        print(f"PM_TOOL={tool} but its credentials are missing from config/keys.env — nothing posted.")
        sys.exit(1)

    row = find_row(slug)
    if not row:
        print(f"Slug '{slug}' not found in bench-index.csv — add it first.")
        sys.exit(1)

    linked = [k.strip() for k in row.get(tool, "").split(",") if k.strip()]
    if not linked:
        print(f"No {tool} ticket linked to '{slug}' — nothing posted.")
        return
    if not key:
        print(f"'{slug}' is linked to: {', '.join(linked)} — re-run with --key <KEY> once the user confirms.")
        sys.exit(1)
    key = key.strip()
    if key not in linked:
        print(f"{key} is not linked to '{slug}' in bench-index.csv — nothing posted.")
        sys.exit(1)

    try:
        if tool == "jira":
            jh = jira_headers(keys)
            jira_post_comment(keys["JIRA_URL"], key, body, jh)
            summary = jira_get_summary(keys["JIRA_URL"], key, jh)
            print(f"Posted to Jira {key} — {summary}" if summary else f"Posted to Jira {key}")
        else:
            asana_post_comment(key, body, asana_headers(keys))
            print(f"Posted to Asana task {key}")
    except Exception as e:
        print(f"{tool.capitalize()} post failed: {e}")
        sys.exit(1)


def cmd_update(slug: str, jira: str, asana: str):
    row = find_row(slug)
    if not row:
        print(f"Slug '{slug}' not found in bench-index.csv")
        sys.exit(1)
    update_row(slug, jira=jira, asana=asana)
    print(f"Updated '{slug}': jira={jira or '(unchanged)'} asana={asana or '(unchanged)'}")


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Bench Index ticket utility")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_lookup = sub.add_parser("lookup")
    p_lookup.add_argument("slug")

    p_post = sub.add_parser("post")
    p_post.add_argument("slug")
    p_post.add_argument("note_file")
    p_post.add_argument("--key", default="",
                        help="Linked Jira key / Asana task GID to post to (required)")

    p_update = sub.add_parser("update")
    p_update.add_argument("slug")
    p_update.add_argument("--jira", default="")
    p_update.add_argument("--asana", default="")

    args = parser.parse_args()

    if args.cmd == "lookup":
        cmd_lookup(args.slug)
    elif args.cmd == "post":
        cmd_post(args.slug, args.note_file, args.key)
    elif args.cmd == "update":
        cmd_update(args.slug, args.jira, args.asana)


if __name__ == "__main__":
    main()
