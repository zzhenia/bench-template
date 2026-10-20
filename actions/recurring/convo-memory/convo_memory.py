#!/usr/bin/env python3
"""
Convo Memory — OptMem-style three-layer memory compression for convo folders.

Layers per convo folder:
  Layer 0 (log)   : YYMMDD-*.md session notes — never touched
  Layer 1 (index) : _memory-index.md — detailed evidence, append-heavy
  Layer 2 (wake)  : _memory-master.md — compact summary, ~60 line cap

Two-phase update per folder (mirrors the retro pipeline in
actions/on-demand/yt-autopilot/backend/retro_analysis.py):
  1. update_index      — Haiku appends new note content to the index (storage budget)
  2. regenerate_master — Haiku compresses the index into the master (reading budget)

Schedule (via launchd): nightly at 02:30. Also runnable on demand:
  python3 convo_memory.py --all                    # incremental, all eligible folders
  python3 convo_memory.py --folder music           # single folder, incremental
  python3 convo_memory.py --folder music --bootstrap   # full rebuild from all notes
  python3 convo_memory.py --all --bootstrap        # bootstrap every eligible folder
  python3 convo_memory.py --all --dry-run          # show what would be processed
  python3 convo_memory.py --all --commit           # narrow-stage + commit + push after run

Safety: writes ONLY _memory-index.md, _memory-master.md and state.json.
Raw notes are opened read-only. On any guard rejection nothing is written
and the watermark does not advance (notes are retried next run).
"""

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Load central keys.env
# ---------------------------------------------------------------------------

BENCH_ROOT = Path(__file__).resolve().parents[3]
_config_path = BENCH_ROOT / "config" / "keys.env"
if _config_path.exists():
    for _line in _config_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CONVOS = BENCH_ROOT / "convos"
CLAUDE_HAIKU = "claude-haiku-4-5-20251001"
# launchd gives this job a minimal PATH, so `claude` must be absolute.
CLAUDE_BIN = str(Path.home() / ".local" / "bin" / "claude")
CLAUDE_TIMEOUT = 300      # seconds per call
NOTE_RE = re.compile(r"^\d{6}-.+\.md$")
BULLET_RE = re.compile(r"^\s*- \[\d{6}\]", re.MULTILINE)
EXCLUDE = {"Templates", "~archive", "~empty", "daily-log"}
MIN_NOTES = 5
BATCH_SIZE = 10           # notes per Haiku call during bootstrap
NOTE_TRUNCATE = 4000      # chars per note fed to the model
MASTER_LINE_CAP = 60      # target; reject above hard cap
MASTER_LINE_HARD_CAP = 90
INDEX_MAX_TOKENS = 4000   # delta only — output stays constant as the index grows
MASTER_MAX_TOKENS = 2500

ACTION_DIR = Path(__file__).resolve().parent
STATE_FILE = ACTION_DIR / "state.json"
LOG_FILE = ACTION_DIR / "trigger.log"
LOCK_FILE = ACTION_DIR / ".convo-memory.lock"

INDEX_NAME = "_memory-index.md"
MASTER_NAME = "_memory-master.md"

INDEX_SKELETON = """# Memory Index — {topic}
Last updated: {today}
Notes indexed: 0

## Decisions

## Facts & Current State

## Preferences & Rules

## Open Threads

## Key References
"""

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            log("WARNING: state.json corrupt, starting fresh")
    return {"folders": {}}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Folder / note discovery
# ---------------------------------------------------------------------------


def list_notes(folder: Path) -> list[Path]:
    """Top-level session notes matching YYMMDD-*.md, chronologically sorted."""
    return sorted(
        (p for p in folder.iterdir() if p.is_file() and NOTE_RE.match(p.name)),
        key=lambda p: p.name,
    )


def eligible_folders(min_notes: int = MIN_NOTES) -> list[Path]:
    folders = []
    for folder in sorted(CONVOS.iterdir()):
        if not folder.is_dir() or folder.name in EXCLUDE:
            continue
        if len(list_notes(folder)) >= min_notes:
            folders.append(folder)
    return folders


def new_notes(folder: Path, state: dict) -> list[Path]:
    """Notes with filename greater than the stored watermark."""
    watermark = state["folders"].get(folder.name, {}).get("last_note", "")
    return [n for n in list_notes(folder) if n.name > watermark]


