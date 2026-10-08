"""Offline routing regression tests; mocks never submit or inspect images."""
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from PyQt6.QtQml import QJSEngine
import qt_cockpit as c
from genesis.backend_routing import Route, use_route
from genesis.generation_pipeline import (
    adapt_prompt, refcontrol_prompt, REFCONTROL_LORA, REFCONTROL_TRIGGER,
)
from genesis.model_compatibility import is_compatible


@pytest.fixture
def catalog():
    info = json.loads((Path(__file__).parent / 'fixtures/runpod_stage_models_schema.json').read_text())
    info['LoraLoaderModelOnly'] = {'input': {'required': {
        'model': ['MODEL'], 'lora_name': [[REFCONTROL_LORA]], 'strength_model': ['FLOAT']} }}
    return info


def capture(monkeypatch, tmp_path, catalog, model, pose=True, loras=None, strengths=None):
    bridge = c.GenerationBridge()
    client = Mock()
    client.upload_image.side_effect = lambda path: {'name': path.name}
    captured = {}
    monkeypatch.setattr(bridge, '_submit_and_save', lambda _, graph, *args: captured.update(graph) or tmp_path / 'result.png')
    with use_route(Route('RUNPOD', 'https://offline-test-8189.proxy.runpod.net')):
        bridge._run_reference_stage(client, catalog, c.remote_reference_workflow(model),
            tmp_path / 'original.png', adapt_prompt('stand beside a chair', model, source_image=True, pose_image=pose),
            'test', 'Stage1', secondary_image=tmp_path / 'control.png' if pose else None,
            model_override=model, loras=loras, lora_strengths=strengths)
    return captured, client


def test_refcontrol_pose_first_original_identity_second(monkeypatch, tmp_path, catalog):
    graph, client = capture(monkeypatch, tmp_path, catalog, c.REMOTE_KLEIN_9B_MODEL, loras=[REFCONTROL_LORA])
    assert graph['__genesis_pose__']['inputs']['image'] == 'control.png'
    assert graph['10']['inputs']['image'] == 'original.png'
    assert graph['__genesis_pose_positive__']['inputs']['conditioning'] == ['4', 0]
    assert graph['17']['inputs']['conditioning'] == ['__genesis_pose_positive__', 0]
    assert graph['17']['inputs']['latent'] == ['15', 0]
    assert graph['15']['inputs']['pixels'] == ['12', 0]
    assert graph['12']['inputs']['image'] == ['10', 0]
    assert graph['4']['inputs']['text'].count(REFCONTROL_TRIGGER) == 1
    assert graph['genesis_lora_1']['inputs']['strength_model'] == 0.9
    assert {call.args[0] for call in client.upload_image.call_args_list} == {tmp_path / 'control.png', tmp_path / 'original.png'}


def test_refcontrol_strength_remains_configurable(monkeypatch, tmp_path, catalog):
    graph, _ = capture(monkeypatch, tmp_path, catalog, c.REMOTE_KLEIN_9B_MODEL,
                       loras=[REFCONTROL_LORA], strengths=[0.85])
    assert graph['genesis_lora_1']['inputs']['strength_model'] == 0.85


def test_refcontrol_requires_both_references_and_injection_is_idempotent():
    for source, pose in [(True, False), (False, True)]:
        with pytest.raises(ValueError, match='separate pose/control'):
            refcontrol_prompt('a chair', c.REMOTE_KLEIN_9B_MODEL, [REFCONTROL_LORA], has_pose=pose, has_source=source)
    assert refcontrol_prompt(REFCONTROL_TRIGGER, c.REMOTE_KLEIN_9B_MODEL, [REFCONTROL_LORA], has_pose=True, has_source=True) == REFCONTROL_TRIGGER


@pytest.mark.parametrize('model', [c.FOUR_B_MODEL, c.KV_9B_MODEL, c.REMOTE_DONUTS_MODEL, c.REMOTE_PHR00T_V19_GGUF_MODEL])
def test_refcontrol_is_not_injected_for_other_families(model):
    assert not is_compatible(model, REFCONTROL_LORA)
    assert refcontrol_prompt('a chair', model, [REFCONTROL_LORA], has_pose=True, has_source=True) == 'a chair'


