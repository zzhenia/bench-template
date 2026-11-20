#!/bin/bash
# automation-status/status.sh
# Launchd detail view of this bench's scheduled jobs.
# Output: state/automation-status/YYMMDD-automations.md at the bench root

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/generate_status.py"
