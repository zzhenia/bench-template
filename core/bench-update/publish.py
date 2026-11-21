#!/usr/bin/env python3
"""Send this bench's own core/ changes to the bench template (nightly, before the update).

The template is the source of truth for core/. A core file this bench changed
since the template version it last took (config/bench-upstream) is committed
straight to the template's main, provided the template has not changed that file
since. A file changed on both sides is left to the update that follows: the bench
merges it (and a later night sends the merged file), or it becomes a pull request.

  publish.py BASE UPSTREAM_REF UPSTREAM_URL BENCH_NAME

Prints `PUBLISHED <files>` or `BLOCKED <reason>`; nothing when there is nothing
to send. Needs `gh` logged in with write access to the template.
"""
import base64, json, os, re, subprocess, sys

base, up_ref, url, name = sys.argv[1:5]


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, check=True).stdout


def files(spec):
    return [f for f in git("diff", "--name-only", *spec, "--", "core").splitlines() if f]


mine = files([base, "HEAD"])
if not mine:
    sys.exit(0)
theirs = set(files([base, up_ref]))
send = [f for f in mine if f not in theirs]
if not send:
    sys.exit(0)

present = [f for f in send if os.path.lexists(f)]
if present and subprocess.run(["bash", "core/bin/scan-personal.sh", *present],
                              capture_output=True).returncode:
    print(f"BLOCKED personal details in {', '.join(present)} (core/bin/scan-personal.sh); not sent")
    sys.exit(0)

m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", url)
if not m:
    print("BLOCKED the template is not on GitHub")
    sys.exit(0)
repo = f"{m[1]}/{m[2]}"


def api(path, body=None, method=None):
    cmd = ["gh", "api", f"repos/{repo}/{path}"]
    if method:
        cmd += ["-X", method]
    if body is not None:
        cmd += ["--input", "-"]
    r = subprocess.run(cmd, input=json.dumps(body) if body is not None else None,
                       capture_output=True, text=True)
    if r.returncode:
        print(f"BLOCKED GitHub said: {(r.stderr or r.stdout).strip()[:200]}")
        sys.exit(0)
    return json.loads(r.stdout or "{}")


head = git("rev-parse", up_ref).strip()
tree = []
for f in send:
    if not os.path.lexists(f):
        tree.append({"path": f, "mode": "100644", "type": "blob", "sha": None})
        continue
    if os.path.islink(f):
        data, mode = os.readlink(f).encode(), "120000"
    else:
        data = open(f, "rb").read()
        mode = "100755" if os.access(f, os.X_OK) else "100644"
    blob = api("git/blobs", {"content": base64.b64encode(data).decode(), "encoding": "base64"})
    tree.append({"path": f, "mode": mode, "type": "blob", "sha": blob["sha"]})

# The template is public: the message names only the files, never this
# bench's commit subjects (they carry personal topics and ticket keys).
msg = f"core: {', '.join(send[:4])}{' …' if len(send) > 4 else ''}"
t = api("git/trees", {"base_tree": api(f"git/commits/{head}")["tree"]["sha"], "tree": tree})
c = api("git/commits", {"message": msg, "tree": t["sha"], "parents": [head],
                         "author": {"name": "The Bench", "email": "bench@users.noreply.github.com"}})
api("git/refs/heads/main", {"sha": c["sha"], "force": False}, method="PATCH")
print(f"PUBLISHED {' '.join(send)}")
