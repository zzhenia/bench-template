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

# Cursor, Warp and Claude Code settings the bench needs (core/env): merged into
# this machine's files, each backed up first; asks before changing your own values.
echo ""
python3 core/env/apply.py

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

# Scheduled jobs (launchd, macOS only): nightly auto-push + bench update,
# auto-note, python-repin, brew-check. Templates: core/tools/<name>/schedule.plist.
echo ""
if [ "$(uname)" = "Darwin" ]; then
  bash core/bin/install-schedules.sh auto-push auto-note python-repin brew-check
  [ -x "$HOME/.local/bin/claude" ] || echo "  Note: auto-note expects the claude CLI at ~/.local/bin/claude."
  command -v jq >/dev/null 2>&1 || echo "  Note: install jq (brew install jq) - the session hook needs it."
else
  echo "  Scheduled jobs skipped: they run on launchd, which needs macOS."
fi

# Skills: core/skills and personal/skills linked into skills/; the bench layout
# (core/bench-update/shape.sh) also creates master-instructions.md if missing.
bash core/bench-update/shape.sh

# Context trim: Claude Code mod that offers a note + clean restart past a token
# limit. Loaded from ~/.claude/settings.json (and this bench's own login, if any).
TRIM_DIR="$(pwd -P)/core/tools/context-trim"
LOGIN_DIR=$(sed -n 1p .claude-login 2>/dev/null | sed "s|^~|$HOME|")
for CFG in "$HOME/.claude" ${LOGIN_DIR:+"$LOGIN_DIR"}; do
  python3 - "$CFG/settings.json" "$TRIM_DIR" <<'PY'
import json, os, sys
path, trim = sys.argv[1], sys.argv[2]
try:
    with open(path) as f:
        cfg = json.load(f)
except FileNotFoundError:
    cfg = {}
env = cfg.setdefault("env", {})
dirs = [d for d in env.get("CLAUDE_CODE_PLUGIN_DIRS", "").split(":") if d]
if trim in dirs or any(os.path.expanduser(d) == trim for d in dirs):
    print(f"  Context trim already loaded in {path}, skipping.")
    sys.exit(0)
env["CLAUDE_CODE_PLUGIN_DIRS"] = ":".join(dirs + [trim])
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")
print(f"✓ Context trim on in {path}: past 100K tokens a band offers to write the")
print("  note and restart clean. Settings: core/tools/context-trim/config.json")
PY
done

echo ""
echo "✓ Bench ready."
echo ""
echo "  Next steps:"
echo "  1. If you picked jira or asana, add its credentials to config/keys.env."
echo "  2. Open this folder in Claude Code: claude ."
echo "  3. Run /status to verify automations, /note to write your first session note."
echo ""
echo "  Optional — install the environment layer for your host:"
echo "    Warp:   core/env/warp/README.md   (project picker, wp, tab configs)"
echo "    Cursor: core/env/cursor/README.md (cw, Claude on window open)"
echo "  Warp and Cursor are the two supported hosts. Any terminal runs the bench"
echo "  fine, it just doesn't get the picker or the wp/cw commands."
