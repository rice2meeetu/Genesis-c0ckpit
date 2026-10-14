import json
import re
from pathlib import Path
from unittest.mock import Mock

import pytest
from PyQt6.QtQml import QJSEngine
import qt_cockpit as c
from genesis.model_compatibility import is_compatible, compatible_loras

FIELDS = ('defaultWidth', 'defaultHeight', 'defaultSteps', 'defaultCfg', 'defaultDenoise', 'defaultSampler', 'defaultScheduler')


def test_every_supported_profile_has_complete_route_specific_defaults():
    report = {'profiles': [{'ready': True, 'evidence': {'MODEL': '/models/' + model}} for model in c.SUPPORTED_CREATE_MODELS]}
    local = c.build_generation_profiles(report, [])
    remote = c.build_remote_generation_profiles({'UNETLoader': {'input': {'required': {'unet_name': [sorted(c.SUPPORTED_CREATE_MODELS)]}}}})
    for row in local + remote:
        for values in (row, row['createDefaults'], row['sourceDefaults']):
            assert all(field in values for field in FIELDS), row['model']
            assert values['schedulerFixed'] == (values['defaultScheduler'] == 'Flux2Scheduler')


def test_defaults_match_saved_miraclein_and_v23_sampler_nodes():
    info = json.loads((Path(__file__).parent / 'fixtures/runpod_stage_models_schema.json').read_text())
    for model, source, path in (
        (c.REMOTE_MIRACLEIN_9B_MODEL, False, c.REMOTE_MIRACLEIN_T2I_WORKFLOW),
        (c.REMOTE_MIRACLEIN_9B_MODEL, True, c.REMOTE_MIRACLEIN_EDIT_WORKFLOW),
        (c.REMOTE_PHR00T_MODEL, True, c.REMOTE_PHR00T_WORKFLOW),
    ):
        raw = json.loads(path.read_text())
        if 'nodes' in raw and any(node.get('type') == 'KSampler' for node in raw['nodes']):
            sampler = next(node for node in raw['nodes'] if node.get('type') == 'KSampler')
            widgets = sampler['widgets_values']
            values = c.model_generation_settings(model, source=source)
            assert widgets[2:7] == [values['defaultSteps'], values['defaultCfg'],
                                    values['defaultSampler'], values['defaultScheduler'], values['defaultDenoise']]
            continue
        prompt = c.workflow_lab.workflow_to_prompt(path, info)
        fields = c.workflow_lab.discover_workflow_controls(prompt)
        values = c.model_generation_settings(model, source=source)
        for key in ('steps', 'cfg', 'sampler'):
            node, field = fields[key]
            assert prompt[str(node)]['inputs'][field] == values['default' + key.capitalize()]
        if 'scheduler' in fields:
            node, field = fields['scheduler']
            assert prompt[str(node)]['inputs'][field] == values['defaultScheduler']
        else:
            assert values['schedulerFixed']


def test_qml_switching_models_and_source_resets_settings_and_preset():
    qml = (c.PROJECT_ROOT / 'genesis/qt_ui/MainPremiumLinux.qml').read_text()
    engine = QJSEngine()
    for name in ('applyGenerationDefaults', 'applyQualityPreset', 'qualityPresetActive'):
        function = re.search(r'    function ' + name + r'\(.*?\n    }', qml, re.S).group()
        assert not engine.evaluate(function).isError()
    engine.evaluate('var activeSourceImage = false, generationSource = ""; var generationWidth, generationHeight, generationSteps, generationCfg, generationDenoise, generationSampler, generationScheduler;')
    profile = c.model_profile_settings(c.REMOTE_MIRACLEIN_9B_MODEL, remote=True)
    engine.evaluate('var selectedGenerationProfile = ' + json.dumps(profile))
    engine.evaluate('applyGenerationDefaults(selectedGenerationProfile)')
    assert engine.evaluate('generationScheduler').toString() == 'simple'
    # A photograph can stay loaded while T2I remains selected.
    engine.evaluate('generationSource = "file:///source.png"; applyGenerationDefaults(selectedGenerationProfile)')
    assert engine.evaluate('generationScheduler').toString() == 'simple'
    engine.evaluate('activeSourceImage = true; applyGenerationDefaults(selectedGenerationProfile)')
    assert engine.evaluate('generationScheduler').toString() == 'Flux2Scheduler'
    for name in ('Fast', 'Balanced', 'Quality'):
        engine.evaluate(f'applyQualityPreset("{name}", 512, 512)')
        expected = profile['sourceQualityPresets'][name]
        assert engine.evaluate('generationWidth').toInt() == expected['width']
        assert engine.evaluate('generationHeight').toInt() == expected['height']
        assert engine.evaluate('generationSteps').toInt() == 12
        assert engine.evaluate('generationCfg').toNumber() == 1.1
        assert engine.evaluate(f'qualityPresetActive("{name}", 512, 512)').toBool()
    profile = c.model_profile_settings(c.QWEN_MODEL)
    engine.evaluate('selectedGenerationProfile = ' + json.dumps(profile))
    engine.evaluate('applyGenerationDefaults(selectedGenerationProfile)')
    assert engine.evaluate('generationScheduler').toString() == 'beta'
    assert engine.evaluate('generationSampler').toString() == 'er_sde'
    # Local v19 Q4 deliberately starts on tested Fast. Selecting Balanced or
    # Quality must restore its six-step identity/consistency baseline.
    assert engine.evaluate('generationSteps').toInt() == 4
    assert not engine.evaluate('applyQualityPreset("Balanced",512,512)').isError()
    assert engine.evaluate('generationSteps').toInt() == 6
    assert not engine.evaluate('applyQualityPreset("Quality",1024,1024)').isError()
    assert engine.evaluate('generationSteps').toInt() == 6