def batch_text(notes: list[Path]) -> str:
    parts = []
    for n in notes:
        try:
            body = n.read_text(encoding="utf-8")[:NOTE_TRUNCATE]
        except Exception as e:
            log(f"WARNING: could not read {n}: {e}")
            continue
        parts.append(f"=== NOTE {n.name} ===\n{body}")
    return "\n\n".join(parts)


def count_bullets(text: str) -> int:
    return len(BULLET_RE.findall(text))


# ---------------------------------------------------------------------------
# Haiku
# ---------------------------------------------------------------------------


def call_haiku(prompt: str, max_tokens: int) -> str:
    """Run the prompt through the Claude Code CLI, billed to the Max subscription.

    Previously this used the anthropic SDK with ANTHROPIC_API_KEY, which billed
    pay-per-token on top of the subscription. `claude -p` reuses the Keychain
    OAuth credentials instead, so nightly runs cost nothing extra.

    ANTHROPIC_API_KEY is stripped from the child environment on purpose: if the
    CLI sees one it may bill the API instead of the subscription, silently
    undoing the whole point of this change.

    max_tokens is advisory now — the CLI exposes no equivalent flag, so output
    length is governed by the prompts themselves.
    """
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    # A bench on its own Anthropic account names that login's config dir in
    # config/claude-login; without it the default login is used.
    login = BENCH_ROOT / "config" / "claude-login"
    if login.is_file() and login.read_text().strip():
        env["CLAUDE_CONFIG_DIR"] = str(Path(login.read_text().strip()).expanduser())
    cmd = [CLAUDE_BIN, "-p", "--model", CLAUDE_HAIKU, "--output-format", "text"]

    last_err = None
    for attempt in range(2):
        try:
            proc = subprocess.run(
                cmd, input=prompt, env=env, capture_output=True,
                text=True, timeout=CLAUDE_TIMEOUT,
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    f"claude exited {proc.returncode}: {proc.stderr.strip()[:300]}")
            out = proc.stdout.strip()
            if not out:
                raise RuntimeError("claude returned empty output")
            return out
        except Exception as e:
            last_err = e
            log(f"WARNING: Haiku call failed (attempt {attempt + 1}): {e}")
    raise RuntimeError(f"Haiku call failed after retry: {last_err}")


# ---------------------------------------------------------------------------
# Phase 1 — index update
# ---------------------------------------------------------------------------


INDEX_SECTIONS = ["Decisions", "Facts & Current State", "Preferences & Rules",
                  "Open Threads", "Key References"]


def _parse_delta(text: str) -> tuple[dict[str, list[str]], list[tuple[str, str]]]:
    """Parse Haiku's delta response into (additions per section, amendments).

    Additions format:  ## ADDITIONS / ### <section> / - [YYMMDD] bullets
    Amendments format: ## AMENDMENTS / - MATCH: <substring> ||| APPEND: <suffix>
    """
    additions: dict[str, list[str]] = {s: [] for s in INDEX_SECTIONS}
    amendments: list[tuple[str, str]] = []
    section = None
    mode = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## ADDITIONS"):
            mode = "add"
            continue
        if stripped.startswith("## AMENDMENTS"):
            mode = "amend"
            continue
        if mode == "add" and stripped.startswith("### "):
            name = stripped[4:].strip()
            section = name if name in INDEX_SECTIONS else None
            continue
        if mode == "add" and section and BULLET_RE.match(line):
            additions[section].append(stripped)
        elif mode == "amend" and stripped.startswith("- MATCH:") and "||| APPEND:" in stripped:
            match_part, _, append_part = stripped[len("- MATCH:"):].partition("||| APPEND:")
            if match_part.strip() and append_part.strip():
                amendments.append((match_part.strip(), append_part.strip()))
    return additions, amendments


