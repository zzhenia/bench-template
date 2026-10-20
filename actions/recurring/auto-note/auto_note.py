#!/usr/bin/env python3
"""Auto-note + auto-close — note a convo window that went quiet, then close it.

Claude Code has no "session went idle" hook, so launchd runs this every five
minutes. Each sweep:

  1. Auto-note. For every session of this bench with a user message whose last
     real turn is older than `default_idle_minutes`, the model writes the session
     note and this script files it in `convos/<topic>/YYMMDD-<slug>.md` (appended
     under the existing note when that date already has one).
  2. Auto-close. A window whose note is written, that has said nothing since,
     whose last turn ended cleanly and whose processes are not using CPU, is
     closed after `autoclose.idle_minutes`. Any new activity cancels it.
     `claude --resume <session id>` brings the conversation back.

Deliberately narrow:
  - Never posts to a ticket tool and never commits; `/push` still owns git.
  - The model returns note *text* and gets no tools; this script writes the file.

Sessions are known through the registry the UserPromptSubmit hook
(`.claude/scripts/convo_session.sh`) writes to ~/.claude/bench-sessions/.

Usage:
    auto_note.py              # normal run (what launchd does)
    auto_note.py --dry-run    # decide and log, write nothing, close nothing
    auto_note.py --force SID  # ignore the idle threshold for one session
    auto_note.py --backfill   # first run: note already-idle sessions for real
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ACTION_DIR = Path(__file__).resolve().parent
BENCH_ROOT = ACTION_DIR.parents[2]
CONVOS = BENCH_ROOT / "convos"
CONFIG_PATH = ACTION_DIR / "config.json"
STATE_PATH = ACTION_DIR / "state.json"
LOCK_PATH = ACTION_DIR / ".auto-note.lock"
LOG_PATH = ACTION_DIR / "auto-note.log"
HEARTBEAT_PATH = ACTION_DIR / ".last-run"   # tells "ran, nothing due" from "never ran"
TEMPLATE_PATH = CONVOS / "Templates" / "Convo Template.md"
REGISTRY_DIR = Path.home() / ".claude" / "bench-sessions"
# A session that never declared `>>topic` is filed here unless the model picks
# an existing convo.
UNDECLARED_TOPIC = "the-bench"
SKIP_FOLDERS = {"Templates"}

# launchd gives this job a minimal PATH, so `claude` must be absolute.
CLAUDE_BIN = str(Path.home() / ".local" / "bin" / "claude")
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
CLAUDE_TIMEOUT = 300


def login_dir() -> Path | None:
    """CLAUDE_CONFIG_DIR of this bench's own Anthropic login, from .claude-login."""
    login = BENCH_ROOT / ".claude-login"
    if login.is_file() and login.read_text().strip():
        return Path(login.read_text().strip()).expanduser()
    return None


def transcript_dirs() -> list[Path]:
    """Where Claude Code keeps this bench's transcripts: projects/<escaped path>
    under the bench's login (if any), the default login, and $CLAUDE_CONFIG_DIR."""
    escaped = re.sub(r"[^A-Za-z0-9]", "-", str(BENCH_ROOT))
    roots = [login_dir(), Path.home() / ".claude",
             Path(os.environ["CLAUDE_CONFIG_DIR"]).expanduser()
             if os.environ.get("CLAUDE_CONFIG_DIR") else None]
    return list(dict.fromkeys(r / "projects" / escaped for r in roots if r))


def transcript_for(sid: str) -> Path | None:
    for d in transcript_dirs():
        if (d / f"{sid}.jsonl").exists():
            return d / f"{sid}.jsonl"
    return None


def show(path: Path) -> str:
    try:
        return str(path.relative_to(BENCH_ROOT))
    except ValueError:
        return str(path)


def log(msg: str) -> None:
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    try:
        with LOG_PATH.open("a") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Config / state
# ---------------------------------------------------------------------------


def load_config() -> dict:
    cfg = json.loads(CONFIG_PATH.read_text())
    cfg.setdefault("default_idle_minutes", 15)
    cfg.setdefault("overrides", {})
    cfg.setdefault("min_note_interval_minutes", 120)
    cfg.setdefault("lookback_hours", 24)
    cfg.setdefault("max_transcript_chars", 60000)
    cfg.setdefault("enabled", True)
    cfg.setdefault("notifications", True)
    cfg.setdefault("banners", False)
    cfg.setdefault("autoclose", {})
    cfg["autoclose"].setdefault("enabled", True)
    cfg["autoclose"].setdefault("idle_minutes", 60)
    return cfg


