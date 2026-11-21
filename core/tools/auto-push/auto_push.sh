#!/bin/bash
# Auto-Push — nightly git safety net for one bench.
#
# Commits everything finished in the working tree, rebases onto origin/main,
# pushes. No Claude call anywhere in here: zero tokens. Session notes and ticket
# comments stay with the interactive /push, which is confirmation-gated.
#
# Each bench installs its own job (core/bin/install-schedules.sh); this script
# works on the bench it lives in, or on BENCH_ROOT when set.
#
# Failure = Slack DM to the owner of SLACK_USER_TOKEN (config/keys.env), else a
# macOS notification, plus a session-start notice. Success is silent apart from
# state/auto-push/state.json and the log.
#
# Settings (config/bench.env, all optional):
#   BENCH_GIT_SSH_KEY=~/.ssh/<key>   push over ssh with this key (launchd has no ssh-agent)
#   AUTO_PUSH_TIDY_DOTFILES=yes      keep only the newest 3 ~/.<file>_oldNN backups
#
# Usage: auto_push.sh [--dry-run]

set -u
ROOT="${BENCH_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd -P)}"
NAME=$(basename "$ROOT")
STATE_DIR="$ROOT/state/auto-push"
STATE="$STATE_DIR/state.json"
LOG="$STATE_DIR/auto-push.log"
STALE_MIN=15                              # skip files touched in the last N minutes (mid-edit guard)
MAX_MB=5                                  # untracked files bigger than this stay out
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
mkdir -p "$STATE_DIR"

setting() {  # KEY — value from config/bench.env, else empty
  grep -E "^$1=" "$ROOT/config/bench.env" 2>/dev/null | tail -1 | cut -d= -f2- | sed -E "s/^[\"']//; s/[\"']$//"
}

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
SSH_KEY=$(setting BENCH_GIT_SSH_KEY); SSH_KEY="${SSH_KEY/#\~/$HOME}"
[ -n "$SSH_KEY" ] && export GIT_SSH_COMMAND="ssh -o IdentitiesOnly=yes -i $SSH_KEY -o BatchMode=yes"
export GIT_TERMINAL_PROMPT=0

log() { printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG"; }

# Home-folder tidy (opt-in): keep the newest 3 numbered backups of each
# dotfile (~/.zshrc_old01…), delete older ones.
if [ "$(setting AUTO_PUSH_TIDY_DOTFILES)" = "yes" ]; then
  for base in $(ls -a "$HOME" | sed -n 's/^\(\..*\)_old[0-9][0-9]*$/\1/p' | sort -u); do
    ls -t "$HOME/${base}"_old[0-9]* 2>/dev/null | tail -n +4 | while read -r f; do
      if [ $DRY = 1 ]; then log "tidy (dry): would delete $f"; else rm -f "$f" && log "tidy: deleted $f"; fi
    done
  done
fi

write_state() {  # status, summary
  python3 - "$STATE" "$1" "$2" <<'PY'
import json, sys, datetime
path, status, summary = sys.argv[1:4]
json.dump({"last_run": datetime.datetime.now().isoformat(timespec="seconds"),
           "status": status, "summary": summary}, open(path, "w"), indent=2)
PY
}

notice_path() { local d; d=$(git -C "$ROOT" rev-parse --absolute-git-dir 2>/dev/null) && echo "$d/bench-notices/${1:-auto-push}"; }

notify() {  # text [notice name] — Slack self-DM, else macOS notification; plus a session-start notice
  local token n
  n=$(notice_path "${2:-auto-push}"); [ -n "$n" ] && mkdir -p "$(dirname "$n")" && printf '%s\n' "$1" > "$n"
  token=$(grep -E '^(export )?SLACK_USER_TOKEN=' "$ROOT/config/keys.env" 2>/dev/null | head -1 | sed -E 's/^(export )?SLACK_USER_TOKEN=//; s/^["'\'']//; s/["'\'']$//')
  python3 - "$token" "$1" <<'PY'
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
  [ $DRY -eq 1 ] || notify ":warning: *Auto-push failed* ($NAME, $(date '+%a %H:%M'))
$1
Fix by hand or run \`/push\` in a bench session. Log: \`$LOG\`"
  exit 1
}

cd "$ROOT" || fail "cannot cd to $ROOT"
log "--- run start $NAME (dry=$DRY)"

# ── pre-flight ────────────────────────────────────────────────────────────────
[ -d .git/rebase-merge ] || [ -d .git/rebase-apply ] && fail "a rebase is already in progress in the working tree — left untouched"
[ -f .git/MERGE_HEAD ] && fail "a merge is in progress in the working tree — left untouched"
[ -f .git/index.lock ] && fail "index.lock present (another git process running?) — skipped tonight"
[ "$(git branch --show-current)" = "main" ] || fail "checked-out branch is '$(git branch --show-current)', not main — skipped"
[ -z "$SSH_KEY" ] || [ -r "$SSH_KEY" ] || fail "deploy key $SSH_KEY (BENCH_GIT_SSH_KEY) missing"

# ── refresh AUTOMATIONS.md (the living inventory of every scheduled job) ──────
if [ $DRY -eq 0 ]; then
  for inv in "$ROOT/core/tools/automation-status/inventory.py" "$ROOT/tools/on-demand/automation-status/inventory.py"; do
    [ -f "$inv" ] || continue
    python3 "$inv" >>"$LOG" 2>&1 || log "inventory.py failed (AUTOMATIONS.md left as it was)"
    break
  done
fi

# ── stage, with the three /push guards ────────────────────────────────────────
git add -A
skipped=()
while IFS= read -r -d '' f; do
  [ -e "$f" ] || continue                       # deletions: nothing to check
  if [ -n "$(find "$f" -mmin -$STALE_MIN 2>/dev/null)" ]; then
    git reset -q -- "$f"; skipped+=("$f (edited <${STALE_MIN}m ago)"); continue
  fi
  case "$(basename "$f" | tr 'A-Z' 'a-z')" in
    *token*|*secret*|*.pem|*.key|.env|*.env|keys.env)
      if ! git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
        git reset -q -- "$f"; skipped+=("$f (credential-shaped, new)"); continue
      fi;;
  esac
  if ! git ls-files --error-unmatch "$f" >/dev/null 2>&1; then
    sz=$(stat -f %z "$f"); if [ "$sz" -gt $((MAX_MB*1024*1024)) ]; then
      git reset -q -- "$f"; skipped+=("$f ($((sz/1048576)) MB, new)"); continue
    fi
  fi
done < <(git diff --cached --name-only -z)

n_staged=$(git diff --cached --name-only | wc -l | tr -d ' ')
for s in "${skipped[@]:-}"; do [ -n "$s" ] && log "left out: $s"; done

# ── commit ────────────────────────────────────────────────────────────────────
if [ "$n_staged" -gt 0 ]; then
  areas=$(git diff --cached --name-only | awk -F/ '{ if (($1=="actions"||$1=="core") && NF>3) print $1"/"$2"/"$3; else if (($1=="actions"||$1=="convos"||$1=="state") && NF>2) print $1"/"$2; else print $1 }' | sort -u)
  n_areas=$(printf '%s\n' "$areas" | wc -l | tr -d ' ')
  msg="auto-push: $n_staged files across $n_areas areas ($(date '+%Y-%m-%d'))"
  body=$(printf '%s\n' "$areas" | sed 's/^/- /')
  if [ $DRY -eq 1 ]; then
    log "DRY: would commit '$msg'"; printf '%s\n' "$body" | tee -a "$LOG"; git reset -q
  else
    git commit -q -m "$msg" -m "Nightly launchd auto-push (core/tools/auto-push). Areas:" -m "$body" \
      -m "Co-Authored-By: auto-push <noreply@bench>" || fail "git commit failed"
    log "committed: $msg"
  fi
else
  log "nothing new to commit"
fi

# ── sync with remote ──────────────────────────────────────────────────────────
git fetch -q origin || fail "git fetch failed (network / deploy key?)"
ahead=$(git rev-list --count origin/main..main); behind=$(git rev-list --count main..origin/main)
log "ahead=$ahead behind=$behind"
if [ $DRY -eq 1 ]; then write_state "dry-run" "ahead=$ahead behind=$behind staged=$n_staged"; log "--- dry run end"; exit 0; fi

if [ "$behind" -gt 0 ]; then
  # --autostash: the files deliberately left out above (edited <15 min ago) are
  # unstaged, and a plain rebase refuses to start while they exist.
  if ! git rebase -q --autostash origin/main 2>>"$LOG"; then
    conflicts=$(git diff --name-only --diff-filter=U | tr '\n' ' ')
    git rebase --abort 2>>"$LOG" || true
    if [ -n "$conflicts" ]; then
      fail "rebase onto origin/main conflicted — aborted, your local commit is intact. Conflicting: $conflicts"
    else
      fail "rebase onto origin/main failed (not a conflict) — see the git error in $LOG"
    fi
  fi
fi

if [ "$(git rev-list --count origin/main..main)" -gt 0 ]; then
  git push -q origin main 2>>"$LOG" || fail "git push rejected (see log)"
  log "pushed $(git rev-list --count "origin/main@{1}"..main 2>/dev/null || echo '?') commit(s)"
else
  log "already in sync — nothing to push"
fi

summary="staged=$n_staged pushed_ahead=$ahead pulled=$behind left_out=${#skipped[@]}"
write_state "ok" "$summary"
n=$(notice_path); [ -n "$n" ] && rm -f "$n"

# ── bench update from the template (core/bench-update/auto.sh) ────────────────
# Runs only after a clean push. Applies and pushes the template's new changes;
# a conflict becomes a pull request on the template. Anything to say goes out
# like a failure: Slack self-DM (else macOS notification) plus a session notice.
if [ -f "$ROOT/core/bench-update/auto.sh" ]; then
  upd=$(bash "$ROOT/core/bench-update/auto.sh" 2>>"$LOG")
  msg=$(printf '%s\n' "$upd" | sed -n '/^NOTIFY: /,$p' | sed 's/^NOTIFY: //')
  log "bench update: ${msg:-nothing to report}"
  if [ -n "$msg" ]; then notify ":arrows_counterclockwise: *Bench update* ($NAME)
$msg" bench-update
  else n=$(notice_path bench-update); [ -n "$n" ] && rm -f "$n"; fi
fi
log "--- run end: $summary"
