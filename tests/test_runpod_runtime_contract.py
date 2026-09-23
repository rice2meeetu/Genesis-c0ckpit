import os
import time
from pathlib import Path
from unittest.mock import Mock

import qt_cockpit

ROOT = Path(__file__).resolve().parents[1]
URL = "https://test-pod-8188.proxy.runpod.net"


def test_remote_runtime_status_reports_offline_on_connection_failure(monkeypatch):
    monkeypatch.setenv("GENESIS_COMFY_URL", URL)
    client = Mock()
    client.system_stats.side_effect = qt_cockpit.workflow_lab.ComfyError("offline")
    monkeypatch.setattr(qt_cockpit.workflow_lab, "ComfyClient", Mock(return_value=client))
    status = qt_cockpit.load_runtime_status()
    assert status["remote"] is True
    assert status["comfyOnline"] is False
    assert status["ready"] is False
    assert status["gpuName"] == "RunPod offline"


def test_remote_runtime_status_reports_actual_gpu_and_memory(monkeypatch):
    monkeypatch.setenv("GENESIS_COMFY_URL", URL)
    client = Mock()
    client.system_stats.return_value = {"devices": [{
        "name": "NVIDIA A100-SXM4-80GB", "type": "cuda",
        "vram_total": 80 * 1024 ** 3, "vram_free": 50 * 1024 ** 3,
    }]}
    factory = Mock(return_value=client)
    monkeypatch.setattr(qt_cockpit.workflow_lab, "ComfyClient", factory)
    status = qt_cockpit.load_runtime_status()
    assert status["comfyOnline"] is True
    assert status["ready"] is True
    assert status["gpuName"] == "NVIDIA A100-SXM4-80GB"
    assert status["vramTotalGiB"] == 80
    assert status["vramUsedGiB"] == 30
    factory.assert_called_once_with(URL, timeout=20)


def test_remote_ui_startup_does_not_wait_for_network(monkeypatch):
    monkeypatch.setenv("GENESIS_COMFY_URL", URL)
    client = Mock(side_effect=AssertionError("startup must not perform network I/O"))
    monkeypatch.setattr(qt_cockpit.workflow_lab, "ComfyClient", client)
    status = qt_cockpit.load_runtime_status(probe_remote=False)
    assert status["remote"] is True
    client.assert_not_called()


def test_remote_catalog_cannot_reuse_previous_pod_or_expired_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    client = Mock(base_url=URL)
    client.object_info.return_value = {"FirstNode": {"input": {}}}
    assert qt_cockpit.load_remote_catalog(client) == client.object_info.return_value
    client.object_info.reset_mock()
    assert qt_cockpit.load_remote_catalog(client) == client.object_info.return_value
    client.object_info.assert_not_called()
    assert qt_cockpit.read_remote_catalog("https://another-pod.example") is None
    path = qt_cockpit.remote_catalog_path(URL)
    os.utime(path, (time.time() - 600, time.time() - 600))
    assert qt_cockpit.read_remote_catalog(URL) is None
    qt_cockpit.load_remote_catalog(client)
    client.object_info.assert_called_once()


def test_remote_connection_never_starts_local_services(monkeypatch):
    monkeypatch.setenv("GENESIS_COMFY_URL", URL)
    client = Mock()
    client.system_stats.return_value = {"devices": [{"name": "A100", "type": "cuda"}]}
    monkeypatch.setattr(qt_cockpit.workflow_lab, "ComfyClient", Mock(return_value=client))
    start = Mock(side_effect=AssertionError("remote must not start local services"))
    monkeypatch.setattr(qt_cockpit.integrations, "start_user_service", start)
    bridge = qt_cockpit.GenerationBridge()
    assert bridge._connect_comfyui()[0] is client
    start.assert_not_called()