def idle_threshold(cfg: dict, topic: str | None) -> int:
    raw = cfg["overrides"].get(topic or "")
    return int(raw) if isinstance(raw, (int, float)) else int(cfg["default_idle_minutes"])


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except json.JSONDecodeError:
            log("WARNING: state.json unreadable, starting fresh")
    return {"noted": {}}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Transcript parsing
# ---------------------------------------------------------------------------

TOPIC_RE = re.compile(r"^\s*>>\s*([A-Za-z0-9_-]+)")
SKIP_PREFIXES = ("<system-reminder", "<command-", "<local-command",
                 "Caveat:", "[Request interrupted")


def _epoch(stamp) -> float | None:
    if not isinstance(stamp, str):
        return None
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content
                 if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(p for p in parts if p)
    return ""


def parse_transcript(path: Path, max_chars: int) -> dict | None:
    """Topic (None if never declared), user-message count, digest, time of the
    last real turn, and whether the last turn ended cleanly."""
    topic, user_msgs, turns, last_ts, done = None, 0, [], None, False
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError as exc:
        log(f"WARNING: cannot read {path.name}: {exc}")
        return None

    for raw in lines:
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if entry.get("isSidechain"):
            continue  # subagent chatter
        etype = entry.get("type")
        if etype not in ("user", "assistant"):
            continue
        # A pending tool result or a tool_use stop means Claude is mid-task;
        # only a clean end_turn counts as finished.
        done = (etype == "assistant"
                and entry.get("message", {}).get("stop_reason") == "end_turn")
        text = _text_of(entry.get("message", {}).get("content")).strip()
        if not text or text.startswith(SKIP_PREFIXES):
            continue
        stamp = _epoch(entry.get("timestamp"))
        if stamp:
            last_ts = stamp
        if etype == "user":
            user_msgs += 1
            if topic is None:
                m = TOPIC_RE.match(text)
                if m:
                    topic = m.group(1).lower()
            turns.append(f"USER: {text}")
        else:
            turns.append(f"CLAUDE: {text}")

    digest = "\n\n".join(turns)
    if len(digest) > max_chars:
        digest = "[...earlier turns trimmed...]\n\n" + digest[-max_chars:]
    return {"topic": topic, "user_msgs": user_msgs, "digest": digest,
            "last_ts": last_ts, "done": done}


# ---------------------------------------------------------------------------
# Note generation
# ---------------------------------------------------------------------------


def convo_folders() -> list[str]:
    """Existing convo folders: the model may refile a note, never invent one."""
    if not CONVOS.is_dir():
        return []
    return sorted(p.name for p in CONVOS.iterdir()
                  if p.is_dir() and p.name not in SKIP_FOLDERS
                  and not p.name.startswith((".", "~")))


def resolve_folder(name: str, folders: list[str]) -> str | None:
    flat = lambda s: re.sub(r"[^a-z0-9]+", "", s.lower())  # noqa: E731
    target = flat(name)
    return next((f for f in folders if target and flat(f) == target), None)


def build_prompt(topic: str | None, digest: str, template: str, appending: bool,
                 folders: list[str]) -> str:
    shape = (
        "Return ONLY the body sections (no `# heading`, no `**Date:**` line) - "
        "it will be appended under an existing note for today."
        if appending else
        f"Fill in this template exactly, keeping its heading structure:\n\n{template}"
    )
    listed = ", ".join(f"`{f}`" for f in folders)
    if topic:
        filing = (f"\nThe session declared the convo `{topic}`. Existing convos: {listed}. "
                  f"Keep `{topic}` unless the bulk of the work clearly belongs to another "
                  "of them.\n")
        header = f"You are writing a session note for the convo `{topic}`."
    else:
        filing = (f"\nThis session never declared a convo. Existing convos: {listed}. "
                  "Pick the one the work actually landed in.\n")
        header = "You are writing a session note for a bench session."
    return f"""{header}

Below is the transcript of a Claude Code session that has gone idle. Summarise
what actually happened: decisions made, work done, files touched, action items,
and anything left open. Be specific - name files, numbers. Do not pad, do not
invent. If a section has nothing real in it, say so in one line.
{filing}
{shape}

The first two lines of your reply must be exactly:
TOPIC: <one convo name from the list above>
SLUG: <two-or-three-word-kebab-case description of the session>

Then the markdown. No preamble, no code fences around the whole thing.

--- TRANSCRIPT ---
{digest}
--- END TRANSCRIPT ---
"""