def _apply_delta(current_index: str, additions: dict[str, list[str]],
                 amendments: list[tuple[str, str]], today: str,
                 notes_indexed: int) -> str:
    """Mechanically apply the delta: append bullets under sections, annotate matches.

    The script owns all file surgery — the model can never remove evidence.
    """
    lines = current_index.splitlines()

    # Amendments: append suffix to the first line containing the match substring
    existing = set()
    for match, suffix in amendments:
        for i, line in enumerate(lines):
            if match in line and BULLET_RE.match(line) and suffix not in line:
                lines[i] = line.rstrip() + " " + suffix
                break

    # Deduplicate additions against existing bullets (exact text match)
    existing = {l.strip() for l in lines if BULLET_RE.match(l)}

    # Append additions at the end of each section
    for section, bullets in additions.items():
        new_bullets = [b for b in bullets if b not in existing]
        if not new_bullets:
            continue
        header = f"## {section}"
        try:
            start = next(i for i, l in enumerate(lines) if l.strip() == header)
        except StopIteration:
            lines.extend(["", header])
            start = len(lines) - 1
        # Find the end of this section (next ## header or EOF)
        end = next((i for i in range(start + 1, len(lines))
                    if lines[i].startswith("## ")), len(lines))
        # Insert before trailing blank lines of the section
        while end > start + 1 and not lines[end - 1].strip():
            end -= 1
        lines[end:end] = new_bullets

    # Update metadata lines
    for i, line in enumerate(lines[:5]):
        if line.startswith("Last updated:"):
            lines[i] = f"Last updated: {today}"
        elif line.startswith("Notes indexed:"):
            lines[i] = f"Notes indexed: {notes_indexed}"

    return "\n".join(lines) + "\n"


def update_index(folder: Path, notes: list[Path], notes_indexed: int) -> bool:
    """Append new note content to the memory index (delta-based, append-only).

    Haiku sees the current index read-only and returns ONLY a delta (new
    bullets + amendments). The script applies it mechanically, so evidence
    loss is structurally impossible and output size stays constant no
    matter how large the index grows.
    """
    topic = folder.name
    index_path = folder / INDEX_NAME
    today = datetime.now().strftime("%Y-%m-%d")

    if index_path.exists():
        current_index = index_path.read_text(encoding="utf-8")
    else:
        current_index = INDEX_SKELETON.format(topic=topic, today=today)

    old_bullets = count_bullets(current_index)

    prompt = f"""You are maintaining a memory index for the topic "{topic}" in a personal knowledge workspace.

## Current Memory Index (read-only reference — do NOT reproduce it)
```
{current_index}
```

## New Session Notes
```
{batch_text(notes)}
```

## Your Task

Extract new memory-worthy items from the new notes and return ONLY a delta. Rules, strictly:

1. Every new bullet starts with "- [YYMMDD]" citing the source note's date (the 6-digit prefix of the note filename). One fact per bullet, one line each.
2. File each bullet under exactly one section: Decisions / Facts & Current State / Preferences & Rules / Open Threads / Key References.
3. Skip filler (greetings, process chatter). Capture decisions, factual state, user preferences, unresolved items, and file paths or links worth re-finding.
4. Do NOT repeat facts already present in the current index. Only genuinely new information.
5. If a new note resolves or supersedes an existing bullet in the index, add an AMENDMENTS entry: the MATCH text is a short distinctive substring copied EXACTLY from that existing bullet, and the APPEND text is "→ resolved [YYMMDD]" or "→ superseded [YYMMDD]". Also add the outcome as a new bullet if it matters.

Return EXACTLY this structure (omit empty sections; use "## AMENDMENTS" only if needed):

## ADDITIONS
### Decisions
- [YYMMDD] ...
### Facts & Current State
- [YYMMDD] ...
### Preferences & Rules
- [YYMMDD] ...
### Open Threads
- [YYMMDD] ...
### Key References
- [YYMMDD] ...

## AMENDMENTS
- MATCH: <exact substring of existing bullet> ||| APPEND: → resolved [YYMMDD]

Markdown only, no code fences, no commentary."""

    try:
        delta = call_haiku(prompt, INDEX_MAX_TOKENS)
    except RuntimeError:
        return False

    if "## ADDITIONS" not in delta:
        log(f"REJECT [{topic}]: delta response missing ## ADDITIONS header")
        return False

    additions, amendments = _parse_delta(delta)
    n_added = sum(len(v) for v in additions.values())
    if n_added == 0 and not amendments:
        log(f"[{topic}] delta empty — nothing memory-worthy in {len(notes)} note(s)")
        return True

    updated = _apply_delta(current_index, additions, amendments, today, notes_indexed)

    new_bullets = count_bullets(updated)
    if new_bullets < old_bullets:  # structurally impossible, but belt-and-braces
        log(f"REJECT [{topic}]: index lost bullets ({old_bullets} -> {new_bullets})")
        return False

    index_path.write_text(updated, encoding="utf-8")
    log(f"[{topic}] index updated ({old_bullets} -> {new_bullets} bullets, "
        f"+{len(notes)} notes, {len(amendments)} amendments)")
    return True


