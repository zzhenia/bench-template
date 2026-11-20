#!/bin/bash
# SessionStart hook: once a day, see whether the bench template has changes
# this bench hasn't taken, and say so. No output when there is nothing to say.
# Offline or GitHub down: quiet for three days running, then one warning a day.
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../../..}" || exit 0
. tools/recurring/bench-update/lib.sh
today=$(date +%F)
{ read -r last fails < "$STATE"; } 2>/dev/null
fails=${fails:-0}
[ "$last" = "$today" ] && exit 0
say() { jq -n --arg m "$1" '{systemMessage:$m}'; }

if ! fetch_upstream; then
  fails=$((fails+1)); echo "$today $fails" > "$STATE"
  [ "$fails" -gt 3 ] && say "Bench update check failed $fails days running (offline, or GitHub unreachable)."
  exit 0
fi
echo "$today 0" > "$STATE"
base=$(find_base) || exit 0
n=$(pending_count "$base")
[ "$n" -gt 0 ] && say "Bench update: $n new change(s) in the bench template. Type /update to apply."
exit 0