@pytest.mark.parametrize('model', [c.REMOTE_PHR00T_V19_MODEL, c.REMOTE_PHR00T_V19_GGUF_MODEL,
                                   c.QWEN_MODEL, c.REMOTE_PHR00T_MODEL,
                                   c.REMOTE_PHR00T_V23_GGUF_MODEL, c.REMOTE_PHR00T_V23_Q2_MODEL])
def test_phr00t_edit_template_and_separate_pose(monkeypatch, tmp_path, catalog, model):
    # Add the selected synthetic asset to the offline catalog.
    for kind, field in [('CheckpointLoaderSimple', 'ckpt_name'), ('UNETLoader', 'unet_name'), ('UnetLoaderGGUF', 'unet_name')]:
        catalog[kind]['input']['required'][field][0].append(model)
    graph, client = capture(monkeypatch, tmp_path, catalog, model)
    encode = next(n['inputs'] for n in graph.values() if n['class_type'] == 'TextEncodeQwenImageEditPlus')
    assert graph[encode['image1'][0]]['inputs']['image'] == 'original.png'
    assert graph[encode['image2'][0]]['inputs']['image'] == 'control.png'
    assert 'Preserve the same person and facial identity' in encode['prompt']
    assert 'Allow the body pose' in encode['prompt']
    assert 'Use image2 only for pose' in encode['prompt']
    assert REFCONTROL_TRIGGER not in encode['prompt']
    assert client.upload_image.call_count == 2


def test_unselected_adapter_does_not_inject_trigger(monkeypatch, tmp_path, catalog):
    graph, _ = capture(monkeypatch, tmp_path, catalog, c.REMOTE_KLEIN_9B_MODEL)
    assert REFCONTROL_TRIGGER not in graph['4']['inputs']['text']


def test_gguf_9b_reference_route_uses_selected_loader(monkeypatch, tmp_path, catalog):
    catalog['UnetLoaderGGUF']['input']['required']['unet_name'][0].append(c.REGULAR_9B_MODEL)
    graph, _ = capture(monkeypatch, tmp_path, catalog, c.REGULAR_9B_MODEL, loras=[REFCONTROL_LORA])
    assert graph['1'] == {'class_type': 'UnetLoaderGGUF', 'inputs': {'unet_name': c.REGULAR_9B_MODEL}}
    assert REFCONTROL_TRIGGER in graph['4']['inputs']['text']


def test_later_identity_lock_receives_untouched_original(monkeypatch, tmp_path):
    bridge = c.GenerationBridge(); bridge._output_dir = tmp_path
    monkeypatch.setattr(bridge, '_connect_comfyui', lambda: (Mock(), {}))
    monkeypatch.setattr(c, 'load_remote_catalog', lambda _: {})
    monkeypatch.setattr(c, 'validate_remote_workflow_assets', Mock())
    run = Mock(side_effect=[tmp_path / 'stage1.png', tmp_path / 'stage2.png', tmp_path / 'stage3.png'])
    monkeypatch.setattr(bridge, '_run_reference_stage', run)
    source, pose = tmp_path / 'original.png', tmp_path / 'control.png'
    with use_route(Route('RUNPOD', 'https://offline-test-8189.proxy.runpod.net')):
        bridge._run_generate('stand beside a chair', '', 512, 512, c.REMOTE_PHR00T_MODEL,
            'None', 'None', 'None', 0, 0, 0, source, pose, True, True, False,
            {'stage2_model': c.REMOTE_MIRACLEIN_V2_MODEL})
    assert run.call_count == 3
    assert run.call_args_list[0].args[3] == source
    assert run.call_args_list[0].kwargs['secondary_image'] == pose
    assert run.call_args_list[1].args[3] == tmp_path / 'stage1.png'
    assert run.call_args_list[2].args[3] == tmp_path / 'stage2.png'
    assert run.call_args_list[2].kwargs['secondary_image'] == source


