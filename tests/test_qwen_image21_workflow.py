import json
from pathlib import Path
from unittest.mock import Mock

import qt_cockpit as cockpit
from genesis.model_compatibility import compatible_loras, model_family
from genesis.model_registry import _match


def test_qwen21_family_is_separate_and_has_no_unverified_loras():
    assert model_family(cockpit.QWEN21_MODEL) == 'qwen_image_2_1'
    assert compatible_loras(cockpit.QWEN21_MODEL, [
        'Flux Klein - NSFW v2.safetensors',
        'Flux-NSFW-uncensored.safetensors',
        'add-detail-xl.safetensors',
    ]) == []


def test_qwen21_t2i_uses_installed_official_assets_and_defaults():
    graph = json.loads(cockpit.QWEN21_T2I_WORKFLOW.read_text())
    assert graph['1']['inputs']['unet_name'] == cockpit.QWEN21_MODEL
    assert graph['3']['inputs']['clip_name'] == cockpit.QWEN21_CLIP
    assert graph['4']['inputs']['vae_name'] == cockpit.QWEN21_VAE
    assert graph['5']['class_type'] == 'TextEncodeQwenImage21'
    assert graph['7']['inputs']['steps'] == 25
    assert graph['7']['inputs']['cfg'] == 1.0
    assert graph['7']['inputs']['sampler_name'] == 'euler'
    assert graph['7']['inputs']['scheduler'] == 'simple'


def test_qwen21_profile_is_runnable_without_source_and_has_model_defaults():
    report = {'profiles': [{
        'name': 'Qwen Image 2.1 BF16',
        'ready': True,
        'evidence': {'MODEL': f'/models/{cockpit.QWEN21_MODEL}'},
    }]}
    profile = cockpit.build_generation_profiles(report, [])[0]
    assert profile['runnable'] is True
    assert profile['sourceRequired'] is False
    assert profile['loras'] == ['None']
    assert profile['defaultSteps'] == 25
    assert profile['defaultCfg'] == 1.0
    assert profile['defaultSampler'] == 'euler'
    assert profile['defaultScheduler'] == 'simple'


def test_qwen21_reference_prunes_unused_second_image(monkeypatch, tmp_path):
    bridge = cockpit.GenerationBridge()
    client = Mock()
    client.upload_image.return_value = {'name': 'source.png', 'subfolder': 'genesis'}
    captured = {}
    monkeypatch.setattr(cockpit.workflow_lab, 'validate_prompt', lambda prompt, info: {
        'valid': True, 'missing_nodes': [], 'missing_inputs': [],
    })
    monkeypatch.setattr(cockpit, 'validate_operation_prompt', lambda *args, **kwargs: None)
    monkeypatch.setattr(
        bridge, '_submit_and_save',
        lambda client, prompt, stamp, stage: captured.update(prompt) or tmp_path / 'out.png',
    )
    bridge._run_reference_stage(
        client, {}, cockpit.QWEN21_REFERENCE_WORKFLOW, tmp_path / 'source.png',
        'Use <image1> as the pose reference.', 'stamp', 'Qwen21',
        controls={'steps': 2, 'cfg': 1.0, 'seed': 7, 'sampler': 'euler', 'scheduler': 'simple'},
        model_override=cockpit.QWEN21_MODEL,
    )
    assert '6' not in captured
    assert captured['7']['inputs']['images'] == {'image_1': ['5', 0]}
    assert captured['5']['inputs']['image'] == 'genesis/source.png'
    client.upload_image.assert_called_once_with(tmp_path / 'source.png')


def test_aisha_base_workflow_uses_base_not_distilled_settings():
    graph = json.loads(cockpit.LOCAL_AISHA_9B_WORKFLOW.read_text())
    assert graph['1']['inputs']['unet_name'] == cockpit.LOCAL_AISHA_9B_MODEL
    assert graph['5']['inputs']['cfg'] == 4.0
    assert graph['7']['inputs']['sampler_name'] == 'euler'
    assert graph['8']['inputs']['steps'] == 50


def test_registry_exact_asset_does_not_confuse_ae_with_qwen_vae():
    paths = [Path('/models/vae/qwen_image_vae.safetensors')]
    assert _match(paths, ('ae.safetensors',)) is None
    assert _match(paths, ('qwen_image_vae.safetensors',)) == paths[0]
