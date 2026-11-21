#!/bin/bash
# Launch the Bench Dashboard — opens in your browser automatically.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/server.py"
