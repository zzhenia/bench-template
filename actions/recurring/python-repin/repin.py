#!/usr/bin/python3
"""Keep every bench caller on a Homebrew Python that has its libraries.

Runs under the system Python (/usr/bin/python3) so a Homebrew upgrade can never
break it. On each run:

1. Waits for any running `brew` to finish.
2. If /opt/homebrew/bin/python3 now points at a newer version than the pinned
   one: installs the pinned version's top-level packages into the new one,
   then checks that every script the callers run still imports. All good →
   repins the callers, reloads them, notifies you. Anything that worked before
   and breaks now → stays on the old version and DMs what is missing (once per
   version).
3. Pins any caller still using the bare `python3` to the current pin.

Callers: ~/Library/LaunchAgents/*.plist (reloaded), plists under the bench's
actions/ and tools/ (repo copies, not loaded), ~/.hammerspoon/init.lua
(reloaded). One instance per Mac covers every bench: LaunchAgents are
machine-wide; setup.sh installs it once and other benches defer to it.
Settings: config.json next to this file.
"""
from __future__ import annotations

import ast
import glob
import json
import os
import re
import shutil
import subprocess
import sys
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
# Other bench checkouts whose repo plists this instance also repins.
BENCHES = [BENCH] + [p for p in (os.path.expanduser(b) for b in CONFIG.get("other_benches", []))
                     if os.path.isdir(p)]
# Compiled app wrappers that run the bare python3 (checked, never rebuilt).
WRAPPERS_DIR = os.path.expanduser(CONFIG.get("wrappers_dir", "~/Applications/Bench Jobs"))
STATE_FILE = os.path.join(HERE, "state.json")
LOCK_FILE = os.path.join(HERE, ".lock")
KEYS_ENV = os.path.join(BENCH, "config/keys.env")
BREW_BIN = "/opt/homebrew/bin"
HS_INIT = os.path.join(HOME, ".hammerspoon/init.lua")
HS_CLI = "/Applications/Hammerspoon.app/Contents/Frameworks/hs/hs"
LAUNCH_AGENTS = os.path.join(HOME, "Library/LaunchAgents")

# /opt/homebrew/bin/python3 or /opt/homebrew/bin/python3.NN, followed by < or "
REF_RE = re.compile(r'/opt/homebrew/bin/python3(\.\d+)?(?=[<"])')
SKIP_PKGS = {"pip", "setuptools", "wheel"}
# Folders whose modules jobs import through sys.path (one tool importing
# another tool's module).
MODULE_ROOTS = [os.path.join(b, d) for b in BENCHES for d in ("actions", "tools")
                if os.path.isdir(os.path.join(b, d))]
SKIP_DIRS = {"__pycache__", "node_modules", ".git", ".venv", "venv"}
# A wrapped script with this guard restarts itself on the newest python3.NN
# that has its libraries, so it only breaks when no installed version does.
GUARD_MARKER = "_ensure_python()"


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
        json.dump(state, f, indent=2)
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
                        f'display notification "{first}" with title "Python repin"'])
        return False


# ── versions ────────────────────────────────────────────────────

