#!/usr/bin/python3
"""Test every Homebrew tool the bench uses after each Homebrew change; repair what broke.

Runs under the system Python (/usr/bin/python3) so a Homebrew upgrade can never
break it. On each run:

1. Waits for any running `brew` to finish.
2. Finds the Homebrew commands bench code calls: absolute /opt/homebrew/bin/<name>
   paths, quoted command names ("ffmpeg"), and shell command positions, in every
   bench in BENCHES plus LaunchAgents and ~/.hammerspoon/init.lua. Commands seen
   on earlier runs stay on the list, so one that vanished is still checked.
3. Tests each one: real work for the tools in SMOKE (a 1 s encode, a PDF render),
   a version probe for the rest.
4. A tool that worked before (or fails with a missing file or library) and fails
   now gets repaired: install if gone → link → install missing deps → reinstall.
   Tested again after each step.
5. Still broken → Slack DM once per broken version. Repaired → log only.

Python and its packages are python-repin's job; python* and pip* are skipped.
One instance per Mac covers every bench; settings in config.json next to this file.
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request

HOME = os.path.expanduser("~")
HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
try:
    with open(os.path.join(HERE, "config.json")) as _f:
        CONFIG = json.load(_f)
except (FileNotFoundError, json.JSONDecodeError):
    CONFIG = {}
# Other bench checkouts whose code this instance also scans.
BENCHES = [BENCH] + [p for p in (os.path.expanduser(b) for b in CONFIG.get("other_benches", []))
                     if os.path.isdir(p)]
STATE_FILE = os.path.join(HERE, "state.json")
LOCK_FILE = os.path.join(HERE, ".lock")
KEYS_ENV = os.path.join(BENCH, "config/keys.env")
BREW = "/opt/homebrew/bin/brew"
BREW_BIN = "/opt/homebrew/bin"
PREFIX = "/opt/homebrew"
HS_INIT = os.path.join(HOME, ".hammerspoon/init.lua")
LAUNCH_AGENTS = os.path.join(HOME, "Library/LaunchAgents")

CODE_EXT = {".py", ".sh", ".zsh", ".bash", ".command", ".js", ".mjs", ".ts",
            ".lua", ".plist", ".applescript"}
SCAN_DIRS = ("actions", "tools", "scripts", "lib", "config", ".claude")
SKIP_DIRS = {"__pycache__", "node_modules", ".git", ".venv", "venv", "~archive"}
SKIP_NAMES = re.compile(r"^(python|pip|idle|pydoc|2to3|brew$)")
# Repairs must not trigger a full Homebrew upgrade of everything else.
BREW_ENV = dict(os.environ, HOMEBREW_NO_AUTO_UPDATE="1",
                HOMEBREW_NO_INSTALL_CLEANUP="1", HOMEBREW_NO_ENV_HINTS="1")
# "No such file: " is test()'s own message for a missing command, not a tool's output.
BROKEN_RE = re.compile(r"Library not loaded|dyld|image not found|No such file: |"
                       r"cannot execute|bad CPU type|Killed: 9")


def log(msg: str) -> None:
    print(time.strftime("%Y-%m-%d %H:%M:%S"), msg, flush=True)


# ── state ───────────────────────────────────────────────────────

def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


# ── slack ───────────────────────────────────────────────────────

def slack_token() -> str | None:
    if os.environ.get("SLACK_USER_TOKEN"):
        return os.environ["SLACK_USER_TOKEN"]
    try:
        with open(KEYS_ENV) as f:
            for line in f:
                line = line.strip()
                if line.startswith("export "):
                    line = line[7:]
                if line.startswith("SLACK_USER_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return None


def _slack(method: str, token: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"https://slack.com/api/{method}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json; charset=utf-8",
                 "Authorization": f"Bearer {token}"})
    return json.loads(urllib.request.urlopen(req, timeout=15).read())


def dm(text: str) -> bool:
    """Slack DM to the owner of SLACK_USER_TOKEN (config/keys.env); falls back
    to a macOS notification. Never raises."""
    log("DM: " + text.replace("\n", " | "))
    token = slack_token()
    try:
        if not token:
            raise RuntimeError("no SLACK_USER_TOKEN")
        me = _slack("auth.test", token)
        ch = _slack("conversations.open", token, {"users": me["user_id"]})
        resp = _slack("chat.postMessage", token,
                      {"channel": ch["channel"]["id"], "text": text})
        if resp.get("ok"):
            return True
        raise RuntimeError(resp.get("error"))
    except Exception as e:  # noqa: BLE001
        log(f"slack failed: {e}")
        first = text.splitlines()[0].replace('"', "'")
        subprocess.run(["osascript", "-e",
                        f'display notification "{first}" with title "Homebrew check"'])
        return False


# ── brew ────────────────────────────────────────────────────────

def wait_for_brew(max_wait: int = 1800) -> None:
    start = time.time()
    while time.time() - start < max_wait:
        r = subprocess.run(["pgrep", "-f", "Homebrew/Library/Homebrew/brew.rb"],
                           capture_output=True)
        if r.returncode != 0:
            return
        time.sleep(15)
    log("brew still running after 30 min; continuing anyway")


def brew(*args: str, timeout: int = 1800) -> tuple[int, str]:
    log("brew " + " ".join(args))
    try:
        r = subprocess.run([BREW, *args], capture_output=True, text=True,
                           env=BREW_ENV, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 1, "timed out"
    out = (r.stdout + r.stderr).strip()
    if r.returncode:
        log(out[-800:])
    return r.returncode, out


def owner(name: str) -> tuple[str, str] | None:
    """(kind, name) of the formula or cask that links /opt/homebrew/bin/<name>."""
    path = os.path.join(BREW_BIN, name)
    if not os.path.lexists(path):
        return None
    real = os.path.realpath(path)
    m = re.match(re.escape(PREFIX) + r"/(Cellar|Caskroom)/([^/]+)/", real)
    if not m:
        return None
    return ("cask" if m.group(1) == "Caskroom" else "formula", m.group(2))


def version_of(kind: str, pkg: str) -> str:
    flag = ["--cask"] if kind == "cask" else []
    r = subprocess.run([BREW, "list", "--versions", *flag, pkg],
                       capture_output=True, text=True, env=BREW_ENV)
    return r.stdout.split()[-1] if r.returncode == 0 and r.stdout.split() else ""


# ── what the bench uses ─────────────────────────────────────────

def code_files() -> list[str]:
    files = []
    for bench in BENCHES:
        for d in SCAN_DIRS:
            for root, dirs, names in os.walk(os.path.join(bench, d)):
                dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
                files += [os.path.join(root, n) for n in names
                          if os.path.splitext(n)[1] in CODE_EXT
                          and os.path.join(root, n) != os.path.abspath(__file__)]
    files += glob.glob(os.path.join(LAUNCH_AGENTS, "*.plist"))
    if os.path.exists(HS_INIT):
        files.append(HS_INIT)
    return files


def used_commands(candidates: set[str]) -> dict[str, list[str]]:
    """{command: [files that call it]} for every candidate the bench calls."""
    abs_re = re.compile(r"/opt/homebrew/bin/([A-Za-z0-9][\w.+-]*)")
    quoted_re = re.compile(r"""["']([A-Za-z0-9][\w.+-]*)["']""")
    # Command position in shell: line start, after | ; & ( $( or `
    shell_re = re.compile(r"(?:^|[|;&(`]|\$\()\s*([A-Za-z0-9][\w.+-]*)(?=\s|$)", re.M)
    used: dict[str, list[str]] = {}
    for path in code_files():
        try:
            with open(path, errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        found = set(abs_re.findall(text))
        found |= {n for n in quoted_re.findall(text) if n in candidates}
        if os.path.splitext(path)[1] in {".sh", ".zsh", ".bash", ".command"}:
            found |= {n for n in shell_re.findall(text) if n in candidates}
        for n in found:
            if not SKIP_NAMES.match(n):
                used.setdefault(n, []).append(path.replace(HOME, "~"))
    return used


# ── tests ───────────────────────────────────────────────────────

def run(cmd: list[str], cwd: str, timeout: int = 120) -> tuple[bool, str]:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=timeout)
    except FileNotFoundError:
        return False, f"No such file: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s: {' '.join(cmd)}"
    except OSError as e:
        return False, str(e)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def sample_video(tmp: str) -> str | None:
    out = os.path.join(tmp, "sample.mp4")
    if not os.path.exists(out):
        ok, _ = run([f"{BREW_BIN}/ffmpeg", "-v", "error", "-y",
                     "-f", "lavfi", "-i", "testsrc=d=1:s=320x240:r=10",
                     "-f", "lavfi", "-i", "sine=d=1", "-shortest",
                     "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", out], tmp)
        if not ok:
            return None
    return out


def sample_pdf(tmp: str) -> str | None:
    out = os.path.join(tmp, "sample.pdf")
    if not os.path.exists(out):
        ok, _ = run([f"{BREW_BIN}/gs", "-q", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite",
                     f"-sOutputFile={out}", "-c",
                     "/Helvetica findfont 20 scalefont setfont 72 720 moveto (bench) show showpage"],
                    tmp)
        if not ok:
            return None
    return out


def produced(path: str) -> bool:
    return os.path.exists(path) and os.path.getsize(path) > 0


def t_ffmpeg(b: str, tmp: str) -> tuple[bool, str]:
    out = os.path.join(tmp, "ff.mp4")
    ok, msg = run([b, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=d=1:s=320x240:r=10",
                   "-f", "lavfi", "-i", "sine=d=1", "-shortest",
                   "-vf", "drawtext=text=bench:fontcolor=white:fontsize=24",
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", out], tmp)
    if not ok or not produced(out):
        return False, msg or "no output"
    ok, enc = run([b, "-hide_banner", "-encoders"], tmp)
    missing = [e for e in ("hevc_videotoolbox", "libx265", "libmp3lame", "libsvtav1")
               if e not in enc]
    return (not missing, f"encoders missing: {', '.join(missing)}" if missing else "")


def t_handbrake(b: str, tmp: str) -> tuple[bool, str]:
    src = sample_video(tmp)
    if not src:
        return run([b, "--version"], tmp)
    out = os.path.join(tmp, "hb.mp4")
    ok, msg = run([b, "-i", src, "-o", out, "-e", "vt_h265", "-q", "60",
                   "-E", "aac", "-f", "av_mp4"], tmp)
    return (ok and produced(out), "" if ok and produced(out) else msg[-600:] or "no output")


def t_ffprobe(b: str, tmp: str) -> tuple[bool, str]:
    src = sample_video(tmp)
    return run([b, "-v", "error", src], tmp) if src else run([b, "-version"], tmp)


def t_gs(b: str, tmp: str) -> tuple[bool, str]:
    out = os.path.join(tmp, "gs.png")
    pdf = sample_pdf(tmp)
    if not pdf:
        return False, "could not write a PDF"
    ok, msg = run([b, "-q", "-dBATCH", "-dNOPAUSE", "-sDEVICE=png16m", "-r72",
                   f"-sOutputFile={out}", pdf], tmp)
    return (ok and produced(out), msg or ("" if produced(out) else "no output"))


def t_pdftotext(b: str, tmp: str) -> tuple[bool, str]:
    pdf = sample_pdf(tmp)
    if not pdf:
        return run([b, "-v"], tmp)
    ok, msg = run([b, pdf, "-"], tmp)
    return (ok and "bench" in msg, "" if ok and "bench" in msg else msg or "no text")


def t_pdftoppm(b: str, tmp: str) -> tuple[bool, str]:
    pdf = sample_pdf(tmp)
    if not pdf:
        return run([b, "-v"], tmp)
    ok, msg = run([b, "-png", "-r", "36", "-singlefile", pdf, os.path.join(tmp, "pp")], tmp)
    return (ok and produced(os.path.join(tmp, "pp.png")), msg or "")


# Real work for the tools jobs lean on hardest; everything else gets a version probe.
SMOKE = {"ffmpeg": t_ffmpeg, "ffprobe": t_ffprobe, "HandBrakeCLI": t_handbrake,
         "gs": t_gs, "pdftotext": t_pdftotext, "pdftoppm": t_pdftoppm}
PROBES = (["--version"], ["-version"], ["version"], ["-V"], ["-v"], ["--help"], ["-h"])


def test(name: str, tmp: str) -> tuple[bool, str]:
    b = os.path.join(BREW_BIN, name)
    if not os.path.lexists(b):
        return False, f"No such file: {b}"
    if not os.path.exists(b):
        return False, f"No such file: broken link {b} -> {os.readlink(b)}"
    if name in SMOKE:
        return SMOKE[name](b, tmp)
    last = ""
    for args in PROBES:
        ok, msg = run([b, *args], tmp, timeout=30)
        if ok:
            return True, ""
        last = msg
        if BROKEN_RE.search(msg):
            break
    return False, last[-600:]


# ── repair ──────────────────────────────────────────────────────

def repair(kind: str, pkg: str, errors: str, retest) -> tuple[bool, list[str]]:
    """Try fixes in order of how much they change; stop at the first that works."""
    tried = []
    cask = ["--cask"] if kind == "cask" else []
    if not version_of(kind, pkg):
        steps = [("install", ["install", *cask, pkg])]
    else:
        steps = [] if kind == "cask" else [("link", ["link", "--overwrite", pkg])]
        if kind == "formula":
            _, missing = brew("missing", pkg)
            deps = sorted({d for line in missing.splitlines()
                           for d in line.split(":", 1)[-1].split() if d})
            if deps:
                steps.append((f"install missing deps {' '.join(deps)}", ["install", *deps]))
        steps.append(("reinstall", ["reinstall", *cask, pkg]))
        # dyld names the dependency whose library is gone (e.g. libbluray for HandBrake)
        for dep in sorted(set(re.findall(r"Library not loaded: " + re.escape(PREFIX)
                                         + r"/(?:opt|Cellar)/([^/]+)/", errors)) - {pkg}):
            steps.append((f"reinstall {dep}", ["reinstall", dep]))
    for label, args in steps:
        code, _ = brew(*args)
        tried.append(label + ("" if code == 0 else " (failed)"))
        if retest():
            return True, tried
    return False, tried


# ── main ────────────────────────────────────────────────────────

def main() -> int:
    if os.path.exists(LOCK_FILE) and time.time() - os.path.getmtime(LOCK_FILE) < 3600:
        log("another run in progress")
        return 0
    open(LOCK_FILE, "w").close()
    try:
        return check()
    except Exception as e:  # noqa: BLE001
        dm(f"Homebrew check crashed: {e}\nLog: /tmp/com.bench.brew-check.log")
        raise
    finally:
        os.remove(LOCK_FILE)


def check() -> int:
    wait_for_brew()
    state = load_state()
    known: dict = state.setdefault("tools", {})
    candidates = set(os.listdir(BREW_BIN)) | set(known)
    used = used_commands(candidates)
    # A command that left /opt/homebrew/bin is only found again via its absolute
    # path; keep the ones we already know so a vanished tool is still checked.
    names = sorted(set(used) | {n for n in known if n not in used and known[n].get("ok_once")})

    broken: dict[tuple[str, str], list[tuple[str, str]]] = {}
    with tempfile.TemporaryDirectory(prefix="brew-check-") as tmp:
        for name in names:
            info = known.setdefault(name, {})
            if name in used:
                info["used_by"] = sorted(set(used[name]))[:5]
            pkg = owner(name)
            if pkg:
                info["kind"], info["package"] = pkg
            elif not info.get("package"):
                known.pop(name)
                continue
            ok, msg = test(name, tmp)
            if ok:
                info["ok_once"] = True
                info["last_ok"] = time.strftime("%Y-%m-%d %H:%M")
                continue
            if not info.get("package"):
                # pip scripts (python-repin's job) and app-bundle links can't be repaired here
                log(f"{name}: not linked from a Homebrew formula or cask, skipped")
                known.pop(name)
                continue
            # Never worked and nothing looks broken → a probe that doesn't fit, not a breakage.
            if not info.get("ok_once") and not BROKEN_RE.search(msg):
                log(f"{name}: no probe works ({msg[:120]}), skipped")
                continue
            log(f"{name}: BROKEN — {msg[:300]}")
            broken.setdefault((info["kind"], info["package"]), []).append((name, msg))

        alerts = state.setdefault("alerted", {})
        for (kind, pkg), fails in broken.items():
            cmds = [n for n, _ in fails]
            fixed, tried = repair(kind, pkg, "\n".join(m for _, m in fails), lambda: all(test(n, tmp)[0] for n in cmds))
            if fixed:
                log(f"{pkg}: repaired by {tried[-1]}")
                state.setdefault("repairs", []).append(
                    {"at": time.strftime("%Y-%m-%d %H:%M"), "package": pkg, "fix": tried[-1]})
                state["repairs"] = state["repairs"][-20:]
                alerts.pop(pkg, None)
                continue
            ver = version_of(kind, pkg) or "not installed"
            if alerts.get(pkg) == ver:
                log(f"{pkg} {ver}: still broken, already DMed")
                continue
            users = sorted({u for n in cmds for u in known[n].get("used_by", [])})
            err = test(cmds[0], tmp)[1].splitlines()
            dm(f"Homebrew check: {pkg} ({ver}) is broken and I couldn't fix it.\n"
               f"Error: {(err[0] if err else '')[:300]}\n"
               f"Tried: {', '.join(tried)}\n"
               f"Used by: {', '.join(users) or ', '.join(cmds)}\n"
               f"Log: /tmp/com.bench.brew-check.log")
            alerts[pkg] = ver
        for pkg in [p for p in alerts if (p not in {k[1] for k in broken})]:
            alerts.pop(pkg)  # healthy again

    state["last_run"] = time.strftime("%Y-%m-%d %H:%M")
    save_state(state)
    log(f"checked {len(names)} commands, {len(broken)} broken package(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
