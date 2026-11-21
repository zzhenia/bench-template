#!/bin/bash
# Nightly bench update, run by auto-push right after a successful push.
# Applies the template's new changes and pushes them. When a file was changed
# both here and in the template, the update is undone and a pull request is
# opened on the template with this bench's version of those files, branched from
# the template version this bench last matched, so GitHub shows the conflict and
# it is merged there like any other. The next night applies the merged result.
#
# Prints lines `NOTIFY: <text>` for the caller to send (Slack + session notice);
# nothing when there is nothing to say. Needs `gh` logged in to open the PR.
cd "$(dirname "$0")/../.." || exit 1
. core/bench-update/lib.sh
[ -n "$UPSTREAM_URL" ] || exit 0
NAME=$(basename "$(pwd -P)")
PR_FILE="$(git rev-parse --git-dir)/bench-update-pr"

say() { printf 'NOTIFY: %s\n' "$1"; }

# 1. Send this bench's own core/ changes to the template (core/bench-update/publish.py).
if fetch_upstream && base=$(find_base); then
  pub=$(python3 core/bench-update/publish.py "$base" "$UP_REF" "$UPSTREAM_URL" "$NAME" 2>&1)
  echo "$pub" | sed 's/^/  /' >&2
  case "$pub" in BLOCKED*) say "Core changes in $NAME were not sent to the template: ${pub#BLOCKED }";; esac
fi

# 2. Take the template's changes (including what was just sent).
out=$(bash core/bench-update/update.sh --auto 2>&1); rc=$?
echo "$out" | sed 's/^/  /' >&2

if [ $rc = 0 ]; then
  rm -f "$PR_FILE"
  if echo "$out" | grep -q '^Applied'; then
    git push -q origin main 2>/dev/null || say "Bench update applied in $NAME but the push failed; run /push."
    echo "$out" | grep -q '^RUN_SETUP' && say "Bench update in $NAME changed setup.sh or a schedule: run \`bash setup.sh\` there."
  fi
  conf=$(echo "$out" | sed -n 's/^ENV: CONFLICT //p')
  [ -n "$conf" ] && say "Bench settings in $NAME need an answer (bench value or yours). Type /update in a session there.
$conf"
  exit 0
fi

if [ $rc = 1 ]; then
  echo "$out" | grep -q "Could not reach" && exit 0   # offline tonight; check.sh warns after 3 days
  say "Bench update in $NAME did not run: $(echo "$out" | tail -1)"
  exit 0
fi

# rc 3: conflicts, already undone by update.sh --auto
base=$(echo "$out" | sed -n 's/^BASE //p')
up=$(git rev-parse "$UP_REF")
files=$(echo "$out" | sed -n '/^CONFLICTS/,$p' | tail -n +2)
if [ -f "$PR_FILE" ]; then
  url=$(cut -d' ' -f2 "$PR_FILE")
  if [ "$(gh pr view "$url" --json state -q .state 2>/dev/null)" = OPEN ]; then
    say "Bench update in $NAME is still waiting on the pull request: $url"; exit 0
  fi
fi
if ! bash core/bin/scan-personal.sh $files >/dev/null 2>&1; then
  say "Bench update in $NAME conflicts in: $files. These files hold personal details, so no pull request was opened. Type /update in a session there to merge by hand."
  exit 0
fi
url=$(python3 - "$UPSTREAM_URL" "$base" "$NAME" $files <<'PY'
import base64, datetime, json, os, re, subprocess, sys
url, base, name, *files = sys.argv[1:]
m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", url)
if not m:
    sys.exit("upstream is not on GitHub")
repo = f"{m[1]}/{m[2]}"
def api(path, body=None, method=None):
    cmd = ["gh", "api", f"repos/{repo}/{path}"]
    if method: cmd += ["-X", method]
    if body is not None: cmd += ["--input", "-"]
    r = subprocess.run(cmd, input=json.dumps(body) if body is not None else None,
                       capture_output=True, text=True)
    if r.returncode: sys.exit(r.stderr.strip() or r.stdout.strip())
    return json.loads(r.stdout or "{}")
tree = []
for f in files:
    try:
        data = open(f, "rb").read()
        blob = api("git/blobs", {"content": base64.b64encode(data).decode(), "encoding": "base64"})
        mode = "100755" if os.access(f, os.X_OK) else "100644"
        tree.append({"path": f, "mode": mode, "type": "blob", "sha": blob["sha"]})
    except FileNotFoundError:
        tree.append({"path": f, "mode": "100644", "type": "blob", "sha": None})
base_tree = api(f"git/commits/{base}")["tree"]["sha"]
t = api("git/trees", {"base_tree": base_tree, "tree": tree})
c = api("git/commits", {"message": f"{name}: local changes to {', '.join(files)}", "tree": t["sha"], "parents": [base]})
branch = f"bench/{re.sub(r'[^a-z0-9-]', '-', name.lower())}-{datetime.date.today():%y%m%d}"
api("git/refs", {"ref": f"refs/heads/{branch}", "sha": c["sha"]})
body = (f"The nightly update of **{name}** stopped: these files were changed both there and here.\n\n"
        + "".join(f"- `{f}`\n" for f in files)
        + "\nThis branch holds that bench's version. Resolve the conflict here (GitHub's "
          "*Resolve conflicts* button), merge, and every bench takes the result on its next nightly update.")
pr = api("pulls", {"title": f"Merge local changes from {name}", "head": branch, "base": "main", "body": body})
print(pr["html_url"])
PY
) || { say "Bench update in $NAME conflicts in: $files. Could not open a pull request on the template (${url:-gh not logged in?}). Type /update in a session there."; exit 0; }
echo "$up $url" > "$PR_FILE"
say "Bench update in $NAME conflicts with the template in: $files. Merge the pull request: $url — the next nightly update applies it."
exit 0
