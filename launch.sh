#!/bin/bash
set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$SCRIPT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
    echo "GENESIS cockpit environment was not found: $PYTHON" >&2
    exit 1
fi

cd "$SCRIPT_DIR"
exec "$PYTHON" "$SCRIPT_DIR/main.py"
