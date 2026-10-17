"""Offline node-schema checks: no GPU loading, network requests or submission."""
import json
import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
import qt_cockpit as cockpit
import genesis.backend_bridge as backend
from genesis.backend_routing import Route, use_route


@pytest.fixture
def catalog():
    # Node schemas were cached on October 2; model choices are test inputs,
    # not evidence that these models are present on the current stopped pod.
    return json.loads((Path(__file__).parent / 'fixtures/runpod_stage_models_schema.json').read_text())


def capture_reference(monkeypatch, tmp_path, catalog, workflow, model, pose=None, controls=None):
    bridge = cockpit.GenerationBridge()
    client = Mock()
    client.upload_image.side_effect = lambda path: {'name': path.name, 'subfolder': ''}
    captured = {}
    monkeypatch.setattr(bridge, '_submit_and_save',
                        lambda client, prompt, stamp, stage: captured.update(prompt) or tmp_path / 'out.png')
    with use_route(Route('RUNPOD', 'https://test-8189.proxy.runpod.net')):
        bridge._run_reference_stage(client, catalog, workflow, tmp_path / 'source.png',
                                    'A ceramic vase beside a window', 'stamp', 'Stage1',
                                    secondary_image=pose, controls=controls, model_override=model)
    return captured, client


def test_pornmaster_v4_uses_gguf_and_saved_edit_settings(monkeypatch, tmp_path, catalog):
    prompt, _ = capture_reference(monkeypatch, tmp_path, catalog,
        cockpit.remote_reference_workflow(cockpit.LOCAL_PORNMASTER_9B_MODEL),
        cockpit.LOCAL_PORNMASTER_9B_MODEL)
    assert prompt['1']['class_type'] == 'UnetLoaderGGUF'
    assert prompt['1']['inputs'] == {'unet_name': cockpit.LOCAL_PORNMASTER_9B_MODEL}
    assert prompt['6']['inputs']['cfg'] == 2.0
    assert prompt['7']['inputs']['steps'] == 4
    assert prompt['2']['inputs']['clip_name'] == 'qwen_3_8b_fp8mixed.safetensors'
    assert prompt['3']['inputs']['vae_name'] == 'flux2-vae.safetensors'


def test_pornmaster_pose_order_and_dimensions_reach_the_sampler(monkeypatch, tmp_path, catalog):
    controls = {**cockpit.remote_reference_controls(cockpit.LOCAL_PORNMASTER_9B_MODEL),
                'width': 768, 'height': 1024, 'seed': 123}
    prompt, client = capture_reference(monkeypatch, tmp_path, catalog,
        cockpit.REMOTE_PORNMASTER_V4_WORKFLOW, cockpit.LOCAL_PORNMASTER_9B_MODEL,
        pose=tmp_path / 'pose.png', controls=controls)
    assert client.upload_image.call_count == 2
    assert prompt['17']['inputs']['conditioning'] == ['__genesis_pose_positive__', 0]
    assert prompt['18']['inputs']['conditioning'] == ['__genesis_pose_negative__', 0]
    for node in ['7', '8']:
        assert prompt[node]['inputs']['width'] == 768
        assert prompt[node]['inputs']['height'] == 1024
    assert prompt['9']['inputs']['noise_seed'] == 123


@pytest.mark.parametrize('workflow,model', [
    (cockpit.STAGE_1_WORKFLOW, cockpit.REMOTE_PHR00T_V19_GGUF_MODEL),
    (cockpit.REMOTE_PHR00T_V19_WORKFLOW, cockpit.REMOTE_PHR00T_V19_MODEL),
])
def test_v19_without_pose_drops_placeholder_but_keeps_source(monkeypatch, tmp_path, catalog, workflow, model):
    prompt, client = capture_reference(monkeypatch, tmp_path, catalog, workflow, model)
    assert '3' not in prompt
    assert 'image2' not in prompt['4']['inputs']
    assert prompt['4']['inputs']['image1'] == ['2', 0]
    client.upload_image.assert_called_once_with(tmp_path / 'source.png')