def test_phr00t_speed_presets_keep_quality_and_fast_sampling():
    v23 = c.model_profile_settings(c.REMOTE_PHR00T_V23_Q2_MODEL, remote=False)
    assert v23['preferredPreset'] == 'Balanced'
    assert v23['sourceQualityPresets']['Fast'] == {'width': 1024, 'height': 640, 'cfg': 1.0, 'steps': 4}
    assert v23['sourceQualityPresets']['Balanced'] == {'width': 1344, 'height': 832, 'cfg': 1.0, 'steps': 4}
    assert v23['sourceQualityPresets']['Quality'] == {'width': 2264, 'height': 1360, 'cfg': 1.2, 'steps': 4}
    assert 'preferredPreset' not in c.model_profile_settings(c.REMOTE_PHR00T_V23_Q2_MODEL, remote=True)
    v19 = c.model_profile_settings(c.QWEN_MODEL, remote=False)
    assert v19['sourceQualityPresets']['Fast']['steps'] == 4
    assert 'tiled VAE decoding' in v19['qualityNote']
    assert v19['sourceQualityPresets']['Balanced']['width'] == 640
    assert v19['sourceQualityPresets']['Quality']['height'] == 1216


def test_qml_phr00t_speed_presets_apply_and_restore_full_quality():
    qml = (c.PROJECT_ROOT / 'genesis/qt_ui/MainPremiumLinux.qml').read_text()
    engine = QJSEngine()
    for name in ('applyGenerationDefaults', 'applyQualityPreset', 'qualityPresetActive'):
        function = re.search(r'    function ' + name + r'\(.*?\n    }', qml, re.S).group()
        assert not engine.evaluate(function).isError()
    p = c.model_profile_settings(c.REMOTE_PHR00T_V23_Q2_MODEL, remote=False)
    engine.evaluate('var selectedGenerationProfile=' + json.dumps(p) + '; var activeSourceImage=true; var generationSource="file:///source.png"; var generationWidth, generationHeight, generationSteps, generationCfg, generationDenoise, generationSampler, generationScheduler, generationReferenceMegapixels, generationOutputTarget, useUpscale; var selectedPresetPayload=null, sdxlFaceIDEnabled=false;')
    assert not engine.evaluate('applyGenerationDefaults(selectedGenerationProfile)').isError()
    assert (engine.evaluate('generationWidth').toInt(), engine.evaluate('generationHeight').toInt()) == (1344, 832)
    assert engine.evaluate('generationCfg').toNumber() == 1.0
    assert not engine.evaluate('applyQualityPreset("Fast",512,512)').isError()
    assert (engine.evaluate('generationWidth').toInt(), engine.evaluate('generationHeight').toInt()) == (1024, 640)
    assert engine.evaluate('generationSteps').toInt() == 4
    assert engine.evaluate('qualityPresetActive("Fast",512,512)').toBool()
    engine.evaluate('generationCfg = 1.2')
    assert not engine.evaluate('qualityPresetActive("Fast",512,512)').toBool()
    assert not engine.evaluate('applyQualityPreset("Quality",1024,1024)').isError()
    assert (engine.evaluate('generationWidth').toInt(), engine.evaluate('generationHeight').toInt()) == (2264, 1360)
    assert engine.evaluate('generationCfg').toNumber() == 1.2
    assert engine.evaluate('qualityPresetActive("Quality",1024,1024)').toBool()
    v19 = c.model_profile_settings(c.QWEN_MODEL, remote=False)
    assert v19['preferredPreset'] == 'Fast'
    assert 'preferredPreset' not in c.model_profile_settings(c.QWEN_MODEL, remote=True)
    assert v19['sourceQualityPresets']['Fast'] == {'width':512,'height':704,'cfg':1.0,'steps':4}
    engine.evaluate('selectedGenerationProfile = ' + json.dumps(v19))
    engine.evaluate('applyGenerationDefaults(selectedGenerationProfile)')
    assert (engine.evaluate('generationWidth').toInt(),engine.evaluate('generationHeight').toInt()) == (512,704)
    assert engine.evaluate('generationSteps').toInt() == 4
    assert engine.evaluate('qualityPresetActive("Fast",512,512)').toBool()
    assert not engine.evaluate('applyQualityPreset("Balanced",512,512)').isError()
    assert engine.evaluate('generationSteps').toInt() == 6
    assert not engine.evaluate('applyQualityPreset("Quality",1024,1024)').isError()
    assert engine.evaluate('generationSteps').toInt() == 6
    assert (engine.evaluate('generationWidth').toInt(),engine.evaluate('generationHeight').toInt()) == (832,1216)


