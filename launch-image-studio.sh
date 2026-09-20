#!/usr/bin/env bash
# Image workspace only: this launcher does not start any local LLM service.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
systemctl --user start genesis-comfyui.service
exec "$SCRIPT_DIR/launch-qt-cockpit.sh" --page create "$@"
