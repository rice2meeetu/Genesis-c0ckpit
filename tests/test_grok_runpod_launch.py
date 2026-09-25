from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import qt_cockpit as cockpit


@pytest.fixture
def studio(monkeypatch, tmp_path):
    root = tmp_path / "MUNGBEAN"
    root.mkdir()
    (root / "START_LOCAL.sh").touch()
    monkeypatch.setattr(cockpit.Path, "home", lambda: tmp_path)
    monkeypatch.setenv("COMFY_URL", "http://127.0.0.1:8188")
    process = Mock()
    process.poll.return_value = None
    launch = Mock(return_value=process)
    monkeypatch.setattr(cockpit.subprocess, "Popen", launch)
    bridge = cockpit.ModuleBridge()
    bridge.backend_router = SimpleNamespace(mode="RUNPOD", endpoint="https://chosen.example")
    return bridge, launch


def test_grok_uses_selected_endpoint_instead_of_inherited_local_default(studio):
    bridge, launch = studio
    bridge.triggerAction("grok imagine")
    env = launch.call_args.kwargs["env"]
    assert env["COMFY_URL"] == "https://chosen.example"
    assert env["IMAGINE_HOST"] == "127.0.0.1"
    assert int(env["IMAGINE_PORT"]) > 0


@pytest.mark.parametrize("mode,endpoint", [("LOCAL", "https://remote.example"),
    ("AUTO", "https://remote.example"), ("RUNPOD", ""), ("RUNPOD", "invalid")])
def test_grok_cannot_silently_fall_back_to_local(studio, mode, endpoint):
    bridge, launch = studio
    bridge.backend_router = SimpleNamespace(mode=mode, endpoint=endpoint)
    bridge.triggerAction("grok imagine")
    launch.assert_not_called()


def test_reopening_same_endpoint_reuses_session_and_switching_captures_new_endpoint(studio, monkeypatch):
    bridge, launch = studio
    opened = Mock()
    monkeypatch.setattr(bridge, "_open", opened)
    bridge.triggerAction("grok imagine")
    bridge.triggerAction("grok imagine")
    assert launch.call_count == 1
    opened.assert_called_once()
    bridge.backend_router.endpoint = "https://new.example"
    bridge.triggerAction("grok imagine")
    assert launch.call_count == 2
    assert launch.call_args.kwargs["env"]["COMFY_URL"] == "https://new.example"
