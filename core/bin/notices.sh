#!/bin/bash
# SessionStart hook: show any bench notice waiting in .git/bench-notices/
# (written by jobs that run unattended, e.g. a blocked core publish), so a
# bench owner without Slack still hears about it. Notices stay until the job
# that wrote one succeeds and deletes it.
cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}" || exit 0
d="$(git rev-parse --git-dir 2>/dev/null)/bench-notices"
ls "$d"/* >/dev/null 2>&1 || exit 0
msg=$(cat "$d"/* | head -c 1500)
jq -n --arg m "$msg" '{systemMessage:$m}'
