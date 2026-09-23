#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# This launcher always opens the local workspace.
unset GENESIS_COMFY_URL
export GENESIS_AI_PROVIDER=LOCAL
exec /usr/bin/python3 "$SCRIPT_DIR/qt_cockpit_linux_premium.py" "$@"
