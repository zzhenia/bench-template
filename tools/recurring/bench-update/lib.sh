# Shared by check.sh and update.sh. Sourced with the bench root as cwd.
UPSTREAM_URL="${BENCH_UPSTREAM_URL:-https://github.com/zzhenia/bench-template.git}"
UP_REF="refs/bench-upstream/main"
BASE_FILE="config/bench-upstream"          # last upstream commit applied here
STATE="$(git rev-parse --git-dir)/bench-update"   # per-clone: date + fail count
# Yours, never touched by an update.
KEEP=(':!convos' ':!config/keys.env' ':!config/bench.env' ':!.claude/settings.local.json' ':!config/bench-upstream')

fetch_upstream() {
  git fetch -q --no-tags "$UPSTREAM_URL" "+main:$UP_REF" 2>/dev/null
}

# The upstream commit this bench last matched. A "Use this template" copy shares
# no history with upstream, so: the recorded base, else a common ancestor (a
# fork), else the upstream commit whose files equal this bench's first commit.
find_base() {
  local b
  b=$(cat "$BASE_FILE" 2>/dev/null)
  if [ -n "$b" ] && git cat-file -e "$b^{commit}" 2>/dev/null; then echo "$b"; return; fi
  b=$(git merge-base HEAD "$UP_REF" 2>/dev/null) && { echo "$b"; return; }
  local root_tree c
  root_tree=$(git rev-parse "$(git rev-list --max-parents=0 HEAD | tail -1)^{tree}")
  for c in $(git rev-list "$UP_REF"); do
    [ "$(git rev-parse "$c^{tree}")" = "$root_tree" ] && { echo "$c"; return; }
  done
  return 1
}

pending_count() {
  git rev-list --count "$1..$UP_REF" -- . "${KEEP[@]}"
}
