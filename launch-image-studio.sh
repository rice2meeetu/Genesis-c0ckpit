#!/usr/bin/env bash
# Image workspace only. Start ComfyUI through GENESIS' guarded service path so
# large ROCm workloads cannot bypass overlap/cooldown protection.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
python3 - <<'PY'
from genesis import integrations
ok, detail = integrations.start_user_service(
    integrations.COMFYUI_SERVICE,
    already_online=integrations.endpoint_online(integrations.COMFYUI_URL, "/system_stats"),
)
if not ok:
    raise SystemExit(f"GENESIS GPU safety blocked ComfyUI start: {detail}")
print(detail)
PY
exec "$SCRIPT_DIR/launch-qt-cockpit.sh" --page create "$@"
