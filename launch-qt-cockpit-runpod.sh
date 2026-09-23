#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export GENESIS_BACKEND_MODE=RUNPOD
# Endpoint comes from GENESIS_RUNPOD_URL, legacy GENESIS_COMFY_URL, or saved settings.
exec /usr/bin/python3 "$SCRIPT_DIR/qt_cockpit_linux_premium.py" "$@"
