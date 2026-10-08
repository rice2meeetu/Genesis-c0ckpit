"""Inspect the Windows-specific guard without importing or launching Windows UI."""
import ast
from pathlib import Path


def test_windows_does_not_claim_local_gpu_safety_without_runtime_evidence():
    path = Path(__file__).resolve().parents[1] / "qt_cockpit_windows.py"
    tree = ast.parse(path.read_text())
    guard = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == "_windows_gpu_preflight")
    namespace = {}
    exec(compile(ast.Module(body=[guard], type_ignores=[]), str(path), "exec"), namespace)
    safe, reason = namespace["_windows_gpu_preflight"]()
    assert safe is False
    assert "runtime verification" in reason
