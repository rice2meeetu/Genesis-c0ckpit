import json

import qt_cockpit
from genesis.model_compatibility import lora_trigger


def _cached_info():
    path = qt_cockpit.Path.home() / ".cache" / "genesis" / "runpod-bdc8a6f5ef980e21-object-info.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_refcontrol_is_offered_for_remote_klein9b_cached_catalog():
    info = _cached_info()
    row = next(
        item for item in qt_cockpit.build_remote_generation_profiles(info)
        if item["model"] == qt_cockpit.REMOTE_KLEIN_9B_MODEL
    )
    assert "refcontrol_v2_poses.safetensors" in row["loras"]


def test_remote_klein_reference_stage_injects_selected_model_only_lora(monkeypatch, tmp_path):
    info = _cached_info()
    bridge = qt_cockpit.GenerationBridge()
    source = tmp_path / "source.png"
    pose = tmp_path / "pose.png"
    source.write_bytes(b"source")
    pose.write_bytes(b"pose")

    class Client:
        def upload_image(self, path):
            return {"name": path.name, "subfolder": ""}

    captured = {}

    def fake_submit(client, prompt, stamp, stage):
        captured.update(prompt)
        return tmp_path / "result.png"

    monkeypatch.setattr(bridge, "_submit_and_save", fake_submit)

    bridge._run_reference_stage(
        Client(),
        info,
        qt_cockpit.REMOTE_KLEIN9B_WORKFLOW,
        source,
        "neutral studio portrait",
        "stamp",
        "Klein9B",
        secondary_image=pose,
        model_override=qt_cockpit.REMOTE_KLEIN_9B_MODEL,
        loras=["refcontrol_v2_poses.safetensors"],
        lora_strengths=[0.65],
    )

    assert captured["genesis_lora_1"]["class_type"] == "LoraLoaderModelOnly"
    assert captured["genesis_lora_1"]["inputs"]["lora_name"] == "refcontrol_v2_poses.safetensors"
    assert captured["6"]["inputs"]["model"] == ["genesis_lora_1", 0]


def test_refcontrol_trigger_metadata_is_exposed():
    assert (
        lora_trigger("refcontrol_v2_poses.safetensors")
        == "apply pose from image 1 with reference from image 2"
    )


def test_klein_pose_reference_is_prepended_before_identity_reference(monkeypatch, tmp_path):
    info = _cached_info()
    bridge = qt_cockpit.GenerationBridge()
    source = tmp_path / "source.png"
    pose = tmp_path / "pose.png"
    source.write_bytes(b"source")
    pose.write_bytes(b"pose")

    class Client:
        def upload_image(self, path):
            return {"name": path.name, "subfolder": ""}

    captured = {}
    monkeypatch.setattr(
        bridge,
        "_submit_and_save",
        lambda client, prompt, stamp, stage: captured.update(prompt) or tmp_path / "result.png",
    )

    bridge._run_reference_stage(
        Client(),
        info,
        qt_cockpit.REMOTE_KLEIN9B_WORKFLOW,
        source,
        "neutral studio portrait",
        "stamp",
        "Klein9B",
        secondary_image=pose,
        model_override=qt_cockpit.REMOTE_KLEIN_9B_MODEL,
    )

    assert captured["__genesis_pose_encode__"]["inputs"]["pixels"] == ["__genesis_pose__", 0]
    assert captured["17"]["inputs"]["conditioning"] == ["__genesis_pose_positive__", 0]
    assert captured["18"]["inputs"]["conditioning"] == ["__genesis_pose_negative__", 0]
    assert captured["__genesis_pose_positive__"]["inputs"]["conditioning"] == ["4", 0]
    assert captured["__genesis_pose_negative__"]["inputs"]["conditioning"] == ["5", 0]
