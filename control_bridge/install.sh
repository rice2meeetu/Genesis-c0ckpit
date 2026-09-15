#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HERE/.venv"
SERVICE_SRC="$HERE/genesis-control-bridge.service"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_DST="$SERVICE_DIR/genesis-control-bridge.service"

printf '\nGENESIS Control Bridge installer\n'
printf 'Repo: %s\n\n' "$HERE"

command -v python3 >/dev/null || { echo 'python3 is required'; exit 1; }
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip wheel
"$VENV/bin/python" -m pip install -r "$HERE/requirements.txt"

mkdir -p "$SERVICE_DIR"
cp "$SERVICE_SRC" "$SERVICE_DST"

# Import the live graphical-session environment so screenshot/input helpers can
# see the current Wayland/X11 session when available.
systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XDG_RUNTIME_DIR DBUS_SESSION_BUS_ADDRESS 2>/dev/null || true
systemctl --user daemon-reload
systemctl --user enable --now genesis-control-bridge.service

printf '\nService status:\n'
systemctl --user --no-pager --full status genesis-control-bridge.service || true

printf '\nBridge endpoint: http://127.0.0.1:8766/mcp\n'
printf 'Logs: journalctl --user -u genesis-control-bridge -f\n'
printf 'Restart: systemctl --user restart genesis-control-bridge\n'
printf 'Stop: systemctl --user stop genesis-control-bridge\n\n'

if command -v ydotool >/dev/null 2>&1; then
    echo 'ydotool detected: keyboard/mouse actions can be enabled if its daemon has permission.'
else
    echo 'Optional GUI control helper not found: ydotool'
fi
