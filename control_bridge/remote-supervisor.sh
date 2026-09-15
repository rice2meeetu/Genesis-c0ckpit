#!/usr/bin/env bash
set -euo pipefail

# Persistent launcher for Desktop Commander's Remote MCP device agent.
# It reuses the device/session persisted by the Desktop Commander package and
# relies on systemd Restart=always to bring it back if the connection drops.

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

if [[ -s "$HOME/.nvm/nvm.sh" ]]; then
  # shellcheck disable=SC1090
  source "$HOME/.nvm/nvm.sh"
  nvm use default >/dev/null 2>&1 || true
fi

if ! command -v npx >/dev/null 2>&1; then
  echo "GENESIS remote supervisor: npx not found" >&2
  exit 127
fi

exec npx -y @wonderwhy-er/desktop-commander@latest remote
