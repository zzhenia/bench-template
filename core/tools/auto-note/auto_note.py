#!/usr/bin/env python3
"""Auto-note — write a session note when a convo terminal goes quiet.

Claude Code has no "session went idle" hook, so this runs from launchd every ten
minutes and infers idleness from the transcript file's mtime. For every session
in this project that has real conversation in it and hasn't been touched for
longer than the configured threshold, it asks the model to write the session
note and drops it in `convos/<topic>/` — the folder the session declared with
`>>`, or the one the model picks when it declared none.

Deliberately narrow:
  - It never posts to a ticket tool. Nobody is at the keyboard to confirm, and
    the bench rule is that ticket comments always need explicit confirmation.
  - The model returns note *text*; this script writes the file. The model gets no
    tools, so it cannot touch anything else.
  - Notes are never committed. `/push` still owns git.

Notification goes back to the terminal the session belongs to exactly once: an
immediate line on its tty, plus a notice file the UserPromptSubmit hook surfaces
next time the user types there. It is never re-sent (the per-sweep re-send filled
windows with the same line dozens of times, 260925).

Usage:
    auto_note.py              # normal run
    auto_note.py --dry-run    # report what it would write, write nothing
    auto_note.py --force SID  # ignore the idle threshold for one session
    auto_note.py --exit PID   # the launcher, when Claude exits: note now, clear
    auto_note.py --mark PATH  # /e wrote PATH itself: record it, no model call
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import contextlib

# core/tools/auto-note/auto_note.py -> bench root; BENCH_ROOT overrides.
BENCH_ROOT = Path(os.environ.get("BENCH_ROOT") or Path(__file__).resolve().parents[3]).resolve()
# Bench-specific settings; defaults live in load_config().
CONFIG_PATH = BENCH_ROOT / "config" / "auto-note.json"
STATE_DIR = BENCH_ROOT / "state" / "auto-note"
STATE_PATH = STATE_DIR / "state.json"
LOCK_PATH = STATE_DIR / ".auto-note.lock"
LOG_PATH = STATE_DIR / "auto-note.log"
# Touched at the end of every sweep. The log only records action, so this is
# the only way to tell "ran, nothing due" apart from "never ran".
HEARTBEAT_PATH = STATE_DIR / ".last-run"
# A bench names its own Claude login's config dir in a root `.claude-login`
# file; without one it runs on the default login.
LOGIN_FILE = ".claude-login"


def _raw_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


# ---------------------------------------------------------------------------
# Benches. Sessions of this bench, and of any `other_benches` in the config
# (benches that share this watcher), are noted; a note goes to whichever bench
# holds the convo folder, and is paid for by the login of the session's bench.
# ---------------------------------------------------------------------------


def benches() -> list[Path]:
    """This bench first, then every other configured bench checked out here."""
    out = [BENCH_ROOT]
    for raw in _raw_config().get("other_benches", []):
        b = Path(raw).expanduser()
        if (b / "convos").is_dir() and b.resolve() != BENCH_ROOT:
            out.append(b)
    return out


def login_of(bench: Path) -> Path | None:
    f = bench / LOGIN_FILE
    line = f.read_text().strip() if f.is_file() else ""
    return Path(line).expanduser() if line else None


def convo_dir(name: str) -> Path:
    """The existing convos/<name> in whichever bench has it; this bench's path
    when none does (callers decide whether to create it)."""
    for bench in benches():
        if (bench / "convos" / name).is_dir():
            return bench / "convos" / name
    return BENCH_ROOT / "convos" / name


def convo_names() -> set[str]:
    return {p.name for b in benches() for p in (b / "convos").iterdir()
            if p.is_dir() and not p.name.startswith((".", "_", "~"))
            and p.name != "Templates"}


def bench_of(path: Path) -> Path:
    path = Path(path).resolve()
    for bench in benches():
        if path == bench.resolve() or bench.resolve() in path.parents:
            return bench
    return BENCH_ROOT


def show(path: Path) -> str:
    """Path relative to its bench; other benches get their name as a prefix."""
    bench = bench_of(path)
    rel = str(Path(path).resolve().relative_to(bench.resolve()))
    return rel if bench == BENCH_ROOT else f"{bench.name}/{rel}"


@contextlib.contextmanager
def bench_login(bench: Path):
    """Run the model call on the login of *bench*."""
    login = login_of(bench)
    if login and not login.is_dir():
        login = None
    saved = {k: os.environ.get(k) for k in ("CLAUDE_CONFIG_DIR", "BENCH_LOGIN")}
    os.environ["BENCH_LOGIN"] = bench.name
    if login:
        os.environ["CLAUDE_CONFIG_DIR"] = str(login)
    else:
        os.environ.pop("CLAUDE_CONFIG_DIR", None)
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _escaped(bench: Path) -> str:
    """Claude Code's projects/ folder name for a working directory."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(bench))


def _transcript_dirs() -> list[Path]:
    roots = [Path.home() / ".claude",
             *(l for l in (login_of(b) for b in benches()) if l),
             *([Path(os.environ["CLAUDE_CONFIG_DIR"]).expanduser()]
               if os.environ.get("CLAUDE_CONFIG_DIR") else [])]
    return list(dict.fromkeys(r / "projects" / _escaped(b)
                              for r in roots for b in benches()))


TRANSCRIPT_DIRS = _transcript_dirs()


def transcript_for(sid: str) -> Path:
    """The session's transcript in whichever login/bench recorded it."""
    for d in TRANSCRIPT_DIRS:
        if (d / f"{sid}.jsonl").exists():
            return d / f"{sid}.jsonl"
    return TRANSCRIPT_DIRS[0] / f"{sid}.jsonl"


