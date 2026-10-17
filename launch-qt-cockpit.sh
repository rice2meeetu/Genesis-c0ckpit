#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Use the current RunPod team pod when one has been explicitly recorded locally.
if [[ -f "$SCRIPT_DIR/.genesis-runpod-current" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/.genesis-runpod-current"
  set +a
fi
# The desktop shortcut is LOCAL unless the user explicitly chooses RUNPOD.
# Keep saved RunPod endpoint metadata without silently starting its tunnel.
export GENESIS_BACKEND_MODE="${GENESIS_BACKEND_MODE:-LOCAL}"
if [[ -z "${GENESIS_RUNPOD_AUTOCONNECT:-}" ]]; then
  if [[ "${GENESIS_BACKEND_MODE^^}" == "RUNPOD" ]]; then
    export GENESIS_RUNPOD_AUTOCONNECT=1
  else
    export GENESIS_RUNPOD_AUTOCONNECT=0
  fi
fi
# Only explicitly selected RUNPOD launches may start the tunnel.
if [[ "${GENESIS_BACKEND_MODE^^}" == "RUNPOD" && "${GENESIS_RUNPOD_AUTOCONNECT}" == "1" && -n "${GENESIS_RUNPOD_SSH_HOST:-}" ]]; then
  if ! bash "$SCRIPT_DIR/scripts/ensure-runpod-8189-tunnel.sh"; then
    echo "GENESIS: 8189 tunnel is unavailable. Open the cockpit and check the connection settings." >&2
  fi
fi
exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/qt_cockpit_linux_premium.py" "$@"
