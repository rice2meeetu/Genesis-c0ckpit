"""Stage 1 source conditioning must not implicitly execute Stage 3 face swap."""
import copy
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

import qt_cockpit as c
from genesis.backend_routing import Route, use_route


@pytest.fixture
def saved_prompt():
    # Neutral API equivalent of the installed decode -> ReActor -> Save template.
    return {
        '1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': c.FOUR_B_MODEL, 'weight_dtype': 'default'}},
        '2': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': c.TEXT_ENCODER_4B, 'type': 'flux2'}},
        '3': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'flux2-vae.safetensors'}},
        '4': {'class_type': 'LoraLoader', 'inputs': {'model': ['1', 0], 'clip': ['2', 0]}},
        '5': {'class_type': 'CLIPTextEncode', 'inputs': {'clip': ['4', 1], 'text': 'A ceramic vase'}},
        '6': {'class_type': 'CLIPTextEncode', 'inputs': {'clip': ['4', 1], 'text': ''}},
        '7': {'class_type': 'EmptySD3LatentImage', 'inputs': {'width': 768, 'height': 768, 'batch_size': 1}},
        '8': {'class_type': 'ModelSamplingAuraFlow', 'inputs': {'model': ['4', 0], 'shift': 3}},
        '9': {'class_type': 'KSampler', 'inputs': {
            'model': ['8', 0], 'positive': ['5', 0], 'negative': ['6', 0],
            'latent_image': ['7', 0], 'seed': 42, 'steps': 8, 'cfg': 1.0,
            'sampler_name': 'res_multistep', 'scheduler': 'simple', 'denoise': 1.0}},
        '10': {'class_type': 'VAEDecode', 'inputs': {'samples': ['9', 0], 'vae': ['3', 0]}},
        '11': {'class_type': 'LoadImage', 'inputs': {'image': 'source.png'}},
        '12': {'class_type': 'ReActorFaceSwap', 'inputs': {
            'input_image': ['10', 0], 'source_image': ['11', 0], 'enabled': True}},
        '13': {'class_type': 'SaveImage', 'inputs': {'images': ['12', 0], 'filename_prefix': 'ComfyUI'}},
    }


@pytest.fixture
def catalog():
    info = json.loads((Path(__file__).parent / 'fixtures/runpod_stage_models_schema.json').read_text())
    info['EmptySD3LatentImage'] = {'input': {'required': {'width': ['INT'], 'height': ['INT'], 'batch_size': ['INT']}}}
    info['ModelSamplingAuraFlow'] = {'input': {'required': {'model': ['MODEL'], 'shift': ['FLOAT']}}}
    # The converted native graph must validate without any executable ReActor node.
    return info


def setup_bridge(monkeypatch, tmp_path, saved_prompt):
    monkeypatch.setattr(c.workflow_lab, 'workflow_to_prompt', lambda *args: copy.deepcopy(saved_prompt))
    bridge = c.GenerationBridge()
    bridge._output_dir = tmp_path
    result = tmp_path / 'generated.png'
    result.write_bytes(b'offline output')
    submit = Mock(return_value=result)
    monkeypatch.setattr(bridge, '_submit_and_save', submit)
    client = Mock()
    client.upload_image.side_effect = lambda path: {'name': path.name}
    return bridge, client, submit


def assert_native_output(graph, pose):
    assert graph['13']['inputs']['images'] == ['10', 0]
    assert graph['10']['inputs']['samples'] == ['9', 0]
    assert not any(node['class_type'].startswith('ReActor') for node in graph.values())
    assert not any(isinstance(v, list) and v and v[0] == '12'
                   for node in graph.values() for v in node['inputs'].values())
    assert graph['genesis_4b_identity_encode']['inputs']['pixels'] == ['11', 0]
    assert graph['9']['inputs']['positive'] == ['genesis_4b_identity_positive', 0]
    if pose:
        assert graph['genesis_4b_pose']['inputs']['image'] == 'pose.png'
        assert graph['genesis_4b_identity_positive']['inputs']['conditioning'] == ['genesis_4b_pose_positive', 0]
    else:
        assert graph['genesis_4b_identity_positive']['inputs']['conditioning'] == ['5', 0]


