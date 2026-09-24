"""Neutral, isolated regression coverage: never contact a service or run inference."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import threading
import pytest
from PIL import Image
from PyQt6.QtCore import QUrl
import qt_cockpit as cockpit
from genesis.backend_bridge import BackendBridge
from genesis.backend_routing import Route, remote_url, use_route
from genesis.media_bridge import MediaBridge
from genesis import media_functions as media


def fixture_image(tmp_path):
    path = tmp_path / 'neutral.png'
    Image.new('RGBA', (8, 8), (40, 80, 120, 100)).save(path)
    return path


@pytest.mark.parametrize('operation', ['face_swap', 'edit', 'inpaint', 'upscale'])
def test_operation_destination_respects_mode_and_safety(operation):
    bridge = BackendBridge(cockpit.GenerationBridge())
    bridge._endpoint = 'https://remote.example'
    bridge._remote_status = {'ready': True}
    bridge._local_status = {'ready': True}
    bridge._local_safe = True
    bridge._mode = 'RUNPOD'
    assert bridge.resolve_operation(operation).url == bridge._endpoint
    bridge._mode = 'LOCAL'
    assert bridge.resolve_operation(operation).destination == 'LOCAL'
    bridge._local_safe = False
    with pytest.raises(ValueError): bridge.resolve_operation(operation)
    bridge._mode = 'AUTO'
    assert bridge.resolve_operation(operation).destination == 'RUNPOD'
    bridge._remote_status = {'ready': False}
    with pytest.raises(ValueError): bridge.resolve_operation(operation)


@pytest.mark.parametrize('operation', ['face_swap', 'edit', 'inpaint'])
def test_queued_operations_capture_route_before_thread_start(tmp_path, monkeypatch, operation):
    path = fixture_image(tmp_path)
    uri = QUrl.fromLocalFile(str(path)).toString()
    bridge = cockpit.GenerationBridge()
    route = Route('RUNPOD', 'https://original.example')
    bridge.backend_router = Mock()
    bridge.backend_router.resolve_operation.return_value = route
    monkeypatch.setattr(cockpit, 'EDIT_WORKFLOW', path)
    worker = Mock(side_effect=lambda *args: remote_url())
    monkeypatch.setattr(bridge, '_run_' + operation, worker)
    thread = Mock()
    monkeypatch.setattr(cockpit.threading, 'Thread', thread)
    if operation == 'face_swap': bridge.queueFaceSwap(uri, uri)
    elif operation == 'edit': bridge.queueEdit(uri, 'neutral mug', 0.5)
    else: bridge.queueInpaint(uri, uri, 'neutral mug', 0.5)
    bridge.backend_router.resolve_operation.assert_called_once_with(operation)
    bridge.backend_router.resolve_operation.return_value = Route('LOCAL', '')
    call = thread.call_args.kwargs
    assert call['target'](*call['args']) == 'https://original.example'
    worker.assert_called_once()


def test_remote_context_does_not_leak_between_threads():
    bridge = cockpit.GenerationBridge()
    observed = []
    with use_route(Route('LOCAL', '')):
        thread = threading.Thread(target=lambda: observed.append(bridge._run_routed_operation(
            Route('RUNPOD', 'https://job.example'), remote_url)))
        thread.start(); thread.join(2)
        assert remote_url() == ''
    assert observed == ['https://job.example']


@pytest.mark.parametrize('mode', ['RUNPOD', 'AUTO'])
def test_facefusion_never_silently_runs_local_in_other_modes(tmp_path, monkeypatch, mode):
    uri = fixture_image(tmp_path).as_uri()
    bridge = cockpit.GenerationBridge()
    bridge.backend_router = SimpleNamespace(mode=mode)
    thread = Mock(side_effect=AssertionError('local process requested'))
    monkeypatch.setattr(cockpit.threading, 'Thread', thread)
    bridge.queueFaceFusion(uri, uri)
    assert 'local image-only' in bridge.status
    thread.assert_not_called()


def test_media_worker_captures_selected_endpoint(monkeypatch):
    bridge = MediaBridge()
    bridge.backend_router = Mock()
    bridge.backend_router.resolve_operation.return_value = Route('RUNPOD', 'https://chosen.example')
    queued = []
    monkeypatch.setattr(bridge, '_start', lambda label, run: queued.append(run))
    bridge._start_upscale('upscale', remote_url)
    bridge.backend_router.resolve_operation.return_value = Route('LOCAL', '')
    assert queued[0]() == 'https://chosen.example'


def test_media_route_failure_never_queues_or_falls_back(monkeypatch):
    bridge = MediaBridge()
    bridge.backend_router = Mock()
    bridge.backend_router.resolve_operation.side_effect = ValueError('RunPod offline')
    start = Mock()
    monkeypatch.setattr(bridge, '_start', start)
    bridge._start_upscale('upscale', Mock())
    assert 'offline' in bridge.status
    start.assert_not_called()


def test_upscale_uses_route_instead_of_stale_environment(tmp_path, monkeypatch):
    source = fixture_image(tmp_path)
    monkeypatch.setenv('GENESIS_COMFY_URL', 'https://stale.example')
    monkeypatch.setattr(media, 'UPSCALE_MODEL', tmp_path / 'absent.pth')
    factory = Mock()
    client = factory.return_value
    client.object_info.return_value = {'UpscaleModelLoader': {'input': {'required': {'model_name': [['4x-UltraSharp.pth']]}}}}
    client.upload_image.return_value = {'name': 'neutral.png'}
    client.wait.return_value = SimpleNamespace(status='completed', outputs=[{'kind':'images'}])
    client.view.return_value = source.read_bytes()
    monkeypatch.setattr(media, 'ComfyClient', factory)
    with use_route(Route('RUNPOD', 'https://chosen.example')):
        media.upscale_enhance(source, tmp_path / 'out.png', scale=4, require_ai=True)
    factory.assert_called_once_with('https://chosen.example', timeout=20)


def test_local_upscale_obeys_kernel_latch(tmp_path, monkeypatch):
    from genesis import integrations
    source = fixture_image(tmp_path)
    monkeypatch.setattr(media, 'UPSCALE_MODEL', source)
    monkeypatch.setattr(integrations, 'gpu_kernel_preflight', lambda: (False, 'kernel hold'))
    factory = Mock(side_effect=AssertionError('must not connect'))
    monkeypatch.setattr(media, 'ComfyClient', factory)
    with use_route(Route('LOCAL', '')):
        with pytest.raises(media.MediaFunctionError, match='kernel hold'):
            media.upscale_enhance(source, tmp_path / 'out.png', require_ai=True)
    factory.assert_not_called()


def test_unavailable_workflow_asset_is_rejected_without_submission():
    prompt = {'1': {'class_type':'CheckpointLoaderSimple', 'inputs':{'ckpt_name':'missing.safetensors'}}}
    info = {'CheckpointLoaderSimple': {'input': {'required': {'ckpt_name': [['installed.safetensors']]}}}}
    with pytest.raises(cockpit.workflow_lab.ComfyError, match='unavailable'):
        cockpit.validate_operation_prompt(prompt, info, 'neutral test')


def test_shared_output_save_creates_fresh_folder_and_preserves_edit_timeout(tmp_path):
    source = fixture_image(tmp_path)
    bridge = cockpit.GenerationBridge()
    bridge._output_dir = tmp_path / 'new-output-folder'
    client = Mock()
    client.submit.return_value = 'neutral-job'
    client.wait.return_value = SimpleNamespace(status='completed', outputs=[{'kind':'images', 'filename':'neutral.png'}])
    client.view.return_value = source.read_bytes()
    with use_route(Route('RUNPOD', 'https://test.example')):
        output = bridge._submit_and_save(client, {}, 'fixture', 'Edit', timeout=3600)
    assert output.is_file()
    assert output.read_bytes() == source.read_bytes()
    assert client.wait.call_args.kwargs['timeout'] == 3600
