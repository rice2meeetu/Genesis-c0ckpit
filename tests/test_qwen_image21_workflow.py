import json
import pytest
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
    assert graph['7']['inputs']['steps'] == 40
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
    assert profile['defaultSteps'] == 40
    assert profile['defaultCfg'] == 1.0
    assert profile['defaultSampler'] == 'euler'
    assert profile['defaultScheduler'] == 'simple'


def test_qwen21_reference_prunes_unused_second_image(monkeypatch, tmp_path):
    monkeypatch.setattr(cockpit, 'remote_url', lambda: '')
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
    assert captured['1'] == {
        'class_type': 'GenesisQwen21ReferenceUNETLoader',
        'inputs': {'unet_name': cockpit.QWEN21_MODEL},
    }
    assert captured['3'] == {
        'class_type': 'GenesisQwen21ReferenceCLIPLoader',
        'inputs': {'clip_name': cockpit.QWEN21_CLIP},
    }
    assert '6' not in captured
    assert captured['7']['inputs']['images.image_1'] == ['5', 0]
    assert 'images' not in captured['7']['inputs']
    assert 'images.image_2' not in captured['7']['inputs']
    assert captured['5']['inputs']['image'] == 'genesis/source.png'
    client.upload_image.assert_called_once_with(tmp_path / 'source.png')


def test_aisha_base_workflow_uses_base_not_distilled_settings():
    graph = json.loads(cockpit.LOCAL_AISHA_9B_WORKFLOW.read_text())
    # The saved template can be a distilled Aisha checkpoint; the builder
    # selects the requested official base model explicitly at runtime.
    assert graph['1']['inputs']['unet_name'] in (cockpit.LOCAL_AISHA_9B_MODEL, cockpit.REMOTE_AISHA_BF16_MODEL)
    assert graph['5']['inputs']['cfg'] == 4.0
    assert graph['7']['inputs']['sampler_name'] == 'euler'
    assert graph['8']['inputs']['steps'] == 50


def test_registry_exact_asset_does_not_confuse_ae_with_qwen_vae():
    paths = [Path('/models/vae/qwen_image_vae.safetensors')]
    assert _match(paths, ('ae.safetensors',)) is None
    assert _match(paths, ('qwen_image_vae.safetensors',)) == paths[0]


def test_qwen21_remote_reference_keeps_native_loader(monkeypatch, tmp_path):
    monkeypatch.setattr(cockpit, 'remote_url', lambda: 'https://example.invalid')
    graph = json.loads(cockpit.QWEN21_REFERENCE_WORKFLOW.read_text())
    monkeypatch.setattr(cockpit, 'remote_workflow_prompt', lambda *args: graph)
    monkeypatch.setattr(cockpit.workflow_lab, 'validate_prompt', lambda *args: {
        'valid': True, 'missing_nodes': [], 'missing_inputs': [],
    })
    monkeypatch.setattr(cockpit, 'validate_operation_prompt', lambda *args: None)
    bridge = cockpit.GenerationBridge()
    client = Mock()
    client.upload_image.return_value = {'name': 'source.png'}
    captured = {}
    monkeypatch.setattr(bridge, '_submit_and_save',
                        lambda client, prompt, stamp, stage: captured.update(prompt) or tmp_path / 'out.png')
    bridge._run_reference_stage(client, {}, cockpit.QWEN21_REFERENCE_WORKFLOW,
                                tmp_path / 'source.png', 'Preserve <image1>.', 'stamp', 'Qwen21',
                                model_override=cockpit.QWEN21_MODEL)
    assert captured['1']['class_type'] == 'UNETLoader'
    assert captured['3']['class_type'] == 'CLIPLoader'
    assert captured['3']['inputs']['clip_name'] == cockpit.QWEN21_CLIP


