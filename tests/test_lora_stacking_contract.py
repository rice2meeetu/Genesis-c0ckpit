from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import qt_cockpit as cockpit
from genesis import model_compatibility as compatibility

LORAS = ["Flux Klein - NSFW v2.safetensors", "Klein_Anatomy_Revamped.safetensors", "flux2klein_body_version_a.safetensors"]
STRENGTHS = [0.2, 0.55, 0.9]


@pytest.mark.parametrize("model", [cockpit.REGULAR_9B_MODEL, cockpit.REMOTE_KLEIN_9B_MODEL, cockpit.LOCAL_MIRACLEIN_9B_MODEL])
def test_profiles_offer_three_slots_and_filter_other_families(model):
    available = LORAS + ["add-detail-xl.safetensors"]
    report = {"profiles": [{"ready": True, "evidence": {"MODEL": "/models/" + model}}]}
    local = cockpit.build_generation_profiles(report, available)[0]
    remote = cockpit.build_remote_generation_profiles({
        "UNETLoader": {"input": {"required": {"unet_name": [[model], {}]}}},
        "LoraLoaderModelOnly": {"input": {"required": {"lora_name": [available, {}]}}},
    })[0]
    for row in (local, remote):
        assert row["maxLoras"] == 3
        assert row["loras"][0] == "None"
        assert set(row["loras"][1:]) == set(LORAS)


def test_no_compatible_loras_means_no_slots():
    report = {"profiles": [{"ready": True, "evidence": {"MODEL": "/models/" + cockpit.QWEN21_MODEL}}]}
    row = cockpit.build_generation_profiles(report, LORAS)[0]
    assert row["maxLoras"] == 0
    assert row["loras"] == ["None"]


@pytest.mark.parametrize("model", [cockpit.REGULAR_9B_MODEL, cockpit.REMOTE_KLEIN_9B_MODEL])
def test_queue_accepts_three_loras_and_preserves_strengths(model, monkeypatch):
    bridge = cockpit.GenerationBridge()
    bridge.backend_router = Mock()
    bridge.backend_router.resolve.return_value = SimpleNamespace(destination="RUNPOD")
    thread = Mock()
    monkeypatch.setattr(cockpit.threading, "Thread", thread)
    bridge.queueGenerate("a ceramic vase", "", 512, 512, model,
                         *LORAS, *STRENGTHS, "", "", False, False, False)
    assert bridge.busy
    thread.return_value.start.assert_called_once()
    assert thread.call_args.kwargs["args"][6:12] == (*LORAS, *STRENGTHS)


def test_source_4b_stacks_only_approved_loras_and_keeps_clip_clean(monkeypatch, tmp_path):
    loras = sorted(compatibility.KLEIN_4B_LORAS)
    monkeypatch.setattr(compatibility, "KLEIN_4B_RUNTIME_VERIFIED_LORAS", set(loras))
    prompt = {str(i): {"inputs": {}} for i in (1, 2, 4, 5, 6, 7, 8, 9, 11)}
    prompt["4"]["inputs"]["lora_name"] = "legacy-default"
    bridge = cockpit.GenerationBridge()
    submit = Mock(return_value=tmp_path / "result.png")
    monkeypatch.setattr(bridge, "_submit_and_save", submit)
    monkeypatch.setattr(cockpit.workflow_lab, "workflow_to_prompt", lambda *args: prompt)
    monkeypatch.setattr(cockpit.workflow_lab, "validate_prompt", lambda *args: {"valid": True, "missing_nodes": [], "missing_inputs": []})
    client = Mock()
    client.upload_image.return_value = {"name": "source.png"}
    bridge._run_4b_source(client, {}, tmp_path / "source.png", "a vase", loras, STRENGTHS, 512, 512, "stamp")
    assert "4" not in prompt
    assert prompt["5"]["inputs"]["clip"] == ["2", 0]
    assert prompt["6"]["inputs"]["clip"] == ["2", 0]
    assert prompt["8"]["inputs"]["model"] == ["genesis_lora_3", 0]
    for i, (name, strength) in enumerate(zip(loras, STRENGTHS), 1):
        inputs = prompt[f"genesis_lora_{i}"]["inputs"]
        assert inputs["lora_name"] == name
        assert inputs["strength_model"] == strength
        assert inputs["model"] == (["1", 0] if i == 1 else [f"genesis_lora_{i-1}", 0])


def test_three_loras_reach_remote_source_workflow(monkeypatch, tmp_path):
    prompt = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": cockpit.REMOTE_KLEIN_9B_MODEL}},
        "6": {"class_type": "CFGGuider", "inputs": {"model": ["1", 0]}},
        "12": {"class_type": "LoadImage", "inputs": {"image": "source.png"}},
    }
    monkeypatch.setattr(cockpit, "remote_url", lambda: "")
    monkeypatch.setattr(cockpit, "_reconcile_remote_klein_clip", lambda *args: None)
    monkeypatch.setattr(cockpit.workflow_lab, "workflow_to_prompt", lambda *args: prompt)
    monkeypatch.setattr(cockpit.workflow_lab, "validate_prompt", lambda *args: {"valid": True, "missing_nodes": [], "missing_inputs": []})
    bridge = cockpit.GenerationBridge()
    monkeypatch.setattr(bridge, "_submit_and_save", Mock(return_value=tmp_path / "result.png"))
    client = Mock()
    client.upload_image.return_value = {"name": "source.png"}
    bridge._run_reference_stage(client, {}, cockpit.REMOTE_KLEIN9B_WORKFLOW, tmp_path / "source.png",
                                "", "stamp", "Klein9B", model_override=cockpit.REMOTE_KLEIN_9B_MODEL,
                                loras=LORAS, lora_strengths=STRENGTHS)
    assert prompt["6"]["inputs"]["model"] == ["genesis_lora_3", 0]
    for i, strength in enumerate(STRENGTHS, 1):
        assert prompt[f"genesis_lora_{i}"]["inputs"]["strength_model"] == strength


def test_lora_controls_use_all_three_slots_and_hide_when_unavailable():
    qml = (cockpit.PROJECT_ROOT / "genesis/qt_ui/MainPremiumLinux.qml").read_text()
    for count in (0, 1, 2):
        assert f'visible: (appRoot.selectedGenerationProfile.maxLoras || 0) > {count}' in qml
    assert 'onActivated: appRoot.selectedLoraTwo = currentText' in qml
    assert 'onActivated: appRoot.selectedLoraThree = currentText' in qml


def test_single_available_adapter_does_not_collapse_slot_controls():
    row = cockpit.build_remote_generation_profiles({
        "UNETLoader": {"input": {"required": {"unet_name": [[cockpit.REMOTE_KLEIN_9B_MODEL], {}]}}},
        "LoraLoaderModelOnly": {"input": {"required": {"lora_name": [[LORAS[0]], {}]}}},
    })[0]
    assert row["maxLoras"] == 3
    assert row["loras"] == ["None", LORAS[0]]
