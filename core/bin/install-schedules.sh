#!/bin/bash
# install-schedules.sh — install this bench's scheduled jobs into launchd.
#
# Every core/tools/<name>/schedule.plist (and the bench's own
# tools/<name>/schedule.plist or tools/<group>/<name>/schedule.plist) is a
# launchd template. This renders its placeholders and installs it as
#   ~/Library/LaunchAgents/com.bench.<bench-slug>.<name>.plist
# then reloads the job, only when the rendered file changed or the job is not
# loaded. Run it after /update and after adding a template; it is idempotent.
#
# Placeholders:
#   __LABEL__       com.bench.<bench-slug>.<name>
#   __BENCH_PATH__  this bench's absolute path
#   __HOME__        $HOME
#   __PYTHON__      Homebrew Python for jobs that need 3.10+. Resolved as: $PYTHON;
#                   else the pinned python3.NN already in the installed plist
#                   or the old job it replaces (python-repin pins it); else the version python-repin has
#                   pinned on this Mac; else /opt/homebrew/bin/python3; else
#                   python3 on PATH; else /usr/bin/python3. A job that reads or
#                   writes under ~/Library/CloudStorage hardcodes /usr/bin/python3
#                   instead (Homebrew Python re-triggers the macOS privacy prompt).
#
# One-per-Mac jobs: a template containing "bench-schedule: one-per-mac" runs once
# per Mac (LaunchAgents are machine-wide). When another bench already runs it,
# this bench is skipped; add this bench's path to "other_benches" in that
# bench's config/<name>.json instead.
#
# Old jobs: a LaunchAgent with another label that runs this bench's copy of the
# same tool (e.g. from before the tool moved to core/) would double-run. It is
# reported and the job skipped, unless --replace-legacy is given: then the old
# job is unloaded and its plist removed before the new one is installed.
#
# Settings (config/bench.env, optional):
#   BENCH_SLUG=<slug>   label part; default: the bench folder name, lowercased
#
# Usage:
#   install-schedules.sh [--dry-run] [--replace-legacy] [name ...]
#   install-schedules.sh --list
# With names, only those jobs are handled.

set -u
BENCH="${BENCH_ROOT:-$(cd "$(dirname "$0")/../.." && pwd -P)}"
AGENTS="$HOME/Library/LaunchAgents"
DRY=0; LIST=0; REPLACE=0; ONLY=()
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --list) LIST=1 ;;
    --replace-legacy) REPLACE=1 ;;
    -h|--help) sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "unknown option: $a" >&2; exit 2 ;;
    *) ONLY+=("$a") ;;
  esac
done

[ "$(uname)" = "Darwin" ] || { echo "Scheduled jobs use launchd, which needs macOS — nothing installed."; exit 0; }

setting() { grep -E "^$1=" "$BENCH/config/bench.env" 2>/dev/null | tail -1 | cut -d= -f2- | sed -E "s/^[\"']//; s/[\"']$//"; }
SLUG=$(setting BENCH_SLUG)
[ -n "$SLUG" ] || SLUG=$(basename "$BENCH" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g')

templates() {
  local f
  for f in "$BENCH"/core/tools/*/schedule.plist "$BENCH"/tools/*/schedule.plist "$BENCH"/tools/*/*/schedule.plist; do
    [ -f "$f" ] || continue
    case "$f" in *"/~archive/"*|*"/archive/"*) continue ;; esac
    echo "$f"
  done
}

