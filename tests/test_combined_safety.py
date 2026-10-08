"""Combined branch regressions: no network, service changes, or GPU submission."""
import json
import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from PyQt6.QtCore import QUrl

import qt_cockpit as c
from genesis.backend_bridge import BackendBridge
from genesis.backend_routing import Route, normalize_endpoint, use_route


PENDING = sorted(c.LOCAL_PENDING_KLEIN_MODELS | {c.QWEN21_MODEL, c.REMOTE_AISHA_9B_MODEL})


@pytest.mark.parametrize("model", PENDING)
def test_installed_large_model_cannot_start_local_worker_or_backend(monkeypatch, tmp_path, model):
    source = tmp_path / "source.png"
    source.write_bytes(b"untouched master")
    profile = c.build_generation_profiles({"profiles": [{"ready": True,
        "evidence": {"MODEL": "/models/" + model}}]}, [])[0]
    assert profile["ready"] and not profile["runnable"]
    bridge = c.GenerationBridge()
    thread = Mock()
    connection = Mock(side_effect=AssertionError("Blocked model must not contact a backend"))
    monkeypatch.setattr(c.threading, "Thread", thread)
    monkeypatch.setattr(bridge, "_connect_comfyui", connection)
    with use_route(Route("LOCAL", "")):
        bridge.queueGenerate("A ceramic vase", "", 512, 512, model,
                             "None", "None", "None", 0, 0, 0,
                             QUrl.fromLocalFile(str(source)).toString() if model in c.SOURCE_EDIT_MODELS else "",
                             "", False, False, False)
        assert "verification is pending" in bridge.status
        bridge._run_generate("A ceramic vase", "", 512, 512, model,
                             "None", "None", "None", 0, 0, 0,
                             source, None, False, False, False)
    thread.assert_not_called()
    connection.assert_not_called()
    assert source.read_bytes() == b"untouched master"


@pytest.mark.parametrize("model", PENDING)
def test_cached_runnable_flag_cannot_bypass_local_model_policy(model):
    bridge = BackendBridge(c.GenerationBridge())
    bridge._mode = "AUTO"
    bridge._local_safe = True
    bridge._local_status = {"ready": True}
    bridge._remote_status = {"ready": False}
    bridge._local = [{"model": model, "runnable": True}]
    with pytest.raises(ValueError, match="no ready backend"):
        bridge.resolve(model)


def test_local_refinement_cannot_bypass_model_policy(monkeypatch, tmp_path):
    bridge = c.GenerationBridge()
    bridge._finish_route = Route("LOCAL", "")
    connection = Mock(side_effect=AssertionError("Must block before backend connection"))
    monkeypatch.setattr(bridge, "_connect_comfyui", connection)
    bridge._run_finish(tmp_path / "result.png", None, ["refine"], 0,
                       c.LOCAL_MIRACLEIN_9B_MODEL, "None", 0)
    assert "verification is pending" in bridge.status
    connection.assert_not_called()


@pytest.mark.parametrize("url", ["https://brother-8188.proxy.runpod.net", "http://localhost:8188"])
def test_blocked_remote_configuration_keeps_startup_offline_without_falling_back(monkeypatch, url):
    monkeypatch.setenv("GENESIS_RUNPOD_URL", url)
    client = Mock(side_effect=AssertionError("Blocked endpoint must not be contacted"))
    monkeypatch.setattr(c.workflow_lab, "ComfyClient", client)
    monkeypatch.setattr(c, "readiness_report", Mock(side_effect=AssertionError("No local fallback")))
    status = c.load_runtime_status(probe_remote=False)
    assert status["remote"] and not status["ready"]
    assert "8188" in status["error"]
    assert c.load_generation_profiles() == []
    client.assert_not_called()


def test_invalid_port_reports_validation_error():
    with pytest.raises(ValueError, match="endpoint port is invalid"):
        normalize_endpoint("https://example.test:bad")


@pytest.mark.parametrize("launcher", ["launch-qt-cockpit.sh", "launch-qt-cockpit-runpod.sh"])
def test_tunnel_failure_still_opens_ui_without_autoconnect(tmp_path, launcher):
    root = Path(__file__).resolve().parents[1]
    shutil.copy2(root / launcher, tmp_path / launcher)
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "ensure-runpod-8189-tunnel.sh").write_text("#!/bin/sh\nexit 1\n")
    python = tmp_path / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    output = tmp_path / "launch.json"
    python.write_text("#!/usr/bin/env python3\nimport json,os\nfrom pathlib import Path\n"
                      "Path(os.environ['GENESIS_TEST_OUTPUT']).write_text(json.dumps({"
                      "'mode':os.environ.get('GENESIS_BACKEND_MODE'),"
                      "'autoconnect':os.environ.get('GENESIS_RUNPOD_AUTOCONNECT')}))\n")
    python.chmod(0o755)
    env = dict(os.environ, GENESIS_RUNPOD_SSH_HOST="offline.test", GENESIS_TEST_OUTPUT=str(output))
    result = subprocess.run(["bash", str(tmp_path / launcher)], env=env,
                            text=True, capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert "tunnel is unavailable" in result.stderr
    assert json.loads(output.read_text())["autoconnect"] is None


def test_model_registry_has_no_duplicate_profiles():
    from genesis.model_registry import MODEL_PROFILES
    names = [row["name"] for row in MODEL_PROFILES]
    assert len(names) == len(set(names))
