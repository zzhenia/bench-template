#!/bin/bash
# ow.sh — drive the Obsidian Writing workspace from the terminal (macOS).
# Run from anywhere inside the vault. Needs the obsidian-writing plugin enabled.
set -euo pipefail

usage() {
  cat <<'USAGE'
usage: ow.sh <command> [args]
  layout                      build the four panes: files | writing | reference | Claude Code
  ref <file>...               open file(s) in the reference pane (vault-relative or absolute)
  active <file>               open a file in the writing pane
  search <query>              search tab in the reference pane, e.g. 'tag:#RS-006'
  focus <writing|reference|terminal>
  tag <ID> <file>...          add ID to the frontmatter tags of each file
  ids                         list research-piece IDs found in the vault
  draft <ID|new> <slug> [--folder <dir>]   new "(ID) YYMMDD_slug.md", tagged, opened in the writing pane
  vault                       print the vault root
USAGE
}

find_vault() {
  if [ -n "${OW_VAULT:-}" ]; then echo "$OW_VAULT"; return; fi
  local d="$PWD"
  while [ "$d" != "/" ]; do
    [ -d "$d/.obsidian" ] && { echo "$d"; return; }
    d=$(dirname "$d")
  done
  echo "ow.sh: no .obsidian folder above $PWD (set OW_VAULT)" >&2; exit 1
}

VAULT=$(find_vault)
VAULT_NAME=$(basename "$VAULT")
PY=/usr/bin/python3
CONF="$VAULT/.obsidian/plugins/obsidian-writing/data.json"

urlenc() { $PY -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "$1"; }
rel() {  # vault-relative path
  local p="$1"
  case "$p" in /*) ;; *) p="$PWD/$p";; esac
  p=$($PY -c 'import os,sys;print(os.path.normpath(sys.argv[1]))' "$p")
  case "$p" in "$VAULT"/*) echo "${p#"$VAULT"/}";; *) echo "ow.sh: $1 is outside the vault" >&2; exit 1;; esac
}
uri() {  # uri action key=value...
  local q="do=$1"; shift
  for kv in "$@"; do q="$q&${kv%%=*}=$(urlenc "${kv#*=}")"; done
  open "obsidian://writing?vault=$(urlenc "$VAULT_NAME")&$q"
}
conf() { [ -f "$CONF" ] && $PY -c 'import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2],""))' "$CONF" "$1" || true; }
PREFIX=$(conf idPrefix); PREFIX=${PREFIX:-RS}

list_ids() {  # "ID<TAB>relative path" sorted by ID
  find "$VAULT" -name "($PREFIX-[0-9][0-9][0-9])*" -not -path '*/.obsidian/*' -not -path '*/.git/*' \
    | sed -E "s|^$VAULT/||" | $PY -c '
import re,sys
rows=[(re.search(r"\(([A-Z]+-\d{3})\)",l).group(1),l.rstrip("\n")) for l in sys.stdin if re.search(r"\(([A-Z]+-\d{3})\)",l)]
for i,p in sorted(rows): print(i+"\t"+p)'
}

cmd=${1:-}; shift || true
case "$cmd" in
  layout) uri layout ;;
  ref|reference) [ $# -ge 1 ] || { usage; exit 1; }
    for f in "$@"; do uri open "file=$(rel "$f")" pane=reference; sleep 0.4; done ;;
  active|writing) [ $# -eq 1 ] || { usage; exit 1; }; uri open "file=$(rel "$1")" pane=writing ;;
  search) [ $# -ge 1 ] || { usage; exit 1; }; uri search "query=$*" pane=reference ;;
  focus) uri focus "pane=${1:-writing}" ;;
  vault) echo "$VAULT" ;;
  ids) list_ids ;;
  tag) [ $# -ge 2 ] || { usage; exit 1; }; id=$1; shift
    for f in "$@"; do
      p="$VAULT/$(rel "$f")"
      $PY - "$p" "$id" <<'PYEOF'
import re,sys
path,tag=sys.argv[1],sys.argv[2]
s=open(path,encoding="utf-8").read()
m=re.match(r"^---\n(.*?)\n---\n",s,re.S)
if m:
    fm=m.group(1)
    tm=re.search(r"^tags:\s*(.*)$",fm,re.M)
    if tm:
        line=tm.group(0); val=tm.group(1).strip()
        if val.startswith("["):
            items=[x.strip().strip("'\"") for x in val.strip("[]").split(",") if x.strip()]
            if tag in items: sys.exit(0)
            items.append(tag); new="tags: ["+", ".join(items)+"]"
            fm=fm.replace(line,new,1)
        elif val=="":
            block=re.search(r"^tags:\s*\n((?:\s+-\s.*\n?)*)",fm,re.M)
            existing=re.findall(r"^\s+-\s*(.*)$",block.group(1),re.M) if block else []
            if tag in [e.strip().strip("'\"") for e in existing]: sys.exit(0)
            fm=fm.replace(block.group(0),block.group(0).rstrip("\n")+"\n  - "+tag+"\n",1)
        else:
            items=[x.strip() for x in val.split(",")]
            if tag in items: sys.exit(0)
            fm=fm.replace(line,"tags: ["+", ".join(items+[tag])+"]",1)
    else:
        fm=fm+"\ntags: ["+tag+"]"
    s="---\n"+fm+"\n---\n"+s[m.end():]
else:
    s="---\ntags: ["+tag+"]\n---\n"+s
open(path,"w",encoding="utf-8").write(s)
print("tagged",tag,path)
PYEOF
    done ;;
  draft) [ $# -ge 2 ] || { usage; exit 1; }; id=$1; slug=$2; shift 2; folder=""
    while [ $# -gt 0 ]; do case "$1" in --folder) folder=$2; shift 2;; *) echo "unknown arg $1" >&2; exit 1;; esac; done
    if [ "$id" = "new" ]; then
      last=$(list_ids | tail -1 | cut -f1 | sed -E 's/.*-//'); last=${last:-0}
      id=$(printf '%s-%03d' "$PREFIX" $((10#$last + 1)))
      [ -n "$folder" ] || folder=$(conf draftDir)
    else
      [ -n "$folder" ] || folder=$(dirname "$(list_ids | awk -F'\t' -v i="$id" '$1==i{print $2; exit}')")
      [ -n "$folder" ] && [ "$folder" != "." ] || folder=$(conf draftDir)
    fi
    folder=${folder:-.}
    mkdir -p "$VAULT/$folder"
    f="$folder/($id) $(date +%y%m%d)_$slug.md"
    n=2; base="$f"
    while [ -e "$VAULT/$f" ]; do f="${base%.md}_$(printf '%02d' $n).md"; n=$((n+1)); done
    printf -- '---\ntags: [%s]\n---\n\n# %s\n\n' "$id" "$slug" > "$VAULT/$f"
    echo "created $f"
    sleep 0.6   # let Obsidian index the new file
    uri open "file=$f" pane=writing ;;
  ""|-h|--help|help) usage ;;
  *) echo "ow.sh: unknown command $cmd" >&2; usage; exit 1 ;;
esac