def test_4b_passes_pose_into_native_reference_chain(monkeypatch, tmp_path):
    graph = {str(i): {'inputs': {}} for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 11)}
    monkeypatch.setattr(c.workflow_lab, 'workflow_to_prompt', lambda *args: graph)
    monkeypatch.setattr(c.workflow_lab, 'validate_prompt', lambda *args: {'valid': True})
    bridge = c.GenerationBridge()
    monkeypatch.setattr(bridge, '_submit_and_save', Mock(return_value=tmp_path / 'out.png'))
    client = Mock(); client.upload_image.side_effect = lambda path: {'name': path.name}
    bridge._run_4b_source(client, {}, tmp_path / 'original.png', 'stand beside a chair', [], [], 512, 512, 'test', pose=tmp_path / 'control.png')
    assert graph['11']['inputs']['image'] == 'original.png'
    assert graph['genesis_4b_pose']['inputs']['image'] == 'control.png'
    assert graph['9']['inputs']['positive'] == ['genesis_4b_identity_positive', 0]
    assert graph['genesis_4b_identity_positive']['inputs']['conditioning'] == ['genesis_4b_pose_positive', 0]
    assert REFCONTROL_TRIGGER not in graph['5']['inputs']['text']


def test_qml_refcontrol_default_strength_is_configurable():
    import re
    qml = (c.PROJECT_ROOT / 'genesis/qt_ui/MainPremiumLinux.qml').read_text()
    engine = QJSEngine()
    function = re.search(r'    function defaultLoraStrength\(.*?\n    }', qml, re.S).group()
    assert not engine.evaluate(function).isError()
    assert engine.evaluate('defaultLoraStrength("folder/refcontrol_v2_poses.safetensors")').toNumber() == 0.9
    assert engine.evaluate('defaultLoraStrength("None")').toNumber() == 0.65


def test_section_selectors_hide_unusable_files_without_losing_runpod_models():
    import re
    qml = (c.PROJECT_ROOT / 'genesis/qt_ui/MainPremiumLinux.qml').read_text()
    engine = QJSEngine()
    rows = [
        dict(model='unavailable', runnable=False, selectable=False, stageOneConfigured=True, stageTwoConfigured=True),
        dict(model='phr00t', runnable=True, selectable=True, stageOneEligible=True, stageTwoEligible=False, remote=True),
        dict(model='klein', runnable=True, selectable=True, stageOneEligible=True, stageTwoEligible=True, remote=True),
        dict(model='unsupported', runnable=False, selectable=True, remote=True),
    ]
    engine.evaluate('var generationSource = ""; var generationProfiles = ' + json.dumps(rows))
    expression = re.search(r'property var generationModel: (.*?)(?=\n    (?:readonly |property |on))', qml, re.S).group(1).strip()
    result = engine.evaluate('var generationModel = ' + expression)
    assert not result.isError(), result.toString()
    assert engine.evaluate('generationModel.map(function(r) { return r.model }).join(",")').toString() == 'phr00t,klein'
    for name, expected in [('stageOneChoices', 'phr00t,klein'), ('stageTwoChoices', 'klein')]:
        expression = re.search(r'property var ' + name + r': (.*)', qml).group(1)
        result = engine.evaluate('var choices = ' + expression)
        assert not result.isError(), result.toString()
        assert engine.evaluate('choices.map(function(r) { return r.model }).join(",")').toString() == expected


