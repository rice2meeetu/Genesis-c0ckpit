"""Windows guards: require verified live CUDA and keep RunPod disabled by default.

These checks extract the isolated preflight function without importing the
Windows-only GUI. No GPU, network or model files are needed for CI.
"""
import ast
from pathlib import Path
from types import SimpleNamespace

SOURCE = Path(__file__).resolve().parents[1] / "qt_cockpit_windows.py"


def _preflight_with(probe):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    guard = next(node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name == "_windows_gpu_preflight")
    namespace = {
        "cuda_preflight": probe,
        "integrations": SimpleNamespace(COMFYUI_URL="http://127.0.0.1:8188"),
    }
    exec(compile(ast.Module(body=[guard], type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace["_windows_gpu_preflight"]()


def test_windows_does_not_claim_local_gpu_safety_without_runtime_evidence():
    safe, reason = _preflight_with(lambda url: (False, "ComfyUI CUDA unavailable"))
    assert safe is False
    assert "unavailable" in reason


def test_windows_only_claims_ready_after_verified_cuda_response():
    safe, reason = _preflight_with(lambda url: (True, "ComfyUI CUDA: RTX 5060 Ti"))
    assert safe is True
    assert "CUDA" in reason


def test_windows_launcher_is_local_only_and_does_not_autoconnect_runpod():
    text = SOURCE.read_text(encoding="utf-8")
    assert 'os.environ["GENESIS_LOCAL_ONLY"] = "1"' in text
    assert 'os.environ["GENESIS_BACKEND_MODE"] = "LOCAL"' in text
    assert 'os.environ["GENESIS_RUNPOD_AUTOCONNECT"] = "0"' in text
