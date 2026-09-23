from unittest.mock import Mock
import pytest
from PIL import Image
import qt_cockpit as cockpit
from genesis import media_functions as media


def test_advanced_generation_preserves_selected_strengths(monkeypatch):
    bridge = cockpit.GenerationBridge()
    queue = Mock()
    monkeypatch.setattr(bridge, 'queueGenerate', queue)
    bridge.queueGenerateAdvanced('a ceramic mug', '', 512, 512, cockpit.FOUR_B_MODEL,
        'one', 'two', '', '', False, False, False, 4, 1.0, 42, 1.0, 'euler', 'normal',
        'three', 0.2, 0.3, 0.4)
    assert queue.call_args.args[5:11] == ('one', 'two', 'three', 0.2, 0.3, 0.4)


def test_create_controls_preserve_graph_links_and_seed():
    prompt = {'1': {'class_type': 'KSampler', 'inputs': {'seed': 0, 'steps': 4, 'cfg': 1.0, 'sampler_name': 'euler', 'scheduler': 'normal', 'denoise': 1.0, 'model': ['3', 0]}},
              '2': {'class_type': 'Flux2Scheduler', 'inputs': {'steps': 4, 'width': 512, 'height': 512}},
              '3': {'class_type': 'RandomNoise', 'inputs': {'noise_seed': 5}}}
    cockpit.apply_create_controls(prompt, {'seed': 42, 'steps': 8, 'cfg': 2.0, 'width': 768, 'height': 512})
    assert prompt['1']['inputs']['seed'] == prompt['3']['inputs']['noise_seed'] == 42
    assert prompt['1']['inputs']['model'] == ['3', 0]
    assert prompt['2']['inputs']['steps'] == 8
    assert prompt['2']['inputs']['width'] == 768


def test_failed_export_keeps_existing_file(tmp_path, monkeypatch):
    src = tmp_path / 'source.png'; dst = tmp_path / 'output.png'
    Image.new('RGB', (8, 8)).save(src)
    dst.write_bytes(b'previous output')
    def fail(source, target, scale):
        target.write_bytes(b'partial')
        raise OSError('disk test failure')
    monkeypatch.setattr(media, '_enhance_pillow', fail)
    with pytest.raises(OSError):
        media.upscale_enhance(src, dst, prefer_ai=False)
    assert dst.read_bytes() == b'previous output'
    assert not list(tmp_path.glob('.genesis-export-*'))


def test_wrong_extension_rejected_before_processing(tmp_path):
    src = tmp_path / 'source.png'
    Image.new('RGBA', (8, 8)).save(src)
    with pytest.raises(media.MediaFunctionError, match='extension'):
        media.upscale_enhance(src, tmp_path / 'output.jpg', prefer_ai=False)


def test_remote_upscale_uses_remote_model_even_without_local_file(tmp_path, monkeypatch):
    src = tmp_path / 'source.png'; dst = tmp_path / 'out.png'
    Image.new('RGBA', (8, 8), (255, 0, 0, 90)).save(src)
    remote_image = tmp_path / 'remote.png'; Image.new('RGB', (32, 32)).save(remote_image)
    client = Mock()
    client.object_info.return_value = {'UpscaleModelLoader': {'input': {'required': {'model_name': [['4x-UltraSharp.pth']]}}}}
    client.upload_image.return_value = {'name': 'source.png', 'subfolder': 'genesis'}
    client.wait.return_value = Mock(status='completed', outputs=[{'kind': 'images'}])
    client.view.return_value = remote_image.read_bytes()
    factory = Mock(return_value=client)
    monkeypatch.setenv('GENESIS_COMFY_URL', 'https://test.example')
    monkeypatch.setattr(media, 'ComfyClient', factory)
    monkeypatch.setattr(media, 'UPSCALE_MODEL', tmp_path / 'absent.pth')
    result = media.upscale_enhance(src, dst, scale=2, require_ai=True)
    factory.assert_called_once_with('https://test.example', timeout=20)
    assert client.submit.call_args.args[0]['2']['inputs']['model_name'] == '4x-UltraSharp.pth'
    assert result.output == dst
    with Image.open(dst) as output:
        assert output.size == (16, 16)
        assert output.getchannel('A').getextrema() == (90, 90)


def test_canvas_rename_is_undoable(tmp_path):
    from genesis.canvas_bridge import CanvasBridge
    source = tmp_path / 'layer.png'
    Image.new('RGBA', (20, 20)).save(source)
    bridge = CanvasBridge()
    bridge.addImage(str(source))
    bridge.renameSelected('Foreground')
    assert bridge.selected['name'] == 'Foreground'
    bridge.undo()
    assert bridge.selected['name'] == 'layer.png'


def test_explicit_standard_resize_stays_cpu(monkeypatch, tmp_path):
    from genesis.media_bridge import MediaBridge
    from genesis import media_bridge
    source = tmp_path / 'input.png'
    target = tmp_path / 'output.png'
    Image.new('RGBA', (8, 8)).save(source)
    bridge = MediaBridge()
    monkeypatch.setattr(bridge, '_choose_image', lambda title: source)
    monkeypatch.setattr(media_bridge.QFileDialog, 'getSaveFileName', lambda *a: (str(target), 'PNG'))
    operation = Mock(return_value=media.OperationResult(target, 'pillow'))
    monkeypatch.setattr(media_bridge, 'upscale_enhance', operation)
    monkeypatch.setattr(bridge, '_start', lambda label, run: run())
    bridge.chooseAndUpscale(2.0, False)
    operation.assert_called_once_with(source, str(target), scale=2.0, prefer_ai=False)


def test_local_startup_does_not_wait_for_backend(monkeypatch):
    monkeypatch.delenv('GENESIS_COMFY_URL', raising=False)
    monkeypatch.setattr(cockpit.workflow_lab, 'system_stats', Mock(side_effect=AssertionError('network during startup')))
    status = cockpit.load_runtime_status(probe_remote=False)
    assert status['remote'] is False
    assert status['ready'] is False


def test_local_runtime_monitor_updates_status_without_remote_catalog(monkeypatch):
    monkeypatch.delenv('GENESIS_COMFY_URL', raising=False)
    status = {'comfyOnline': True, 'ready': True, 'remote': False}
    monkeypatch.setattr(cockpit, 'load_runtime_status', lambda: status)
    monkeypatch.setattr(cockpit, 'load_remote_catalog', Mock(side_effect=AssertionError('remote catalog in local mode')))
    monitor = cockpit.RemoteRuntimeMonitor()
    received = []
    monitor.statusReady.connect(received.append)
    monitor._probe()
    assert received == [status]
