"""FaceID graph and fail-closed checks. These tests never submit GPU jobs."""
import copy
import json
from unittest.mock import Mock
import pytest
import qt_cockpit as c


@pytest.fixture
def info():
    d = {
        "IPAdapterModelLoader": {"input": {"required": {"ipadapter_file": [[c.FACEID_SDXL_MODEL]]}}},
        "LoraLoaderModelOnly": {"input": {"required": {"lora_name": [[c.FACEID_SDXL_LORA]]}}},
        "CLIPVisionLoader": {"input": {"required": {"clip_name": [[c.FACEID_CLIP]]}}},
        "IPAdapterFaceID": {}, "IPAdapterInsightFaceLoader": {},
        "ControlNetLoader": {"input": {"required": {"control_net_name": [[c.REMOTE_SDXL_POSE_CONTROLNET]]}}},
    }
    return d


def graph():
    return {
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": ""}},
        "5": {"class_type": "KSampler", "inputs": {"model": ["user_lora_3", 0], "denoise": 0.8}},
        "user_lora_3": {"class_type": "LoraLoader", "inputs": {"model": ["user_lora_2", 0]}},
        "genesis_source": {"class_type": "LoadImage", "inputs": {"image": "person-a.png"}},
    }


def test_identity_keeps_user_loras_and_openpose(info):
    p = graph()
    c.attach_sdxl_pose(p, info, {"name": "skeleton.png"}, 1024, 1024)
    pose_before = copy.deepcopy(p["genesis_pose_apply"])
    c.attach_sdxl_faceid(p, info, {})
    assert p["genesis_faceid_lora"]["inputs"]["model"] == ["user_lora_3", 0]
    assert p["5"]["inputs"]["model"] == ["genesis_faceid", 0]
    assert p["5"]["inputs"]["positive"] == ["genesis_pose_apply", 0]
    assert p["genesis_pose_apply"] == pose_before
    assert p["genesis_faceid"]["inputs"]["image"] == ["genesis_source", 0]
    assert p["5"]["inputs"]["denoise"] == 0.55
    assert p["genesis_faceid_insight"]["inputs"]["provider"] == "CPU"


@pytest.mark.parametrize("kind", ["IPAdapterModelLoader", "LoraLoaderModelOnly", "CLIPVisionLoader",
                                  "IPAdapterFaceID", "IPAdapterInsightFaceLoader"])
def test_missing_capability_leaves_graph_unchanged(info, kind):
    p = graph(); before = copy.deepcopy(p); info.pop(kind)
    with pytest.raises(c.workflow_lab.ComfyError):
        c.attach_sdxl_faceid(p, info, {})
    assert p == before


@pytest.mark.parametrize("value", [0.44, 0.61, float("nan")])
def test_denoise_rejected_outside_identity_range(info, value):
    with pytest.raises(c.workflow_lab.ComfyError, match="denoise"):
        c.attach_sdxl_faceid(graph(), info, {"denoise": value})


def test_no_source_fails_closed(info):
    p = graph(); p.pop("genesis_source")
    with pytest.raises(c.workflow_lab.ComfyError, match="Person A"):
        c.attach_sdxl_faceid(p, info, {})


def test_adjustable_strength_and_denoise(info):
    p = graph()
    c.attach_sdxl_faceid(p, info, {"faceid_strength": 0.9, "denoise": 0.45})
    assert p["genesis_faceid"]["inputs"]["weight"] == 0.9
    assert p["5"]["inputs"]["denoise"] == 0.45


def test_direct_reactor_stage_blocks_before_upload(tmp_path):
    b = c.GenerationBridge(); client = Mock()
    with pytest.raises(c.workflow_lab.ComfyError, match="target is unverified"):
        b._run_reference_stage(client, {}, c.STAGE_3_WORKFLOW, tmp_path/"target.png",
                               "", "test", "Stage3", secondary_image=tmp_path/"person-a.png")
    client.upload_image.assert_not_called()


