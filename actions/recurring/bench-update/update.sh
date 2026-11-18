#!/bin/bash
# Apply the bench template's new changes to this bench as one commit.
# Exit 0 = applied (or nothing to do); 3 = conflicts left in the files listed;
# 1 = could not start (message says why). Your convos, keys and settings are never touched.
cd "$(dirname "$0")/../../.." || exit 1
. actions/recurring/bench-update/lib.sh
[ -z "$(git status --porcelain)" ] || { echo "Uncommitted changes; commit them first."; exit 1; }
fetch_upstream || { echo "Could not reach $UPSTREAM_URL"; exit 1; }
base=$(find_base) || { echo "Could not tell which template version this bench started from."; exit 1; }
up=$(git rev-parse "$UP_REF")
[ "$(pending_count "$base")" -gt 0 ] || { echo "Already up to date."; exit 0; }
log=$(git log --format='- %s' "$base..$up" -- . "${KEEP[@]}")
git diff --binary "$base" "$up" -- . "${KEEP[@]}" > "$(git rev-parse --git-dir)/bench-update.patch"
git apply --3way --index "$(git rev-parse --git-dir)/bench-update.patch" 2>/dev/null
echo "$up" > "$BASE_FILE"; git add "$BASE_FILE"
conflicts=$(git diff --name-only --diff-filter=U)
if [ -n "$conflicts" ]; then
  echo "CONFLICTS (upstream $up):"; echo "$conflicts"; echo "CHANGES:"; echo "$log"; exit 3
fi
git commit -q -m "bench update from template ${up:0:7}" -m "$log"
echo "Applied $(git rev-list --count "$base..$up" -- . "${KEEP[@]}") change(s):"; echo "$log"
git diff --name-only HEAD~1 | grep -qE '^(setup\.sh|actions/.*\.plist)$' && echo "RUN_SETUP: setup.sh or a schedule changed; run bash setup.sh"
exit 0
