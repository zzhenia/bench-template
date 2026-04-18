#!/bin/bash
set -e

echo ""
echo "Setting up your bench..."

if [ ! -f config/keys.env ]; then
  cp config/keys.env.template config/keys.env
  echo "✓ Created config/keys.env"
else
  echo "  config/keys.env already exists, skipping copy."
fi

# Ask for the user's name if not already set
CURRENT_NAME=$(grep '^BENCH_OWNER=' config/keys.env | cut -d= -f2-)
if [ -z "$CURRENT_NAME" ]; then
  echo ""
  read -rp "Hello! How shall I call you? " BENCH_NAME
  if [ -n "$BENCH_NAME" ]; then
    sed -i '' "s/^BENCH_OWNER=.*/BENCH_OWNER=$BENCH_NAME/" config/keys.env
    echo "✓ Welcome, $BENCH_NAME!"
  fi
fi

echo ""
echo "✓ Bench ready."
echo ""
echo "  Next steps:"
echo "  1. Edit config/keys.env with your API keys (optional)."
echo "  2. Open this folder in Claude Code: claude ."
echo "  3. Run /status to verify automations, /note to write your first session note."
