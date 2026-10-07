#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/.genesis-runpod-current" ]]; then
  set -a
  source "$SCRIPT_DIR/.genesis-runpod-current"
  set +a
fi
if [[ -n "${GENESIS_RUNPOD_SSH_HOST:-}" ]]; then
  bash "$SCRIPT_DIR/scripts/ensure-runpod-8189-tunnel.sh"
fi
exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/qt_cockpit_linux_premium.py" "$@"
