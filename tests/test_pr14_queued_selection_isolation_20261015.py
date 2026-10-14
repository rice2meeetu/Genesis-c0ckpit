"""Queued requests may not overwrite the next manual generation's selections.

No models, personal photos, network connections or GPU jobs are used here.
"""
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import Mock

from PyQt6.QtCore import QCoreApplication
import qt_cockpit as cockpit
from genesis.backend_routing import Route


def _args(source_url='', prompt='queued portrait'):
    return (prompt, '', 512, 512, cockpit.FOUR_B_MODEL, 'None', 'None',
            source_url, '', False, False, False, 4, 1.0, -1, 1.0,
            'euler', 'simple', 'None', 0.5, 0.5, 0.5)


def _state(bridge):
    return (bridge._sdxl_faceid_enabled, bridge._sdxl_faceid_strength,
            bridge._stage_two_model, bridge._output_target_long_edge,
            bridge._source_reference_megapixels, bridge._extra_reference_url)


def test_queued_job_uses_its_snapshot_but_restores_current_ui_selections(monkeypatch):
    QCoreApplication.instance() or QCoreApplication([])
    bridge = cockpit.GenerationBridge()
    route = Route('LOCAL', '')
    bridge.backend_router = SimpleNamespace(mode='LOCAL', endpoint='', resolve=lambda model: route)
    chosen_character = {'value': None}
    monkeypatch.setattr(bridge, '_snapshot_character_a', lambda: chosen_character['value'])

    original_dispatch = bridge._dispatch_next_generation
    monkeypatch.setattr(bridge, '_dispatch_next_generation', lambda: None)
    bridge.setSdxlFaceID(True, 0.91)
    bridge.setStageTwoModel(cockpit.REMOTE_AISHA_9B_MODEL)
    bridge.setOutputTarget(3840)
    bridge.setSourceReferenceMegapixels(0.8)
    bridge.setExtraReferenceSource('file:///temporary-old-reference.png')
    bridge.setStageThreeEngine('reactor_inswapper')
    at_queue = _state(bridge)
    bridge.enqueueGenerateAdvanced(*_args())
    assert bridge.pendingGenerationCount == 1
    assert bridge._pending_generations[0]['character_snapshot'] is None

    bridge.setSdxlFaceID(False, 0.35)
    bridge.setStageTwoModel(cockpit.REMOTE_MIRACLEIN_9B_MODEL)
    bridge.setOutputTarget(2560)
    bridge.setSourceReferenceMegapixels(0.3)
    bridge.setExtraReferenceSource('file:///current-next-reference.png')
    bridge.setStageThreeEngine('reactor_hyperswap')
    chosen_character['value'] = {'id': 'later-character', 'master': '/tmp/not-a-source.png'}
    current_ui = _state(bridge)
    assert current_ui != at_queue

    captured = []
    def fake_worker_start(*args):
        captured.append({'controls': dict(bridge._next_generation_controls),
                         'route': bridge._queued_route_override,
                         'engine': bridge._active_stage_three_engine})
        bridge._set_busy(True)
    monkeypatch.setattr(bridge, 'queueGenerate', fake_worker_start)
    original_dispatch()
    assert bridge.busy and bridge._queue_active
    assert bridge.pendingGenerationCount == 0
    assert len(captured) == 1
    controls = captured[0]['controls']
    assert controls['faceid_enabled'] is True
    assert controls['faceid_strength'] == 0.91
    assert controls['output_long_edge'] == 3840
    assert controls['source_reference_megapixels'] == 0.8
    assert controls['extra_reference_url'] == 'file:///temporary-old-reference.png'
    assert controls['character_snapshot'] is None
    assert captured[0]['route'] == route
    assert captured[0]['engine'] == 'reactor_inswapper'
    assert _state(bridge) == current_ui
    assert bridge._stage_three_engine == 'reactor_hyperswap'
    assert bridge._queued_route_override is None
    assert bridge._queued_character_override is None

    bridge._set_busy(False)
    QCoreApplication.processEvents()
    assert not bridge._queue_active
    assert bridge._active_stage_three_engine is None
    assert _state(bridge) == current_ui

    # A subsequent manual request must capture today's UI settings rather
    # than inheriting anything from the earlier queued job.
    bridge.queueGenerateAdvanced(*_args(prompt='manual after queue'))
    assert len(captured) == 2
    fresh = captured[-1]['controls']
    assert fresh['faceid_enabled'] is False
    assert fresh['faceid_strength'] == 0.35
    assert fresh['output_long_edge'] == 2560
    assert fresh['source_reference_megapixels'] == 0.3
    assert fresh['extra_reference_url'] == 'file:///current-next-reference.png'
    assert fresh['character_snapshot'] == chosen_character['value']
    assert bridge._next_generation_controls is None
    bridge._set_busy(False)
    QCoreApplication.processEvents()


def test_invalid_queued_request_does_not_leave_stale_generation_controls(monkeypatch, tmp_path):
    QCoreApplication.instance() or QCoreApplication([])
    bridge = cockpit.GenerationBridge()
    route = Route('LOCAL', '')
    bridge.backend_router = SimpleNamespace(mode='LOCAL', endpoint='', resolve=lambda model: route)
    bridge.setOutputTarget(3840)
    missing = (tmp_path/'does-not-exist.png').as_uri()
    bridge.enqueueGenerateAdvanced(*_args(source_url=missing))
    assert not bridge.busy
    assert not bridge._queue_active
    assert bridge.pendingGenerationCount == 0
    assert 'source image is unavailable' in bridge.status
    assert bridge._next_generation_controls is None
    assert bridge._queued_route_override is None
    assert bridge._queued_character_override is None


def test_queued_snapshot_restored_even_if_launch_throws(monkeypatch):
    QCoreApplication.instance() or QCoreApplication([])
    bridge = cockpit.GenerationBridge()
    bridge.backend_router = SimpleNamespace(mode='LOCAL', endpoint='', resolve=lambda model: Route('LOCAL',''))
    original_dispatch = bridge._dispatch_next_generation
    monkeypatch.setattr(bridge, '_dispatch_next_generation', lambda: None)
    bridge.setOutputTarget(3840)
    bridge.enqueueGenerateAdvanced(*_args())
    bridge.setOutputTarget(2560)
    before = _state(bridge)
    def launch_failure(*args):
        raise RuntimeError('synthetic launch failure')
    monkeypatch.setattr(bridge, 'queueGenerateAdvanced', launch_failure)
    try:
        original_dispatch()
    except RuntimeError:
        pass
    assert _state(bridge) == before
    assert bridge._queued_route_override is None
    assert bridge._queued_character_override is None
    assert not bridge.busy
    assert not bridge._queue_active
