#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Optional machine-local current-pod selection. Keep credentials out of this file.
if [[ -f "$SCRIPT_DIR/.genesis-runpod-current" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/.genesis-runpod-current"
  set +a
fi
export GENESIS_BACKEND_MODE=RUNPOD
# Endpoint comes from GENESIS_RUNPOD_URL, legacy GENESIS_COMFY_URL, or saved settings.
if [[ -n "${GENESIS_RUNPOD_SSH_HOST:-}" && "${GENESIS_RUNPOD_AUTOCONNECT:-1}" == "1" ]]; then
  if ! bash "$SCRIPT_DIR/scripts/ensure-runpod-8189-tunnel.sh"; then
    echo "GENESIS: 8189 tunnel is unavailable. Open the cockpit and check the connection settings." >&2
  fi
fi
exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/qt_cockpit_linux_premium.py" "$@"