@pytest.mark.parametrize('remote,has_source,denoise,source_latent', [
    ('', True, 0.3, True),
    ('', True, 1.0, False),
    ('', False, 0.3, False),
    ('https://example.invalid', True, 0.3, False),
])
def test_qwen21_source_initialization_respects_route_and_strength(
        monkeypatch, tmp_path, remote, has_source, denoise, source_latent):
    monkeypatch.setattr(cockpit, 'remote_url', lambda: remote)
    monkeypatch.setattr(cockpit, 'remote_workflow_prompt',
                        lambda *args: json.loads(cockpit.QWEN21_REFERENCE_WORKFLOW.read_text()))
    monkeypatch.setattr(cockpit.workflow_lab, 'validate_prompt', lambda *args: {
        'valid': True, 'missing_nodes': [], 'missing_inputs': [],
    })
    monkeypatch.setattr(cockpit, 'validate_operation_prompt', lambda *args: None)
    bridge = cockpit.GenerationBridge()
    client = Mock()
    client.upload_image.return_value = {'name': 'source.png'}
    captured = {}
    monkeypatch.setattr(bridge, '_submit_and_save',
                        lambda client, prompt, stamp, stage: captured.update(prompt) or tmp_path / 'out.png')
    bridge._run_reference_stage(
        client, {}, cockpit.QWEN21_REFERENCE_WORKFLOW, tmp_path / 'source.png',
        'Keep <image1>.', 'stamp', 'Qwen21', controls={'denoise': denoise},
        model_override=cockpit.QWEN21_MODEL, initialize_from_source=has_source,
    )
    assert captured['8']['inputs']['denoise'] == denoise
    if source_latent:
        assert captured['8']['inputs']['latent_image'] == ['__qwen21_source_latent__', 0]
        assert captured['__qwen21_source_scale__']['inputs'] == {
            'image': ['5', 0], 'upscale_method': 'lanczos', 'megapixels': 1.0,
            'resolution_steps': 32,
        }
        assert captured['__qwen21_source_latent__']['inputs'] == {
            'pixels': ['__qwen21_source_scale__', 0], 'vae': ['4', 0],
        }
    else:
        assert captured['8']['inputs']['latent_image'] == ['7', 2]
        assert '__qwen21_source_latent__' not in captured


def test_qwen21_local_two_references_use_comfy_dynamic_input_keys(monkeypatch, tmp_path):
    monkeypatch.setattr(cockpit, 'remote_url', lambda: '')
    monkeypatch.setattr(cockpit.workflow_lab, 'validate_prompt', lambda *args: {
        'valid': True, 'missing_nodes': [], 'missing_inputs': [],
    })
    monkeypatch.setattr(cockpit, 'validate_operation_prompt', lambda *args: None)
    client = Mock()
    client.upload_image.side_effect = [{'name': 'source.png'}, {'name': 'pose.png'}]
    bridge = cockpit.GenerationBridge()
    captured = {}
    monkeypatch.setattr(bridge, '_submit_and_save',
                        lambda client, prompt, stamp, stage: captured.update(prompt))
    bridge._run_reference_stage(client, {}, cockpit.QWEN21_REFERENCE_WORKFLOW,
        tmp_path / 'source.png', 'Match the source and pose.', 'stamp', 'Qwen21',
        secondary_image=tmp_path / 'pose.png', model_override=cockpit.QWEN21_MODEL)
    inputs = captured['7']['inputs']
    assert inputs['images.image_1'] == ['5', 0]
    assert inputs['images.image_2'] == ['6', 0]
    assert 'images' not in inputs
    assert captured['5']['inputs']['image'] == 'source.png'
    assert captured['6']['inputs']['image'] == 'pose.png'


@pytest.mark.parametrize('remote,width,height,expected', [
    ('', 512, 512, 512), ('', 768, 1152, 768),
    ('', 1152, 768, 768), ('', 1024, 1024, 1024),
    ('https://example.invalid', 512, 512, 1024),
])
def test_qwen21_reference_size_controls_and_source_latent_agree(monkeypatch, tmp_path, remote, width, height, expected):
    monkeypatch.setattr(cockpit, 'remote_url', lambda: remote)
    monkeypatch.setattr(cockpit, 'remote_workflow_prompt',
                        lambda *args: json.loads(cockpit.QWEN21_REFERENCE_WORKFLOW.read_text()))
    monkeypatch.setattr(cockpit.workflow_lab, 'validate_prompt', lambda *args: {
        'valid': True, 'missing_nodes': [], 'missing_inputs': [],
    })
    monkeypatch.setattr(cockpit, 'validate_operation_prompt', lambda *args: None)
    bridge = cockpit.GenerationBridge()
    client = Mock()
    client.upload_image.return_value = {'name': 'source.png'}
    captured = {}
    monkeypatch.setattr(bridge, '_submit_and_save', lambda client, prompt, stamp, stage: captured.update(prompt))
    bridge._run_reference_stage(client, {}, cockpit.QWEN21_REFERENCE_WORKFLOW,
        tmp_path / 'source.png', 'Keep the source.', 'stamp', 'Qwen21',
        controls={'width': width, 'height': height, 'denoise': 0.3},
        model_override=cockpit.QWEN21_MODEL, initialize_from_source=True)
    assert captured['7']['inputs']['resolution'] == expected
    if not remote:
        assert captured['__qwen21_source_scale__']['inputs']['megapixels'] == (expected / 1024) ** 2
    else:
        assert '__qwen21_source_scale__' not in captured


