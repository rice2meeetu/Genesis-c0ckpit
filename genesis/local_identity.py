"""Local-only GENESIS face-swap engine discovery (no network or GPU side effects)."""
from pathlib import Path


ENGINE_FILES = {
    "reactor_inswapper": "models/insightface/inswapper_128.onnx",
    "reactor_reswapper": "models/reswapper/reswapper_256.onnx",
    "reactor_hyperswap": "models/hyperswap/hyperswap_1a_256.onnx",
}


def installed_reactor_engines(comfy_root=None):
    """Enumerate installed *local* node and model files, even if ComfyUI is stopped.

    The running ComfyUI /object_info schema remains authoritative before any
    swap is submitted. A remote catalog never qualifies a local swap engine.
    """
    root = Path(comfy_root) if comfy_root else Path.home() / "AI" / "ComfyUI"
    if not (root / "custom_nodes/comfyui-reactor-node/nodes.py").is_file():
        return []
    if not (root / "main.py").is_file():
        return []
    return [engine for engine, filename in ENGINE_FILES.items()
            if (root / filename).is_file()]
