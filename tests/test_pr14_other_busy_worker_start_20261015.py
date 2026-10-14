"""Do not strand Busy when non-generation workers cannot start (no GPU/network)."""
from pathlib import Path
from types import SimpleNamespace

import pytest
from PyQt6.QtCore import QCoreApplication, QUrl

import qt_cockpit as cockpit
from genesis.backend_routing import Route


class NoThread:
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs

    def start(self):
        raise RuntimeError('synthetic worker launch failure')


def bridge_and_image(tmp_path, monkeypatch):
    QCoreApplication.instance() or QCoreApplication([])
    bridge = cockpit.GenerationBridge()
    bridge.backend_router = SimpleNamespace(mode='LOCAL', endpoint='',
        resolve_operation=lambda operation: Route('LOCAL', ''),
        resolve=lambda model: Route('LOCAL', ''))
    file = tmp_path/'test-input.png'
    file.write_bytes(b'not a real image: no processing performed')
    monkeypatch.setattr(cockpit.threading, 'Thread', NoThread)
    return bridge, QUrl.fromLocalFile(str(file)).toString(), file


def assert_unstuck(bridge, action_name):
    assert not bridge.busy
    assert not bridge._queue_active
    assert action_name in bridge.status
    assert 'synthetic worker launch failure' in bridge.status


@pytest.mark.parametrize('operation', ['facefusion', 'inpaint', 'edit'])
def test_three_original_busy_reproductions_recover(monkeypatch, tmp_path, operation):
    bridge, image_url, image = bridge_and_image(tmp_path, monkeypatch)
    if operation == 'facefusion':
        root = tmp_path/'facefusion'; (root/'.venv/bin').mkdir(parents=True)
        for name in ('.venv/bin/python', 'facefusion.py', 'facefusion.ini'):
            (root/name).write_bytes(b'fixture')
        monkeypatch.setattr(cockpit.integrations, 'FACEFUSION_ROOT', root)
        bridge.setFaceFusionProvider('cpu')
        bridge.queueFaceFusion(image_url, image_url)
        assert_unstuck(bridge, 'FaceFusion')
    elif operation == 'inpaint':
        bridge.queueInpaint(image_url, image_url, 'repair a painting', 0.5)
        assert_unstuck(bridge, 'Inpaint')
    else:
        monkeypatch.setattr(cockpit, 'EDIT_WORKFLOW', image)
        bridge.queueEdit(image_url, 'repaint in watercolor', 0.5)
        assert_unstuck(bridge, 'Image edit')


def test_wan_failure_does_not_leave_busy(monkeypatch, tmp_path):
    bridge, image_url, _ = bridge_and_image(tmp_path, monkeypatch)
    monkeypatch.setattr(cockpit, 'remote_url', lambda: 'https://test-pod-8189.proxy.runpod.net')
    bridge.queueWanVideo(image_url, 'pan across sky', 13, 42)
    assert_unstuck(bridge, 'Wan video')


def test_manual_person_a_swap_worker_failure_does_not_leave_busy(monkeypatch, tmp_path):
    bridge, image_url, _ = bridge_and_image(tmp_path, monkeypatch)
    # Review picks are simulated; no face model, image inspection or swap.
    monkeypatch.setattr('genesis.person_a_targeting.choose_face_region',
                        lambda image, purpose: SimpleNamespace())
    bridge.queueFaceSwap(image_url, image_url)
    assert_unstuck(bridge, 'Face swap')


def test_character_reference_worker_failure_does_not_leave_busy(monkeypatch, tmp_path):
    bridge, image_url, image = bridge_and_image(tmp_path, monkeypatch)
    monkeypatch.setattr(cockpit, 'get_character',
                        lambda character_id: {'primary_image': str(image), 'adult_confirmed': True})
    eligible = (cockpit.SOURCE_EDIT_MODELS & cockpit.SUPPORTED_CREATE_MODELS)
    model = next(iter(eligible))
    bridge.backend_router.resolve = lambda model: Route('RUNPOD', 'https://test-pod-8189.proxy.runpod.net')
    bridge.queueCharacterReferenceSet('fixture-character', model)
    assert_unstuck(bridge, 'Character reference set')


def test_busy_helper_does_not_reset_busy_after_successful_worker_start(monkeypatch):
    QCoreApplication.instance() or QCoreApplication([])
    bridge = cockpit.GenerationBridge()
    calls = []
    class GoodThread:
        def __init__(self, *args, **kwargs):
            calls.append(kwargs)
        def start(self):
            calls.append('started')
    monkeypatch.setattr(cockpit.threading, 'Thread', GoodThread)
    bridge._set_busy(True)
    assert bridge._start_busy_worker(lambda: None, label='Test') is True
    assert bridge.busy
    assert calls[-1] == 'started'
    bridge._set_busy(False)


def test_busy_helper_handles_thread_constructor_failure(monkeypatch):
    QCoreApplication.instance() or QCoreApplication([])
    bridge = cockpit.GenerationBridge()
    class ConstructorFailure:
        def __init__(self, *args, **kwargs):
            raise RuntimeError('synthetic thread constructor failure')
    monkeypatch.setattr(cockpit.threading, 'Thread', ConstructorFailure)
    bridge._set_busy(True)
    assert bridge._start_busy_worker(lambda: None, label='Test') is False
    assert not bridge.busy
    assert 'constructor failure' in bridge.status
