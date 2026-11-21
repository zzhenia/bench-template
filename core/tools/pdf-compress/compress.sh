#!/usr/bin/env bash
# Compress a PDF using Ghostscript.
# Usage: compress.sh <input.pdf> [quality]
# Quality: screen (72dpi) | ebook (150dpi, default) | printer (300dpi)

set -euo pipefail

INPUT="${1:?Usage: compress.sh <input.pdf> [screen|ebook|printer]}"
QUALITY="${2:-ebook}"

if [[ ! -f "$INPUT" ]]; then
  echo "File not found: $INPUT" >&2
  exit 1
fi

DIR=$(dirname "$INPUT")
BASE=$(basename "$INPUT" .pdf)
OUTPUT="${DIR}/${BASE}_compressed.pdf"
GS=$(command -v gs || echo /opt/homebrew/bin/gs)
[[ -x "$GS" ]] || { echo "Ghostscript not found: brew install ghostscript" >&2; exit 1; }

"$GS" -sDEVICE=pdfwrite \
   -dCompatibilityLevel=1.4 \
   -dPDFSETTINGS=/"$QUALITY" \
   -dNOPAUSE -dBATCH -dQUIET \
   -sOutputFile="$OUTPUT" \
   "$INPUT"

ORIG=$(du -h "$INPUT" | cut -f1)
COMP=$(du -h "$OUTPUT" | cut -f1)
echo "${ORIG} → ${COMP}  (${QUALITY})  →  ${OUTPUT}"
