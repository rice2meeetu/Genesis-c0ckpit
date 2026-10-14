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
# An explicit RunPod URL requests the connected launch profile; an SSH host
# alone is not consent to enable background remote polling. Preserve a manual
# LOCAL override and its explicit autoconnect=0 choice.
if [[ -n "${GENESIS_RUNPOD_URL:-}" ]]; then
  export GENESIS_BACKEND_MODE="${GENESIS_BACKEND_MODE:-RUNPOD}"
  export GENESIS_RUNPOD_AUTOCONNECT="${GENESIS_RUNPOD_AUTOCONNECT:-1}"
fi
# A previously configured tunnel can be checked without silently enabling
# RunPod polling. GENESIS_RUNPOD_AUTOCONNECT=0 skips it when requested.
if [[ -n "${GENESIS_RUNPOD_SSH_HOST:-}" && "${GENESIS_RUNPOD_AUTOCONNECT:-1}" == "1" ]]; then
  if ! bash "$SCRIPT_DIR/scripts/ensure-runpod-8189-tunnel.sh"; then
    echo "GENESIS: 8189 tunnel is unavailable. Open the cockpit and check the connection settings." >&2
  fi
fi
exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/qt_cockpit_linux_premium.py" "$@"