def test_v19_with_pose_preserves_both_inputs(monkeypatch, tmp_path, catalog):
    prompt, _ = capture_reference(monkeypatch, tmp_path, catalog,
        cockpit.STAGE_1_WORKFLOW, cockpit.REMOTE_PHR00T_V19_GGUF_MODEL, pose=tmp_path / 'pose.png')
    assert prompt['4']['inputs']['image1'] == ['2', 0]
    assert prompt['4']['inputs']['image2'] == ['3', 0]
    assert prompt['3']['inputs']['image'] == 'pose.png'


def test_live_v23_maps_to_safetensors_graph_and_active_encoder(monkeypatch, tmp_path, catalog):
    prompt, _ = capture_reference(monkeypatch, tmp_path, catalog,
        cockpit.remote_reference_workflow(cockpit.REMOTE_PHR00T_MODEL),
        cockpit.REMOTE_PHR00T_MODEL,
        controls=cockpit.remote_reference_controls(cockpit.REMOTE_PHR00T_MODEL))
    assert prompt['1']['class_type'] == 'UNETLoader'
    assert prompt['1']['inputs']['unet_name'] == cockpit.REMOTE_PHR00T_MODEL
    assert prompt['2']['inputs']['type'] == 'qwen_image'
    assert prompt['2']['inputs']['clip_name'] == cockpit.REMOTE_PHR00T_CLIP
    assert prompt['8']['inputs']['cfg'] == 1.2
    assert prompt['8']['inputs']['steps'] == 4


def test_shared_v23_q8_uses_gguf_route_and_selected_asset(monkeypatch, tmp_path, catalog):
    model = cockpit.REMOTE_PHR00T_V23_GGUF_MODEL
    catalog['UnetLoaderGGUF']['input']['required']['unet_name'][0] = [model]
    prompt, _ = capture_reference(monkeypatch, tmp_path, catalog,
        cockpit.remote_reference_workflow(model), model,
        controls=cockpit.remote_reference_controls(model))
    assert prompt['1']['class_type'] == 'UnetLoaderGGUF'
    assert prompt['1']['inputs']['unet_name'] == model
    samplers = [n for n in prompt.values() if n['class_type'] == 'KSampler']
    assert samplers[0]['inputs']['steps'] == 4
    row = next(r for r in cockpit.build_remote_generation_profiles(catalog) if r['model'] == model)
    assert row['runnable'] and not row['sourceRequired']  # native no-reference T2I
    assert row['loras'] == ['None']


def test_v23_q2_uses_validated_local_phr00t_workflow():
    assert cockpit.remote_reference_workflow(cockpit.REMOTE_PHR00T_V23_Q2_MODEL) == cockpit.STAGE_1_WORKFLOW


def test_missing_pornmaster_asset_stops_before_upload(monkeypatch, tmp_path, catalog):
    catalog['UnetLoaderGGUF']['input']['required']['unet_name'][0] = [cockpit.REMOTE_PHR00T_MODEL]
    client = Mock()
    bridge = cockpit.GenerationBridge()
    monkeypatch.setattr(bridge, '_connect_comfyui', lambda: (client, {}))
    monkeypatch.setattr(cockpit, 'load_remote_catalog', lambda client: catalog)
    with use_route(Route('RUNPOD', 'https://test-8189.proxy.runpod.net')):
        bridge._run_generate('A ceramic vase', '', 768, 1024, cockpit.LOCAL_PORNMASTER_9B_MODEL,
                             'None', 'None', 'None', 0, 0, 0, tmp_path / 'source.png', None,
                             False, False, False)
    assert 'unavailable components' in bridge.status
    client.upload_image.assert_not_called()
    client.submit.assert_not_called()


