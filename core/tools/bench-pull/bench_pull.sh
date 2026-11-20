#!/bin/bash
# Bench Pull — keeps one bench's working copy level with GitHub.
#
# Other machines and agents may push to the bench repo during the day. This
# fetches, and if the local main is behind, rebases onto origin/main with
# --autostash so the pull works even while a session has uncommitted edits.
#
# No Claude call, no tokens. It never commits, never pushes, never resolves a
# conflict — committing and pushing stay with /push and the nightly auto-push.
#
# Each bench installs its own job (core/bin/install-schedules.sh); this script
# works on the bench it lives in, or on BENCH_ROOT when set.
#
# Failure = Slack DM to the owner of SLACK_USER_TOKEN (config/keys.env), else a
# macOS notification, plus a session-start notice; throttled to one every
# NOTIFY_EVERY_H hours so a persistent problem does not alert every 15 minutes.
# Success is silent.
#
# Settings (config/bench.env, optional):
#   BENCH_GIT_SSH_KEY=~/.ssh/<key>   fetch over ssh with this key (launchd has no ssh-agent)
#
# Usage: bench_pull.sh [--dry-run]

set -u
ROOT="${BENCH_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd -P)}"
NAME=$(basename "$ROOT")
STATE_DIR="$ROOT/state/bench-pull"
STATE="$STATE_DIR/state.json"
LOG="$STATE_DIR/bench-pull.log"
STAMP="$STATE_DIR/.last-notify"
NOTIFY_EVERY_H=6
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
mkdir -p "$STATE_DIR"

setting() {  # KEY — value from config/bench.env, else empty
  grep -E "^$1=" "$ROOT/config/bench.env" 2>/dev/null | tail -1 | cut -d= -f2- | sed -E "s/^[\"']//; s/[\"']$//"
}

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
SSH_KEY=$(setting BENCH_GIT_SSH_KEY); SSH_KEY="${SSH_KEY/#\~/$HOME}"
[ -n "$SSH_KEY" ] && export GIT_SSH_COMMAND="ssh -o IdentitiesOnly=yes -i $SSH_KEY -o BatchMode=yes"
export GIT_TERMINAL_PROMPT=0

cd "$ROOT" || exit 1

log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >>"$LOG"; }

write_state() {  # status, summary
  python3 - "$STATE" "$1" "$2" <<'PY'
import json, sys, datetime
path, status, summary = sys.argv[1:4]
json.dump({"last_run": datetime.datetime.now().isoformat(timespec="seconds"),
           "status": status, "summary": summary}, open(path, "w"), indent=2)
PY
}

notice_path() { local d; d=$(git rev-parse --absolute-git-dir 2>/dev/null) && echo "$d/bench-notices/bench-pull"; }

notify() {  # text — throttled; Slack self-DM, else macOS notification; plus a session-start notice
  local token now last n
  n=$(notice_path); [ -n "$n" ] && mkdir -p "$(dirname "$n")" && printf '%s\n' "$1" > "$n"
  now=$(date +%s); last=0; [ -f "$STAMP" ] && last=$(cat "$STAMP" 2>/dev/null || echo 0)
  if [ $(( now - last )) -lt $(( NOTIFY_EVERY_H * 3600 )) ]; then log "alert suppressed (throttle)"; return; fi
  echo "$now" > "$STAMP"
  token=$(grep -E '^(export )?SLACK_USER_TOKEN=' "$ROOT/config/keys.env" 2>/dev/null | head -1 | sed -E 's/^(export )?SLACK_USER_TOKEN=//; s/^["'\'']//; s/["'\'']$//')
  python3 - "$token" "$1" >>"$LOG" 2>&1 <<'PY'
import json, subprocess, sys, urllib.request
token, text = sys.argv[1:3]
def slack(method, body=None):
    req = urllib.request.Request(f"https://slack.com/api/{method}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"})
    return json.loads(urllib.request.urlopen(req, timeout=20).read())
try:
    if not token:
        raise RuntimeError("no SLACK_USER_TOKEN")
    me = slack("auth.test")["user_id"]
    ch = slack("conversations.open", {"users": me})["channel"]["id"]
    r = slack("chat.postMessage", {"channel": ch, "text": text, "unfurl_links": False})
    if not r.get("ok"):
        raise RuntimeError(r.get("error"))
    print("slack: ok")
except Exception as e:
    print("slack failed:", e, "- macOS notification instead")
    msg = text.splitlines()[0].replace('"', "'").replace("*", "")
    subprocess.run(["osascript", "-e", f'display notification "{msg}" with title "Bench"'])
PY
}

fail() {  # reason
  log "FAIL: $1"
  write_state "failed" "$1"
  [ $DRY -eq 1 ] || notify ":warning: *Bench pull failed* ($NAME, $(date '+%a %H:%M'))
$1
This machine is no longer level with GitHub — work pushed from elsewhere will not appear locally until this is fixed. Fix by hand in a bench session: \`git pull --rebase --autostash\`."
  exit 1
}

done_ok() {  # summary
  write_state "ok" "$1"
  n=$(notice_path); [ -n "$n" ] && rm -f "$n"
  exit 0
}

# ── pre-flight ────────────────────────────────────────────────────────────────
[ -d .git/rebase-merge ] || [ -d .git/rebase-apply ] && fail "a rebase is already in progress — left untouched"
[ -f .git/index.lock ] && fail "index.lock present (another git is running) — left untouched"
branch=$(git rev-parse --abbrev-ref HEAD)
[ "$branch" = "main" ] || { log "on branch $branch, not main — skipped"; write_state "skipped" "on branch $branch"; exit 0; }

git fetch -q origin || fail "git fetch failed (network / deploy key?)"
behind=$(git rev-list --count main..origin/main)
ahead=$(git rev-list --count origin/main..main)

[ "$behind" -eq 0 ] && done_ok "already level with origin/main (ahead=$ahead)"

if [ $DRY -eq 1 ]; then log "dry run: would pull $behind commit(s)"; write_state "dry-run" "behind=$behind ahead=$ahead"; exit 0; fi

if ! git rebase -q --autostash origin/main 2>>"$LOG"; then
  conflicts=$(git diff --name-only --diff-filter=U | tr '\n' ' ')
  git rebase --abort 2>>"$LOG" || true
  if [ -n "$conflicts" ]; then
    fail "rebase onto origin/main conflicted — aborted, your work is intact. Conflicting: $conflicts"
  else
    fail "rebase onto origin/main failed (not a conflict) — see the git error in $LOG"
  fi
fi

log "pulled $behind commit(s) from origin/main"
done_ok "pulled $behind commit(s) (ahead=$ahead)"
