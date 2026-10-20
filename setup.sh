#!/bin/bash
set -e
cd "$(dirname "$0")"

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
    if grep -q '^BENCH_OWNER=' config/keys.env; then
      sed -i '' "s/^BENCH_OWNER=.*/BENCH_OWNER=$BENCH_NAME/" config/keys.env
    else
      echo "BENCH_OWNER=$BENCH_NAME" >> config/keys.env
    fi
    echo "✓ Welcome, $BENCH_NAME!"
  fi
fi

# Bench colour: the Cursor window and the Claude session colour (config/bench.env)
CURRENT_COLOR=$(grep '^BENCH_COLOR=' config/bench.env 2>/dev/null | cut -d= -f2-)
if [ -z "$CURRENT_COLOR" ]; then
  echo ""
  read -rp "Bench colour — red, blue, green, yellow, purple, orange, pink or cyan? [blue] " COLOR
  COLOR=$(echo "${COLOR:-blue}" | tr '[:upper:]' '[:lower:]')
  case "$COLOR" in red|blue|green|yellow|purple|orange|pink|cyan) ;; *) echo "  '$COLOR' not recognised — using blue."; COLOR=blue ;; esac
  python3 scripts/bench-colour.py "$COLOR"
  CURSOR_USER="$HOME/Library/Application Support/Cursor/User/settings.json"
  if [ -f "$CURSOR_USER" ] && ! grep -q '"window.autoDetectColorScheme": *true' "$CURSOR_USER"; then
    echo "  To follow the system's light/dark switch, turn on Cursor's"
    echo "  Window: Auto Detect Color Scheme setting."
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

# Auto-note + auto-close of idle convo windows (launchd, macOS only)
echo ""
if [ "$(uname)" = "Darwin" ]; then
  BENCH_PATH=$(pwd -P)
  BENCH_NAME_SLUG=$(basename "$BENCH_PATH" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g')
  LABEL="com.bench.$BENCH_NAME_SLUG.auto-note"
  AGENTS_DIR="$HOME/Library/LaunchAgents"
  PLIST="$AGENTS_DIR/$LABEL.plist"
  PYTHON_BIN=$(command -v python3 || echo /usr/bin/python3)
  mkdir -p "$AGENTS_DIR"
  NEW_PLIST=$(sed -e "s|__LABEL__|$LABEL|g" -e "s|__BENCH_PATH__|$BENCH_PATH|g" \
                  -e "s|__PYTHON__|$PYTHON_BIN|g" -e "s|__HOME__|$HOME|g" \
                  actions/recurring/auto-note/com.bench.auto-note.plist)
  if [ -f "$PLIST" ] && [ "$(cat "$PLIST")" = "$NEW_PLIST" ] \
     && launchctl list "$LABEL" >/dev/null 2>&1; then
    echo "  Auto-note already installed ($LABEL), skipping."
  else
    launchctl unload "$PLIST" >/dev/null 2>&1 || true
    printf '%s\n' "$NEW_PLIST" > "$PLIST"
    if launchctl load "$PLIST"; then
      echo "✓ Auto-note on: idle convo windows get a session note after 15 min and"
      echo "  close after 60 min ($LABEL, every 5 min). Settings and how to turn it"
      echo "  off: actions/recurring/auto-note/instructions.md"
    else
      echo "  Could not load $PLIST. Load it by hand: launchctl load \"$PLIST\""
    fi
  fi
  [ -x "$HOME/.local/bin/claude" ] || echo "  Note: auto-note expects the claude CLI at ~/.local/bin/claude."
  command -v jq >/dev/null 2>&1 || echo "  Note: install jq (brew install jq) - the session hook needs it."
else
  echo "  Auto-note skipped: it runs on launchd, which needs macOS."
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
