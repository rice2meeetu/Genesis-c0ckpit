import os
from pathlib import Path

import qt_cockpit


ROOT = Path(__file__).resolve().parents[1]


def test_remote_runtime_status_reports_offline_when_tunnel_is_down(monkeypatch):
    monkeypatch.setenv("GENESIS_COMFY_URL", "http://127.0.0.1:18188")
    monkeypatch.setattr(qt_cockpit.integrations, "endpoint_online", lambda *args, **kwargs: False)

    status = qt_cockpit.load_runtime_status()

    assert status["remote"] is True
    assert status["comfyOnline"] is False
    assert status["ready"] is False
    assert status["gpuName"] == "RunPod offline"


def test_remote_runtime_status_reports_online_when_endpoint_answers(monkeypatch):
    monkeypatch.setenv("GENESIS_COMFY_URL", "http://127.0.0.1:18188")
    monkeypatch.setattr(qt_cockpit.integrations, "endpoint_online", lambda *args, **kwargs: True)

    status = qt_cockpit.load_runtime_status()

    assert status["remote"] is True
    assert status["comfyOnline"] is True
    assert status["ready"] is True
    assert "RunPod" in status["gpuName"]


def test_runpod_launcher_starts_tunnel_on_demand():
    launcher = (ROOT / "launch-qt-cockpit-runpod.sh").read_text(encoding="utf-8")
    service = (ROOT / "systemd" / "genesis-runpod-tunnel.service").read_text(encoding="utf-8")

    assert "systemctl --user start genesis-runpod-tunnel.service" in launcher
    assert "GENESIS_COMFY_URL" in launcher
    assert "EnvironmentFile=%h/.config/genesis/runpod-tunnel.env" in service
    assert "RUNPOD_SSH_USER" in service
    assert "RUNPOD_SSH_HOST" in service
    assert "RUNPOD_SSH_PORT" in service
    assert "Restart=on-failure" in service
    assert "RestartSec=30" in service


def test_premium_generation_ui_uses_real_bridge_progress_and_remote_badge():
    qml = (ROOT / "genesis" / "qt_ui" / "MainPremiumLinux.qml").read_text(encoding="utf-8")

    assert "genesisBridge.progress" in qml
    assert "RUNPOD ONLINE" in qml
    assert "RUNPOD OFFLINE" in qml
