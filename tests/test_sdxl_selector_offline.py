"""Offline SDXL selector regression tests. No generation or GPU work."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from unittest.mock import Mock
import qt_cockpit as cockpit
from genesis.backend_bridge import BackendBridge


@pytest.fixture(autouse=True)
def isolated_backend_settings(monkeypatch):
    # Route-selection tests must never overwrite the user's saved backend mode.
    monkeypatch.setattr("genesis.backend_bridge.QSettings", lambda *args: Mock())


def _local_sdxl(model):
    return {
        "label": model, "model": model, "runnable": True, "ready": True,
        "remote": False, "stageOneEligible": True, "sourceSupported": True,
        "loras": ["None"], "modelPath": "/models/checkpoints/" + model,
    }


@pytest.mark.parametrize("model", [cockpit.REMOTE_DONUTS_MODEL, cockpit.REMOTE_BIGLUSTY_DONUT_MODEL])
def test_offline_runpod_shows_and_routes_installed_local_sdxl(model):
    bridge = BackendBridge(cockpit.GenerationBridge())
    bridge._mode = "RUNPOD"
    bridge._endpoint = "https://test-8189.proxy.runpod.net"
    bridge._connected = True
    bridge._local_safe = True
    bridge._local_status = {"ready": True}
    bridge._remote_status = {"ready": False}
    bridge._local = [_local_sdxl(model)]
    bridge._remote = []
    events = []
    bridge.profilesReady.connect(events.append)
    bridge._publish()
    offline = next(row for row in events[-1] if row["model"] == model)
    assert offline["stageOneEligible"] and offline["ready"]
    assert not offline["routeReady"] and not offline["selectable"]
    bridge.prepareModelRoute(model)
    assert bridge.mode == "AUTO"
    active = next(row for row in events[-1] if row["model"] == model)
    assert active["routeReady"] and active["runnable"] and active["selectable"]
    assert active["destination"] == "LOCAL"
    assert bridge.resolve(model).destination == "LOCAL"


@pytest.mark.parametrize("model", [cockpit.REMOTE_DONUTS_MODEL, cockpit.REMOTE_BIGLUSTY_DONUT_MODEL])
def test_gpu_safety_prevents_local_sdxl_switch(model):
    bridge = BackendBridge(cockpit.GenerationBridge())
    bridge._mode = "RUNPOD"
    bridge._local_safe = False
    bridge._local_status = {"ready": True}
    bridge._remote_status = {"ready": False}
    bridge._local = [_local_sdxl(model)]
    bridge.prepareModelRoute(model)
    assert bridge.mode == "RUNPOD"
    with pytest.raises(ValueError, match="no ready backend"):
        bridge.resolve(model)


def test_qml_picker_can_choose_both_unavailable_sdxl_profiles(tmp_path):
    script = r"""
import sys
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QApplication
import qt_cockpit_linux_premium as launcher

launcher.load_pose_items = lambda **kwargs: []
launcher.load_grok_preset_items = lambda: []
launcher.load_curated_pose_presets = lambda: []
launcher.load_runtime_status = lambda **kwargs: {"identityEngines":[]}
launcher.BackendBridge.start = lambda self: None
engines = []
factory = launcher.QQmlApplicationEngine
launcher.QQmlApplicationEngine = lambda: (engines.append(factory()) or engines[-1])

def verify():
    try:
        window = engines[0].rootObjects()[0]
        names = ["donutsdeliverymixV4_v41.safetensors",
                 "biglustydonutmixNSFW_v12.safetensors"]
        rows = [{"model":name, "label":name, "stageOneConfigured":True,
                 "stageOneEligible":True, "profileSelectable":True, "selectable":False, "runnable":False,
                 "ready":False, "routeReady":False, "loras":["None"]}
                for name in names]
        window.setProperty("generationModel", rows)
        QApplication.processEvents()
        picker = window.findChild(QObject, "stageOneModelPicker")
        button = window.findChild(QObject, "generateButton")
        assert picker is not None and picker.property("count") == 2
        assert button is not None and not button.property("enabled")
        for index, name in enumerate(names):
            window.selectStageOneAvailableChoice(index)
            QApplication.processEvents()
            assert window.property("selectedModelName") == name
            assert not button.property("enabled")
        print("OFFLINE_SDXL_PICKER_OK")
        QApplication.instance().exit(0)
    except Exception:
        import traceback
        traceback.print_exc()
        QApplication.instance().exit(1)

class CheckedApp(QApplication):
    def exec(self):
        QTimer.singleShot(200, verify)
        QTimer.singleShot(12000, lambda: self.exit(2))
        return super().exec()
launcher.QApplication = CheckedApp
sys.argv = ["offline-selector-test", "--page", "create"]
sys.exit(launcher.main())
"""
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen",
               XDG_RUNTIME_DIR=str(runtime), QTWEBENGINE_DISABLE_SANDBOX="1",
               QT_QUICK_BACKEND="software", QSG_RHI_BACKEND="software",
               LIBGL_ALWAYS_SOFTWARE="1", GENESIS_RUNPOD_AUTOCONNECT="0")
    result = subprocess.run([sys.executable, "-c", script],
                            cwd=Path(__file__).resolve().parents[1], env=env,
                            text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OFFLINE_SDXL_PICKER_OK" in result.stdout


@pytest.mark.parametrize("model", [cockpit.REMOTE_DONUTS_MODEL, cockpit.REMOTE_BIGLUSTY_DONUT_MODEL])
@pytest.mark.parametrize("busy, remote_ready", [(True, False), (False, True)])
def test_explicit_selection_preserves_busy_or_ready_remote_route(model, busy, remote_ready):
    generation = Mock(busy=busy)
    bridge = BackendBridge(generation)
    bridge._mode = "RUNPOD"
    bridge._local_safe = True
    bridge._local_status = {"ready": True}
    bridge._remote_status = {"ready": remote_ready}
    bridge._local = [_local_sdxl(model)]
    bridge.prepareModelRoute(model)
    assert bridge.mode == "RUNPOD"
    bridge.settings.setValue.assert_not_called()


@pytest.mark.parametrize("model", [cockpit.REMOTE_DONUTS_MODEL, cockpit.REMOTE_BIGLUSTY_DONUT_MODEL])
def test_local_sdxl_registry_evidence_builds_runnable_profile(model):
    from genesis.model_registry import MODEL_PROFILES
    configured = next(p for p in MODEL_PROFILES if model in p["model"])
    report = {"profiles": [{"name": configured["name"], "ready": True,
                           "evidence": {"MODEL": "/models/checkpoints/" + model,
                                        "WORKFLOW": str(cockpit.REMOTE_SDXL_T2I_WORKFLOW)}}]}
    row = cockpit.build_generation_profiles(report, [])[0]
    assert row["model"] == model
    assert row["runnable"] and row["stageOneEligible"]
