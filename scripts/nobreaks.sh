#!/bin/bash
# nobreaks — unwrap hard-wrapped text.
#
# Joins lines that are continuations of the same paragraph, and leaves
# alone: blank lines (paragraph breaks), list items (-, *, +, •, 1., 1)),
# headings (#), quotes (>), setext underlines and rules (===, ---, ***),
# fenced code blocks (``` / ~~~), and indented lines (code blocks).
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
  s/^[ ]{1,3}(?![-*+>\#]|\xe2\x80\xa2|\d{1,3}[.)])(?=\S)//mg;
                                      # 1-3 leading spaces = wrap artifact, not code
                                      # (kept when they indent a nested list item)
  s/(\w)-\n(?!\d{1,3}[.)]\s)(?=\w)/$1/g;   # word split across lines by a hyphen
  1 while s{
      ^(                              # $1: a line that can absorb the next
          (?![ \t])                   #   not indented
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
OUT=$(printf '%s\n' "$IN" | unwrap)
AFTER=$(printf '%s\n' "$OUT" | wc -l | tr -d ' ')

# Joining is the only step that removes a line with text on it — collapsing
# blank lines is not a join, so count text lines, not all lines.
BEFORE_TEXT=$(printf '%s\n' "$IN" | grep -c '[^[:space:]]' | tr -d ' ' || true)
AFTER_TEXT=$(printf '%s\n' "$OUT" | grep -c '[^[:space:]]' | tr -d ' ' || true)

if [ "$TO_CLIP" -eq 1 ]; then
  if [ -n "$OUT" ] && { [ "$FROM_CLIP" -eq 0 ] || [ "$OUT" != "$IN" ]; }; then
    printf '%s\n' "$OUT" | pbcopy
  fi
  if [ "$AFTER_TEXT" = "$BEFORE_TEXT" ]; then
    printf '! %s lines in, %s out — nothing to join. Run: nobreaks --dump\n' "$BEFORE" "$AFTER"
  else
    printf '✓ %s lines → %s → clipboard\n' "$BEFORE" "$AFTER"
  fi
else
  printf '%s\n' "$OUT"
fi