def bench_of_transcript(path: Path) -> Path:
    for b in benches():
        if path.parent.name == _escaped(b):
            return b
    return BENCH_ROOT


REGISTRY_DIR = Path.home() / ".claude" / "bench-sessions"
# The CLI's own session files (<config>/sessions/<pid>.json: {pid, sessionId})
# locate a window that never typed a `>>topic`, so never got a registry entry.
# The auto-note already knows such a window's topic from the transcript, and
# that is enough to shout into it and to close it (261104).
CONFIG_DIRS = list(dict.fromkeys(d.parents[1] for d in TRANSCRIPT_DIRS))


def cli_session_location(sid: str) -> tuple[str, int | None]:
    """(tty, pid) of the live CLI running session *sid*, read from the CLI's
    own session files; ("", None) when it is not running or sits on no tty."""
    for cfg in CONFIG_DIRS:
        for f in (cfg / "sessions").glob("*.json"):
            try:
                d = json.loads(f.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            if d.get("sessionId") != sid or not d.get("pid"):
                continue
            pid = int(d["pid"])
            try:
                out = subprocess.run(["ps", "-o", "tty=", "-p", str(pid)],
                                     capture_output=True, text=True, timeout=5).stdout.strip()
            except (OSError, subprocess.SubprocessError):
                continue
            if out and out != "??":
                return f"/dev/{out}", pid
    return "", None
# The bench's own convo template wins; core ships the default.
TEMPLATE_PATH = next((p for p in (BENCH_ROOT / "convos" / "Templates" / "Convo Template.md",
                                  BENCH_ROOT / "core" / "skills" / "note" / "template.md")
                      if p.is_file()), BENCH_ROOT / "core" / "skills" / "note" / "template.md")
# A session that never declared `>>topic` still gets a note; the model files it, and
# this is the folder when it names none (config "undeclared_topic").
UNDECLARED_TOPIC = "the-bench"

# Note success/failure notices and terminal reminders (config "notifications");
# main() copies it here. Tab-close warnings ignore it.
NOTE_NOTIFICATIONS_ENABLED = True

# macOS banners only (config "banners"). Off leaves the pink terminal line
# and the parked notice alone, and silences tab-close banners too.
BANNERS_ENABLED = True


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
    cfg = _raw_config()
    cfg.setdefault("default_idle_minutes", 60)
    cfg.setdefault("overrides", {})
    cfg.setdefault("min_note_interval_minutes", 120)
    cfg.setdefault("lookback_hours", 24)
    cfg.setdefault("max_transcript_chars", 60000)
    cfg.setdefault("enabled", True)
    cfg.setdefault("notifications", True)
    cfg.setdefault("banners", True)
    # `--exit`: a window the user is closing gets a fresh note if it said at least
    # this much since the last one. Lower than the sweep's gate on purpose: the
    # window is going away, this is the last chance.
    cfg.setdefault("exit_min_msgs_threshold", 2)
    cfg.setdefault("autoclose", {})
    cfg["autoclose"].setdefault("enabled", True)
    cfg["autoclose"].setdefault("idle_minutes", 60)
    cfg.setdefault("topic_aliases", {})
    cfg.setdefault("undeclared_topic", "the-bench")
    cfg.setdefault("model", "haiku")
    return cfg


def idle_threshold(cfg: dict, topic: str) -> int:
    raw = cfg["overrides"].get(topic)
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
# Shorthand topics the user types -> the real convo folder (config
# "topic_aliases"); without it the sweep would recreate a merged folder.
TOPIC_ALIASES: dict[str, str] = {}
SKIP_PREFIXES = ("<system-reminder", "<command-", "<local-command",
                 "Caveat:", "[Request interrupted")


def _epoch(stamp) -> float | None:
    """ISO-8601 timestamp from a transcript entry to epoch seconds."""
    if not isinstance(stamp, str):
        return None
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _text_of(content) -> str:
    """Flatten a message content field (string, or list of blocks) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [b.get("text", "") for b in content
                 if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(p for p in parts if p)
    return ""


def parse_transcript(path: Path, max_chars: int) -> dict | None:
    """Pull the convo topic (None when the session never declared one), the
    user-message count, and a readable digest."""
    topic = None
    user_msgs = 0
    turns: list[str] = []
    last_ts = None  # epoch of the last real turn; see `evaluate`
    done = False    # last non-sidechain record is an assistant turn that ended cleanly

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
            continue  # subagent chatter, not the user's conversation
        etype = entry.get("type")
        if etype not in ("user", "assistant"):
            continue
        # A pending tool result (type user, no text) or a tool_use stop means
        # Claude is still mid-task; only a clean end_turn counts as finished.
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
                    topic = TOPIC_ALIASES.get(topic, topic)
            turns.append(f"USER: {text}")
        else:
            turns.append(f"CLAUDE: {text}")

    digest = "\n\n".join(turns)
    if len(digest) > max_chars:
        digest = "[…earlier turns trimmed…]\n\n" + digest[-max_chars:]

    return {"topic": topic, "user_msgs": user_msgs, "digest": digest,
            "last_ts": last_ts, "done": done}


# ---------------------------------------------------------------------------
# Note generation
# ---------------------------------------------------------------------------


def convo_folders() -> list[str]:
    """Convo folders that already exist, as filing candidates.

    Only existing folders: the model picks where a note belongs, it never
    invents a new convo. Anything it returns that is not in this list is
    ignored and the session's own `>>` topic wins.
    """
    return sorted(convo_names())


def resolve_folder(name: str, folders: list[str]) -> str | None:
    """Match a convo name the model returned back to a real folder.

    Compared on letters and digits only, so case, punctuation and stray
    whitespace in a folder name cannot strand it. Returning the real directory
    name matters: `write_note` builds the path straight from it, so a near-miss
    would quietly create a second folder beside the one that already exists.
    """
    flat = lambda s: re.sub(r"[^a-z0-9]+", "", s.lower())  # noqa: E731
    target = flat(name)
    if not target:
        return None
    for folder in folders:
        if flat(folder) == target:
            return folder
    return None


def build_prompt(topic: str | None, digest: str, template: str, appending: bool,
                 folders: list[str] | None = None) -> str:
    shape = (
        "Return ONLY the body sections (no `# heading`, no `**Date:**` line) — "
        "it will be appended under an existing note for today."
        if appending else
        "Fill in this template exactly, keeping its heading structure:\n\n"
        f"{template}"
    )
    filing = ""
    if folders and topic:
        filing = (
            "\nThe session opened by declaring `" + topic + "`, but work drifts. "
            "Decide where this note actually belongs from the convos that exist:\n\n"
            + ", ".join(f"`{f}`" for f in folders)
            + f"\n\nKeep `{topic}` unless the bulk of the session is clearly about a "
              "different one — a session that wandered but did its real work under the "
              "declared topic still belongs there. Judge by where the work landed, not "
              "by what got mentioned in passing.\n"
        )
    elif folders:
        filing = (
            "\nThis session never declared a convo, so decide where the note belongs "
            "from the convos that exist:\n\n"
            + ", ".join(f"`{f}`" for f in folders)
            + "\n\nPick the one the work actually landed in, not one mentioned in "
              "passing. Your TOPIC line is the filing decision.\n"
        )
    header = (f"You are writing a session note for the Bench convo `{topic}`."
              if topic else "You are writing a session note for a Bench session.")
    return f"""{header}

Below is the transcript of a Claude Code session that has gone idle. Summarise
what actually happened: decisions made, work done, files touched, action items,
and anything left open. Be specific — name files, tickets, numbers. Do not pad,
do not invent, do not editorialise. If a section has nothing real to put in it,
write a single line saying so rather than making something up.
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


MODEL = "haiku"
CLAUDE_TIMEOUT = 300


def call_model(prompt: str) -> str:
    """Write the note. A bench with an AI profile (lib/bench_ai.py) uses it,
    operation `notes`; otherwise `claude -p` with config "model" on the login
    already set by bench_login(). ANTHROPIC_API_KEY is stripped so the CLI uses
    the subscription login rather than billing the API."""
    if (BENCH_ROOT / "lib" / "bench_ai.py").is_file():
        sys.path.insert(0, str(BENCH_ROOT / "lib"))
        from bench_ai import generate as ai_generate
        return ai_generate(prompt, "notes", max_tokens=1200)
    import shutil
    exe = shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude")
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    cmd = [exe, "-p", "--model", MODEL, "--output-format", "text"]
    last_err = None
    for attempt in range(2):
        try:
            proc = subprocess.run(cmd, input=prompt, env=env, capture_output=True,
                                  text=True, timeout=CLAUDE_TIMEOUT, cwd=str(STATE_DIR))
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
    """Pull the TOPIC and SLUG lines off the front. Returns (topic, slug, body).

    Both are optional and order-independent: an older prompt, or a model that
    drops the topic line, still yields a usable slug and body.
    """
    lines = reply.splitlines()
    topic, slug = None, "session"
    for _ in range(2):
        if not lines:
            break
        head = lines[0].strip()
        if head.upper().startswith("TOPIC:"):
            candidate = re.sub(r"[^a-z0-9-]+", "-",
                               head.split(":", 1)[1].strip().lower()).strip("-")
            topic = candidate or None
        elif head.upper().startswith("SLUG:"):
            candidate = re.sub(r"[^a-z0-9]+", "-",
                               head.split(":", 1)[1].strip().lower()).strip("-")
            if candidate:
                slug = "-".join(candidate.split("-")[:3])
        else:
            break
        lines = lines[1:]
    return topic, slug, "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def today_notes(topic: str, ended: datetime) -> list[Path]:
    """Existing notes filed under the session's own date, newest name last.

    Dated by when the session actually happened, not when the watcher woke up —
    a session that went quiet at 23:50 must not land in tomorrow's note.
    """
    folder = convo_dir(topic)
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.glob(f"{ended:%y%m%d}*.md")
                  if not p.name.startswith("_memory"))