@pytest.mark.parametrize('model,steps,cfg', [
    (cockpit.REMOTE_MIRACLEIN_9B_MODEL, 12, 1.1),
    (cockpit.LOCAL_PORNMASTER_9B_MODEL, 4, 2.0),
])
def test_refinement_uses_selected_model_settings_and_previous_output(monkeypatch, tmp_path, model, steps, cfg):
    bridge = cockpit.GenerationBridge()
    bridge._output_dir = tmp_path
    monkeypatch.setattr(bridge, '_connect_comfyui', lambda: (Mock(), {}))
    monkeypatch.setattr(cockpit, 'load_remote_catalog', lambda client: {})
    monkeypatch.setattr(cockpit, 'validate_remote_workflow_assets', Mock())
    run = Mock(side_effect=[tmp_path / 'stage1.png', tmp_path / 'stage2.png'])
    monkeypatch.setattr(bridge, '_run_reference_stage', run)
    with use_route(Route('RUNPOD', 'https://test-8189.proxy.runpod.net')):
        bridge._run_generate('A ceramic vase', '', 768, 1024, cockpit.REMOTE_PHR00T_MODEL,
                             'None', 'None', 'None', 0, 0, 0, tmp_path / 'source.png', None,
                             True, False, False, {'stage2_model': model, 'seed': 7})
    second = run.call_args_list[1]
    assert second.args[2] == cockpit.remote_reference_workflow(model)
    assert second.args[3] == tmp_path / 'stage1.png'
    assert second.kwargs['controls']['steps'] == steps
    assert second.kwargs['controls']['cfg'] == cfg


@pytest.mark.parametrize('mode,opt_in,expected', [
    ('RUNPOD', '1', True), ('RUNPOD', '0', False), ('RUNPOD', '', False), ('LOCAL', '1', False),
])
def test_startup_connects_only_with_explicit_option(monkeypatch, mode, opt_in, expected):
    monkeypatch.setenv('GENESIS_BACKEND_MODE', mode)
    monkeypatch.setenv('GENESIS_RUNPOD_URL', 'https://test-8189.proxy.runpod.net')
    monkeypatch.setenv('GENESIS_RUNPOD_AUTOCONNECT', opt_in)
    bridge = backend.BackendBridge(cockpit.GenerationBridge())
    connect, refresh = Mock(), Mock()
    monkeypatch.setattr(bridge, 'connectRemote', connect)
    monkeypatch.setattr(bridge, 'refresh', refresh)
    bridge.start()
    assert connect.called == expected
    assert refresh.called == (not expected)


def test_desktop_launcher_respects_endpoint_and_local_override(tmp_path):
    root = Path(__file__).resolve().parents[1]
    shutil.copy2(root / 'launch-qt-cockpit.sh', tmp_path)
    python = tmp_path / '.venv/bin/python'
    python.parent.mkdir(parents=True)
    output = tmp_path / 'environment.json'
    python.write_text('#!/usr/bin/env python3\nimport os,json\n'
                      'from pathlib import Path\n'
                      'Path(os.environ["GENESIS_TEST_ENV_OUTPUT"]).write_text(json.dumps({k:v for k,v in os.environ.items() if k.startswith("GENESIS_")}))\n')
    python.chmod(0o755)
    env = dict(os.environ, GENESIS_RUNPOD_URL='https://chosen-8189.proxy.runpod.net',
               GENESIS_TEST_ENV_OUTPUT=str(output))
    env.pop('GENESIS_BACKEND_MODE', None)
    env.pop('GENESIS_RUNPOD_AUTOCONNECT', None)
    subprocess.run(['bash', str(tmp_path / 'launch-qt-cockpit.sh')], env=env, check=True)
    result = json.loads(output.read_text())
    assert result['GENESIS_BACKEND_MODE'] == 'LOCAL'
    assert result['GENESIS_RUNPOD_URL'] == env['GENESIS_RUNPOD_URL']
    assert result['GENESIS_RUNPOD_AUTOCONNECT'] == '0'
    env.update(GENESIS_BACKEND_MODE='RUNPOD')
    env.pop('GENESIS_RUNPOD_AUTOCONNECT', None)
    subprocess.run(['bash', str(tmp_path / 'launch-qt-cockpit.sh')], env=env, check=True)
    result = json.loads(output.read_text())
    assert result['GENESIS_BACKEND_MODE'] == 'RUNPOD'
    assert result['GENESIS_RUNPOD_AUTOCONNECT'] == '1'
    env.update(GENESIS_BACKEND_MODE='LOCAL', GENESIS_RUNPOD_AUTOCONNECT='0')
    subprocess.run(['bash', str(tmp_path / 'launch-qt-cockpit.sh')], env=env, check=True)
    result = json.loads(output.read_text())
    assert result['GENESIS_BACKEND_MODE'] == 'LOCAL'
    assert result['GENESIS_RUNPOD_AUTOCONNECT'] == '0'


