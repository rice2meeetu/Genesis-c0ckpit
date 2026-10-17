from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

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
    # Port allocation is not the launch contract under test. Avoid opening a
    # real socket, while verifying each new launch requests a loopback port.
    listener = MagicMock()
    listener.__enter__.return_value = listener
    listener.getsockname.return_value = ("127.0.0.1", 43123)
    monkeypatch.setattr("socket.socket", lambda: listener)
    bridge = cockpit.ModuleBridge()
    bridge.backend_router = SimpleNamespace(mode="RUNPOD", endpoint="https://chosen.example")
    yield bridge, launch
    assert listener.bind.call_count == launch.call_count
    for call in listener.bind.call_args_list:
        assert call.args == (("127.0.0.1", 0),)


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
    assert bridge.studioUrl.startswith("http://127.0.0.1:")
    opened.assert_not_called()
    bridge.backend_router.endpoint = "https://new.example"
    bridge.triggerAction("grok imagine")
    assert launch.call_count == 2
    assert launch.call_args.kwargs["env"]["COMFY_URL"] == "https://new.example"


def test_grok_never_inherits_managed_brain_without_shared_brain(studio, monkeypatch):
    bridge, launch = studio
    monkeypatch.setenv("MUNGBEAN_MANAGE_BRAIN", "1")
    monkeypatch.delenv("GENESIS_BRAIN_URL", raising=False)
    monkeypatch.delenv("GENESIS_CLOUD_BASE_URL", raising=False)
    bridge.triggerAction("grok imagine")
    assert launch.call_args.kwargs["env"]["MUNGBEAN_MANAGE_BRAIN"] == "0"


def test_shared_brain_route_and_model_changes_start_a_new_session(studio, monkeypatch):
    bridge, launch = studio
    monkeypatch.setenv("GENESIS_BRAIN_URL", "https://brain.example/v1/")
    monkeypatch.setenv("GENESIS_BRAIN_MODEL", "qwen-powerful")
    monkeypatch.setenv("MUNGBEAN_MANAGE_BRAIN", "1")
    bridge.triggerAction("grok imagine")
    env = launch.call_args.kwargs["env"]
    assert env["BRAIN_URL"] == "https://brain.example/v1"
    assert env["GENESIS_BRAIN_MODEL"] == "qwen-powerful"
    assert env["MUNGBEAN_MANAGE_BRAIN"] == "0"
    monkeypatch.setenv("GENESIS_BRAIN_MODEL", "another-qwen")
    bridge.triggerAction("grok imagine")
    assert launch.call_count == 2


@pytest.mark.parametrize("url", ["https://brain.example", "https://brain.example/v1/"])
def test_assistant_shares_brain_configuration_without_duplicate_v1(monkeypatch, url):
    from genesis.assistant_bridge import AssistantBridge
    monkeypatch.setenv("GENESIS_BRAIN_URL", url)
    monkeypatch.setenv("GENESIS_BRAIN_MODEL", "qwen-powerful")
    bridge = AssistantBridge()
    assert bridge._cloud_base_url() == "https://brain.example"
    assert bridge._cloud_model() == "qwen-powerful"