def write_note(topic: str, slug: str, body: str, ended: datetime,
               dry_run: bool) -> tuple[Path, bool]:
    """Write or append the note. Returns (path, appended)."""
    folder = convo_dir(topic)
    stamp = f"{ended:%y%m%d}"
    existing = today_notes(topic, ended)

    if existing:
        target, appended = existing[0], True
        chunk = (f"\n\n---\n\n#### Auto-note — session idle since "
                 f"{ended:%H:%M}\n\n{body}\n")
        if not dry_run:
            with target.open("a") as fh:
                fh.write(chunk)
    else:
        target, appended = folder / f"{stamp}-{slug}.md", False
        if not dry_run:
            folder.mkdir(parents=True, exist_ok=True)
            header = (f"# {topic}\n**Date:** {stamp}\n"
                      f"<!-- written automatically: session idle since "
                      f"{ended:%H:%M} -->\n\n")
            target.write_text(header + body + "\n")

    return target, appended


PINK = "\033[38;5;213m"


def tty_live(tty_path: str, pid: int | None = None, topic: str = "") -> bool:
    """True if *this session's* Claude CLI is still attached to this tty.

    macOS recycles ttys numbers as windows close and open, so a registry entry
    written this morning can point at a completely different Claude window by
    the afternoon (the same ttys number served two different windows in one day).
    Match on the CLI pid the hook recorded; for older entries without one, fall
    back to the `-n <topic>` in the command line. Any `claude` at all is not enough.
    """
    if not tty_path or not os.path.exists(tty_path):
        return False
    dev = tty_path.removeprefix("/dev/")
    try:
        out = subprocess.run(["ps", "-eo", "pid=,tty=,command="],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3 or parts[1] != dev or "claude" not in parts[2]:
            continue
        if pid is not None:
            if int(parts[0]) == pid:
                return True
            continue
        if topic and f"-n {topic}" in parts[2]:
            return True
    return False


def write_pink(session_id: str, message: str) -> bool:
    """One pink line into the session's window. Returns True if it landed."""
    reg = REGISTRY_DIR / f"{session_id}.json"
    tty_path, pid, topic = "", None, ""
    if reg.exists():
        try:
            entry = json.loads(reg.read_text())
            tty_path = entry.get("tty", "") or ""
            pid = entry.get("pid") or None
            topic = entry.get("topic", "") or ""
        except (json.JSONDecodeError, OSError):
            pass
    if not tty_live(tty_path, pid, topic):
        tty_path, pid = cli_session_location(session_id)   # no `>>` ever typed
        if not pid:
            return False
    try:
        with open(tty_path, "w") as fh:
            fh.write(f"\n{PINK}{message}\033[0m\n")
        return True
    except OSError as exc:
        log(f"WARNING: tty write to {tty_path} failed: {exc}")
        return False


def banner(topic: str, message: str) -> None:
    """macOS notification, the one channel that survives a closed window.

    Follows the bench's existing pattern (spanish-vocab-clipper, web-clipper):
    osascript, no extra dependency. launchd runs this agent inside the Aqua
    session, so the banner is allowed to post. Best effort — a failure here must
    never stop the note itself, which is already written by the time we are called.
    """
    if not BANNERS_ENABLED:
        return
    body = message.replace("[auto-note] ", "").replace('"', "'").replace("\\", "")
    title = "auto-note"
    sub = topic.replace('"', "'")
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{body}" with title "{title}" subtitle "{sub}"'],
            check=False, capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        log(f"WARNING: banner failed for {topic}: {exc}")


def notify(session_id: str, message: str, topic: str = "") -> None:
    """Tell the originating terminal, three ways over.

    The tty write lands immediately but a TUI redraw can wipe it, so the same
    message is also parked as a notice the UserPromptSubmit hook injects the next
    time the user types in that window.

    Since 260826 there is a third channel: a macOS notification banner. The tty
    write only lands if that window still exists — 23 of the first 47 notes were
    written into a closed window and never showed anything, and the notice file
    only surfaces if the user happens to reopen that same session. The banner does
    not depend on either.

    ASCII only, the two text channels. Fixed 260823: the message used to open with 📝 and
    carry an em dash, and the hook's systemMessage rendered in the Claude TUI as
    a single "ð" — the first byte of the emoji's UTF-8, with the rest of the line
    thrown away. Call sites are plain ASCII now, but a note path or an exception
    string can still smuggle anything in, so it is flattened here too.
    """
    if not NOTE_NOTIFICATIONS_ENABLED:
        return
    message = message.encode("ascii", "replace").decode("ascii")
    if not write_pink(session_id, message):
        log(f"no live tty for {session_id[:8]} — notice file + banner only")

    try:
        REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
        (REGISTRY_DIR / f"{session_id}.notice").write_text(message)
    except OSError as exc:
        log(f"WARNING: could not park notice for {session_id[:8]}: {exc}")

    banner(topic or session_id[:8], message)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def evaluate(path: Path, cfg: dict, state: dict, force: bool) -> dict | None:
    """Decide whether this transcript is due for a note. No model calls here."""
    session_id = path.stem

    parsed = parse_transcript(path, cfg["max_transcript_chars"])
    if parsed is None:
        return None  # unreadable transcript
    if parsed["user_msgs"] < 1:
        return None  # no user messages to note

    # Idleness comes from the last real turn, NOT the file mtime (260825).
    # A session that is merely open keeps its transcript touched by attachment
    # and hook records, so mtime never went stale and nothing was ever due.
    ended = parsed["last_ts"] or path.stat().st_mtime
    idle_min = (time.time() - ended) / 60

    threshold = idle_threshold(cfg, parsed["topic"])
    if not force and idle_min < threshold:
        return None

    prior = state["noted"].get(session_id)
    if prior and not force:
        new_msgs = parsed["user_msgs"] - prior.get("user_msgs", 0)
        if new_msgs <= 0:
            return None  # already noted, nothing new said since
        # Don't re-note the same session too frequently; check min_note_interval
        wrote_at = _epoch(prior.get("at"))
        if (wrote_at is not None
                and (time.time() - wrote_at) / 60 < int(cfg["min_note_interval_minutes"])):
            return None

    return {"session_id": session_id, "idle_min": idle_min,
            "threshold": threshold, "ended": datetime.fromtimestamp(ended),
            **parsed}


def generate(job: dict, state: dict, template: str, dry_run: bool) -> Path | None:
    """Write the note for one due session. Returns the note's path relative to
    the bench, or None when the model call or the write failed."""
    session_id, topic = job["session_id"], job["topic"]
    log(f"{session_id[:8]} topic={topic or '(undeclared)'} idle={job['idle_min']:.0f}m "
        f"(threshold {job['threshold']}m) msgs={job['user_msgs']}"
        + (" [DRY RUN]" if dry_run else ""))

    try:
        folders = convo_folders()
        appending = bool(topic and today_notes(topic, job["ended"]))
        # The session's own bench pays for its note.
        with bench_login(bench_of_transcript(transcript_for(session_id))):
            reply = call_model(
                build_prompt(topic, job["digest"], template, appending, folders))
        picked, slug, body = split_header(reply)
        # The declared `>>` topic is the default; the model may reroute a session
        # that drifted, but only to a convo that already exists. Anything else it
        # returns is dropped rather than creating a folder nobody asked for.
        filed = topic or UNDECLARED_TOPIC
        if picked:
            resolved = resolve_folder(TOPIC_ALIASES.get(picked, picked), folders)
            if resolved and resolved != topic:
                log(f"  filed {topic or '(undeclared)'} -> {resolved}")
                filed = resolved
            elif not resolved:
                log(f"  ignored suggested topic {picked!r} (no such convo)")
        if not topic and filed == UNDECLARED_TOPIC:
            log(f"  no topic and none picked; filed under {UNDECLARED_TOPIC}")
        target, appended = write_note(filed, slug, body, job["ended"], dry_run)
    except Exception as exc:  # noqa: BLE001 — must surface, never crash the sweep
        log(f"ERROR: auto-note failed for {topic or '(undeclared)'} ({session_id[:8]}): {exc}")
        if not dry_run:
            notify(session_id,
                   f"[auto-note] FAILED for {topic}: {exc}. "
                   f"Run /note manually. Log: {LOG_PATH}", topic)
        return None

    rel = show(target)
    verb = "appended to" if appended else "wrote"
    log(f"  {verb} {rel}")

    if not dry_run:
        notify(session_id,
               f"[auto-note] {int(job['idle_min'])}m idle: {verb} {rel} "
               f"(not committed, not posted to a ticket). Say /note to redo.", topic)
        state["noted"][session_id] = {
            "topic": filed, "file": str(rel), "user_msgs": job["user_msgs"],
            "at": datetime.now().isoformat(timespec="seconds"),
        }
        save_state(state)
    return rel


# ---------------------------------------------------------------------------
# Auto-close (260826)
# ---------------------------------------------------------------------------
#
# A window that has had its note written, has said nothing since, is not
# computing anything, and whose last turn ended cleanly, is finished. After
# `autoclose.idle_minutes` the tab's shell gets SIGHUP, no warning first (the
# warning was dropped 260925: nothing changed, so nothing to say). Cursor and
# Warp both close a terminal tab when its shell exits, so the tab goes away on
# its own. Any prompt before that resets the clock (the hook bumps last_prompt).
# The conversation is not lost: `claude --resume <session_id>` brings it back.


def tty_cpu(dev: str) -> float:
    """Total CPU seconds of every process on a tty. Grows only while something
    there is actually working — a Claude waiting at the prompt is flat."""
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
        t = parts[1]
        try:
            h, m, sec = (["0", "0"] + t.split(":"))[-3:]
            total += int(h) * 3600 + int(m) * 60 + float(sec)
        except ValueError:
            pass
    return total


def cli_pid_on_tty(tty_path: str, topic: str) -> int | None:
    """Find the Claude CLI pid on a tty. Registry entries written before the
    260826 hook change carry no `pid` — 48 of 53 of them on the day auto-close
    shipped — and close_window bailed on every one, so those windows were
    "closed" in the log every 5 minutes forever and never actually closed."""
    dev = (tty_path or "").removeprefix("/dev/")
    if not dev:
        return None
    try:
        out = subprocess.run(["ps", "-eo", "pid=,tty=,command="],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    match = None
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3 or parts[1] != dev or "claude" not in parts[2]:
            continue
        if topic and f"-n {topic}" in parts[2]:
            return int(parts[0])
        match = int(parts[0])
    return match


def tty_chain(claude_pid: int) -> list[int]:
    """Every process from the CLI up to the tab's login shell: claude, the
    expect relay, the launcher's subshell, the interactive zsh. The shell's
    parent is the host's pty broker (Cursor Helper, Warp), which is off-tty,
    and that is where the walk stops."""
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
    """Close the tab and prove it. HUP to the login shell was the whole method
    from 260826, and on 260915 it closed nothing: a tab's zsh, expect and
    claude were all still running the next afternoon while the log said
    "autoclose formula". Now: HUP the shell, then TERM the whole chain, then
    KILL it, checking after each step, and report closed only when every pid
    is gone. Cursor and Warp drop the tab once the shell process is dead."""
    topic = entry.get("topic")
    pid = entry.get("pid") or cli_pid_on_tty(entry.get("tty", ""), topic or "")
    if not pid:
        log(f"WARNING: no pid for {topic} — cannot close")
        return False
    chain = tty_chain(int(pid)) or [int(pid)]
    steps = (("HUP", [chain[-1]], 1), ("TERM", chain, 15), ("KILL", chain, 9))
    left = chain
    for name, targets, sig in steps:
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


def frozen(pid) -> bool:
    """`/freeze` (core/tools/freeze/freeze.sh) marks a tab as never auto-closed. The
    mark holds the CLI's start time, so a recycled pid does not inherit it."""
    if not pid:
        return False
    f = REGISTRY_DIR / "frozen" / str(pid)
    try:
        want = f.read_text().strip()
        got = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)], capture_output=True,
                             text=True).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    if " ".join(got.split()) == want:
        return True
    f.unlink(missing_ok=True)
    return False


