#!/usr/bin/env bash
set -e
APPDIR="$HOME/GENESIS-Photo-Studio"
VENV="$APPDIR/.venv"
echo "Installing isolated background-removal backend..."
"$VENV/bin/pip" install "rembg[cpu]"
echo "Done. Re-open GENESIS Photo Studio."