def call_model(prompt: str) -> str:
    """`claude -p` on the bench's login. ANTHROPIC_API_KEY is stripped so the
    CLI uses the subscription login rather than billing the API."""
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    login = login_dir()
    if login:
        env["CLAUDE_CONFIG_DIR"] = str(login)
    cmd = [CLAUDE_BIN, "-p", "--model", CLAUDE_MODEL, "--output-format", "text"]
    last_err = None
    for attempt in range(2):
        try:
            proc = subprocess.run(cmd, input=prompt, env=env, capture_output=True,
                                  text=True, timeout=CLAUDE_TIMEOUT, cwd=str(ACTION_DIR))
            if proc.returncode != 0:
                raise RuntimeError(f"claude exited {proc.returncode}: "
                                   f"{proc.stderr.strip()[:300]}")
            if not proc.stdout.strip():
                raise RuntimeError("claude returned empty output")
            return proc.stdout.strip()
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            log(f"WARNING: model call failed (attempt {attempt + 1}): {exc}")
    raise RuntimeError(f"model call failed after retry: {last_err}")


def split_header(reply: str) -> tuple[str | None, str, str]:
    """Pull the TOPIC and SLUG lines off the front. Returns (topic, slug, body)."""
    lines = reply.splitlines()
    topic, slug = None, "session"
    for _ in range(2):
        if not lines:
            break
        head = lines[0].strip()
        if head.upper().startswith("TOPIC:"):
            topic = re.sub(r"[^a-z0-9-]+", "-",
                           head.split(":", 1)[1].strip().lower()).strip("-") or None
        elif head.upper().startswith("SLUG:"):
            cand = re.sub(r"[^a-z0-9]+", "-",
                          head.split(":", 1)[1].strip().lower()).strip("-")
            if cand:
                slug = "-".join(cand.split("-")[:3])
        else:
            break
        lines = lines[1:]
    return topic, slug, "\n".join(lines).strip()


def today_notes(topic: str, ended: datetime) -> list[Path]:
    """Notes already filed under the date the session went quiet."""
    folder = CONVOS / topic
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.glob(f"{ended:%y%m%d}*.md")
                  if not p.name.startswith("_memory"))


def write_note(topic: str, slug: str, body: str, ended: datetime,
               dry_run: bool) -> tuple[Path, bool]:
    folder, stamp = CONVOS / topic, f"{ended:%y%m%d}"
    existing = today_notes(topic, ended)
    if existing:
        target = existing[0]
        if not dry_run:
            with target.open("a") as fh:
                fh.write(f"\n\n---\n\n#### Auto-note - session idle since "
                         f"{ended:%H:%M}\n\n{body}\n")
        return target, True
    target = folder / f"{stamp}-{slug}.md"
    if not dry_run:
        folder.mkdir(parents=True, exist_ok=True)
        target.write_text(f"# {topic}\n**Date:** {stamp}\n"
                          f"<!-- written automatically: session idle since "
                          f"{ended:%H:%M} -->\n\n{body}\n")
    return target, False


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

PINK = "\033[38;5;213m"
NOTIFICATIONS = True
BANNERS = False