wanted() {  # name
  [ ${#ONLY[@]} -eq 0 ] && return 0
  local n; for n in "${ONLY[@]}"; do [ "$n" = "$1" ] && return 0; done; return 1
}

loaded() { launchctl list "$1" >/dev/null 2>&1; }

repin_python() {  # the python3.NN python-repin has pinned on this Mac, if any
  local f bench v
  for f in "$AGENTS"/*.plist; do
    grep -q "python-repin/repin.py" "$f" 2>/dev/null || continue
    bench=$(grep -o '<string>/[^<]*/core/tools/python-repin/repin.py' "$f" | head -1 | sed 's|<string>||; s|/core/tools/python-repin/repin.py||')
    [ -n "$bench" ] && [ -f "$bench/state/python-repin/state.json" ] || continue
    v=$(/usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("pinned",""))' "$bench/state/python-repin/state.json" 2>/dev/null)
    [ -n "$v" ] && [ -x "/opt/homebrew/bin/python$v" ] && { echo "/opt/homebrew/bin/python$v"; return; }
  done
}

resolve_python() {  # installed-plist [old-job-plists...]
  local p
  [ -n "${PYTHON:-}" ] && { echo "$PYTHON"; return; }
  p=$(cat "$@" 2>/dev/null | grep -o '/opt/homebrew/bin/python3\.[0-9][0-9]*' | head -1)
  [ -n "$p" ] && [ -x "$p" ] && { echo "$p"; return; }
  p=$(repin_python); [ -n "$p" ] && { echo "$p"; return; }
  [ -x /opt/homebrew/bin/python3 ] && { echo /opt/homebrew/bin/python3; return; }
  command -v python3 2>/dev/null || echo /usr/bin/python3
}

tool_paths() {  # name — path fragments a LaunchAgent running this bench's copy would contain
  printf '%s\n' "$BENCH/core/tools/$1/" "$BENCH/tools/$1/" "$BENCH/tools/recurring/$1/" "$BENCH/tools/on-demand/$1/"
}

legacy_jobs() {  # name own-plist — other LaunchAgents running this bench's copy of the tool
  local f
  for f in "$AGENTS"/*.plist; do
    [ "$f" = "$2" ] && continue
    grep -qF -f <(tool_paths "$1") "$f" 2>/dev/null && echo "$f"
  done
}

other_bench_job() {  # name own-plist — a LaunchAgent running another bench's copy (one-per-Mac jobs)
  local f
  for f in "$AGENTS"/*.plist; do
    [ "$f" = "$2" ] && continue
    grep -qE "/(core/tools|tools/recurring|tools)/$1/" "$f" 2>/dev/null || continue
    grep -qF "$BENCH/" "$f" && continue
    echo "$f"; return
  done
}

label_of() { [ -f "$1" ] && /usr/libexec/PlistBuddy -c 'Print :Label' "$1" 2>/dev/null || basename "$1" .plist; }

render() {  # template label python
  sed -e "s|__LABEL__|$2|g" -e "s|__BENCH_PATH__|$BENCH|g" -e "s|__HOME__|$HOME|g" -e "s|__PYTHON__|$3|g" "$1"
}

mkdir -p "$AGENTS"
n_tpl=0; rc=0
[ $DRY -eq 1 ] && echo "(dry run: nothing is written, loaded or unloaded)"
[ $LIST -eq 1 ] && printf '%-16s %-44s %s\n' JOB LABEL STATUS

while IFS= read -r tpl; do
  name=$(basename "$(dirname "$tpl")")
  wanted "$name" || continue
  n_tpl=$((n_tpl+1))
  label="com.bench.$SLUG.$name"
  plist="$AGENTS/$label.plist"
  one_per_mac=0; grep -q "bench-schedule: one-per-mac" "$tpl" && one_per_mac=1
  other=""; [ $one_per_mac -eq 1 ] && other=$(other_bench_job "$name" "$plist")
  legacy=$(legacy_jobs "$name" "$plist")

  if [ $LIST -eq 1 ]; then
    if [ -n "$other" ]; then st="runs for another bench ($(label_of "$other"))"
    elif [ -f "$plist" ] && loaded "$label"; then st="installed, loaded"
    elif [ -f "$plist" ]; then st="installed, NOT loaded"
    else st="not installed"; fi
    [ -n "$legacy" ] && st="$st; old job: $(for l in $legacy; do label_of "$l"; done | tr '\n' ' ')"
    [ $one_per_mac -eq 1 ] && st="$st [one per Mac]"
    printf '%-16s %-44s %s\n' "$name" "$label" "$st"
    continue
  fi

  if [ -n "$other" ]; then
    echo "  $name: already runs on this Mac for another bench ($(label_of "$other")) — skipped."
    echo "    To cover this bench too, add \"$BENCH\" to other_benches in that bench's config/$name.json."
    continue
  fi

  py=$(resolve_python "$plist" $legacy)
  if [ -n "$legacy" ]; then
    if [ $REPLACE -eq 0 ]; then
      echo "  $name: an old job already runs this bench's copy: $(for l in $legacy; do label_of "$l"; done | tr '\n' ' ')— skipped."
      echo "    Re-run with --replace-legacy to unload and remove it and install $label."
      rc=1; continue
    fi
    for l in $legacy; do
      if [ $DRY -eq 1 ]; then echo "  $name: would unload and remove old job $(label_of "$l") ($l)"
      else old=$(label_of "$l"); launchctl unload "$l" >/dev/null 2>&1; rm -f "$l" && echo "  $name: removed old job $old"; fi
    done
  fi

  new=$(render "$tpl" "$label" "$py")
  if [ -f "$plist" ] && [ "$(cat "$plist")" = "$new" ] && loaded "$label"; then
    echo "  $name: unchanged ($label)"
    continue
  fi
  if [ $DRY -eq 1 ]; then
    if [ -f "$plist" ]; then echo "  $name: would update and reload $label"; else echo "  $name: would install and load $label"; fi
    grep -q "__PYTHON__" "$tpl" && echo "    python: $py"
    continue
  fi
  mkdir -p "$BENCH/state/$name"
  tmp=$(mktemp); printf '%s\n' "$new" > "$tmp"
  if ! plutil -lint -s "$tmp" >/dev/null; then echo "  $name: rendered plist is invalid — not installed"; rm -f "$tmp"; rc=1; continue; fi
  [ -f "$plist" ] && launchctl unload "$plist" >/dev/null 2>&1
  mv "$tmp" "$plist"
  if launchctl load "$plist" && loaded "$label"; then
    echo "✓ $name: loaded ($label)"
  else
    echo "  $name: could not load — try: launchctl load \"$plist\""; rc=1
  fi
done < <(templates)

[ $n_tpl -eq 0 ] && echo "No schedule.plist templates${ONLY[*]:+ for: ${ONLY[*]}}."
if [ $LIST -eq 1 ]; then
  for f in "$AGENTS"/com.bench."$SLUG".*.plist; do
    [ -f "$f" ] || continue
    n=${f##*/com.bench.$SLUG.}; n=${n%.plist}
    [ -f "$BENCH/core/tools/$n/schedule.plist" ] || ls "$BENCH"/tools/"$n"/schedule.plist "$BENCH"/tools/*/"$n"/schedule.plist >/dev/null 2>&1 \
      || printf '%-16s %-44s %s\n' "$n" "com.bench.$SLUG.$n" "installed, no template (remove with launchctl unload + rm)"
  done
fi
exit $rc
