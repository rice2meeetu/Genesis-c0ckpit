#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_root="$project_root/.runtime/facefusion"
if [[ ! -d "$runtime_root" ]]; then
    git clone --depth 1 --branch 3.9.1 https://github.com/facefusion/facefusion.git "$runtime_root"
fi
if [[ ! -x "$runtime_root/.venv/bin/python" ]]; then
    python3 -m venv "$runtime_root/.venv"
fi
cd "$runtime_root"
PATH="$runtime_root/.venv/bin:$PATH" "$runtime_root/.venv/bin/python" install.py migraphx --skip-conda
if [[ ! -f "$runtime_root/facefusion.ini" ]] || git diff --quiet -- facefusion.ini; then
    cp "$project_root/genesis/reference/facefusion-genesis.ini" "$runtime_root/facefusion.ini"
fi
"$runtime_root/.venv/bin/python" facefusion.py --version