def ps_rows() -> list[list[str]]:
    try:
        out = subprocess.run(["ps", "-eo", "pid=,tty=,command="],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [p for p in (line.split(None, 2) for line in out.splitlines()) if len(p) == 3]


def tty_live(tty_path: str, pid: int | None) -> bool:
    """True only if *this session's* Claude CLI pid is still on that tty: ttys
    numbers get recycled, so any `claude` on the tty is not enough."""
    if not tty_path or not pid or not os.path.exists(tty_path):
        return False
    dev = tty_path.removeprefix("/dev/")
    return any(int(p[0]) == int(pid) and p[1] == dev and "claude" in p[2]
               for p in ps_rows())


def write_pink(session_id: str, message: str) -> bool:
    try:
        entry = json.loads((REGISTRY_DIR / f"{session_id}.json").read_text())
    except (OSError, json.JSONDecodeError):
        return False
    tty_path = entry.get("tty") or ""
    if not tty_live(tty_path, entry.get("pid")):
        return False
    try:
        with open(tty_path, "w") as fh:
            fh.write(f"\n{PINK}{message}\033[0m\n")
        return True
    except OSError as exc:
        log(f"WARNING: tty write to {tty_path} failed: {exc}")
        return False


def banner(topic: str, message: str) -> None:
    """macOS notification; best effort, off unless config `banners` is true."""
    if not BANNERS or sys.platform != "darwin":
        return
    body = message.replace("[auto-note] ", "").replace('"', "'").replace("\\", "")
    sub = topic.replace('"', "'")
    try:
        subprocess.run(["osascript", "-e", f'display notification "{body}" '
                        f'with title "auto-note" subtitle "{sub}"'],
                       check=False, capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        log(f"WARNING: banner failed for {topic}: {exc}")


def notify(session_id: str, message: str, topic: str = "") -> None:
    """Once: a pink line on the window's tty, plus a notice file the hook shows
    on the next prompt (a TUI redraw can wipe the tty line). ASCII only: the
    hook's systemMessage mangles multi-byte characters."""
    if not NOTIFICATIONS:
        return
    message = message.encode("ascii", "replace").decode("ascii")
    if not write_pink(session_id, message):
        log(f"  no live tty for {session_id[:8]} - notice file only")
    try:
        REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
        (REGISTRY_DIR / f"{session_id}.notice").write_text(message)
    except OSError as exc:
        log(f"WARNING: could not park notice for {session_id[:8]}: {exc}")
    banner(topic or session_id[:8], message)


# ---------------------------------------------------------------------------
# Sweep: auto-note
# ---------------------------------------------------------------------------


def evaluate(path: Path, parsed: dict, cfg: dict, state: dict, force: bool) -> dict | None:
    """Is this transcript due for a note? No model calls here."""
    sid = path.stem
    if parsed["user_msgs"] < 1:
        return None
    # Idleness from the last real turn, not mtime: an open session keeps its
    # transcript touched by hook records.
    ended = parsed["last_ts"] or path.stat().st_mtime
    idle_min = (time.time() - ended) / 60
    threshold = idle_threshold(cfg, parsed["topic"])
    if not force and idle_min < threshold:
        return None
    prior = state["noted"].get(sid)
    if prior and not force:
        if parsed["user_msgs"] - prior.get("user_msgs", 0) <= 0:
            return None  # already noted, nothing new since
        wrote_at = _epoch(prior.get("at"))
        if wrote_at and (time.time() - wrote_at) / 60 < int(cfg["min_note_interval_minutes"]):
            return None
    return {"session_id": sid, "idle_min": idle_min, "threshold": threshold,
            "ended": datetime.fromtimestamp(ended), **parsed}


def generate(job: dict, state: dict, template: str, dry_run: bool) -> None:
    sid, topic = job["session_id"], job["topic"]
    log(f"{sid[:8]} topic={topic or '(undeclared)'} idle={job['idle_min']:.0f}m "
        f"(threshold {job['threshold']}m) msgs={job['user_msgs']}"
        + (" [DRY RUN]" if dry_run else ""))
    try:
        folders = convo_folders()
        appending = bool(topic and today_notes(topic, job["ended"]))
        picked, slug, body = split_header(call_model(
            build_prompt(topic, job["digest"], template, appending, folders)))
        filed = topic or UNDECLARED_TOPIC
        if picked:
            resolved = resolve_folder(picked, folders)
            if resolved and resolved != filed:
                log(f"  filed {topic or '(undeclared)'} -> {resolved}")
                filed = resolved
        target, appended = write_note(filed, slug, body, job["ended"], dry_run)
    except Exception as exc:  # noqa: BLE001 - surface it, never crash the sweep
        log(f"ERROR: auto-note failed for {topic or '(undeclared)'} ({sid[:8]}): {exc}")
        if not dry_run:
            notify(sid, f"[auto-note] FAILED for {topic}: {exc}. Run /note manually. "
                        f"Log: {LOG_PATH}", topic or "")
        return
    rel, verb = show(target), ("appended to" if appended else "wrote")
    log(f"  {'would have ' if dry_run else ''}{verb} {rel}")
    if not dry_run:
        notify(sid, f"[auto-note] {int(job['idle_min'])}m idle: {verb} {rel} "
                    f"(not committed). Say /note to redo.", topic or "")
        state["noted"][sid] = {"topic": filed, "file": rel, "user_msgs": job["user_msgs"],
                               "at": datetime.now().isoformat(timespec="seconds")}
        save_state(state)


# ---------------------------------------------------------------------------
# Sweep: auto-close
# ---------------------------------------------------------------------------
#
# A window is finished when its note is written, nothing has been said since,
# the last turn ended cleanly, and the CPU time on its tty has not moved since
# the previous sweep. After `autoclose.idle_minutes` of that it is closed: HUP to
# the tab's login shell, then TERM, then KILL the chain, reporting "closed" only
# once every pid is gone. Terminal hosts drop a tab whose shell has exited.


def tty_cpu(dev: str) -> float:
    """Total CPU seconds of every process on a tty; flat while Claude waits."""
    try:
        out = subprocess.run(["ps", "-eo", "tty=,cputime="],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return -1.0
    total = 0.0
    for line in out.splitlines():
        parts = line.split()
        if len(parts) != 2 or parts[0] != dev:
            continue
        try:
            h, m, sec = (["0", "0"] + parts[1].split(":"))[-3:]
            total += int(h) * 3600 + int(m) * 60 + float(sec)
        except ValueError:
            pass
    return total


def tty_chain(claude_pid: int) -> list[int]:
    """The CLI and every on-tty ancestor up to the tab's login shell."""
    chain, pid = [], claude_pid
    for _ in range(8):
        try:
            out = subprocess.run(["ps", "-o", "ppid=,tty=", "-p", str(pid)],
                                 capture_output=True, text=True, timeout=5).stdout.split()
        except (OSError, subprocess.SubprocessError):
            break
        if len(out) != 2 or out[1] == "??":
            break
        chain.append(pid)
        pid = int(out[0])
        if pid <= 1:
            break
    return chain


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def close_window(entry: dict) -> bool:
    topic, pid = entry.get("topic"), entry.get("pid")
    if not pid:
        log(f"WARNING: no pid for {topic} - cannot close")
        return False
    chain = tty_chain(int(pid)) or [int(pid)]
    left = chain
    for name, targets, sig in (("HUP", [chain[-1]], 1), ("TERM", chain, 15),
                               ("KILL", chain, 9)):
        for t in targets:
            try:
                os.kill(t, sig)
            except ProcessLookupError:
                pass
            except OSError as exc:
                log(f"WARNING: {name} to {t} failed for {topic}: {exc}")
        time.sleep(2)
        left = [t for t in chain if _alive(t)]
        if not left:
            log(f"  closed {topic} with {name} (chain {chain})")
            return True
    log(f"WARNING: {topic} still running after HUP/TERM/KILL: {left}")
    return False


def own_entries() -> list[tuple[Path, dict]]:
    """Registry entries of sessions running in this bench (the registry is
    shared by every bench on the machine)."""
    found = []
    if not REGISTRY_DIR.is_dir():
        return found
    root = str(BENCH_ROOT)
    for reg in REGISTRY_DIR.glob("*.json"):
        try:
            entry = json.loads(reg.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        cwd = entry.get("cwd") or ""
        if cwd == root or cwd.startswith(root + os.sep):
            found.append((reg, entry))
    return found


def autoclose(cfg: dict, state: dict, parsed_by_sid: dict, dry_run: bool) -> None:
    ac = cfg["autoclose"]
    if not ac["enabled"]:
        return
    pending = state.setdefault("close_pending", {})
    cpu_seen = state.setdefault("cpu", {})
    now = time.time()

    for reg, entry in own_entries():
        sid = reg.stem
        tty_path, pid, topic = entry.get("tty", ""), entry.get("pid"), entry.get("topic", "")
        if not tty_live(tty_path, pid):
            pending.pop(sid, None); cpu_seen.pop(sid, None)
            continue

        cpu_now = tty_cpu(tty_path.removeprefix("/dev/"))
        cpu_prev = cpu_seen.get(sid)
        cpu_seen[sid] = cpu_now
        # An idle TUI ticks under a second per sweep; more means real work.
        working = cpu_prev is None or cpu_now < 0 or (cpu_now - cpu_prev) > 5.0

        parsed = parsed_by_sid.get(sid)
        noted = state["noted"].get(sid) or {}
        idle_min = (now - (parsed["last_ts"] if parsed and parsed["last_ts"] else now)) / 60
        ready = (parsed is not None and parsed["done"] and not working
                 and noted.get("file") and noted.get("user_msgs", 0) >= parsed["user_msgs"]
                 and idle_min >= ac["idle_minutes"])

        if not ready:
            if sid in pending:
                log(f"  autoclose cancelled for {topic} ({sid[:8]}): activity resumed")
                pending.pop(sid, None)
            continue

        mark = pending.setdefault(sid, {"at": now, "topic": topic})
        if mark.get("failed", 0) >= 2:
            continue  # gave up on this window; never retry every sweep
        log(f"  autoclose {topic} ({sid[:8]}) after {int(idle_min)}m idle "
            f"- resume with: claude --resume {sid}" + (" [DRY RUN]" if dry_run else ""))
        if dry_run:
            continue
        if close_window(entry):
            banner(topic, f"[auto-note] closed {topic} after {int(idle_min)}m idle. "
                          f"Resume: claude --resume {sid}")
            pending.pop(sid, None); cpu_seen.pop(sid, None)
            reg.unlink(missing_ok=True)
            (REGISTRY_DIR / f"{sid}.notice").unlink(missing_ok=True)
        else:
            mark["failed"] = mark.get("failed", 0) + 1
            if mark["failed"] >= 2:
                log(f"  giving up on closing {topic} ({sid[:8]}) - close it by hand")
    if not dry_run:
        save_state(state)


def prune_registry(days: int = 7) -> None:
    cutoff = time.time() - days * 86400
    for reg, _ in own_entries():
        try:
            if reg.stat().st_mtime < cutoff:
                reg.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="decide and log, write nothing, close nothing")
    ap.add_argument("--force", metavar="SESSION_ID",
                    help="ignore the idle threshold for one session id")
    ap.add_argument("--backfill", action="store_true",
                    help="on a fresh state file, note already-idle sessions for real")
    args = ap.parse_args()

    cfg = load_config()
    global NOTIFICATIONS, BANNERS
    NOTIFICATIONS, BANNERS = bool(cfg["notifications"]), bool(cfg["banners"])
    if not cfg["enabled"] and not args.force:
        log("disabled in config.json - nothing to do")
        return 0

    tdirs = [d for d in transcript_dirs() if d.is_dir()]
    if not tdirs:
        log(f"no transcripts yet for this bench (looked in "
            f"{', '.join(str(d) for d in transcript_dirs())})")
        return 0

    if LOCK_PATH.exists():
        age = time.time() - LOCK_PATH.stat().st_mtime
        if age < 3600:
            log("another run is in progress - skipping")
            return 0
        log(f"reclaiming stale lock ({age / 60:.0f}m old)")
    if not args.dry_run:
        LOCK_PATH.touch()

    candidates, jobs = [], []
    try:
        if not args.dry_run:
            prune_registry()
        state = load_state()
        template = TEMPLATE_PATH.read_text() if TEMPLATE_PATH.is_file() else ""
        cutoff = time.time() - cfg["lookback_hours"] * 3600
        candidates = [p for d in tdirs for p in d.glob("*.jsonl")
                      if p.stat().st_mtime >= cutoff
                      or (args.force and p.stem == args.force)]
        registered = {reg.stem for reg, _ in own_entries()}

        parsed_by_sid = {}
        for path in sorted(candidates, key=lambda p: p.stat().st_mtime):
            parsed = parse_transcript(path, cfg["max_transcript_chars"])
            if not parsed:
                continue
            if path.stem in registered:
                parsed_by_sid[path.stem] = parsed
            job = evaluate(path, parsed, cfg, state,
                           force=bool(args.force and path.stem == args.force))
            if job:
                jobs.append(job)

        # A fresh state file would otherwise backfill every session idle in the
        # last day, most of it already written up by hand. Seed them instead.
        if not state["noted"] and jobs and not args.backfill and not args.force:
            log(f"first run - seeding {len(jobs)} already-idle session(s) as done "
                f"(re-run with --backfill to write them for real)")
            if not args.dry_run:
                for job in jobs:
                    state["noted"][job["session_id"]] = {
                        "topic": job["topic"], "file": None, "seeded": True,
                        "user_msgs": job["user_msgs"],
                        "at": datetime.now().isoformat(timespec="seconds")}
                save_state(state)
            return 0

        if args.dry_run:
            print(f"[dry run] {len(candidates)} recent session(s), {len(jobs)} due for "
                  f"a note, {len(parsed_by_sid)} registered window(s)")
        for job in jobs:
            generate(job, state, template, args.dry_run)
        autoclose(cfg, load_state() if not args.dry_run else state,
                  parsed_by_sid, args.dry_run)
    finally:
        if not args.dry_run:
            LOCK_PATH.unlink(missing_ok=True)
            try:
                HEARTBEAT_PATH.write_text(f"{datetime.now():%Y-%m-%d %H:%M:%S} "
                                          f"candidates={len(candidates)} due={len(jobs)}\n")
            except OSError:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