def test_verified_local_source_default_does_not_change_t2i_or_remote():
    local_source = cockpit.model_generation_settings(cockpit.QWEN21_MODEL, source=True)
    assert (local_source['defaultWidth'], local_source['defaultHeight']) == (768, 768)
    for source, remote in [(False, False), (False, True), (True, True)]:
        defaults = cockpit.model_generation_settings(cockpit.QWEN21_MODEL, source=source, remote=remote)
        assert (defaults['defaultWidth'], defaults['defaultHeight']) == (1024, 1024)
    local = cockpit.model_profile_settings(cockpit.QWEN21_MODEL)
    assert local['qualityPresets']['Quality'] == {'width': 1024, 'height': 1024}
    assert 'eight-minute' in local['qualityNote']
    assert 'eight-minute' not in cockpit.model_profile_settings(cockpit.QWEN21_MODEL, remote=True)['qualityNote']


def test_qwen21_specific_adapter_is_selectable_but_older_qwen_adapter_stays_blocked():
    from genesis.model_compatibility import is_compatible
    matched='Qwen2.1_Anything2RealCharacters.safetensors'
    old='NSFW Qwen by TheseAlpacas V2.safetensors'
    assert is_compatible(cockpit.QWEN21_MODEL,matched)
    assert not is_compatible(cockpit.QWEN21_MODEL,old)
    assert not is_compatible(cockpit.QWEN_MODEL,matched)
    assert cockpit.model_lora_limit(cockpit.QWEN21_MODEL)==3


def test_qwen21_model_only_adapter_is_connected_before_cache(monkeypatch):
    graph=json.loads(cockpit.QWEN21_T2I_WORKFLOW.read_text())
    monkeypatch.setattr(cockpit.workflow_lab,'workflow_to_prompt',lambda *a:graph)
    monkeypatch.setattr(cockpit.workflow_lab,'validate_prompt',lambda *a:{'valid':True,'missing_nodes':[],'missing_inputs':[]})
    name='Qwen2.1_Anything2RealCharacters.safetensors'
    result=cockpit.build_create_prompt({},'Adult person in an ordinary portrait',768,768,cockpit.QWEN21_MODEL,[name],[0.45])
    assert result['genesis_lora_1']['inputs']=={'model':['1',0],'lora_name':name,'strength_model':0.45}
    assert result['2']['inputs']['model']==['genesis_lora_1',0]
    assert result['7']['inputs']['steps']==40


def test_qwen21_reference_adapter_inserted_before_cache(monkeypatch,tmp_path):
    monkeypatch.setattr(cockpit,'remote_url',lambda:'')
    b=cockpit.GenerationBridge()
    client=Mock();client.upload_image.return_value={'name':'source.png','subfolder':'genesis'}
    monkeypatch.setattr(cockpit.workflow_lab,'validate_prompt',lambda *a:{'valid':True,'missing_nodes':[],'missing_inputs':[]})
    monkeypatch.setattr(cockpit,'validate_operation_prompt',lambda *a:None)
    captured={}
    monkeypatch.setattr(b,'_submit_and_save',lambda _,graph,*args:captured.update(graph) or tmp_path/'done.png')
    model='Qwen2.1_Anything2RealCharacters.safetensors'
    b._run_reference_stage(client,{},cockpit.QWEN21_REFERENCE_WORKFLOW,tmp_path/'source.png','Ordinary portrait', 'stamp','Qwen21',model_override=cockpit.QWEN21_MODEL, loras=[model],lora_strengths=[0.5])
    assert captured['2']['inputs']['model']==['genesis_lora_1',0]
    assert captured['genesis_lora_1']['inputs']['lora_name']==model


def test_aisha_base_builder_explicitly_overrides_distilled_template(monkeypatch):
    template=json.loads(cockpit.LOCAL_AISHA_9B_WORKFLOW.read_text())
    monkeypatch.setattr(cockpit.workflow_lab,'workflow_to_prompt',lambda *a:template)
    monkeypatch.setattr(cockpit.workflow_lab,'validate_prompt',lambda *a:{'valid':True,'missing_nodes':[],'missing_inputs':[]})
    graph=cockpit.build_create_prompt({},'Adult subject portrait',512,512,cockpit.LOCAL_AISHA_9B_MODEL,[],[])
    assert graph['1']['inputs']['unet_name']==cockpit.LOCAL_AISHA_9B_MODEL


def test_phr00t_pose_catalog_reports_image2_method_not_sdxl_controlnet():
    info={'CheckpointLoaderSimple':{'input':{'required':{'ckpt_name':[[cockpit.REMOTE_PHR00T_V19_MODEL]]}}}}
    rows=cockpit.build_remote_generation_profiles(info)
    row=next(r for r in rows if r['model']==cockpit.REMOTE_PHR00T_V19_MODEL)
    assert row['poseReady']
    assert row['poseMethod'].startswith('Image-2')
    assert 'NOT OpenPoseXL2' in row['note']