def test_miraclein_switch_preserves_connected_dimensions(monkeypatch, tmp_path, catalog):
    model = cockpit.REMOTE_MIRACLEIN_9B_MODEL
    prompt, _ = capture_reference(monkeypatch, tmp_path, catalog,
        cockpit.remote_reference_workflow(model), model,
        controls=cockpit.remote_reference_controls(model))
    scheduler = next(n for n in prompt.values() if n['class_type'] == 'Flux2Scheduler')
    assert isinstance(scheduler['inputs']['width'], list)
    assert isinstance(scheduler['inputs']['height'], list)
    assert scheduler['inputs']['steps'] == 12


@pytest.mark.parametrize('model', [cockpit.REMOTE_DONUTS_MODEL, cockpit.REMOTE_BIGLUSTY_DONUT_MODEL])
def test_sdxl_models_map_to_shared_t2i_workflow(model):
    assert cockpit.remote_reference_workflow(model) == cockpit.REMOTE_SDXL_T2I_WORKFLOW


@pytest.mark.parametrize("model", [cockpit.LOCAL_MIRACLEIN_9B_MODEL, cockpit.LOCAL_PORNMASTER_9B_MODEL])
@pytest.mark.parametrize("destination", ["LOCAL", "RUNPOD"])
def test_local_refinement_does_not_inherit_scene_replacement(monkeypatch, tmp_path, model, destination):
    bridge = cockpit.GenerationBridge()
    run = Mock(return_value=tmp_path / "refined.png")
    monkeypatch.setattr(bridge, "_run_reference_stage", run)
    current = tmp_path / "previous.png"
    with use_route(Route(destination, "https://test-8189.proxy.runpod.net" if destination == "RUNPOD" else "")):
        bridge._refine_result(Mock(), {}, current, model, "test", include_realism=False)
    text = run.call_args.args[4]
    assert run.call_args.args[3] == current
    if destination == "LOCAL":
        assert "Keep the existing background" in text
        assert "do not add or replace content" in text
        assert "Allow pose" not in text
        assert "infer a coherent environment" not in text
        assert "selected pose/control" not in text
    else:
        assert text == cockpit.adapt_prompt(cockpit.REFINE_INSTRUCTION, model, source_image=True, include_realism=False)


@pytest.mark.parametrize('workflow,model,encoder', [
    (cockpit.STAGE_1_WORKFLOW, cockpit.REMOTE_PHR00T_V19_GGUF_MODEL, '4'),
    (cockpit.REMOTE_PHR00T_V19_WORKFLOW, cockpit.REMOTE_PHR00T_V19_MODEL, '4'),
    (cockpit.REMOTE_PHR00T_WORKFLOW, cockpit.REMOTE_PHR00T_MODEL, '5'),
])
def test_phr00t_true_text_to_image_uses_zero_input_images(monkeypatch, tmp_path, catalog, workflow, model, encoder):
    client = Mock()
    monkeypatch.setattr(cockpit, 'validate_operation_prompt', lambda *args: None)
    bridge = cockpit.GenerationBridge()
    graph = {}
    monkeypatch.setattr(bridge, '_submit_and_save', lambda c, p, *args: graph.update(p) or tmp_path/'result.png')
    with use_route(Route('RUNPOD', 'https://test-8189.proxy.runpod.net')):
        result = bridge._run_reference_stage(client, catalog, workflow, None,
            'A ceramic vase on a sunlit table', 'stamp', 'Phr00t-TextToImage',
            model_override=model, controls={'width':1024,'height':640,'steps':4,'cfg':1.0})
    assert result == tmp_path/'result.png'
    client.upload_image.assert_not_called()
    assert not any(n['class_type'] == 'LoadImage' for n in graph.values())
    assert not any(key.startswith('image') for key in graph[encoder]['inputs'])
    assert graph[encoder]['inputs']['prompt'] == 'A ceramic vase on a sunlit table'
    assert graph['1']['inputs'].get('unet_name',graph['1']['inputs'].get('ckpt_name')) == model
    sampler = next(n for n in graph.values() if n['class_type']=='KSampler')
    assert sampler['inputs']['steps'] == 4 and sampler['inputs']['cfg'] == 1.0
    assert any(n['class_type']=='EmptyLatentImage' for n in graph.values())