@pytest.mark.parametrize('destination', ['LOCAL', 'RUNPOD'])
@pytest.mark.parametrize('pose', [False, True])
def test_4b_source_saves_native_output_without_mutating_template(monkeypatch, tmp_path, saved_prompt, catalog, destination, pose):
    original = copy.deepcopy(saved_prompt)
    bridge, client, submit = setup_bridge(monkeypatch, tmp_path, saved_prompt)
    route = Route(destination, 'https://offline.example' if destination == 'RUNPOD' else '')
    with use_route(route):
        bridge._run_4b_source(client, catalog, tmp_path / 'source.png', 'A ceramic vase', [], [],
                             640, 640, 'stamp', controls={'steps': 8, 'cfg': 1.0, 'seed': 123},
                             pose=tmp_path / 'pose.png' if pose else None)
    graph = submit.call_args.args[1]
    assert_native_output(graph, pose)
    assert graph['9']['inputs']['steps'] == 8
    assert graph['9']['inputs']['seed'] == 123
    assert client.upload_image.call_count == (2 if pose else 1)
    assert saved_prompt == original
    client.submit.assert_not_called()


@pytest.mark.parametrize('broken', ['swap_class', 'swap_input', 'missing_decode', 'decode_class',
                                    'save_class', 'save_input', 'extra_swap_consumer'])
def test_changed_output_topology_fails_before_upload(monkeypatch, tmp_path, saved_prompt, catalog, broken):
    if broken == 'swap_class':
        saved_prompt['12']['class_type'] = 'PreviewImage'
    elif broken == 'swap_input':
        saved_prompt['12']['inputs']['input_image'] = ['11', 0]
    elif broken == 'missing_decode':
        saved_prompt.pop('10')
    elif broken == 'decode_class':
        saved_prompt['10']['class_type'] = 'PreviewImage'
    elif broken == 'save_class':
        saved_prompt['13']['class_type'] = 'PreviewImage'
    elif broken == 'save_input':
        saved_prompt['13']['inputs']['images'] = ['11', 0]
    else:
        saved_prompt['extra'] = {'class_type': 'PreviewImage', 'inputs': {'images': ['12', 0]}}
    bridge, client, submit = setup_bridge(monkeypatch, tmp_path, saved_prompt)
    with pytest.raises(c.workflow_lab.ComfyError, match='output topology changed'):
        bridge._run_4b_source(client, catalog, tmp_path / 'source.png', 'A ceramic vase', [], [], 640, 640, 'stamp')
    client.upload_image.assert_not_called()
    submit.assert_not_called()


@pytest.mark.parametrize(('stage_three', 'stage_engine'), [
    (False, 'reactor_inswapper'),
    (True, 'reactor_inswapper'),
    (True, 'facefusion_nsfw'),
])
def test_stage_three_remains_a_separate_manual_review(monkeypatch, tmp_path, saved_prompt, catalog, stage_three, stage_engine):
    # Neither the host's saved engine nor installed model set may drive this offline test.
    monkeypatch.setattr(c, 'installed_reactor_engines', lambda: ['reactor_inswapper'])
    ff_root = tmp_path / 'facefusion-test'
    (ff_root / '.venv/bin').mkdir(parents=True)
    for file in (ff_root / '.venv/bin/python', ff_root / 'facefusion.py', ff_root / 'facefusion.ini'):
        file.touch()
    monkeypatch.setattr(c.integrations, 'FACEFUSION_ROOT', ff_root)
    bridge, client, submit = setup_bridge(monkeypatch, tmp_path, saved_prompt)
    bridge._stage_three_engine = stage_engine
    source = tmp_path / 'source.png'
    source.write_bytes(b'offline source')
    catalog.update({'ReActorFaceSwapOpt': {}, 'ReActorOptions': {}})
    client.object_info.return_value = catalog
    monkeypatch.setattr(bridge, '_connect_comfyui', lambda: (client, {}))
    monkeypatch.setattr(c.integrations, 'ensure_ai_model_volume_readonly', lambda *args: (True, 'ready'))
    signals = []
    bridge.stageThreeSelectionRequired.disconnect(bridge._choose_stage_three_faces)
    bridge.stageThreeSelectionRequired.connect(lambda *args: signals.append(args))
    with use_route(Route('LOCAL', '')):
        result = bridge._run_generate('A ceramic vase', '', 640, 640, c.FOUR_B_MODEL,
                                     'None', 'None', 'None', 0, 0, 0, source, None,
                                     False, stage_three, False, {'steps': 8, 'cfg': 1.0, 'seed': 123})
    assert result == tmp_path / 'generated.png', bridge.status
    assert submit.call_count == 1
    assert_native_output(submit.call_args.args[1], False)
    assert signals == ([(str(result), str(source))] if stage_three else [])
    assert bridge._pending_stage_three == stage_three
