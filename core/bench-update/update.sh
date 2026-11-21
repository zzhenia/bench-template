#!/bin/bash
# Apply the bench template's new changes to this bench as one commit.
# Exit 0 = applied (or nothing to do); 3 = conflicts left in the files listed;
# 1 = could not start (message says why). Your convos, keys and settings are never touched.
# --auto (the nightly run): uncommitted files are fine unless the update touches them,
# and a conflict is undone instead of left in the files.
cd "$(dirname "$0")/../.." || exit 1
. core/bench-update/lib.sh
# Editor and terminal settings (core/env): applied on every run, even with no update.
apply_env() { python3 core/env/apply.py </dev/null | sed 's/^/ENV: /'; }
AUTO=0; [ "${1:-}" = "--auto" ] && AUTO=1
[ $AUTO = 1 ] || [ -z "$(git status --porcelain)" ] || { echo "Uncommitted changes; commit them first."; exit 1; }
[ -n "$UPSTREAM_URL" ] || { echo "No BENCH_UPSTREAM_URL in config/bench.env; this bench takes no updates."; exit 1; }
fetch_upstream || { echo "Could not reach $UPSTREAM_URL"; exit 1; }
base=$(find_base) || { echo "Could not tell which template version this bench started from."; exit 1; }
up=$(git rev-parse "$UP_REF")
# Bench layout (core/bench-update/shape.sh): old skill copies out, master-instructions.md in.
shape() { [ -f core/bench-update/shape.sh ] && bash core/bench-update/shape.sh; }
if [ "$(pending_count "$base")" -eq 0 ]; then
  out=$(shape); [ -n "$out" ] && echo "$out" && git commit -q -m "bench shape: one home per skill" -m "$out"
  echo "Already up to date."; apply_env; exit 0
fi
if [ $AUTO = 1 ]; then
  busy=$(comm -12 <(git diff --name-only "$base" "$up" -- "${PATHS[@]}" "${KEEP[@]}" | sort) \
                  <(git status --porcelain | cut -c4- | sort))
  [ -z "$busy" ] || { echo "Uncommitted changes in files the update touches: $busy"; exit 1; }
fi
log=$(git log --format='- %s' "$base..$up" -- "${PATHS[@]}" "${KEEP[@]}")
git diff --binary "$base" "$up" -- "${PATHS[@]}" "${KEEP[@]}" > "$(git rev-parse --git-dir)/bench-update.patch"
git apply --3way --index "$(git rev-parse --git-dir)/bench-update.patch" 2>/dev/null
echo "$up" > "$BASE_FILE"; git add "$BASE_FILE"
bash core/bin/link-skills.sh >/dev/null 2>&1 && git add -A "$(bash core/bin/link-skills.sh --dir)" 2>/dev/null
shaped=$(shape)
conflicts=$(git diff --name-only --diff-filter=U)
if [ -n "$conflicts" ] && [ $AUTO = 1 ]; then
  git reset -q --merge HEAD
  echo "BASE $base"; echo "CONFLICTS (upstream $up):"; echo "$conflicts"; exit 3
fi
if [ -n "$conflicts" ]; then
  echo "CONFLICTS (upstream $up):"; echo "$conflicts"; echo "CHANGES:"; echo "$log"; exit 3
fi
git commit -q -m "bench update from template ${up:0:7}" -m "$log"
[ -n "$shaped" ] && echo "$shaped"
echo "Applied $(git rev-list --count "$base..$up" -- "${PATHS[@]}" "${KEEP[@]}") change(s):"; echo "$log"
git diff --name-only HEAD~1 | grep -qE '^(setup\.sh|(core|tools)/.*\.plist)$' && echo "RUN_SETUP: setup.sh or a schedule changed; run bash setup.sh"
apply_env
exit 0
