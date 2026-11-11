#!/usr/bin/env bash
# two-part-maxim-check.sh — detect "A/The [noun] that X is the [one/noun] that Y" sentences
# Usage: two-part-maxim-check.sh <text-file>
# Exit 0 = no pattern found (pass); exit 1 = pattern found (prints offending sentence)
set -euo pipefail
FILE="${1:?usage: two-part-maxim-check.sh <text-file>}"
python3 - "$FILE" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
# Split into sentences; handle common abbreviations minimally
sentences = re.split(r'(?<=[.!?])\s+', text.strip())
# Pattern: (A|An|The) <words> that <words> is the <word(s)> that <words>
# The two "that" clauses bracket "is the" — the verdict structure.
pattern = re.compile(
    r'\b(A|An|The)\b[^.!?]*\bthat\b[^.!?]*\bis the\b[^.!?]*(one|same|\w+)\b[^.!?]*\bthat\b',
    re.IGNORECASE
)
found = False
for sent in sentences:
    if pattern.search(sent):
        print(f"FAIL: two-part maxim: {sent[:120]}")
        found = True
if found:
    sys.exit(1)
sys.exit(0)
PY
