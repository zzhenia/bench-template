#!/bin/bash
# nobreaks — unwrap hard-wrapped text.
#
# Joins lines that are continuations of the same paragraph, and leaves
# alone: blank lines (paragraph breaks), list items (-, *, +, •, 1., 1)),
# headings (#), quotes (>), setext underlines and rules (===, ---, ***),
# fenced code blocks (``` / ~~~), and indented lines (code blocks).
# Paths split by a terminal wrap are rejoined without the stray space.
#
#   nobreaks              # no stdin: read clipboard, write clipboard
#   nobreaks < file       # stdin -> stdout
#   nobreaks file...      # file(s) -> stdout
#   pbpaste | nobreaks    # stdin -> stdout
#   nobreaks -c file      # force clipboard output
#   nobreaks -p           # force clipboard input
#   nobreaks -d           # dump input with line endings shown (debug)
#   nobreaks -h           # help

set -euo pipefail

usage() { awk 'NR>1 && /^#/ { sub(/^# ?/, ""); print; next } NR>1 { exit }' "$0"; exit 0; }

TO_CLIP=0
FROM_CLIP=0
DUMP=0
FILES=()
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage ;;
    -c|--clipboard) TO_CLIP=1; shift ;;
    -p|--paste) FROM_CLIP=1; shift ;;
    -d|--dump) DUMP=1; shift ;;
    --) shift; FILES+=("$@"); break ;;
    -*) echo "nobreaks: unknown option $1" >&2; exit 2 ;;
    *) FILES+=("$1"); shift ;;
  esac
done

# Byte semantics on purpose: a codepoint > 255 in the pattern (\x{2022}) would
# flip the whole regex to Unicode rules against undecoded bytes, so • is spelled
# as its UTF-8 bytes instead.
unwrap() {
perl -0777 -pe '
  s/\r\n?/\n/g;                       # normalize CRLF
  s/(?:[ \t]|\xc2\xa0)+$//mg;         # strip trailing whitespace (incl. NBSP)
  my @fence;                          # park fenced code blocks, restored at the end
  s{^((?:```|~~~)[^\n]*\n.*?(?:^(?:```|~~~)[^\n]*$|\z))}
   {push @fence, $1; "\x00" . $#fence . "\x00"}egms;
  s/^[ ]{1,3}(?![-*+]\s|\xe2\x80\xa2\s|\d{1,3}[.)]\s|>|\#{1,6}[ \t])(?=\S)//mg;
                                      # 1-3 leading spaces = wrap artifact, not code
                                      # (kept when they indent a nested list item)
  1 while s/^(?!\x00)((?:[ ]{0,3}\S|[ ]*(?:[-*+]|\xe2\x80\xa2|\d{1,3}[.)])\s)[^\n]*\n)[ \t]{4,}(?![-*+]\s|\xe2\x80\xa2\s|\d{1,3}[.)]\s|>|\#{1,6}[ \t])(?=\S)/$1/mg;
                                      # 4+ indent directly under a text line = wrapped
                                      # continuation, not code (a code block needs a
                                      # blank line before it); nested list items keep theirs
  s/(\w)-\n(?!\d{1,3}[.)]\s)(?=\w)/$1/g;   # word split across lines by a hyphen
  1 while s{
      ^(                              # $1: a line that can absorb the next
          (?!(?:[ ]{4}|\t)(?![ ]*(?:[-*+]|\xe2\x80\xa2|\d{1,3}[.)])\s))   # not indented, unless it is a nested list item
          (?!\s*$)                    #   not blank
          (?!\#{1,6}[ \t])            #   not a heading
          (?!>)                       #   not a quote
          (?!\x00)                    #   not a parked code block
          (?!(?:=+|-{3,}|\*{3,}|_{3,})[ \t]*$)   # not a rule/underline
          .*\S
      )
      \n
      (?![ \t])                       # next line not indented
      (?!\s*$)                        # next line not blank
      (?!\#{1,6}[ \t]|>)              # next line not heading/quote
      (?!\x00)                        # next line not a parked code block
      (?!(?:[-*+]|\xe2\x80\xa2)\s)    # next line not a bullet
      (?!\d{1,3}[.)]\s)               # next line not numbered
      (?!(?:=+|-{3,}|\*{3,}|_{3,})[ \t]*$)   # next line not a rule/underline
      (\S)
  }{$1 $2}mgx;
  s/\n{3,}/\n\n/g;                    # collapse runs of blank lines
  s{\x00(\d+)\x00}{$fence[$1]}g;      # put the code blocks back