def autoclose(cfg: dict, state: dict, parsed_by_sid: dict, dry_run: bool) -> None:
    ac = cfg["autoclose"]
    if not ac["enabled"] or not REGISTRY_DIR.is_dir():
        return
    pending = state.setdefault("close_pending", {})
    cpu_seen = state.setdefault("cpu", {})
    now = time.time()

    # One CLI can host several sessions in a row (/clear, /resume, "write note
    # and restart"), each with its own registry entry and the same pid. Only the
    # newest entry per pid speaks for the window: on 261023 the 3-hour-old
    # entries of finished sessions closed four tabs that were busy in a newer one.
    entries, newest = [], {}
    for reg in REGISTRY_DIR.glob("*.json"):
        try:
            entry = json.loads(reg.read_text())
            mtime = reg.stat().st_mtime
        except (json.JSONDecodeError, OSError):
            continue
        entries.append((reg, entry))
        pid = entry.get("pid")
        if pid and mtime > newest.get(pid, (0, ""))[0]:
            newest[pid] = (mtime, reg.stem)

    # A window that never typed `>>topic` has no registry entry. Once its note
    # is written the topic is known, so find the CLI through its own session
    # file and judge the window like any other (261104: a window
    # of another bench sat open for six days with its note long filed).
    registered = {reg.stem for reg, _ in entries}
    for sid, noted in state.get("noted", {}).items():
        parsed = parsed_by_sid.get(sid)
        if sid in registered or not parsed or not noted.get("file"):
            continue
        tty_path, pid = cli_session_location(sid)
        if not pid:
            continue
        entry = {"session_id": sid, "topic": noted.get("topic", ""), "tty": tty_path,
                 "pid": pid, "cwd": "", "unregistered": True}
        entries.append((REGISTRY_DIR / f"{sid}.json", entry))
        mtime = parsed["last_ts"] or 0
        if mtime > newest.get(pid, (0, ""))[0]:
            newest[pid] = (mtime, sid)

    for reg, entry in entries:
        sid = reg.stem
        tty_path, pid, topic = entry.get("tty", ""), entry.get("pid"), entry.get("topic", "")
        if pid and newest[pid][1] != sid:
            pending.pop(sid, None); cpu_seen.pop(sid, None)
            continue
        if not tty_live(tty_path, pid, topic):
            pending.pop(sid, None); cpu_seen.pop(sid, None)
            continue
        if frozen(pid):
            pending.pop(sid, None)
            continue

        dev = tty_path.removeprefix("/dev/")
        cpu_now = tty_cpu(dev)
        cpu_prev = cpu_seen.get(sid)
        cpu_seen[sid] = cpu_now
        working = cpu_prev is None or cpu_now < 0 or (cpu_now - cpu_prev) > 5.0  # idle TUI ticks ~0.7s per sweep

        parsed = parsed_by_sid.get(sid)
        noted = state["noted"].get(sid) or {}
        idle_min = (now - (parsed["last_ts"] if parsed and parsed["last_ts"] else 0)) / 60

        # A turn that never ended cleanly (interrupted, hung tool) left done
        # False forever, so its tab never closed: 6268911b sat open 261114-15
        # with its note filed. Past twice the idle limit, a flat-CPU window is
        # finished whatever its last turn did.
        ended = parsed is not None and (parsed["done"] or idle_min >= 2 * ac["idle_minutes"])
        ready = (parsed is not None and ended and not working
                 and noted.get("file") and noted.get("user_msgs", 0) >= parsed["user_msgs"]
                 and idle_min >= ac["idle_minutes"])

        if not ready:
            if sid in pending:
                log(f"  autoclose cancelled for {topic} ({sid[:8]}): activity resumed")
                pending.pop(sid, None)
            continue

        warn = pending.setdefault(sid, {"at": now, "topic": topic})
        if warn.get("failed", 0) >= 2:
            continue   # gave up on this window; see close_window's WARNING

        log(f"  autoclose {topic} ({sid[:8]}) after {int(idle_min)}m idle"
            f"{' (no >> typed; located via CLI session file)' if entry.get('unregistered') else ''}"
            f" - resume with: claude --resume {sid}")
        if dry_run:
            continue
        if close_window(entry):
            banner(topic, f"[auto-note] closed {topic} tab after {int(idle_min)}m idle. "
                          f"Resume: claude --resume {sid[:8]}...")
            pending.pop(sid, None); cpu_seen.pop(sid, None)
            reg.unlink(missing_ok=True)
            (REGISTRY_DIR / f"{sid}.notice").unlink(missing_ok=True)
        else:
            # Never retry a failing close every sweep — that is what turned one
            # stuck window into a wall of repeated pink lines (260826).
            warn["failed"] = warn.get("failed", 0) + 1
            if warn["failed"] >= 2:
                log(f"  giving up on closing {topic} ({sid[:8]}) — close it by hand")
                (REGISTRY_DIR / f"{sid}.notice").unlink(missing_ok=True)
    save_state(state)


