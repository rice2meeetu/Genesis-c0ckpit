#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="/home/rice2meetyou/Genesis-c0ckpit"
export GENESIS_COMFY_URL="${GENESIS_COMFY_URL:-https://a5yw5n79egqcxy-8188.proxy.runpod.net}"

# Direct RunPod HTTPS proxy mode: no local SSH tunnel is required for this pod.
# The URL can be overridden temporarily by exporting GENESIS_COMFY_URL first.

exec /usr/bin/python3 "$SCRIPT_DIR/qt_cockpit_linux_premium.py" "$@"
