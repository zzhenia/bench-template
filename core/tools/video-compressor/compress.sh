#!/bin/bash
# Post-recording compression
# Finds the latest OBS recording, asks for quality preference, compresses with HandBrake (VideoToolbox H.265)
# Output lands in the same folder as the source (OBS_DIR, default ~/Movies/OBS)
# Usage: bash compress.sh
# ─────────────────────────────────────────────────────────────

OBS_DIR="${OBS_DIR:-$HOME/Movies/OBS}"
HANDBRAKE="$(command -v HandBrakeCLI || echo /opt/homebrew/bin/HandBrakeCLI)"

# Find latest video file, excluding already-compressed outputs
LATEST=$(ls -t "$OBS_DIR"/*.{mkv,mp4,mov,flv} 2>/dev/null | grep -v "_compr" | head -1)

if [[ -z "$LATEST" ]]; then
  echo "No video files found in $OBS_DIR"
  exit 1
fi

echo "Latest recording: $(basename "$LATEST")"
echo ""
# Accept choice as first argument (from dashboard), otherwise prompt interactively
if [[ -n "$1" ]]; then
  CHOICE="$1"
else
  echo "How do you want to process it?"
  echo "  1) Good quality   — VT H.265 quality 45, larger file, great for final exports"
  echo "  2) High compression — VT H.265 quality 60, much smaller file, fine for uploads"
  echo "  3) Cancel"
  echo ""
  read -rp "Choose [1/2/3]: " CHOICE
fi

case "$CHOICE" in
  1|good)
    QUALITY=45
    AUDIO_BITRATE="192"
    LABEL="good quality (VT quality 45)"
    ;;
  2|high)
    QUALITY=60
    AUDIO_BITRATE="128"
    LABEL="high compression (VT quality 60)"
    ;;
  3|cancel|"")
    echo "Cancelled."
    exit 0
    ;;
  *)
    echo "Invalid choice. Cancelled."
    exit 1
    ;;
esac

BASENAME=$(basename "$LATEST")
NAME="${BASENAME%.*}"
OUTPUT="$OBS_DIR/${NAME}_compr.mp4"

echo ""
echo "Compressing with $LABEL..."
echo "Input:  $LATEST"
echo "Output: $OUTPUT"
echo ""

"$HANDBRAKE" \
  -i "$LATEST" \
  -o "$OUTPUT" \
  -e vt_h265 \
  -q "$QUALITY" \
  --encoder-preset speed \
  -B "$AUDIO_BITRATE" \
  -E aac \
  -f av_mp4 \
  --two-pass

if [[ $? -eq 0 ]]; then
  echo ""
  echo "Done. Compressed file saved to:"
  echo "  $OUTPUT"
else
  echo "Compression failed."
  exit 1
fi
