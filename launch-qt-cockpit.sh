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
export GENESIS_BACKEND_MODE="${GENESIS_BACKEND_MODE:-RUNPOD}"
export GENESIS_RUNPOD_AUTOCONNECT="${GENESIS_RUNPOD_AUTOCONNECT:-1}"
# Endpoint comes from GENESIS_RUNPOD_URL, GENESIS_COMFY_URL, or saved settings.
if [[ -n "${GENESIS_RUNPOD_SSH_HOST:-}" ]]; then
  if ! bash "$SCRIPT_DIR/scripts/ensure-runpod-8189-tunnel.sh"; then
    echo "GENESIS: RunPod tunnel unavailable; continuing to open Cockpit." >&2
  fi
fi
exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/qt_cockpit_linux_premium.py" "$@"
