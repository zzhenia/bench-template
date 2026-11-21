#!/bin/bash
# Link every skill in core/skills/ and personal/skills/ into the folder Claude
# Code reads (.claude/skills, or wherever that symlink points). Removes links
# whose skill is gone; leaves real folders alone. Personal wins on a name clash.
# --dir prints the folder it links into and exits.
cd "$(dirname "$0")/../.." || exit 1
dir=.claude/skills
if [ -L "$dir" ]; then dir=$(cd "$(dirname "$dir")" && cd "$(readlink skills)" && pwd -P); dir=${dir#"$(pwd -P)/"}; fi
[ "${1:-}" = --dir ] && { echo "$dir"; exit 0; }
mkdir -p "$dir"
up=$(echo "$dir" | sed -E 's#[^/]+#..#g')          # .claude/skills -> ../..
for src in core/skills personal/skills; do
  for s in "$src"/*/; do
    [ -f "$s/SKILL.md" ] || continue
    n=$(basename "$s")
    [ -e "$dir/$n" ] && [ ! -L "$dir/$n" ] && { echo "skip $n: $dir/$n is a real folder" >&2; continue; }
    ln -sfn "$up/$src/$n" "$dir/$n"
  done
done
for l in "$dir"/*; do [ -L "$l" ] && [ ! -e "$l" ] && rm "$l"; done
exit 0