@pytest.mark.parametrize('with_pose,field', [(False,'image2'),(True,'image3')])
def test_phr00t_explicit_extra_reference_keeps_image_order(monkeypatch, tmp_path, catalog, with_pose, field):
    source = tmp_path/'person.png';source.write_bytes(b'person')
    extra = tmp_path/'appearance.png';extra.write_bytes(b'appearance')
    pose = tmp_path/'pose.png';pose.write_bytes(b'pose')
    client = Mock(); client.upload_image.side_effect=lambda p: {'name':p.name, 'subfolder':''}
    bridge = cockpit.GenerationBridge()
    monkeypatch.setattr(cockpit, 'validate_operation_prompt', lambda *args:None)
    graph = {}
    monkeypatch.setattr(bridge, '_submit_and_save', lambda c,p,*args:graph.update(p) or tmp_path/'result.png')
    with use_route(Route('RUNPOD', 'https://test-8189.proxy.runpod.net')):
        bridge._run_reference_stage(client,catalog,cockpit.STAGE_1_WORKFLOW,source,
            'Photograph on a tabletop','stamp','Phr00t-v19-GGUF',
            secondary_image=pose if with_pose else None,
            controls={'extra_reference_url':extra.as_uri()},
            model_override=cockpit.REMOTE_PHR00T_V19_GGUF_MODEL)
    assert graph['4']['inputs']['image1'] == ['2',0]
    if with_pose: assert graph['4']['inputs']['image2'] == ['3',0]
    assert graph['4']['inputs'][field] == ['__genesis_extra_reference__',0]
    assert graph['__genesis_extra_reference__']['inputs']['image']=='appearance.png'
    assert graph['4']['inputs']['prompt'].endswith(
        'as an additional visual reference, not a replacement for the main subject in Picture 1.')
    assert 'Picture '+('3' if with_pose else '2') in graph['4']['inputs']['prompt']
    assert client.upload_image.call_count == 3 if with_pose else client.upload_image.call_count == 2


@pytest.mark.parametrize('pixel_size,optimized', [((768,512), True),((1344,832),True),((2264,1360),False)])
def test_phr00t_isolated_framing_encoder_opt_in_and_quality_fallback(monkeypatch,tmp_path,catalog,pixel_size,optimized):
    model=cockpit.REMOTE_PHR00T_V23_Q2_MODEL
    cat=dict(catalog)
    cat['GenesisQwenImageEditFraming']={'input':{'required':{'clip':['CLIP'],
        'prompt':['STRING']},'optional':{'target_latent':['LATENT'],
        'image1':['IMAGE'],'image2':['IMAGE'],'image3':['IMAGE'],'image4':['IMAGE'],
        'vae':['VAE']}}}
    client=Mock()
    client.upload_image.return_value={'name':'source.png','subfolder':''}
    bridge=cockpit.GenerationBridge()
    graph={}
    # This synthetic catalog only exercises graph wiring; real node-schema
    # validation runs separately against local ComfyUI /object_info.
    monkeypatch.setattr(cockpit.workflow_lab, 'validate_prompt', lambda *a: {
        'valid':True,'missing_nodes':[],'missing_inputs':[]})
    monkeypatch.setattr(cockpit,'validate_operation_prompt',lambda *a:None)
    monkeypatch.setattr(bridge,'_submit_and_save',lambda c,p,*a:graph.update(p) or tmp_path/'saved.png')
    with use_route(Route('LOCAL','')):
        bridge._run_reference_stage(client,cat,cockpit.STAGE_1_WORKFLOW,tmp_path/'source.png',
            'Change the teapot colour','stamp','Phr00t-v23-GGUF',
            model_override=model,controls={'width':pixel_size[0],'height':pixel_size[1]})
    encoder=graph['4']
    assert encoder['class_type']==('GenesisQwenImageEditFraming' if optimized else 'TextEncodeQwenImageEditPlus')
    assert ('target_latent' in encoder['inputs']) is optimized
    if optimized: assert encoder['inputs']['target_latent']==graph['7']['inputs']['latent_image']
    assert graph['6']['inputs']['width']==pixel_size[0]
    assert graph['6']['inputs']['height']==pixel_size[1]


