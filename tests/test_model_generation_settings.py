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
    engine.evaluate('var generationSource = ""; var generationWidth, generationHeight, generationSteps, generationCfg, generationDenoise, generationSampler, generationScheduler;')
    profile = c.model_profile_settings(c.REMOTE_MIRACLEIN_9B_MODEL, remote=True)
    engine.evaluate('var selectedGenerationProfile = ' + json.dumps(profile))
    engine.evaluate('applyGenerationDefaults(selectedGenerationProfile)')
    assert engine.evaluate('generationScheduler').toString() == 'simple'
    engine.evaluate('generationSource = "file:///source.png"; applyGenerationDefaults(selectedGenerationProfile)')
    assert engine.evaluate('generationScheduler').toString() == 'Flux2Scheduler'
    for name, size in (('Fast', 768), ('Balanced', 1024), ('Quality', 1536)):
        engine.evaluate(f'applyQualityPreset("{name}", 512, 512)')
        assert engine.evaluate('generationWidth').toInt() == size
        assert engine.evaluate('generationSteps').toInt() == 12
        assert engine.evaluate('generationCfg').toNumber() == 1.1
        assert engine.evaluate(f'qualityPresetActive("{name}", 512, 512)').toBool()
    profile = c.model_profile_settings(c.QWEN_MODEL)
    engine.evaluate('selectedGenerationProfile = ' + json.dumps(profile))
    engine.evaluate('applyGenerationDefaults(selectedGenerationProfile)')
    assert engine.evaluate('generationScheduler').toString() == 'beta'
    assert engine.evaluate('generationSampler').toString() == 'er_sde'
    assert engine.evaluate('generationSteps').toInt() == 6


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


def test_base_9b_graph_defaults_match_undistilled_profile(monkeypatch):
    monkeypatch.setattr(c, "REGULAR_9B_WORKFLOWS", (c.REMOTE_MIRACLEIN_T2I_WORKFLOW,))
    info = json.loads((Path(__file__).parent / 'fixtures/runpod_stage_models_schema.json').read_text())
    info['UnetLoaderGGUF']['input']['required']['unet_name'][0].append(c.REGULAR_9B_MODEL)
    info['FluxGuidance'] = {'input': {'required': {'conditioning': ['CONDITIONING'], 'guidance': ['FLOAT']}}}
    prompt = c.build_create_prompt(info, 'A ceramic vase', 512, 512, c.REGULAR_9B_MODEL)
    assert prompt['134']['inputs']['steps'] == 50
    assert prompt['134']['inputs']['cfg'] == 4.0


def test_aisha_t2i_keeps_legacy_face_swap_workflow_separate():
    legacy = json.loads((c.REFERENCE_WORKFLOW_ROOT / 'GENESIS_AISHA_9B_TEST.json').read_text())
    assert any(node['type'] == 'ReActorFaceSwap' for node in legacy['nodes'])
    assert c.LOCAL_AISHA_9B_WORKFLOW.name == 'GENESIS_AISHA_9B_T2I.json'
    create = json.loads(c.LOCAL_AISHA_9B_WORKFLOW.read_text())
    assert any(node['class_type'] == 'Flux2Scheduler' for node in create.values())
    assert not any(node['class_type'] == 'ReActorFaceSwap' for node in create.values())
