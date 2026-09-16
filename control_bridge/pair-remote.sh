#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SERVICE="genesis-remote-control.service"

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
if [[ -s "$HOME/.nvm/nvm.sh" ]]; then
  # shellcheck disable=SC1090
  source "$HOME/.nvm/nvm.sh"
  nvm use default >/dev/null 2>&1 || true
fi

command -v npx >/dev/null 2>&1 || {
  echo "npx is required. Install Node.js 18+ first." >&2
  exit 127
}

mkdir -p "$HOME/.config/systemd/user"
cp "$HERE/genesis-remote-control.service" "$HOME/.config/systemd/user/$SERVICE"
chmod +x "$HERE/remote-supervisor.sh"
systemctl --user daemon-reload

cat <<'EOF'

GENESIS remote pairing
----------------------
A browser verification page should open. Sign in and approve the device.
Leave this terminal running once it reports Device ready.

This first process is the live connection. If it exits later, the persistent
systemd service is enabled automatically and will restart the agent for you.

EOF

cleanup() {
  echo
  echo "Enabling persistent GENESIS remote-control service..."
  systemctl --user enable "$SERVICE" >/dev/null 2>&1 || true
  systemctl --user restart "$SERVICE" >/dev/null 2>&1 || true
  echo "Remote supervisor enabled."
  echo "Status: systemctl --user status $SERVICE"
  echo "Logs:   journalctl --user -u $SERVICE -f"
}
trap cleanup EXIT INT TERM

npx -y @wonderwhy-er/desktop-commander@latest remote
