import qt_cockpit


def test_stage1_uses_regular_clip_loader_for_scaled_fp8_when_no_gguf_encoder(monkeypatch):
    monkeypatch.setattr(qt_cockpit.workflow_lab, 'workflow_to_prompt', lambda *a, **k: {
        '31': {'class_type': 'CLIPLoaderGGUF', 'inputs': {'clip_name': 'missing.gguf', 'type': 'qwen_image'}}
    })
    info = {
        'CLIPLoader': {'input': {'required': {'clip_name': [[qt_cockpit.REMOTE_PHR00T_CLIP]], 'type': [['qwen_image']]}}},
        'CLIPLoaderGGUF': {'input': {'required': {'clip_name': [[qt_cockpit.REMOTE_PHR00T_CLIP]], 'type': [['qwen_image']]}}},
    }
    prompt = qt_cockpit.remote_workflow_prompt(qt_cockpit.STAGE_1_WORKFLOW, info)
    assert prompt['31']['class_type'] == 'CLIPLoader'
    assert prompt['31']['inputs']['clip_name'] == qt_cockpit.REMOTE_PHR00T_CLIP
