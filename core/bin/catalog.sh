#!/bin/bash
# List every skill and tool on this bench with a one-line description, as
# tab-separated rows: kind <TAB> name <TAB> where <TAB> description.
#   kind  = skill | tool | job (a tool with a schedule)
#   where = core (shared by every bench) | bench (this bench only)
# A skill's line is the `description:` in its SKILL.md. A tool's line is the
# `description:` in its instructions.md frontmatter, else its first prose line.
cd "$(dirname "$0")/../.." || exit 1

desc_of() {  # $1 = file; prints frontmatter description or first prose line
  awk '
    NR==1 && /^---$/ { fm=1; next }
    fm && /^---$/ { fm=0; next }
    fm && /^description:/ { sub(/^description:[ ]*/, ""); gsub(/^["'\'']|["'\'']$/, ""); print; found=1; exit }
    fm { next }
    /^[[:space:]]*$/ || /^#/ || /^```/ || /^\*\*[^*]+:\*\*[[:space:]]*$/ || /^[-=]+$/ { next }
    { gsub(/\*\*/, ""); print; exit }
  ' "$1" 2>/dev/null | cut -c1-200
}

script_desc() {  # $1 = tool folder; first comment or docstring line of its main script
  local s; s=$(ls "$1"/*.sh "$1"/*.py "$1"/*.js 2>/dev/null | head -1); [ -n "$s" ] || return
  awk '
    NR==1 && /^#!/ { next }
    /^[[:space:]]*$/ || /^(import|from|set|cd|use) / || /^# -\*-/ { next }
    /^"""/ { sub(/^"""/, ""); sub(/"""$/, ""); if ($0 != "") { print; exit } ds=1; next }
    ds { print; exit }
    /^(#|\/\/)/ { sub(/^(#|\/\/)+[[:space:]]*/, ""); if ($0 != "") { print; exit } next }
    { exit }
  ' "$s" | cut -c1-200
}

row() { printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4"; }

for src in core/skills:core personal/skills:bench; do
  dir=${src%%:*}; where=${src##*:}
  for f in "$dir"/*/SKILL.md; do
    [ -f "$f" ] || continue
    n=$(basename "$(dirname "$f")")
    row skill "$n" "$where" "$(desc_of "$f")"
  done
done

for src in core/tools:core tools/on-demand:bench tools/recurring:bench; do
  dir=${src%%:*}; where=${src##*:}
  for d in "$dir"/*/; do
    [ -d "$d" ] || continue
    [ -L "${d%/}" ] && continue          # old path left as a link into core
    n=$(basename "$d")
    kind=tool
    { [ "$dir" = tools/recurring ] || ls "$d" | grep -qE '(^schedule\.plist$|\.plist$)'; } && kind=job
    f="$d/instructions.md"; [ -f "$f" ] || f=$(ls "$d"/*.md 2>/dev/null | head -1)
    d1=$( [ -n "$f" ] && desc_of "$f")
    [ -z "$d1" ] && d1=$(script_desc "$d")
    row "$kind" "$n" "$where" "$d1"
  done
done