def test_4b_source_applies_visible_controls_and_seed(monkeypatch, tmp_path):
    prompt = {str(i): {'inputs': {}} for i in (1, 2, 4, 5, 6, 7, 8, 9, 11)}
    prompt['9']['inputs'] = {'seed': 42, 'steps': 8, 'cfg': 1, 'denoise': 1, 'sampler_name': 'res_multistep', 'scheduler': 'simple'}
    monkeypatch.setattr(c.workflow_lab, 'workflow_to_prompt', lambda *args: prompt)
    monkeypatch.setattr(c.workflow_lab, 'validate_prompt', lambda *args: {'valid': True})
    bridge = c.GenerationBridge()
    monkeypatch.setattr(bridge, '_submit_and_save', Mock(return_value=tmp_path / 'result.png'))
    client = Mock(); client.upload_image.return_value = {'name': 'source.png'}
    controls = dict(steps=17, cfg=1.3, denoise=0.65, sampler='euler', scheduler='beta', seed=123)
    bridge._run_4b_source(client, {}, tmp_path / 'source.png', 'a vase', [], [], 512, 512, 'stamp', controls=controls)
    for key, value in controls.items():
        assert prompt['9']['inputs']['sampler_name' if key == 'sampler' else key] == value


def test_connections_are_never_replaced_by_scalar_controls():
    prompt = {'1': {'inputs': {'steps': ['2', 0], 'scheduler': ['2', 1]}}}
    c.apply_create_controls(prompt, {'steps': 12, 'scheduler': 'simple'})
    assert prompt['1']['inputs']['steps'] == ['2', 0]
    assert prompt['1']['inputs']['scheduler'] == ['2', 1]


def test_unknown_families_and_cross_family_adapters_are_not_compatible():
    assert not is_compatible('unknown-model.safetensors', 'unknown-lora.safetensors')
    model = c.REMOTE_MIRACLEIN_9B_MODEL
    assert compatible_loras(model, ['refcontrol_v2_poses.safetensors', 'add-detail-xl.safetensors', 'F2K4BBabe_Engel_v1.0.safetensors']) == ['refcontrol_v2_poses.safetensors']
    assert is_compatible(c.REMOTE_DARKBEAST_9B_MODEL, 'refcontrol_v2_poses.safetensors')


def test_local_catalog_preserves_lora_subdirectory_names(monkeypatch, tmp_path):
    root = tmp_path / 'models'; folder = root / 'loras' / 'klein9b'; folder.mkdir(parents=True)
    (folder / 'refcontrol_v2_poses.safetensors').write_bytes(b'test')
    monkeypatch.setattr(c, 'remote_url', lambda: '')
    monkeypatch.setattr(c, 'MODEL_ROOTS', [root])
    monkeypatch.setattr(c, 'lora_trigger_words', lambda path: ['refcontrol'])
    monkeypatch.setattr(c, 'readiness_report', lambda: {'profiles': [{'ready': True, 'evidence': {'MODEL': '/models/' + c.REMOTE_MIRACLEIN_9B_MODEL}}]})
    row = c.load_generation_profiles()[0]
    assert row['loras'] == ['None', 'klein9b/refcontrol_v2_poses.safetensors']
    assert row['triggers']['klein9b/refcontrol_v2_poses.safetensors'] == ['refcontrol']


def test_scheduler_picker_contains_all_editable_model_defaults():
    qml = (c.PROJECT_ROOT / 'genesis/qt_ui/MainPremiumLinux.qml').read_text()
    options = json.loads(re.search(r'\["beta", "simple"[^\]]+\]', qml).group())
    for model in c.SUPPORTED_CREATE_MODELS:
        for source in (False, True):
            values = c.model_generation_settings(model, source=source)
            if not values['schedulerFixed']:
                assert values['defaultScheduler'] in options


def test_lora_training_tags_are_not_mislabeled_as_activation_triggers(tmp_path):
    import struct
    sample = tmp_path / 'sample.safetensors'
    header = {'__metadata__': {'ss_tag_frequency':'{"1_misc":{"all":23,"misc":40,"portrait":9}}'}}
    binary = json.dumps(header).encode()
    sample.write_bytes(struct.pack('<Q',len(binary)) + binary)
    assert c.lora_trigger_words(sample) == []
    header['__metadata__']['modelspec.trigger_phrase'] = 'verified_phrase'
    binary = json.dumps(header).encode()
    sample.write_bytes(struct.pack('<Q',len(binary)) + binary)
    assert c.lora_trigger_words(sample) == ['verified_phrase']


def test_phr00t_does_not_offer_unverified_qwen2_lora():
    adapter='NSFW Qwen by TheseAlpacas V2.safetensors'
    for model in (c.QWEN_MODEL,c.REMOTE_PHR00T_V23_Q2_MODEL,c.REMOTE_PHR00T_MODEL):
        assert not is_compatible(model,adapter)
        assert c.model_lora_limit(model)==0
