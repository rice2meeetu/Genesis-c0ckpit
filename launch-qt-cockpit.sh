#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export GENESIS_BACKEND_MODE="${GENESIS_BACKEND_MODE:-RUNPOD}"
export GENESIS_RUNPOD_AUTOCONNECT="${GENESIS_RUNPOD_AUTOCONNECT:-1}"
# Endpoint comes from GENESIS_RUNPOD_URL, GENESIS_COMFY_URL, or saved settings.
exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/qt_cockpit_linux_premium.py" "$@"