# Plain shell tabs (261115). A terminal tab with only an idle login shell in it
# (no Claude, no server, nothing running) closes after
# `autoclose.shell_idle_minutes` (default 4 h) since its last input or output.
# Only tabs of a terminal app's pty host are touched (Cursor, Warp, Terminal).
SHELL_HOSTS = ("pty-host", "Warp", "Terminal.app")


def close_idle_shells(cfg: dict, dry_run: bool) -> None:
    limit = cfg["autoclose"].get("shell_idle_minutes", 240)
    try:
        out = subprocess.run(["ps", "-axo", "pid=,ppid=,tty=,comm="],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return
    procs = {}
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) == 4:
            procs[int(parts[0])] = (int(parts[1]), parts[2], parts[3])
    parents = {pp for pp, _, _ in procs.values()}
    now = time.time()
    for pid, (ppid, tty, comm) in procs.items():
        if not comm.endswith("zsh") and not comm.endswith("bash"):
            continue
        if pid in parents or tty in ("??", "") or ppid not in procs:
            continue
        if not any(h in procs[ppid][2] for h in SHELL_HOSTS):
            continue
        try:
            st = os.stat(f"/dev/{tty}")
        except OSError:
            continue
        idle_min = (now - max(st.st_atime, st.st_mtime)) / 60
        if idle_min < limit:
            continue
        log(f"  close idle shell tab {tty} (pid {pid}) after {int(idle_min)}m idle")
        if dry_run:
            continue
        try:
            os.kill(pid, signal.SIGHUP)
        except OSError:
            pass


