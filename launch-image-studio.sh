#!/usr/bin/env bash
# Image workspace only. Keep ComfyUI off while browsing the UI; generation,
# edit, and inpaint acquire the guarded ROCm backend on demand.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
exec "$SCRIPT_DIR/launch-qt-cockpit.sh" --page create "$@"
