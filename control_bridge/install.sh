#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HERE/.venv"
SERVICE_DIR="/etc/systemd/system"
BRIDGE_SERVICE_SRC="$HERE/genesis-control-bridge.service"
BRIDGE_SERVICE_DST="$SERVICE_DIR/genesis-control-bridge.service"
REMOTE_SERVICE_SRC="$HERE/genesis-remote-control.service"
REMOTE_SERVICE_DST="$SERVICE_DIR/genesis-remote-control.service"

printf '\nGENESIS Control Bridge installer\n'
printf 'Repo: %s\n\n' "$HERE"

command -v python3 >/dev/null || { echo 'python3 is required'; exit 1; }
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip wheel
"$VENV/bin/python" -m pip install -r "$HERE/requirements.txt"

mkdir -p "$SERVICE_DIR"
cp "$BRIDGE_SERVICE_SRC" "$BRIDGE_SERVICE_DST"
cp "$REMOTE_SERVICE_SRC" "$REMOTE_SERVICE_DST"
chmod +x "$HERE/install.sh" "$HERE/pair-remote.sh" "$HERE/remote-supervisor.sh"

# Import the live graphical-session environment so screenshot/input helpers can
# see the current Wayland/X11 session when available.
systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS 2>/dev/null || true
sudo systemctl daemon-reload
sudo systemctl enable --now genesis-control-bridge.service

printf '\nLocal bridge status:\n'
sudo systemctl --no-pager --full status genesis-control-bridge.service || true

printf '\nLocal MCP endpoint: http://127.0.0.1:8766/mcp\n'
printf 'Bridge logs: journalctl --user -u genesis-control-bridge -f\n\n'

if command -v ydotool >/dev/null 2>&1; then
    echo 'ydotool detected: keyboard/mouse actions can be enabled if its daemon has permission.'
else
    echo 'Optional GUI control helper not found: ydotool'
fi

if command -v npx >/dev/null 2>&1 || [[ -s "$HOME/.nvm/nvm.sh" ]]; then
    printf '\nRemote control bootstrap is ready. Pair once with:\n  %s/pair-remote.sh\n' "$HERE"
    echo 'After pairing, genesis-remote-control.service will keep restarting the remote agent if it drops.'
else
    echo
    echo 'Remote pairing not enabled yet: Node.js/npx is not installed.'
fi
