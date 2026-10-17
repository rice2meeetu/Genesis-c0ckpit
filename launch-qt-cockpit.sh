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
# The normal desktop shortcut is LOCAL by default. The dedicated RunPod
# launcher opts in to the remote backend and its SSH tunnel explicitly.
export GENESIS_BACKEND_MODE="${GENESIS_BACKEND_MODE:-LOCAL}"
if [[ -z "${GENESIS_RUNPOD_AUTOCONNECT:-}" ]]; then
  if [[ "${GENESIS_BACKEND_MODE^^}" == "RUNPOD" ]]; then
    export GENESIS_RUNPOD_AUTOCONNECT=1
  else
    export GENESIS_RUNPOD_AUTOCONNECT=0
  fi
fi
# Endpoint comes from GENESIS_RUNPOD_URL, GENESIS_COMFY_URL, or saved settings.
if [[ "${GENESIS_BACKEND_MODE^^}" == "RUNPOD" && "${GENESIS_RUNPOD_AUTOCONNECT}" == "1" && -n "${GENESIS_RUNPOD_SSH_HOST:-}" ]]; then
  if ! bash "$SCRIPT_DIR/scripts/ensure-runpod-8189-tunnel.sh"; then
    echo "GENESIS: RunPod tunnel unavailable; continuing to open Cockpit." >&2
  fi
fi
exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/qt_cockpit_linux_premium.py" "$@"