@pytest.mark.parametrize('model', [c.REMOTE_DONUTS_MODEL, c.REMOTE_BIGLUSTY_DONUT_MODEL])
def test_sdxl_source_and_pose_reach_distinct_sampler_inputs(monkeypatch, tmp_path, catalog, model):
    client = Mock(); client.upload_image.side_effect = lambda path: {'name': path.name}
    bridge = c.GenerationBridge(); bridge._output_dir = tmp_path
    monkeypatch.setattr(bridge, '_connect_comfyui', lambda: (client, {}))
    catalog['ControlNetLoader'] = {'input': {'required': {'control_net_name': [[c.REMOTE_SDXL_POSE_CONTROLNET]]}}}
    monkeypatch.setattr(c, 'load_remote_catalog', lambda _: catalog)
    # Node construction is exercised; no network or image generation is permitted.
    monkeypatch.setattr(c, 'validate_operation_prompt', Mock())
    graph = {str(i): {'inputs': {}} for i in range(1, 8)}
    monkeypatch.setattr(c, 'build_create_prompt', lambda *args: graph)
    submitted = Mock(return_value=tmp_path / 'out.png')
    monkeypatch.setattr(bridge, '_submit_and_save', submitted)
    with use_route(Route('RUNPOD', 'https://offline-test-8189.proxy.runpod.net')):
        bridge._run_generate('stand beside a chair', '', 768, 1024, model,
            'None', 'None', 'None', 0, 0, 0, tmp_path / 'original.png', tmp_path / 'control.png',
            False, False, False, {'denoise': 0.65})
    assert submitted.call_count == 1, bridge.status
    assert graph['genesis_source']['inputs']['image'] == 'original.png'
    assert graph['genesis_pose_image']['inputs']['image'] == 'control.png'
    assert graph['genesis_pose_controlnet']['inputs']['control_net_name'] == 'OpenPoseXL2.safetensors'
    assert graph['5']['inputs']['latent_image'] == ['genesis_source_encode', 0]
    assert graph['5']['inputs']['positive'] == ['genesis_pose_apply', 0]
    assert all(REFCONTROL_TRIGGER not in str(n['inputs']) for n in graph.values())


def test_family_specific_identity_guidance_and_sdxl_source_default():
    assert c.model_generation_settings(c.REMOTE_DONUTS_MODEL, source=True)['defaultDenoise'] == 0.65
    assert c.model_generation_settings(c.REMOTE_DONUTS_MODEL)['defaultDenoise'] == 1.0
    assert 'Lower denoise' in c.model_profile_settings(c.REMOTE_PHR00T_MODEL)['identityGuidance']
    assert 'original source' in c.model_profile_settings(c.REMOTE_DONUTS_MODEL)['identityGuidance']


@pytest.mark.parametrize('model', sorted(c.SUPPORTED_CREATE_MODELS))
@pytest.mark.parametrize('source', [False, True])
def test_quality_buttons_restore_each_models_settings_and_preserve_seed(model, source):
    import re
    qml = (c.PROJECT_ROOT / 'genesis/qt_ui/MainPremiumLinux.qml').read_text()
    engine = QJSEngine()
    for name in ('applyGenerationDefaults', 'applyQualityPreset'):
        function = re.search(r'    function ' + name + r'\(.*?\n    }', qml, re.S).group()
        assert not engine.evaluate(function).isError()
    profile = c.model_profile_settings(model, remote=True)
    engine.evaluate('var selectedGenerationProfile = ' + json.dumps(profile))
    engine.evaluate('var generationSource = ' + json.dumps('original.png' if source else ''))
    engine.evaluate('var generationSeed = 123; var generationWidth, generationHeight, generationSteps, generationCfg, generationDenoise, generationSampler, generationScheduler;')
    defaults = profile['sourceDefaults' if source else 'createDefaults']
    for quality in ('Fast', 'Balanced', 'Quality'):
        engine.evaluate('generationSteps = 99; generationCfg = 99; generationSampler = "wrong"; generationScheduler = "wrong"; generationDenoise = 0;')
        engine.evaluate('applyQualityPreset(' + json.dumps(quality) + ', 1, 1)')
        for setting in ('Steps', 'Cfg', 'Denoise', 'Sampler', 'Scheduler'):
            assert engine.evaluate('generation' + setting).toVariant() == defaults['default' + setting], (model, source, setting)
        assert engine.evaluate('generationWidth').toInt() == profile['qualityPresets'][quality]['width']
        assert engine.evaluate('generationHeight').toInt() == profile['qualityPresets'][quality]['height']
        assert engine.evaluate('generationSeed').toInt() == 123
        assert engine.evaluate('generationSource').toString() == ('original.png' if source else '')


