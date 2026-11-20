#!/bin/bash
# automation-status/status.sh
# Generates a dated markdown snapshot of all scheduled launchd automations.
# Output: assets/YYMMDD-automations.md

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/generate_status.py"
