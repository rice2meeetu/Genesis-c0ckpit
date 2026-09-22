#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="/home/rice2meetyou/Genesis-c0ckpit"
export GENESIS_COMFY_URL="http://127.0.0.1:18188"

# RunPod is on-demand: start the tunnel when this launcher is used rather than
# keeping a stale cloud endpoint in a permanent restart loop.
systemctl --user start genesis-runpod-tunnel.service >/dev/null 2>&1 || true

exec /usr/bin/python3 "$SCRIPT_DIR/qt_cockpit_linux_premium.py" "$@"
