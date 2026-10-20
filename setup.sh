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

# Project-management tool for ticket comments (stored in config/bench.env)
CURRENT_PM=$(grep '^PM_TOOL=' config/bench.env | cut -d= -f2-)
if [ -z "$CURRENT_PM" ]; then
  echo ""
  read -rp "Project-management tool for ticket comments — jira, asana or none? [none] " PM
  PM=$(echo "${PM:-none}" | tr '[:upper:]' '[:lower:]')
  case "$PM" in jira|asana|none) ;; *) echo "  '$PM' not recognised — using none."; PM=none ;; esac
  sed -i '' "s/^PM_TOOL=.*/PM_TOOL=$PM/" config/bench.env
  echo "✓ PM tool: $PM (change it in config/bench.env)"
fi

echo ""
echo "✓ Bench ready."
echo ""
echo "  Next steps:"
echo "  1. If you picked jira or asana, add its credentials to config/keys.env."
echo "  2. Open this folder in Claude Code: claude ."
echo "  3. Run /status to verify automations, /note to write your first session note."
echo ""
echo "  Optional — install the environment layer for your host:"
echo "    Warp:   config/warp/README.md   (project picker, wp, tab configs)"
echo "    Cursor: config/cursor/README.md (cw, Claude on window open)"
echo "  Warp and Cursor are the two supported hosts. Any terminal runs the bench"
echo "  fine, it just doesn't get the picker or the wp/cw commands."
