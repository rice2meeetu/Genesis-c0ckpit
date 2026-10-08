#!/usr/bin/env bash
set -euo pipefail
# Optional machine-local direct SSH connection; never forwards ComfyUI 8188.
[[ -n "${GENESIS_RUNPOD_SSH_HOST:-}" ]] || exit 0
[[ "${GENESIS_RUNPOD_URL:-}" == "http://127.0.0.1:18189" ]] || exit 0
if /usr/bin/python3 - <<'PY'
import socket
try:
    with socket.create_connection(('127.0.0.1',18189),timeout=1): pass
except OSError: raise SystemExit(1)
PY
then exit 0; fi
exec /usr/bin/ssh -f -N -o BatchMode=yes -o ConnectTimeout=8 \
    -o ExitOnForwardFailure=yes -o ServerAliveInterval=20 -o ServerAliveCountMax=3 \
    -o StrictHostKeyChecking=accept-new \
    -o UserKnownHostsFile="${GENESIS_RUNPOD_KNOWN_HOSTS:-/tmp/genesis-runpod-8189-known-hosts}" \
    -L 127.0.0.1:18189:127.0.0.1:8189 \
    -p "${GENESIS_RUNPOD_SSH_PORT:-22}" \
    -i "$HOME/.runpod/ssh/runpodctl-ssh-key" \
    "${GENESIS_RUNPOD_SSH_USER:-root}@${GENESIS_RUNPOD_SSH_HOST}"