def test_runpod_launcher_uses_overridable_https_proxy_without_tunnel():
    launcher = (ROOT / "launch-qt-cockpit-runpod.sh").read_text(encoding="utf-8")
    assert "${GENESIS_COMFY_URL:-https://" in launcher
    assert "a5yw5n79egqcxy-8188.proxy.runpod.net" in launcher
    assert "systemctl" not in launcher
    assert "qt_cockpit_linux_premium.py" in launcher


def test_premium_generation_ui_uses_real_bridge_progress_and_remote_badge():
    qml = (ROOT / "genesis" / "qt_ui" / "MainPremiumLinux.qml").read_text(encoding="utf-8")
    assert "genesisBridge.progress" in qml
    assert "RUNPOD ONLINE" in qml
    assert "RUNPOD OFFLINE" in qml


def test_prompt_override_never_replaces_conditioning_links():
    prompt = {
        "6": {"class_type": "CFGGuider", "inputs": {"positive": ["4", 0], "negative": ["5", 0]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": "a ceramic mug"}},
    }
    controls = qt_cockpit.workflow_lab.discover_workflow_controls(prompt)
    assert controls["positive"] == ("4", "text")
    assert "negative" not in controls


def test_missing_refinement_asset_blocks_before_any_generation(monkeypatch, tmp_path):
    monkeypatch.setenv("GENESIS_COMFY_URL", URL)
    bridge = qt_cockpit.GenerationBridge()
    client = Mock(base_url=URL)
    monkeypatch.setattr(bridge, "_connect_comfyui", lambda: (client, {}))
    info = {"CheckpointLoaderSimple": {"input": {"required": {"ckpt_name": [["available.safetensors"]]}}}}
    monkeypatch.setattr(qt_cockpit, "load_remote_catalog", lambda client: info)
    monkeypatch.setattr(qt_cockpit.workflow_lab, "workflow_to_prompt", lambda path, info: {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "missing.safetensors"}}
    })
    bridge._run_generate("a mug", "", 512, 512, qt_cockpit.QWEN_MODEL,
                         "None", "None", "None", 0.0, 0.0, 0.0,
                         tmp_path / "source.png", None, True, False, False)
    assert qt_cockpit.REMOTE_AISHA_9B_MODEL in bridge.status
    client.submit.assert_not_called()
    client.upload_image.assert_not_called()


def test_runpod_pipeline_hands_results_forward_and_keeps_original_identity(monkeypatch, tmp_path):
    monkeypatch.setenv("GENESIS_COMFY_URL", URL)
    bridge = qt_cockpit.GenerationBridge()
    bridge._output_dir = tmp_path
    client = Mock(base_url=URL)
    monkeypatch.setattr(bridge, "_connect_comfyui", lambda: (client, {}))
    monkeypatch.setattr(qt_cockpit, "load_remote_catalog", lambda client: {})
    monkeypatch.setattr(qt_cockpit, "validate_remote_workflow_assets", lambda *args: None)
    source = tmp_path / "original.png"
    pose = tmp_path / "pose.png"
    stage1, stage2, stage3 = [tmp_path / f"stage{i}.png" for i in (1, 2, 3)]
    run = Mock(side_effect=[stage1, stage2, stage3])
    monkeypatch.setattr(bridge, "_run_reference_stage", run)
    bridge._run_generate("a neutral portrait", "", 512, 512, qt_cockpit.REMOTE_PHR00T_MODEL,
                         "None", "None", "None", 0.0, 0.0, 0.0,
                         source, pose, True, True, False, {"seed": 42})
    first, second, third = run.call_args_list
    assert first.args[2:4] == (qt_cockpit.REMOTE_PHR00T_WORKFLOW, source)
    assert first.kwargs["secondary_image"] == pose
    assert second.args[2:4] == (qt_cockpit.REMOTE_KLEIN9B_WORKFLOW, stage1)
    assert second.kwargs["model_override"] == qt_cockpit.REMOTE_AISHA_9B_MODEL
    assert third.args[2:4] == (qt_cockpit.STAGE_3_WORKFLOW, stage2)
    assert third.kwargs["secondary_image"] == source
    assert bridge.status.startswith("Complete")
