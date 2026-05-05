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

Silently skips any integration whose credentials are not configured in keys.env.
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
    if not KEYS_FILE.exists():
        return keys
    with open(KEYS_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                keys[k.strip()] = v.strip()
    return keys

def jira_configured(keys: dict) -> bool:
    return all(keys.get(k) for k in ("JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_URL"))

def asana_configured(keys: dict) -> bool:
    if not keys.get("ASANA_PAT"):
        return False
    if not keys.get("ASANA_WORKSPACE_GID"):
        # Auto-fetch workspace GID from Asana API
        gid = _auto_fetch_asana_workspace(keys)
        if gid:
            keys["ASANA_WORKSPACE_GID"] = gid
            return True
        return False
    return True


def _auto_fetch_asana_workspace(keys: dict) -> str | None:
    """Fetch the first workspace GID using the Asana PAT and save it to keys.env."""
    try:
        r = requests.get(
            "https://app.asana.com/api/1.0/workspaces",
            headers={"Authorization": f"Bearer {keys['ASANA_PAT']}", "Accept": "application/json"},
            params={"limit": 1},
        )
        r.raise_for_status()
        workspaces = r.json().get("data", [])
        if not workspaces:
            print("  Asana: no workspaces found for this PAT")
            return None
        gid = workspaces[0]["gid"]
        name = workspaces[0].get("name", "")
        print(f"  Asana: auto-detected workspace {gid} ({name}) — saving to keys.env")
        # Append to keys.env
        with open(KEYS_FILE, "a") as f:
            f.write(f"\nASANA_WORKSPACE_GID={gid}\n")
        return gid
    except Exception as e:
        print(f"  Asana: could not auto-detect workspace ({e})")
        return None

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


def jira_post_comment(base_url: str, key: str, body: str, headers: dict):
    """Post a rich-text (ADF) comment to a Jira issue."""
    adf_body = _build_adf_from_lines(body)
    r = requests.post(
        f"{base_url}/rest/api/3/issue/{key}/comment",
        headers=headers,
        json={"body": adf_body},
    )
    r.raise_for_status()

def jira_search(base_url: str, slug: str, headers: dict, keys: dict) -> str | None:
    words = slug.replace("-", " ")
    project_keys = keys.get("JIRA_PROJECT_KEYS", "").strip()
    if project_keys:
        projects = ", ".join(p.strip() for p in project_keys.split(","))
        jql = f'project in ({projects}) AND summary ~ "{words}" ORDER BY created DESC'
    else:
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


def cmd_post(slug: str, note_file: str):
    note_path = Path(note_file)
    if not note_path.exists():
        print(f"Note file not found: {note_file}")
        sys.exit(1)
    body = _build_brief_comment(note_path)

    keys = load_keys()
    has_jira  = jira_configured(keys)
    has_asana = asana_configured(keys)

    if not has_jira and not has_asana:
        print("No ticket integrations configured — skipping ticket posting.")
        sys.exit(0)

    row = find_row(slug)
    if not row:
        print(f"Slug '{slug}' not found in bench-index.csv — add it first.")
        sys.exit(1)

    jira_key  = row.get("jira", "").strip()
    asana_gid = row.get("asana", "").strip()

    if has_jira:
        jh = jira_headers(keys)
        base_url = keys["JIRA_URL"]

        if not jira_key:
            print(f"No Jira ticket for '{slug}', searching...")
            found = jira_search(base_url, slug, jh, keys)
            if found:
                jira_key = found
                update_row(slug, jira=found)
                print(f"  Updated bench-index.csv with Jira {found}")
            else:
                print(f"  No Jira match.")

    if has_asana:
        ah = asana_headers(keys)
        asana_workspace = keys["ASANA_WORKSPACE_GID"]

        if not asana_gid:
            if not sys.stdin.isatty():
                print(f"No Asana task for '{slug}' — skipping (non-interactive).")
            else:
                print(f"No Asana task for '{slug}', searching...")
                found = asana_search(slug, ah, asana_workspace)
                if found:
                    confirm = input(f"  Link Asana {found} to '{slug}'? [y/N] ").strip().lower()
                    if confirm == "y":
                        asana_gid = found
                        update_row(slug, asana=found)
                        print(f"  Updated bench-index.csv with Asana {found}")
                    else:
                        print(f"  Skipped Asana link.")
                else:
                    print(f"  No Asana match.")

    posted = False
    if jira_key and has_jira:
        try:
            jira_post_comment(base_url, jira_key, body, jh)
            print(f"Posted to Jira {jira_key}")
            posted = True
        except Exception as e:
            print(f"Jira post failed: {e}")

    if asana_gid and has_asana:
        try:
            asana_post_comment(asana_gid, body, ah)
            print(f"Posted to Asana task {asana_gid}")
            posted = True
        except Exception as e:
            print(f"Asana post failed: {e}")

    if not posted:
        print("No comment posted — no matching tickets found.")


def cmd_search(slug: str):
    keys = load_keys()
    has_jira  = jira_configured(keys)
    has_asana = asana_configured(keys)

    if not has_jira and not has_asana:
        print("No ticket integrations configured — nothing to search.")
        sys.exit(0)

    print(f"Searching for '{slug}'...")
    jira_key  = None
    asana_gid = None

    if has_jira:
        jira_key = jira_search(keys["JIRA_URL"], slug, jira_headers(keys), keys)
    if has_asana:
        asana_gid = asana_search(slug, asana_headers(keys), keys["ASANA_WORKSPACE_GID"])
        if asana_gid:
            confirm = input(f"  Link Asana {asana_gid} to '{slug}'? [y/N] ").strip().lower()
            if confirm != "y":
                print(f"  Skipped Asana link.")
                asana_gid = None

    if jira_key or asana_gid:
        update_row(slug, jira=jira_key or "", asana=asana_gid or "")
        print(f"bench-index.csv updated.")
    else:
        print(f"No matches found.")


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
