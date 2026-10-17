"""NSFW FaceFusion uses local MIGraphX for its actual face-swap model."""
import json
from pathlib import Path

import pytest

import qt_cockpit as cockpit
from genesis import integrations


def test_gpu_execution_profile_must_show_real_migraphx_nodes(tmp_path, monkeypatch):
    monkeypatch.setattr(integrations, "FACEFUSION_ROOT", tmp_path)
    cache = tmp_path / ".cache" / "migraphx"
    cache.mkdir(parents=True)
    profile = cache / "real-swapper.json"
    profile.write_text(json.dumps([
        {"cat": "Node", "args": {"provider": "CPUExecutionProvider"}},
        {"cat": "Node", "args": {"provider": "MIGraphXExecutionProvider"}},
    ]))
    cockpit._verify_facefusion_gpu_profile(f"GENESIS_GPU_PROFILE {profile}", "migraphx")
    cockpit._verify_facefusion_gpu_profile("", "cpu")


def test_gpu_execution_profile_rejects_cpu_only_or_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(integrations, "FACEFUSION_ROOT", tmp_path)
    cache = tmp_path / ".cache" / "migraphx"
    cache.mkdir(parents=True)
    profile = cache / "cpu-only.json"
    profile.write_text(json.dumps([{"cat": "Node", "args": {"provider": "CPUExecutionProvider"}}]))
    with pytest.raises(RuntimeError, match="silent CPU fallback"):
        cockpit._verify_facefusion_gpu_profile(f"GENESIS_GPU_PROFILE {profile}", "migraphx")
    with pytest.raises(RuntimeError, match="silent CPU fallback"):
        cockpit._verify_facefusion_gpu_profile("", "migraphx")


def test_gpu_profile_rejects_files_outside_isolated_runtime(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    monkeypatch.setattr(integrations, "FACEFUSION_ROOT", runtime)
    outsider = tmp_path / "outsider.json"
    outsider.write_text(json.dumps([{"cat": "Node", "args": {"provider": "MIGraphXExecutionProvider"}}]))
    with pytest.raises(RuntimeError, match="silent CPU fallback"):
        cockpit._verify_facefusion_gpu_profile(f"GENESIS_GPU_PROFILE {outsider}", "migraphx")


def test_gpu_mode_accelerates_swapper_locally_and_keeps_cpu_mode_clean():
    gpu = cockpit._facefusion_runtime_env("migraphx")
    assert gpu["GENESIS_FF_GPU_SWAPPER_ONLY"] == "1"
    assert gpu["GENESIS_FF_GPU_PROFILE"] == "1"
    cpu = cockpit._facefusion_runtime_env("cpu")
    assert "GENESIS_FF_GPU_SWAPPER_ONLY" not in cpu or cpu["GENESIS_FF_GPU_SWAPPER_ONLY"] != "1"