def prune_registry(days: int = 7) -> None:
    """Drop session registry entries older than `days`. Undrained notices stay."""
    if not REGISTRY_DIR.is_dir():
        return
    cutoff = time.time() - days * 86400
    for entry in REGISTRY_DIR.glob("*.json"):
        try:
            if entry.stat().st_mtime < cutoff:
                entry.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Closing a window by hand (260916): `/exit` and `/e`
# ---------------------------------------------------------------------------
#
# Waiting three hours for the sweep was the only way a finished tab got its note
# and went away, and nothing told the user whether either had happened. Now the
# bench's terminal launcher (if it has one) calls `--exit <cli pid>` the moment Claude exits:
# the note is written right there, one line says where it went, and the shell
# exits so the tab closes. `/e` (skills/e) goes one step further: Claude writes
# the note itself, calls `--mark`, and ends with the launcher's close word, which
# the launcher turns into /exit.


def registry_entries_for_pid(cli_pid: int) -> list[tuple[Path, dict]]:
    found = []
    for reg in REGISTRY_DIR.glob("*.json"):
        try:
            entry = json.loads(reg.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if entry.get("pid") == cli_pid:
            found.append((reg, entry))
    return found


def wait_lock(max_wait: int = 90) -> bool:
    """Take the sweep's lock, waiting for a running sweep to finish."""
    deadline = time.time() + max_wait
    while LOCK_PATH.exists() and time.time() - LOCK_PATH.stat().st_mtime < 3600:
        if time.time() > deadline:
            return False
        time.sleep(1)
    LOCK_PATH.touch()
    return True


def exit_note(cli_pid: int, cfg: dict) -> int:
    """`--exit PID`. Exit code 0: noted, or nothing to note, the tab may close.
    1: the note failed, the tab must stay open so the failure is seen."""
    entries = registry_entries_for_pid(cli_pid)
    if not entries:
        print("[auto-note] no convo in this window (no >> topic) - nothing to note")
        return 0
    # /clear keeps the pid and starts a new session; the newest one is the live one.
    _, entry = max(entries, key=lambda t: t[1].get("last_prompt") or 0)
    sid, topic = entry["session_id"], entry.get("topic", "")
    path = transcript_for(sid)
    if not wait_lock():
        print("[auto-note] a sweep has held the lock for 90s - run /note by hand")
        return 1
    rc = 0
    try:
        state = load_state()
        parsed = parse_transcript(path, cfg["max_transcript_chars"]) if path.exists() else None
        if not parsed or parsed["user_msgs"] < 1:
            print(f"[auto-note] {topic}: no user messages to note")
        else:
            prior = state["noted"].get(sid) or {}
            new = parsed["user_msgs"] - prior.get("user_msgs", 0)
            if prior.get("file") and new < int(cfg["exit_min_msgs_threshold"]):
                print(f"[auto-note] {topic}: already noted in {prior['file']}")
            else:
                ended = parsed["last_ts"] or path.stat().st_mtime
                job = {"session_id": sid, "idle_min": (time.time() - ended) / 60,
                       "threshold": 0, "ended": datetime.fromtimestamp(ended), **parsed}
                log(f"exit: {sid[:8]} topic={topic or '(undeclared)'} msgs={parsed['user_msgs']}")
                rel = generate(job, state, TEMPLATE_PATH.read_text(), dry_run=False)
                if rel is None:
                    print(f"[auto-note] {topic}: note FAILED - see {LOG_PATH}")
                    rc = 1
                else:
                    print(f"[auto-note] {topic}: wrote {rel} (not committed, not posted to a ticket)")
    finally:
        LOCK_PATH.unlink(missing_ok=True)
    if rc == 0:
        for reg, _ in entries:
            reg.unlink(missing_ok=True)
            (REGISTRY_DIR / f"{reg.stem}.notice").unlink(missing_ok=True)
    return rc


def mark_note(note_path: str, cfg: dict, dry_run: bool) -> int:
    """`--mark PATH`, run from inside the session by /e after it wrote PATH.
    Finds the session by walking up from this process to the Claude CLI (the
    registry knows the CLI's pid) and records the note, so neither the sweep
    nor `--exit` writes a second one."""
    note = Path(note_path)
    if not note.is_absolute():
        note = Path.cwd() / note
        if not note.is_file():
            note = BENCH_ROOT / note_path
    if not note.is_file():
        print(f"[auto-note] no such note: {note_path}"); return 1
    if note.parent.parent.name != "convos":
        print(f"[auto-note] {note_path} is not a convo note"); return 1
    rel = show(note)
    pid, entries = os.getpid(), []
    for _ in range(12):
        entries = registry_entries_for_pid(pid)
        if entries:
            break
        try:
            out = subprocess.run(["ps", "-o", "ppid=", "-p", str(pid)],
                                 capture_output=True, text=True, timeout=5).stdout.strip()
            pid = int(out)
        except (OSError, subprocess.SubprocessError, ValueError):
            break
        if pid <= 1:
            break
    if not entries:
        print("[auto-note] this window is not a registered convo session - nothing marked")
        return 1
    _, entry = max(entries, key=lambda t: t[1].get("last_prompt") or 0)
    sid = entry["session_id"]
    path = transcript_for(sid)
    parsed = parse_transcript(path, cfg["max_transcript_chars"]) if path.exists() else None
    msgs = parsed["user_msgs"] if parsed else 0
    record = {"topic": note.parent.name or entry.get("topic", ""),
              "file": rel, "user_msgs": msgs,
              "at": datetime.now().isoformat(timespec="seconds"), "by": "/e"}
    if dry_run:
        print(f"[auto-note] would mark {sid[:8]} as noted: {record}")
        return 0
    if not wait_lock():
        print("[auto-note] a sweep has held the lock for 90s - not marked"); return 1
    try:
        state = load_state()
        state["noted"][sid] = record
        save_state(state)
    finally:
        LOCK_PATH.unlink(missing_ok=True)
    log(f"marked {sid[:8]} noted by /e: {rel}")
    print(f"[auto-note] marked: {rel}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be written, write nothing")
    ap.add_argument("--force", metavar="SESSION_ID",
                    help="ignore the idle threshold for one session id")
    ap.add_argument("--backfill", action="store_true",
                    help="on a fresh state file, actually note the already-idle "
                         "sessions instead of seeding them as done")
    ap.add_argument("--exit", metavar="CLI_PID", type=int,
                    help="Claude just exited in the window whose CLI had this pid: "
                         "note it now, print one line, forget the window")
    ap.add_argument("--mark", metavar="NOTE_PATH",
                    help="record NOTE_PATH as this session's note (used by /e)")
    args = ap.parse_args()

    cfg = load_config()
    global NOTE_NOTIFICATIONS_ENABLED, BANNERS_ENABLED, MODEL, UNDECLARED_TOPIC
    NOTE_NOTIFICATIONS_ENABLED = bool(cfg["notifications"])
    BANNERS_ENABLED = bool(cfg["banners"])
    MODEL = str(cfg["model"])
    UNDECLARED_TOPIC = str(cfg["undeclared_topic"])
    TOPIC_ALIASES.update({k: v for k, v in cfg["topic_aliases"].items() if not k.startswith("_")})
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if args.exit:
        return exit_note(args.exit, cfg)
    if args.mark:
        return mark_note(args.mark, cfg, args.dry_run)
    if not cfg["enabled"] and not args.force:
        log(f"disabled in {CONFIG_PATH.name} — nothing to do")
        return 0

    tdirs = [d for d in TRANSCRIPT_DIRS if d.is_dir()]
    if not tdirs:
        log(f"ERROR: no transcript dir found (first tried: {TRANSCRIPT_DIRS[0]})")
        return 1

    # Single-writer lock. A stale lock (>1h) is assumed dead and reclaimed.
    if LOCK_PATH.exists():
        age = time.time() - LOCK_PATH.stat().st_mtime
        if age < 3600:
            log("another run is in progress — skipping")
            return 0
        log(f"reclaiming stale lock ({age / 60:.0f}m old)")
    LOCK_PATH.touch()

    try:
        prune_registry()
        state = load_state()
        template = TEMPLATE_PATH.read_text()
        cutoff = time.time() - cfg["lookback_hours"] * 3600

        candidates = [p for d in tdirs for p in d.glob("*.jsonl")
                      if p.stat().st_mtime >= cutoff
                      or (args.force and p.stem == args.force)]

        jobs, parsed_by_sid = [], {}
        for path in sorted(candidates, key=lambda p: p.stat().st_mtime):
            job = evaluate(path, cfg, state,
                           force=bool(args.force and path.stem == args.force))
            if job:
                jobs.append(job)
            if path.stem in {r.stem for r in REGISTRY_DIR.glob("*.json")}:
                parsed = parse_transcript(path, cfg["max_transcript_chars"])
                if parsed:
                    parsed_by_sid[path.stem] = parsed

        # First run on a fresh state file would otherwise backfill every session
        # that has gone quiet in the last 24h — a pile of notes for work that was
        # very likely already written up by hand. Seed instead, and say so.
        first_run = not state["noted"]
        if first_run and jobs and not args.backfill and not args.force:
            log(f"first run — seeding {len(jobs)} already-idle session(s) as done "
                f"(re-run with --backfill to write them for real):")
            for job in jobs:
                log(f"  skipped {job['session_id'][:8]} topic={job['topic']} "
                    f"idle={job['idle_min']:.0f}m")
                if not args.dry_run:
                    state["noted"][job["session_id"]] = {
                        "topic": job["topic"], "file": None,
                        "user_msgs": job["user_msgs"], "seeded": True,
                        "at": datetime.now().isoformat(timespec="seconds"),
                    }
            if not args.dry_run:
                save_state(state)
            return 0

        for job in jobs:
            generate(job, state, template, args.dry_run)
        autoclose(cfg, load_state(), parsed_by_sid, args.dry_run)
        if cfg["autoclose"]["enabled"]:
            close_idle_shells(cfg, args.dry_run)
    finally:
        LOCK_PATH.unlink(missing_ok=True)
        if not args.dry_run:
            try:
                HEARTBEAT_PATH.write_text(
                    f"{datetime.now():%Y-%m-%d %H:%M:%S} "
                    f"candidates={len(candidates)} due={len(jobs)}\n")
            except (OSError, NameError):
                pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
