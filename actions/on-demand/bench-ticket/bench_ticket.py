#!/usr/bin/env python3
"""
bench_ticket.py — Bench Index ticket utility.

Commands:
  lookup <slug>               Print Jira/Asana refs for a slug.
  post   <slug> <note-file>   Post note as a comment to ticket(s). Searches if
                              no ticket found; proposes creation if still none.
  search <slug>               Search Jira+Asana for a ticket; update CSV if found.
  update <slug> [--jira KEY] [--asana GID]
                              Manually write ticket refs into bench-index.csv.
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

# ── Config loading ───────────────────────────────────────────────────────────

def load_keys() -> dict:
    keys = {}
    with open(KEYS_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                keys[k.strip()] = v.strip()
    return keys

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

def jira_post_comment(base_url: str, key: str, body: str, headers: dict):
    adf_body = {
        "version": 1,
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": body}]}],
    }
    r = requests.post(
        f"{base_url}/rest/api/3/issue/{key}/comment",
        headers=headers,
        json={"body": adf_body},
    )
    r.raise_for_status()

def jira_search(base_url: str, slug: str, headers: dict, keys: dict) -> str | None:
    """Search configured Jira projects for a task whose summary contains the slug words."""
    words = slug.replace("-", " ")
    project_keys = keys.get("JIRA_PROJECT_KEYS", "").strip()
    if project_keys:
        projects = ", ".join(p.strip() for p in project_keys.split(","))
        jql = f'project in ({projects}) AND summary ~ "{words}" ORDER BY created DESC'
    else:
        # Fall back to a broad search without project filter
        jql = f'summary ~ "{words}" ORDER BY created DESC'
    r = requests.post(
        f"{base_url}/rest/api/3/search/jql",
        headers=headers,
        json={"jql": jql, "maxResults": 5, "fields": ["summary"]},
    )
    issues = r.json().get("issues", [])
    if issues:
        key = issues[0]["key"]
        summary = issues[0]["fields"]["summary"]
        print(f"  Jira: found {key} — {summary}")
        return key
    return None

# ── Asana helpers ────────────────────────────────────────────────────────────

ASANA_API = "https://app.asana.com/api/1.0"

def get_asana_workspace(keys: dict) -> str | None:
    """Get Asana workspace GID from keys.env. Returns None if not configured."""
    gid = keys.get("ASANA_WORKSPACE_GID", "").strip()
    if not gid:
        print("  Asana workspace GID not configured (set ASANA_WORKSPACE_GID in config/keys.env) — skipping Asana.")
        return None
    return gid

def asana_headers(keys: dict) -> dict:
    return {"Authorization": f"Bearer {keys['ASANA_PAT']}", "Accept": "application/json"}

def asana_post_comment(task_gid: str, body: str, headers: dict):
    r = requests.post(
        f"{ASANA_API}/tasks/{task_gid}/stories",
        headers=headers,
        json={"data": {"text": body}},
    )
    r.raise_for_status()

def asana_search(slug: str, headers: dict, workspace_gid: str) -> str | None:
    words = slug.replace("-", " ")
    r = requests.get(
        f"{ASANA_API}/workspaces/{workspace_gid}/tasks/search",
        headers=headers,
        params={"text": words, "opt_fields": "gid,name", "limit": 5},
    )
    tasks = r.json().get("data", [])
    if tasks:
        gid = tasks[0]["gid"]
        name = tasks[0]["name"]
        print(f"  Asana: found {gid} — {name}")
        return gid
    return None

def asana_create_task(name: str, notes: str, headers: dict, workspace_gid: str) -> str:
    r = requests.post(
        f"{ASANA_API}/tasks",
        headers=headers,
        json={"data": {
            "name": name,
            "notes": notes,
            "workspace": workspace_gid,
            "assignee": "me",
        }},
    )
    r.raise_for_status()
    return r.json()["data"]["gid"]

# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_lookup(slug: str):
    row = find_row(slug)
    if not row:
        print(f"Slug '{slug}' not found in bench-index.csv")
        sys.exit(1)
    print(f"slug:   {row['slug']}")
    print(f"jira:   {row['jira'] or '(none)'}")
    print(f"asana:  {row['asana'] or '(none)'}")


def cmd_post(slug: str, note_file: str):
    note_path = Path(note_file)
    if not note_path.exists():
        print(f"Note file not found: {note_file}")
        sys.exit(1)
    body = note_path.read_text().strip()

    keys = load_keys()
    jh = jira_headers(keys)
    ah = asana_headers(keys)
    base_url = keys["JIRA_URL"]
    asana_workspace = get_asana_workspace(keys)

    row = find_row(slug)
    if not row:
        print(f"Slug '{slug}' not found in bench-index.csv — add it first.")
        sys.exit(1)

    jira_key  = row.get("jira", "").strip()
    asana_gid = row.get("asana", "").strip()

    # If either is missing, try to search first
    if not jira_key:
        print(f"No Jira ticket for '{slug}', searching...")
        found = jira_search(base_url, slug, jh, keys)
        if found:
            jira_key = found
            update_row(slug, jira=found)
            print(f"  Updated bench-index.csv with Jira {found}")
        else:
            print(f"  No Jira match. Propose: create a Jira ticket for '{slug}', "
                  f"or run: bench_ticket.py update {slug} --jira <KEY>")

    if not asana_gid and asana_workspace:
        print(f"No Asana task for '{slug}', searching...")
        found = asana_search(slug, ah, asana_workspace)
        if found:
            asana_gid = found
            update_row(slug, asana=found)
            print(f"  Updated bench-index.csv with Asana {found}")
        else:
            print(f"  No Asana match. Propose: create Asana task for '{slug}', or run: "
                  f"bench_ticket.py update {slug} --asana <GID>")

    posted = False
    if jira_key:
        try:
            jira_post_comment(base_url, jira_key, body, jh)
            print(f"Posted to Jira {jira_key}")
            posted = True
        except Exception as e:
            print(f"Jira post failed: {e}")

    if asana_gid and asana_workspace:
        try:
            asana_post_comment(asana_gid, body, ah)
            print(f"Posted to Asana task {asana_gid}")
            posted = True
        except Exception as e:
            print(f"Asana post failed: {e}")

    if not posted:
        print("No comment posted — update bench-index.csv with the correct ticket refs.")


def cmd_search(slug: str):
    keys = load_keys()
    jh = jira_headers(keys)
    ah = asana_headers(keys)
    base_url = keys["JIRA_URL"]
    asana_workspace = get_asana_workspace(keys)

    print(f"Searching for '{slug}'...")
    jira_key  = jira_search(base_url, slug, jh, keys)
    asana_gid = asana_search(slug, ah, asana_workspace) if asana_workspace else None

    if jira_key or asana_gid:
        update_row(slug, jira=jira_key or "", asana=asana_gid or "")
        print(f"bench-index.csv updated.")
    else:
        print(f"No matches found. Add manually with: bench_ticket.py update {slug} --jira KEY --asana GID")


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

    p_search = sub.add_parser("search")
    p_search.add_argument("slug")

    p_update = sub.add_parser("update")
    p_update.add_argument("slug")
    p_update.add_argument("--jira", default="")
    p_update.add_argument("--asana", default="")

    args = parser.parse_args()

    if args.cmd == "lookup":
        cmd_lookup(args.slug)
    elif args.cmd == "post":
        cmd_post(args.slug, args.note_file)
    elif args.cmd == "search":
        cmd_search(args.slug)
    elif args.cmd == "update":
        cmd_update(args.slug, args.jira, args.asana)


if __name__ == "__main__":
    main()