# ---------------------------------------------------------------------------
# Phase 2 — master regeneration
# ---------------------------------------------------------------------------


def regenerate_master(folder: Path, notes_indexed: int, latest_note: str) -> bool:
    """Compress the index into the compact master. Returns True on success."""
    topic = folder.name
    index_path = folder / INDEX_NAME
    master_path = folder / MASTER_NAME
    if not index_path.exists():
        log(f"REJECT [{topic}]: no index to regenerate master from")
        return False

    evidence = index_path.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    latest_date = latest_note[:6] if latest_note else "??????"

    prompt = f"""You are generating a compact wake-up summary from a detailed memory index for the topic "{topic}".

## Memory Index
```
{evidence}
```

## Your Task

Produce the master memory file an AI assistant reads first when this topic comes up. HARD CONSTRAINTS:

- Under {MASTER_LINE_CAP} lines total. Prioritize current state over history.
- Resolved/superseded items appear only if the resolution itself matters going forward.
- Structure exactly:

# Memory Master — {topic}
Last updated: {today} | Covers {notes_indexed} notes through {latest_date}
Detail: _memory-index.md · raw notes in this folder

## What This Is
(1-2 lines: what this topic/project is)

## Current State
(bullets: where things stand now)

## Standing Decisions & Rules
(bullets: decisions and preferences that remain in force)

## Active Work / Next Steps
(bullets: open items and what happens next)

## Key References
(bullets: paths, links, IDs worth re-finding)

## Open Questions
(bullets, or "None")

Return markdown only, no code fences, starting with "# Memory Master — {topic}"."""

    try:
        updated = call_haiku(prompt, MASTER_MAX_TOKENS)
    except RuntimeError:
        return False

    if f"# Memory Master — {topic}" not in updated:
        log(f"REJECT [{topic}]: master response missing expected header")
        return False

    line_count = len(updated.splitlines())
    if line_count > MASTER_LINE_HARD_CAP:
        log(f"REJECT [{topic}]: master is {line_count} lines (hard cap {MASTER_LINE_HARD_CAP})")
        return False
    if line_count > MASTER_LINE_CAP:
        log(f"WARNING [{topic}]: master is {line_count} lines (target {MASTER_LINE_CAP})")

    master_path.write_text(updated, encoding="utf-8")
    log(f"[{topic}] master regenerated ({line_count} lines)")
    return True


# ---------------------------------------------------------------------------
# Folder processing
# ---------------------------------------------------------------------------


def _advance_watermark(state: dict, folder: Path, last_note: str, notes_indexed: int):
    state["folders"][folder.name] = {
        "last_note": last_note,
        "last_run": datetime.now().isoformat(timespec="seconds"),
        "notes_indexed": notes_indexed,
    }
    save_state(state)


def bootstrap_folder(folder: Path, state: dict, dry_run: bool = False) -> dict:
    """Full rebuild: feed all notes chronologically in batches through update_index.

    Resumable — the watermark advances after each successful batch, so an
    interrupted bootstrap continues where it stopped on the next run.
    """
    topic = folder.name
    pending = new_notes(folder, state)
    total = len(list_notes(folder))
    if not pending:
        return {"folder": topic, "status": "up-to-date"}
    if dry_run:
        return {"folder": topic, "status": "would-bootstrap", "notes": len(pending)}

    log(f"[{topic}] bootstrap: {len(pending)} notes in batches of {BATCH_SIZE}")
    done = total - len(pending)
    for i in range(0, len(pending), BATCH_SIZE):
        batch = pending[i:i + BATCH_SIZE]
        done += len(batch)
        if not update_index(folder, batch, done):
            return {"folder": topic, "status": "failed",
                    "error": f"index update rejected at batch starting {batch[0].name}"}
        _advance_watermark(state, folder, batch[-1].name, done)

    latest = list_notes(folder)[-1].name
    master_ok = regenerate_master(folder, done, latest)
    return {"folder": topic, "status": "bootstrapped" if master_ok else "index-only",
            "notes": len(pending)}


