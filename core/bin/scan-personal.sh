#!/bin/bash
# Look for personal details in the given paths (default: core/) before they are
# published. Prints file:line: match for each hit; exit 1 when there are hits.
#   Built in: e-mail addresses, home-folder paths, Slack IDs, IP addresses.
#   config/private-terms.txt: this bench's own words (names, domains, ticket
#     prefixes), one extended regex per line, case-insensitive. Never published.
#   core/scan-allow.txt: regexes for hits that are fine (e.g. example.com).
cd "$(dirname "$0")/../.." || exit 2
[ $# -gt 0 ] || set -- core
patterns=(
  '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
  '/(Users|home)/[a-z][a-z0-9._-]+'
  '\b[CDGUW]0[A-Z0-9]{8,10}\b'
  '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b'
)
args=(); for p in "${patterns[@]}"; do args+=(-e "$p"); done
hits=$(grep -rnIEo --exclude-dir=.git "${args[@]}" "$@" 2>/dev/null)
if [ -s config/private-terms.txt ]; then
  terms=$(grep -vE '^\s*(#|$)' config/private-terms.txt)
  [ -n "$terms" ] && hits+=$'\n'$(grep -rnIEoi --exclude-dir=.git -f <(echo "$terms") "$@" 2>/dev/null)
fi
if [ -s core/scan-allow.txt ]; then
  hits=$(echo "$hits" | grep -vE -f <(grep -vE '^\s*(#|$)' core/scan-allow.txt))
fi
hits=$(echo "$hits" | grep -v '^$' | sort -u)
[ -z "$hits" ] && exit 0
echo "$hits"; exit 1