def test_phr00t_framing_fallback_when_node_absent(monkeypatch,tmp_path,catalog):
    bridge=cockpit.GenerationBridge()
    client=Mock();client.upload_image.return_value={'name':'source.png'}
    graph={}
    monkeypatch.setattr(cockpit.workflow_lab,'validate_prompt',lambda *a: {
        'valid':True,'missing_nodes':[],'missing_inputs':[]})
    monkeypatch.setattr(cockpit,'validate_operation_prompt',lambda *a:None)
    monkeypatch.setattr(bridge,'_submit_and_save',lambda c,p,*a:graph.update(p) or tmp_path/'saved.png')
    with use_route(Route('LOCAL','')):
        bridge._run_reference_stage(client,catalog,cockpit.STAGE_1_WORKFLOW,tmp_path/'source.png',
            'A red teapot','stamp','Phr00t-GGUF',model_override=cockpit.QWEN_MODEL)
    assert graph['4']['class_type']=='TextEncodeQwenImageEditPlus'
    assert 'target_latent' not in graph['4']['inputs']


def test_isolated_genesis_framing_node_does_not_replace_comfy_qwen_core():
    source=(cockpit.PROJECT_ROOT/'genesis/reference/comfy_nodes/genesis_qwen_framing/__init__.py').read_text()
    assert 'node_id="GenesisQwenImageEditFraming"' in source
    assert 'node_id="TextEncodeQwenImageEditPlus"' not in source
    assert 'async def comfy_entrypoint()' in source
    assert 'target_latent' in source


@pytest.mark.parametrize('with_pose', [False, True])
def test_v19_actual_source_dispatch_passes_tiled_decoder_model_override(monkeypatch, tmp_path, catalog, with_pose):
    bridge = cockpit.GenerationBridge()
    bridge._output_dir = tmp_path
    client = Mock()
    client.object_info.return_value = catalog
    monkeypatch.setattr(bridge, '_connect_comfyui', lambda: (client, {}))
    monkeypatch.setattr(cockpit, 'validate_remote_workflow_assets', lambda *a: None)
    monkeypatch.setattr(bridge, '_record_finish', lambda *a, **k: None)
    calls = []
    monkeypatch.setattr(bridge, '_run_reference_stage',
                        lambda *a, **k: calls.append(k) or tmp_path / 'out.png')
    source = tmp_path / 'source.png'
    pose = tmp_path / 'pose.png' if with_pose else None
    with use_route(Route('LOCAL', '')):
        bridge._run_generate('A teapot', '', 512, 704, cockpit.QWEN_MODEL,
                             'None', 'None', 'None', 0.5, 0.5, 0.5,
                             source, pose, False, False, False,
                             {'width': 512, 'height': 704})
    assert len(calls) == 1
    assert calls[0]['model_override'] == cockpit.QWEN_MODEL
    assert calls[0].get('secondary_image') == pose


