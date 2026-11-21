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

if [ ! -f master-instructions.md ]; then
  cp core/bench-update/master-instructions.template.md master-instructions.md
  git add master-instructions.md
  echo "SHAPE: created master-instructions.md from the template; fill in this bench's own parts"
fi
exit 0