@pytest.mark.parametrize("enabled", [False, True])
def test_main_create_route_opt_in_and_catalog_refresh(monkeypatch, tmp_path, info, enabled):
    from genesis.backend_routing import Route, use_route
    b = c.GenerationBridge(); b._output_dir = tmp_path
    client = Mock(); client.upload_image.side_effect = lambda p: {"name": p.name}
    monkeypatch.setattr(b, "_connect_comfyui", lambda: (client, {}))
    catalog = Mock(return_value=info); monkeypatch.setattr(c, "load_remote_catalog", catalog)
    monkeypatch.setattr(c, "build_create_prompt", lambda *a, **kw: graph())
    monkeypatch.setattr(c, "apply_create_controls", lambda *a: None)
    monkeypatch.setattr(c, "validate_operation_prompt", lambda *a: None)
    captured = {}
    monkeypatch.setattr(b, "_submit_and_save", lambda _, p, *a: captured.update(p) or tmp_path/"out.png")
    with use_route(Route("RUNPOD", "https://offline-test-8189.proxy.runpod.net")):
        result = b._run_generate("portrait", "", 1024, 1024, c.REMOTE_DONUTS_MODEL,
            "None", "None", "None", 0, 0, 0, tmp_path/"person-a.png", tmp_path/"skeleton.png",
            False, False, False, {"faceid_enabled": enabled, "denoise": 0.55})
    assert result == tmp_path/"out.png", b._status
    assert ("genesis_faceid" in captured) is enabled
    assert captured["genesis_pose_apply"]["inputs"]["control_net"] == ["genesis_pose_controlnet", 0]
    if enabled:
        catalog.assert_called_once_with(client, refresh=True)
    else:
        catalog.assert_called_once_with(client)


def test_faceid_other_family_rejected_before_submission(monkeypatch, tmp_path):
    from genesis.backend_routing import Route, use_route
    b = c.GenerationBridge(); b._output_dir = tmp_path
    monkeypatch.setattr(b, "_connect_comfyui", lambda: (Mock(), {}))
    monkeypatch.setattr(c, "load_remote_catalog", lambda *a, **kw: {})
    monkeypatch.setattr(c, "validate_remote_workflow_assets", lambda *a: None)
    submit = Mock(); monkeypatch.setattr(b, "_submit_and_save", submit)
    with use_route(Route("RUNPOD", "https://offline-test-8189.proxy.runpod.net")):
        assert b._run_generate("portrait", "", 512, 512, c.REMOTE_PHR00T_MODEL,
            "None", "None", "None", 0, 0, 0, tmp_path/"person-a.png", None,
            False, False, False, {"faceid_enabled": True}) is None
    submit.assert_not_called()
    assert "supported only for SDXL" in b._status


def test_source_latent_only_when_pose_first_is_off(info, monkeypatch, tmp_path):
    """On a new pose, FaceID sees the source but its original body cannot override OpenPose."""
    from genesis.backend_routing import Route, use_route
    for faceid_enabled, pose_selected, expected_pose_first in ((True, True, True), (True, False, False), (False, True, False)):
        b = c.GenerationBridge()
        b._output_dir = tmp_path
        client = Mock()
        client.upload_image.side_effect = lambda p: {"name": p.name, "subfolder": "genesis"}
        monkeypatch.setattr(b, "_connect_comfyui", lambda: (client, {}))
        monkeypatch.setattr(c, "load_remote_catalog", lambda *a, **kw: info)
        def build(*a, **kw):
            prompt = graph()
            prompt["4"] = {"class_type": "EmptyLatentImage", "inputs": {"width": 768, "height": 768, "batch_size": 1}}
            prompt["5"]["inputs"]["latent_image"] = ["4", 0]
            return prompt
        monkeypatch.setattr(c, "build_create_prompt", build)
        monkeypatch.setattr(c, "apply_create_controls", lambda *a: None)
        monkeypatch.setattr(c, "validate_operation_prompt", lambda *a: None)
        captured = {}
        monkeypatch.setattr(b, "_submit_and_save", lambda _, p, *a: captured.update(copy.deepcopy(p)) or tmp_path/"out.png")
        pose = tmp_path/"skeleton.png" if pose_selected else None
        with use_route(Route("RUNPOD", "https://offline-test-8189.proxy.runpod.net")):
            result = b._run_generate("portrait", "", 768, 768, c.REMOTE_DONUTS_MODEL,
                "None", "None", "None", 0, 0, 0,
                tmp_path/"person-a.png", pose, False, False, False,
                {"faceid_enabled": faceid_enabled, "denoise": 0.55})
        assert result == tmp_path/"out.png", b._status
        assert "genesis_source" in captured
        if expected_pose_first:
            assert "genesis_source_encode" not in captured
            assert captured["5"]["inputs"]["latent_image"] == ["4", 0]
            assert captured["5"]["inputs"]["denoise"] == 1.0
            assert "genesis_pose_apply" in captured
            assert "genesis_faceid" in captured
        else:
            assert captured["5"]["inputs"]["latent_image"] == ["genesis_source_encode", 0]
            assert ("genesis_faceid" in captured) == faceid_enabled
            assert ("genesis_pose_apply" in captured) == pose_selected
            if faceid_enabled:
                assert captured["5"]["inputs"]["denoise"] == 0.55