def process_folder(folder: Path, state: dict, dry_run: bool = False) -> dict:
    """Incremental: process only notes newer than the watermark."""
    topic = folder.name
    pending = new_notes(folder, state)
    if not pending:
        return {"folder": topic, "status": "up-to-date"}
    if dry_run:
        return {"folder": topic, "status": "would-process", "notes": len(pending)}

    prev = state["folders"].get(topic, {}).get("notes_indexed", 0)
    notes_indexed = prev + len(pending)
    if not update_index(folder, pending, notes_indexed):
        return {"folder": topic, "status": "failed", "error": "index update rejected"}

    _advance_watermark(state, folder, pending[-1].name, notes_indexed)

    master_ok = regenerate_master(folder, notes_indexed, pending[-1].name)
    return {"folder": topic, "status": "processed" if master_ok else "index-only",
            "notes": len(pending)}


# ---------------------------------------------------------------------------
# Optional git commit (narrow staging, off by default)
# ---------------------------------------------------------------------------


def commit_outputs() -> dict:
    """Narrow-stage memory files + state.json, commit, push."""
    def _git(*args):
        return subprocess.run(["git", *args], cwd=str(BENCH_ROOT),
                              capture_output=True, text=True, timeout=120)

    rel_state = str(STATE_FILE.relative_to(BENCH_ROOT))
    pull = _git("pull", "--rebase", "--autostash")
    if pull.returncode != 0:
        return {"ok": False, "error": f"git pull failed: {pull.stderr.strip()}"}

    paths = [str(p.relative_to(BENCH_ROOT))
             for p in CONVOS.glob(f"*/{INDEX_NAME}")] + \
            [str(p.relative_to(BENCH_ROOT))
             for p in CONVOS.glob(f"*/{MASTER_NAME}")] + [rel_state]
    add = _git("add", "--", *paths)
    if add.returncode != 0:
        return {"ok": False, "error": f"git add failed: {add.stderr.strip()}"}
    if _git("diff", "--cached", "--quiet").returncode == 0:
        return {"ok": True, "committed": False}

    commit = _git("commit", "-m", "Convo memory: nightly compression update",
                  "-m", "Automated by actions/recurring/convo-memory.")
    if commit.returncode != 0:
        return {"ok": False, "error": f"git commit failed: {commit.stderr.strip()}"}
    push = _git("push")
    if push.returncode != 0:
        return {"ok": False, "error": f"git push failed (commit saved locally): {push.stderr.strip()}"}
    return {"ok": True, "committed": True}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Convo memory compression (OptMem three-layer)")
    parser.add_argument("--folder", help="process a single convo folder by name")
    parser.add_argument("--all", action="store_true", help="process all eligible folders")
    parser.add_argument("--bootstrap", action="store_true",
                        help="full rebuild from all notes (batched, resumable)")
    parser.add_argument("--dry-run", action="store_true", help="report what would be done")
    parser.add_argument("--commit", action="store_true",
                        help="narrow-stage + commit + push memory files after run")
    parser.add_argument("--min-notes", type=int, default=MIN_NOTES,
                        help=f"eligibility threshold (default {MIN_NOTES})")
    args = parser.parse_args()

    if not args.folder and not args.all:
        parser.error("specify --folder <name> or --all")

    # Prevent overlapping runs
    lock_fh = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log("Another convo-memory run is in progress; exiting")
        sys.exit(0)

    state = load_state()

    if args.folder:
        folder = CONVOS / args.folder
        if not folder.is_dir():
            log(f"ERROR: no such convo folder: {args.folder}")
            sys.exit(1)
        folders = [folder]
    else:
        folders = eligible_folders(args.min_notes)

    log(f"Run start: {len(folders)} folder(s), mode={'bootstrap' if args.bootstrap else 'incremental'}"
        + (" [dry-run]" if args.dry_run else ""))

    results = []
    for folder in folders:
        fn = bootstrap_folder if args.bootstrap else process_folder
        result = fn(folder, state, dry_run=args.dry_run)
        results.append(result)
        if result["status"] not in ("up-to-date",):
            log(f"  {result}")

    processed = [r for r in results if r["status"] not in ("up-to-date",)]
    failed = [r for r in results if r["status"] == "failed"]
    log(f"Run done: {len(processed)} processed, {len(failed)} failed, "
        f"{len(results) - len(processed)} up-to-date")

    if args.commit and not args.dry_run and processed:
        result = commit_outputs()
        log(f"Commit: {result}")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