'
}

# Paths a terminal wrapped mid-name come back with a space where the break was
# ("261104-d omain-swap.sh"). For each path token (/, ~/, $HOME/), a space is
# dropped only when the joined form matches something on disk and the spaced
# form does not, so real spaces ("My Drive", "2. Briefs") are kept.
fixpaths() {
/usr/bin/python3 -I -c '
import os, re, sys
home = os.path.expanduser("~")
def expand(p):
    for pre in ("${HOME}", "$HOME", "~"):
        if p.startswith(pre + "/") or p == pre:
            return home + p[len(pre):]
    return p
def valid(p):
    # every full component exists; the last one may be a prefix of an entry
    p = expand(p).rstrip(".,;:)")
    if os.path.exists(p): return True
    d, b = os.path.split(p)
    if not d or not os.path.isdir(d): return False
    try: return any(e.startswith(b) for e in os.listdir(d))
    except OSError: return False
start = re.compile(r"(?:(?<=^)|(?<=[\s\"\x27=(]))(?:\$\{HOME\}|\$HOME|~)?/[^\s\"\x27`]")
chunk = re.compile(r" ([^\s\"\x27`]+)")
tok = re.compile(r"[^\s\"\x27`]*")
out, i, text = [], 0, sys.stdin.read()
while True:
    m = start.search(text, i)
    if not m: out.append(text[i:]); break
    out.append(text[i:m.start()])
    j = tok.match(text, m.start()).end()
    path = text[m.start():j]
    while True:
        c = chunk.match(text, j)
        if not c: break
        joined, spaced = path + c.group(1), path + " " + c.group(1)
        if valid(spaced): path = spaced
        elif valid(joined) and not valid(path + " "): path = joined
        else: break
        j = c.end()
    out.append(path); i = j
sys.stdout.write("".join(out))
'
}

# -t 0 is false both for a pipe and for a *closed* fd 0; only the pipe should
# fall through to cat, or a caller that closed stdin hangs forever.
STDIN_OPEN=1
if [ -d /dev/fd ] && [ ! -e /dev/fd/0 ]; then STDIN_OPEN=0; fi

if [ "$FROM_CLIP" -eq 1 ] || { [ ${#FILES[@]} -eq 0 ] && { [ -t 0 ] || [ "$STDIN_OPEN" -eq 0 ]; }; }; then
  IN=$(pbpaste)
  if [ -z "$IN" ]; then
    echo "nobreaks: clipboard is empty or holds no text (image or rich-text-only) — leaving it alone" >&2
    exit 1
  fi
  FROM_CLIP=1; TO_CLIP=1
elif [ ${#FILES[@]} -gt 0 ]; then
  IN=$(cat -- "${FILES[@]}")
else
  IN=$(cat)
fi

if [ "$DUMP" -eq 1 ]; then
  printf '%s\n' "$IN" | cat -et
  exit 0
fi

BEFORE=$(printf '%s\n' "$IN" | wc -l | tr -d ' ')
OUT=$(printf '%s\n' "$IN" | unwrap | fixpaths)
AFTER=$(printf '%s\n' "$OUT" | wc -l | tr -d ' ')

# Joining is the only step that removes a line with text on it — collapsing
# blank lines is not a join, so count text lines, not all lines.
BEFORE_TEXT=$(printf '%s\n' "$IN" | grep -c '[^[:space:]]' | tr -d ' ' || true)
AFTER_TEXT=$(printf '%s\n' "$OUT" | grep -c '[^[:space:]]' | tr -d ' ' || true)

if [ "$TO_CLIP" -eq 1 ]; then
  if [ -n "$OUT" ] && { [ "$FROM_CLIP" -eq 0 ] || [ "$OUT" != "$IN" ]; }; then
    printf '%s\n' "$OUT" | pbcopy
  fi
  if [ "$AFTER_TEXT" = "$BEFORE_TEXT" ] && [ "$OUT" != "$IN" ]; then
    printf '✓ %s lines, spaces fixed → clipboard\n' "$BEFORE"
  elif [ "$AFTER_TEXT" = "$BEFORE_TEXT" ]; then
    printf '! %s lines in, %s out — nothing to join. Run: nobreaks --dump\n' "$BEFORE" "$AFTER"
  else
    printf '✓ %s lines → %s → clipboard\n' "$BEFORE" "$AFTER"
  fi
else
  printf '%s\n' "$OUT"
fi
