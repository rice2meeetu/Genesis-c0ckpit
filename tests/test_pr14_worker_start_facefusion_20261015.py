"""Offline regression checks for worker launch failure and FaceFusion readiness."""
from pathlib import Path
from types import SimpleNamespace

from PyQt6.QtCore import QCoreApplication, QUrl
import pytest

import qt_cockpit as cockpit
from genesis.backend_routing import Route


def args(prompt='portrait'):
    return (prompt, '', 512, 512, cockpit.FOUR_B_MODEL,
            'None', 'None', '', '', False, False, False,
            4, 1.0, -1, 1.0, 'euler', 'simple', 'None', 0.5, 0.5, 0.5)


def local_bridge():
    QCoreApplication.instance() or QCoreApplication([])
    bridge = cockpit.GenerationBridge()
    bridge.backend_router = SimpleNamespace(
        mode='LOCAL', endpoint='', resolve=lambda model: Route('LOCAL', ''))
    return bridge


class RefusesToStart:
    def __init__(self, *a, **kw):
        self.args = kw.get('args')
    def start(self):
        raise RuntimeError('cannot start new thread: synthetic')


def test_manual_generation_recovers_busy_when_thread_start_fails(monkeypatch):
    bridge = local_bridge()
    monkeypatch.setattr(cockpit.threading, 'Thread', RefusesToStart)
    bridge.queueGenerateAdvanced(*args())
    assert not bridge.busy
    assert not bridge._queue_active
    assert bridge._active_stage_three_engine is None
    assert bridge._next_generation_controls is None
    assert 'Generation could not start' in bridge.status
    assert 'synthetic' in bridge.status
    # A second manual click must be possible, rather than getting stuck Busy.
    bridge.queueGenerateAdvanced(*args('retry'))
    assert not bridge.busy
    assert 'Generation could not start' in bridge.status


def test_queued_generation_failure_clears_queue_state_and_continues(monkeypatch):
    bridge = local_bridge()
    old_model = bridge._stage_two_model
    bridge._set_busy(True)
    bridge.enqueueGenerateAdvanced(*args('first'))
    bridge.enqueueGenerateAdvanced(*args('second'))
    assert bridge.pendingGenerationCount == 2
    bridge._set_busy(False)
    attempts = []
    class FailsThenStarts:
        def __init__(self, *a, **kw):
            self.kw = kw
        def start(self):
            attempts.append(self.kw)
            if len(attempts) == 1:
                raise RuntimeError('synthetic thread capacity exhausted')
            # A synthetic successful start, no real worker or GPU involved.
            bridge._set_busy(True)
    monkeypatch.setattr(cockpit.threading, 'Thread', FailsThenStarts)
    bridge._dispatch_next_generation()
    assert len(attempts) == 2
    assert attempts[0]['args'][1] == 'first'
    assert attempts[1]['args'][1] == 'second'
    assert bridge.busy and bridge._queue_active
    assert bridge.pendingGenerationCount == 0
    assert bridge._stage_two_model == old_model
    assert bridge._queued_route_override is None
    assert bridge._queued_character_override is None
    assert bridge._next_generation_controls is None
    bridge._set_busy(False)
    QCoreApplication.processEvents()
    assert not bridge._queue_active
    assert bridge._active_stage_three_engine is None


def test_queued_generation_all_launches_fail_without_stranding_busy(monkeypatch):
    bridge = local_bridge()
    bridge._set_busy(True)
    bridge.enqueueGenerateAdvanced(*args('one'))
    bridge.enqueueGenerateAdvanced(*args('two'))
    bridge._set_busy(False)
    monkeypatch.setattr(cockpit.threading, 'Thread', RefusesToStart)
    bridge._dispatch_next_generation()
    assert not bridge.busy
    assert not bridge._queue_active
    assert bridge.pendingGenerationCount == 0
    assert bridge._active_stage_three_engine is None
    assert bridge._queued_route_override is None
    assert bridge._queued_character_override is None
    assert 'Generation could not start' in bridge.status


@pytest.mark.parametrize('runtime', ['venv', 'miniforge'])
def test_facefusion_availability_matches_the_actual_launch_runtime(monkeypatch, tmp_path, runtime):
    bridge = local_bridge()
    root = tmp_path/'facefusion'
    root.mkdir()
    for basename in ['facefusion.py', 'facefusion.ini']:
        (root/basename).write_text('fixture')
    home = tmp_path/'home'
    if runtime == 'venv':
        python = root/'.venv/bin/python'
    else:
        python = home/'miniforge3/envs/facefusion-rocm/bin/python'
    python.parent.mkdir(parents=True)
    python.write_text('fixture')
    monkeypatch.setattr(cockpit.integrations, 'FACEFUSION_ROOT', root)
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: home))
    assert bridge.faceFusionAvailable is True
    assert bridge._facefusion_python() == python
    bridge.setFaceFusionProvider('cpu')
    src = tmp_path/'source.png'; src.write_bytes(b'fixture')
    dst = tmp_path/'target.png'; dst.write_bytes(b'fixture')
    launches = []
    class FakeThread:
        def __init__(self, *a, **kw):
            launches.append(kw)
        def start(self):
            pass
    monkeypatch.setattr(cockpit.threading, 'Thread', FakeThread)
    bridge.queueFaceFusion(QUrl.fromLocalFile(str(dst)).toString(), QUrl.fromLocalFile(str(src)).toString())
    assert len(launches) == 1, bridge.status
    assert launches[0]['args'][2] == python
    bridge._set_busy(False)
    (root/'facefusion.ini').unlink()
    assert bridge.faceFusionAvailable is False


def test_facefusion_does_not_advertise_missing_installation(monkeypatch, tmp_path):
    bridge = local_bridge()
    root=tmp_path/'missing'
    root.mkdir()
    monkeypatch.setattr(cockpit.integrations,'FACEFUSION_ROOT',root)
    monkeypatch.setattr(Path,'home',classmethod(lambda cls:tmp_path/'home'))
    assert bridge.faceFusionAvailable is False