def test_sampler_picker_contains_all_supported_model_defaults():
    import re
    qml = (c.PROJECT_ROOT / 'genesis/qt_ui/MainPremiumLinux.qml').read_text()
    options = json.loads(re.search(r'model: (\["er_sde"[^\]]+\])', qml).group(1))
    for model in c.SUPPORTED_CREATE_MODELS:
        for source in (False, True):
            assert c.model_generation_settings(model, source=source)['defaultSampler'] in options


def test_seed_controls_are_shared_and_do_not_override_connected_fields():
    graph = {'1': {'class_type': 'KSampler', 'inputs': {'seed': 9}},
             '2': {'class_type': 'RandomNoise', 'inputs': {'noise_seed': 9}},
             '3': {'class_type': 'Custom', 'inputs': {'seed': ['2', 0]}}}
    c.apply_create_controls(graph, {'seed': 123})
    assert graph['1']['inputs']['seed'] == graph['2']['inputs']['noise_seed'] == 123
    assert graph['3']['inputs']['seed'] == ['2', 0]


def test_source_picker_hides_models_without_source_edit_workflows():
    import re
    qml = (c.PROJECT_ROOT / 'genesis/qt_ui/MainPremiumLinux.qml').read_text()
    engine = QJSEngine()
    rows = c.build_remote_generation_profiles({
        'UNETLoader': {'input': {'required': {'unet_name': [[c.REMOTE_KLEIN_9B_MODEL, c.KV_9B_MODEL]]}}}})
    assert next(row for row in rows if row['model'] == c.KV_9B_MODEL)['sourceSupported'] is False
    expression = re.search(r'property var generationModel: (.*?)(?=\n    (?:readonly |property |on))', qml, re.S).group(1).strip()
    engine.evaluate('var generationProfiles = ' + json.dumps(rows))
    for source, expected_count in [('', 2), ('original.png', 1)]:
        engine.evaluate('var generationSource = ' + json.dumps(source))
        result = engine.evaluate('var generationModel = ' + expression)
        assert not result.isError(), result.toString()
        assert engine.evaluate('generationModel.length').toInt() == expected_count
        if source:
            assert engine.evaluate('generationModel[0].model').toString() == c.REMOTE_KLEIN_9B_MODEL


def test_phr00t_extra_character_angle_keeps_pose_in_image2(monkeypatch,tmp_path,catalog):
    primary=tmp_path/'primary.png';primary.write_bytes(b'original primary')
    angle=tmp_path/'angle.png';angle.write_bytes(b'original angle')
    pose=tmp_path/'pose.png';pose.write_bytes(b'control only')
    bridge=c.GenerationBridge();bridge._character_a='character-a'
    monkeypatch.setattr(c,'get_character',lambda _:dict(primary_image=str(primary),references=[str(primary),str(angle)]))
    client=Mock();client.upload_image.side_effect=lambda p:{'name':p.name}
    graph={};monkeypatch.setattr(bridge,'_submit_and_save',lambda _,g,*args:graph.update(g) or tmp_path/'result.png')
    with use_route(Route('RUNPOD','https://offline-8189.proxy.runpod.net')):
        bridge._run_reference_stage(client,catalog,c.STAGE_1_WORKFLOW,primary,'Neutral pose instruction','stamp','Phr00t-v19-GGUF',secondary_image=pose,model_override=c.REMOTE_PHR00T_V19_GGUF_MODEL)
    assert graph['2']['inputs']['image']=='primary.png'
    assert graph['3']['inputs']['image']=='pose.png'
    assert graph['4']['inputs']['image2']==['3',0]
    assert graph['4']['inputs']['image3']==['__character_a_image3',0]
    assert graph['__character_a_image3']['inputs']['image']=='angle.png'
    assert primary.read_bytes()==b'original primary' and angle.read_bytes()==b'original angle'