@pytest.mark.parametrize('model,tiled', [
    (cockpit.QWEN_MODEL, True),
    (cockpit.REMOTE_PHR00T_V23_Q2_MODEL, False),
])
@pytest.mark.parametrize('has_source', [False, True])
def test_local_v19_q4_uses_tiled_vae_decode_without_changing_output_links(
        monkeypatch, tmp_path, catalog, model, tiled, has_source):
    info = dict(catalog)
    info['VAEDecodeTiled'] = {'input': {'required': {
        'samples': ['LATENT'], 'vae': ['VAE'],
        'tile_size': ['INT'], 'overlap': ['INT'],
        'temporal_size': ['INT'], 'temporal_overlap': ['INT'],
    }}}
    source = tmp_path / 'teapot.png' if has_source else None
    client = Mock()
    client.upload_image.return_value = {'name': 'teapot.png', 'subfolder': ''}
    graph = {}
    bridge = cockpit.GenerationBridge()
    monkeypatch.setattr(cockpit.workflow_lab, 'validate_prompt', lambda *a: {
        'valid': True, 'missing_nodes': [], 'missing_inputs': []})
    monkeypatch.setattr(cockpit, 'validate_operation_prompt', lambda *a: None)
    monkeypatch.setattr(bridge, '_submit_and_save',
                        lambda cli, prompt, *a: graph.update(prompt) or tmp_path / 'out.png')
    with use_route(Route('LOCAL', '')):
        bridge._run_reference_stage(client, info, cockpit.STAGE_1_WORKFLOW,
            source, 'A red teapot', 'stamp', 'Stage1',
            controls={'width': 512, 'height': 704, 'steps': 4, 'cfg': 1.0},
            model_override=model)
    decoder = graph['8']
    assert decoder['class_type'] == ('VAEDecodeTiled' if tiled else 'VAEDecode')
    if tiled:
        assert decoder['inputs'] == {
            'samples': ['7', 0], 'vae': ['32', 0],
            'tile_size': 256, 'overlap': 64,
            'temporal_size': 64, 'temporal_overlap': 8,
        }
    else:
        assert 'tile_size' not in decoder['inputs']
    assert graph['9']['inputs']['images'] == ['8', 0]
    assert graph['10']['inputs']['images'] == ['8', 0]


def test_v19_q4_no_tiled_node_preserves_existing_comfy_oom_fallback(
        monkeypatch, tmp_path, catalog):
    client = Mock()
    bridge = cockpit.GenerationBridge()
    graph = {}
    monkeypatch.setattr(cockpit.workflow_lab, 'validate_prompt', lambda *a: {
        'valid': True, 'missing_nodes': [], 'missing_inputs': []})
    monkeypatch.setattr(cockpit, 'validate_operation_prompt', lambda *a: None)
    monkeypatch.setattr(bridge, '_submit_and_save',
                        lambda cli, prompt, *a: graph.update(prompt) or tmp_path / 'out.png')
    with use_route(Route('LOCAL', '')):
        bridge._run_reference_stage(client, catalog, cockpit.STAGE_1_WORKFLOW,
            None, 'A red teapot', 'stamp', 'Stage1',
            model_override=cockpit.QWEN_MODEL)
    assert graph['8']['class_type'] == 'VAEDecode'
    assert 'tile_size' not in graph['8']['inputs']


def test_runpod_v19_q4_never_uses_local_tiled_vae(monkeypatch, tmp_path, catalog):
    info = dict(catalog)
    info['VAEDecodeTiled'] = {'input': {'required': {
        'samples': ['LATENT'], 'vae': ['VAE'],
        'tile_size': ['INT'], 'overlap': ['INT'],
        'temporal_size': ['INT'], 'temporal_overlap': ['INT'],
    }}}
    client = Mock()
    bridge = cockpit.GenerationBridge()
    graph = {}
    monkeypatch.setattr(cockpit, 'validate_operation_prompt', lambda *a: None)
    monkeypatch.setattr(bridge, '_submit_and_save',
                        lambda cli, prompt, *a: graph.update(prompt) or tmp_path / 'out.png')
    with use_route(Route('RUNPOD', 'https://test-8189.proxy.runpod.net')):
        bridge._run_reference_stage(client, info, cockpit.STAGE_1_WORKFLOW,
            None, 'A red teapot', 'stamp', 'Stage1',
            model_override=cockpit.QWEN_MODEL)
    assert graph['8']['class_type'] == 'VAEDecode'