def brew_default_version() -> str | None:
    """'3.15' for whatever /opt/homebrew/bin/python3 resolves to."""
    exe = os.path.join(BREW_BIN, "python3")
    if not os.path.exists(exe):
        return None
    out = subprocess.run([exe, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
                         capture_output=True, text=True)
    return out.stdout.strip() or None


def vkey(v: str) -> tuple:
    return tuple(int(x) for x in v.split("."))


def py(v: str) -> str:
    return os.path.join(BREW_BIN, f"python{v}")


def wait_for_brew(max_wait: int = 1800) -> None:
    start = time.time()
    while time.time() - start < max_wait:
        r = subprocess.run(["pgrep", "-f", "Homebrew/Library/Homebrew/brew.rb"],
                           capture_output=True)
        if r.returncode != 0:
            return
        time.sleep(15)
    log("brew still running after 30 min; continuing anyway")


# ── callers ─────────────────────────────────────────────────────

def caller_files() -> list[tuple[str, str]]:
    """(path, kind) for every file that may reference Homebrew python."""
    files = [(p, "agent") for p in glob.glob(os.path.join(LAUNCH_AGENTS, "*.plist"))]
    for bench in BENCHES:
        for d in ("actions", "tools"):
            for p in glob.glob(os.path.join(bench, d, "**/*.plist"), recursive=True):
                if "archive/" not in p and not in_nested_repo(bench, p):
                    files.append((p, "repo"))
    if os.path.exists(HS_INIT):
        files.append((HS_INIT, "hammerspoon"))
    return [(p, k) for p, k in files if REF_RE.search(open(p, errors="ignore").read())]


def in_nested_repo(bench: str, path: str) -> bool:
    """True for files inside a separate git repo checked out under a bench
    (a project cloned into tools/): that repo's owner repins it."""
    d = os.path.dirname(path)
    while len(d) > len(bench):
        if os.path.exists(os.path.join(d, ".git")):
            return True
        d = os.path.dirname(d)
    return False


def scripts_run_by(path: str) -> list[str]:
    """.py files a caller runs (absolute paths found in the file)."""
    text = open(path, errors="ignore").read()
    found = re.findall(r'(/Users/[^<>"\s]+\.py)', text)
    return sorted({p for p in found if os.path.exists(p)})


def tool_root(script: str) -> str:
    """The tool folder a script belongs to (…/<actions|tools>/<kind>/<name>), else its dir."""
    m = re.match(r"(.*/(?:actions|tools)/[^/]+/[^/]+)/", script)
    return m.group(1) if m else os.path.dirname(script)


_MODULE_INDEX: dict[str, list[str]] | None = None
_STDLIB: set[str] | None = None


def stdlib_names() -> set[str]:
    """Standard-library module names (the system Python is too old to list them)."""
    global _STDLIB
    if _STDLIB is None:
        r = subprocess.run([os.path.join(BREW_BIN, "python3"), "-c",
                            "import sys, json; print(json.dumps(sorted(sys.stdlib_module_names)))"],
                           capture_output=True, text=True)
        _STDLIB = set(json.loads(r.stdout or "[]"))
    return _STDLIB


def module_index() -> dict[str, list[str]]:
    """module name -> .py files under MODULE_ROOTS (archives skipped)."""
    global _MODULE_INDEX
    if _MODULE_INDEX is None:
        _MODULE_INDEX = {}
        for root in MODULE_ROOTS:
            for d, dirs, files in os.walk(root):
                dirs[:] = [x for x in dirs if x not in SKIP_DIRS and "archive" not in x]
                for f in files:
                    if f.endswith(".py"):
                        _MODULE_INDEX.setdefault(f[:-3], []).append(os.path.join(d, f))
    return _MODULE_INDEX


def _imports_in(files: list[str]) -> tuple[set[str], set[str]]:
    """(imported top-level names, the files' own module/package names)."""
    names, local = set(), set()
    for f in files:
        local.add(os.path.splitext(os.path.basename(f))[0])
        local.add(os.path.basename(os.path.dirname(f)))
        try:
            tree = ast.parse(open(f, errors="ignore").read())
        except (SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names.add(node.module.split(".")[0])
    return names, local


def third_party_imports(script: str) -> set[str]:
    """Top-level modules imported anywhere in the script's tool folder, minus
    the folder's own modules (so a server's backend imports count too).
    Bench modules it pulls in from other tool folders via sys.path are
    followed, so their libraries count as well."""
    root = tool_root(script)
    files = [script] if root == os.path.dirname(script) else [
        p for p in glob.glob(os.path.join(root, "**/*.py"), recursive=True)
        if "/.venv/" not in p and "/venv/" not in p and "/__pycache__/" not in p]
    names, local = _imports_in(files)
    names -= local
    seen = set(files)
    stdlib = stdlib_names()
    todo = [n for n in names if n not in stdlib]
    while todo:
        n = todo.pop()
        # An installed package wins over a same-named bench file; follow only
        # names no Python can import.
        if any(importable(v, {n}).get(n) for v in installed_versions()):
            continue
        extra = [f for f in module_index().get(n, []) if f not in seen]
        if not extra:
            continue
        names.discard(n)
        seen.update(extra)
        more, own = _imports_in(extra)
        # The followed module's neighbours are local to it too
        for f in extra:
            own |= {os.path.splitext(x)[0] for x in os.listdir(os.path.dirname(f)) if x.endswith(".py")}
        local |= own
        for m in more - local - names:
            names.add(m)
            if m not in stdlib:
                todo.append(m)
    return names - local


def wrapper_scripts() -> list[str]:
    """Scripts run by Bench Jobs app wrappers through the bare python3. The
    wrappers are signed for Full Disk Access, so this routine never rebuilds
    them; it only checks they still work on the new version."""
    out = []
    for binpath in glob.glob(os.path.join(WRAPPERS_DIR, "*.app/Contents/MacOS/*")):
        s = subprocess.run(["strings", binpath], capture_output=True, text=True).stdout.split()
        if "/opt/homebrew/bin/python3" in s:
            out += [p for p in s if p.endswith(".py") and os.path.exists(p)]
    return out


CHECK_SNIPPET = """
import importlib, json, sys
ok = {}
for m in sys.argv[1:]:
    try:
        importlib.import_module(m); ok[m] = True
    except Exception:
        ok[m] = False
print(json.dumps(ok))
"""


def importable(v: str, modules: set[str]) -> dict:
    if not modules:
        return {}
    r = subprocess.run([py(v), "-c", CHECK_SNIPPET, *sorted(modules)],
                       capture_output=True, text=True, cwd=HOME, timeout=600)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {m: False for m in modules}


def relink_broken_brew_packages(v: str) -> list[str]:
    """Homebrew sometimes leaves a formula's site-packages links as empty
    folders after a Python upgrade; pip then fails with 'No package metadata
    was found'. Relink any formula whose dist-info has no METADATA."""
    site = f"/opt/homebrew/lib/python{v}/site-packages"
    fixed = []
    for info in glob.glob(os.path.join(site, "*.dist-info")):
        if os.path.exists(os.path.join(info, "METADATA")):
            continue
        rel = os.path.relpath(info, "/opt/homebrew")
        owners = glob.glob(f"/opt/homebrew/Cellar/*/*/{rel}/METADATA")
        for o in owners:
            formula = o.split("/Cellar/")[1].split("/")[0]
            subprocess.run(["brew", "link", "--overwrite", formula], capture_output=True)
            fixed.append(formula)
    if fixed:
        log(f"relinked Homebrew formulas: {', '.join(fixed)}")
    return fixed


def install_packages(old: str, new: str) -> str:
    """Install old's top-level packages into new. Returns pip's error tail or ''."""
    r = subprocess.run([py(old), "-m", "pip", "list", "--not-required", "--format=json"],
                       capture_output=True, text=True)
    pkgs = [p["name"] for p in json.loads(r.stdout or "[]")
            if p["name"].lower() not in SKIP_PKGS]
    log(f"installing into {new}: {' '.join(pkgs)}")
    failed = []
    # One by one, so a single package without a wheel doesn't block the rest.
    for p in pkgs:
        r = subprocess.run([py(new), "-m", "pip", "install", "--quiet",
                            "--break-system-packages", p],
                           capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            failed.append(p)
            log(f"pip failed for {p}: {r.stderr.strip().splitlines()[-1:]}")
    return ", ".join(failed)


# ── rewrite + reload ────────────────────────────────────────────

def repin(files: list[tuple[str, str]], target: str) -> list[str]:
    """Point every reference at python<target>. Returns changed paths."""
    stamp = time.strftime("%y%m%d-%H%M")
    bak_dir = os.path.join(LAUNCH_AGENTS + "-bak-" + stamp)
    changed = []
    for path, kind in files:
        text = open(path).read()
        new = REF_RE.sub(f"/opt/homebrew/bin/python{target}", text)
        if new == text:
            continue
        if kind == "agent":
            os.makedirs(bak_dir, exist_ok=True)
            shutil.copy2(path, bak_dir)
        elif kind == "hammerspoon":
            n = 1
            while os.path.exists(f"{HS_INIT}_old{n:02d}"):
                n += 1
            shutil.copy2(path, f"{HS_INIT}_old{n:02d}")
        with open(path, "w") as f:
            f.write(new)
        changed.append(path)
        if kind == "agent":
            subprocess.run(["launchctl", "unload", path], capture_output=True)
            subprocess.run(["launchctl", "load", path], capture_output=True)
        elif kind == "hammerspoon" and os.path.exists(HS_CLI):
            subprocess.run([HS_CLI, "-c", "hs.reload()"], capture_output=True, timeout=30)
    return changed


def label(path: str) -> str:
    if path == HS_INIT:
        return "Hammerspoon"
    return os.path.basename(path).replace(".plist", "")


# ── main ────────────────────────────────────────────────────────

def main() -> int:
    if os.path.exists(LOCK_FILE) and time.time() - os.path.getmtime(LOCK_FILE) < 3600:
        log("another run in progress")
        return 0
    open(LOCK_FILE, "w").close()
    try:
        return run()
    finally:
        os.remove(LOCK_FILE)


def installed_versions() -> list[str]:
    """Every Homebrew python3.NN, newest first."""
    vs = [m.group(1) for p in glob.glob(os.path.join(BREW_BIN, "python3.*"))
          if (m := re.fullmatch(r".*/python(3\.\d+)", p))]
    return sorted(vs, key=vkey, reverse=True)


def guarded(script: str) -> bool:
    return GUARD_MARKER in open(script, errors="ignore").read()


def check_wrappers(state: dict, newest: str, pinned: str) -> None:
    """App wrappers always run the newest Homebrew python. DM once per new
    breakage: fixing it means rebuilding a signed wrapper (you re-grant
    Full Disk Access) or getting the library onto the new version. A guarded
    script restarts itself on an older version that works, so it counts as
    broken only when no installed version has its libraries."""
    broken, fallback = {}, {}
    for s in wrapper_scripts():
        mods = third_party_imports(s)
        ok_old = {m for m, ok in importable(pinned, mods).items() if ok} if pinned != newest else mods
        bad = sorted(m for m, ok in importable(newest, ok_old).items() if not ok)
        if bad and guarded(s):
            # Libraries that work on at least one installed version
            known = set()
            for v in installed_versions():
                known |= {m for m, ok in importable(v, mods).items() if ok}
            runner = next((v for v in installed_versions()
                           if all(importable(v, known).values())), None)
            if runner:
                fallback[s] = runner
                log(f"{s.replace(BENCH + '/', '')}: runs on {runner} ({newest} lacks {', '.join(bad)})")
                continue
        if bad:
            broken[s] = bad
    if fallback:
        state["wrapper_fallback"] = {s.replace(BENCH + "/", ""): v for s, v in fallback.items()}
    else:
        state.pop("wrapper_fallback", None)
    sig = json.dumps([newest, broken], sort_keys=True)
    if broken and state.get("wrapper_alert") != sig:
        lines = "\n".join(f"• {s.replace(BENCH + '/', '')}: {', '.join(b)}"
                          for s, b in broken.items())
        dm(f"Python repin needs you: these app-wrapped jobs run Python {newest} and "
           f"can't import what they need (no {newest} build exists yet):\n{lines}\n"
           f"They work until their next restart. Tell the bench whether to rebuild "
           f"the wrapper on Python {pinned if pinned != newest else state.get('previous', '?')} "
           f"(you'll re-grant Full Disk Access once) or wait for the library.")
    if broken:
        state["wrapper_alert"] = sig
    else:
        state.pop("wrapper_alert", None)


def run() -> int:
    wait_for_brew()
    state = load_state()
    newest = brew_default_version()
    pinned = state.get("pinned")
    if not newest:
        dm("Python repin: /opt/homebrew/bin/python3 is missing. Bench jobs stay on "
           f"python{pinned}; nothing changed.")
        return 1
    if not pinned or not os.path.exists(py(pinned)):
        pinned = newest if not pinned else pinned
    files = caller_files()

    if vkey(newest) > vkey(pinned) and state.get("blocked") != newest:
        log(f"new Homebrew python {newest} (pinned {pinned})")
        relink_broken_brew_packages(newest)
        pip_failed = install_packages(pinned, newest)
        modules = set()
        for path, _ in files:
            for s in scripts_run_by(path):
                modules |= third_party_imports(s)
        # Guarded wrappers fall back on their own, so they don't block the switch
        for s in wrapper_scripts():
            if not guarded(s):
                modules |= third_party_imports(s)
        before = importable(pinned, modules)
        after = importable(newest, {m for m, ok in before.items() if ok})
        broken = sorted(m for m, ok in after.items() if not ok)
        if broken:
            # Modules that came in as some other package's dependency: install
            # their distribution directly, then check again.
            r = subprocess.run([py(pinned), "-c",
                                "import json, importlib.metadata as m; "
                                "print(json.dumps(m.packages_distributions()))"],
                               capture_output=True, text=True)
            dists = json.loads(r.stdout or "{}")
            for mod in broken:
                for d in dists.get(mod, []):
                    subprocess.run([py(newest), "-m", "pip", "install", "--quiet",
                                    "--break-system-packages", d],
                                   capture_output=True, text=True, timeout=1800)
            after = importable(newest, set(broken))
            broken = sorted(m for m, ok in after.items() if not ok)
        if broken:
            state["blocked"] = newest
            check_wrappers(state, newest, pinned)
            save_state(state)
            dm(f"Python repin: Homebrew installed Python {newest}, but these libraries "
               f"don't work on it yet: {', '.join(broken)}. All bench jobs stay on "
               f"{pinned} and keep running. Ask the bench to switch once they're fixed "
               f"(or I'll retry on the next Python update).")
            return 0
        changed = repin(files, newest)
        state.update(pinned=newest, previous=pinned, switched=time.strftime("%Y-%m-%d %H:%M"))
        state.pop("blocked", None)
        check_wrappers(state, newest, pinned)
        save_state(state)
        names = ", ".join(sorted(label(p) for p in changed if "/Library/LaunchAgents/" in p or p == HS_INIT))
        extra = f" (pip skipped: {pip_failed}; nothing the jobs import)" if pip_failed else ""
        dm(f"Python repin: switched the bench from Python {pinned} to {newest} — "
           f"libraries installed, every job's imports checked{extra}. Reloaded: {names}. "
           f"If macOS asks whether python{newest} may access files, allow it.")
        return 0

    # Same version: just pin any caller still on bare python3.
    stray = [(p, k) for p, k in files
             if re.search(r'/opt/homebrew/bin/python3(?=[<"])', open(p).read())]
    if stray:
        changed = repin(stray, pinned)
        log(f"pinned stray callers to {pinned}: {', '.join(map(label, changed))}")
    state["pinned"] = pinned
    check_wrappers(state, newest, state.get("previous", pinned) if newest == pinned else pinned)
    state["checked"] = time.strftime("%Y-%m-%d %H:%M")
    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
