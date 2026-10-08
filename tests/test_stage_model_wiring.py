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
    assert row['runnable'] and row['sourceRequired']
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
    ('RUNPOD', '1', False), ('RUNPOD', '0', False), ('RUNPOD', '', False), ('LOCAL', '1', False),
])
def test_startup_preserves_explicit_connect_behavior(monkeypatch, mode, opt_in, expected):
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
