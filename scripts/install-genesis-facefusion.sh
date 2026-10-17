#!/usr/bin/env bash
# Validate the installed, isolated NSFW FaceFusion runtime.
# Do not reinstall the previously removed official SFW FaceFusion.
set -euo pipefail
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
runtime_root="$project_root/.runtime/facefusion-nsfw-modern"
if [[ ! -x "$runtime_root/.venv/bin/python" || ! -f "$runtime_root/facefusion.py" ]]; then
    echo "The isolated NSFW FaceFusion runtime is not installed: $runtime_root" >&2
    echo "Do not install the old standard FaceFusion into GENESIS." >&2
    exit 1
fi
if [[ ! -s "$runtime_root/.assets/models/inswapper_128.onnx" ]]; then
    echo "Missing the isolated Inswapper model in $runtime_root/.assets/models" >&2
    exit 1
fi
cd "$runtime_root"
"$runtime_root/.venv/bin/python" facefusion.py --version
"$runtime_root/.venv/bin/python" - <<'PY'
import onnxruntime as ort
from facefusion import choices
assert 'MIGraphXExecutionProvider' in choices.execution_provider_set.values()
assert 'CPUExecutionProvider' in ort.get_available_providers()
print('NSFW FaceFusion local CPU ready; MIGraphX installed:', 'MIGraphXExecutionProvider' in ort.get_available_providers())
print('Cached MIGraphX models:', len(list(__import__('pathlib').Path('.cache/migraphx').glob('*.mxr'))))
PY
