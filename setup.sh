#!/bin/bash
set -e

echo "Setting up your bench..."

if [ ! -f config/keys.env ]; then
  cp config/keys.env.template config/keys.env
  echo "✓ Created config/keys.env — fill in your API keys before running actions."
else
  echo "  config/keys.env already exists, skipping."
fi

echo ""
echo "✓ Bench ready."
echo "  1. Edit config/keys.env with your API keys."
echo "  2. Open this folder in Claude Code: claude ."
echo "  3. Run /status to verify automations, /note to write your first session note."
