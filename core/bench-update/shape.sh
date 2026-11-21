#!/bin/bash
# Bring this bench to the layout every bench shares. Run by update.sh on every
# /update and every nightly run; safe to run by hand. Stages what it changes and
# prints one "SHAPE: ..." line per change; the caller commits.
#
# - Skills have one home: core/skills/<n> or personal/skills/<n>. The folder
#   Claude Code reads (skills/, via .claude/skills) holds links only.
#   A real folder there that also exists in core/ or personal/ is an old copy
#   and is removed (git rm; it stays in history). A real folder with no other
#   home moves to personal/skills/<n>. A folder with uncommitted changes is
#   left alone and reported.
# - master-instructions.md: every bench has one at its root, the first file a
#   session reads. Created from core/bench-update/master-instructions.template.md
#   when missing.
cd "$(dirname "$0")/../.." || exit 1
dir=$(bash core/bin/link-skills.sh --dir)
[ -n "$dir" ] || exit 1

for d in "$dir"/*/; do
  d=${d%/}; n=${d##*/}
  [ -n "$n" ] && [ -d "$d" ] && [ ! -L "$d" ] || continue
  if [ -n "$(git status --porcelain -- "$d")" ]; then
    echo "SHAPE: left $d alone: it has uncommitted changes; merge it into its home by hand"
    continue
  fi
  if [ -d "core/skills/$n" ] || [ -d "personal/skills/$n" ]; then
    home=core/skills/$n; [ -d "personal/skills/$n" ] && home=personal/skills/$n
    git rm -rq -- "$d" >/dev/null 2>&1
    find "$d" \( -name .DS_Store -o -name '*.pyc' \) -delete 2>/dev/null
    find "$d" -depth -type d -empty -delete 2>/dev/null
    echo "SHAPE: removed old copy $d (home: $home)"
  else
    mkdir -p personal/skills
    git mv -- "$d" "personal/skills/$n" 2>/dev/null || mv -- "$d" "personal/skills/$n"
    echo "SHAPE: moved $d to personal/skills/$n (its only copy)"
  fi
done
bash core/bin/link-skills.sh >/dev/null 2>&1
git add -A -- "$dir" personal/skills 2>/dev/null

# Core files have one home: core/. A tracked file elsewhere with exactly the
# same content as a core file is an old copy (scripts/nobreaks.sh,
# .claude/scripts/*, config/warp/*) and is removed. convos/, personal/, state/
# and node_modules/ are never checked; files under 64 bytes are skipped.
git ls-files -s -- . ':!skills' ':!convos' ':!personal' ':!state' ':!**/node_modules/**' |
awk -F'\t' '{split($1, m, " "); if (m[1] == "120000") next
  if ($2 ~ /^core\//) core[m[2]] = $2; else { sha[NR] = m[2]; path[NR] = $2 } }
  END { for (i in path) if (sha[i] in core) print path[i] "\t" core[sha[i]] }' |
while IFS=$'\t' read -r f home; do
  [ -f "$f" ] && [ "$(wc -c < "$f")" -ge 64 ] || continue
  if [ -n "$(git status --porcelain -- "$f")" ]; then
    echo "SHAPE: left $f alone: same as $home but it has uncommitted changes"
  else
    git rm -q -- "$f" && echo "SHAPE: removed old copy $f (home: $home)"
    find "$(dirname "$f")" -depth -type d -empty -delete 2>/dev/null
  fi
done

if [ ! -f master-instructions.md ]; then
  cp core/bench-update/master-instructions.template.md master-instructions.md
  git add master-instructions.md
  echo "SHAPE: created master-instructions.md from the template; fill in this bench's own parts"
fi
exit 0
