"""Regression cases for PR13 review #5522485587; no GPU inference."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image
from PyQt6.QtCore import QUrl

import qt_cockpit as c
from genesis.backend_bridge import BackendBridge
from genesis.backend_routing import Route, use_route
from genesis.character_library import (
    add_reference, get_character, preferred_reference, reference_is_approved,
    save_character, set_reference_details, update_reference,
)


def image(tmp_path, name):
    path = tmp_path / name
    Image.new('RGB', (32, 32), 'white').save(path)
    return path


@pytest.mark.parametrize('mode', ['AUTO', 'RUNPOD', 'LOCAL'])
def test_face_swap_fails_closed_without_safe_local_backend(mode):
    bridge = BackendBridge(c.GenerationBridge())
    bridge._mode = mode
    bridge._endpoint = 'https://remote-8189.proxy.runpod.net'
    bridge._connected = True
    bridge._remote_status = {'ready': True}
    bridge._local_safe = False
    bridge._local_status = {'ready': False}
    with pytest.raises(ValueError, match='local-only'):
        bridge.resolve_operation('face_swap')
    bridge._local_safe = True
    bridge._local_status['ready'] = True
    route = bridge.resolve_operation('face_swap')
    assert route == Route('LOCAL', '')
    assert bridge.resolve_operation('edit').destination == ('RUNPOD' if mode == 'RUNPOD' else 'LOCAL')


def test_face_swap_rejects_even_mocked_remote_routing_before_face_dialog(tmp_path, monkeypatch):
    b = c.GenerationBridge()
    b.backend_router = SimpleNamespace(resolve_operation=lambda op: Route('RUNPOD', 'https://remote.example'))
    selector = Mock(side_effect=AssertionError('No user face dialog should open'))
    monkeypatch.setattr('genesis.person_a_targeting.choose_face_region', selector)
    path = image(tmp_path, 'safe.png')
    b.queueFaceSwap(QUrl.fromLocalFile(str(path)).toString(), QUrl.fromLocalFile(str(path)).toString())
    assert 'local-only' in b.status
    selector.assert_not_called()
    assert not b.busy


def test_direct_face_swap_worker_never_uploads_to_remote(tmp_path, monkeypatch):
    b = c.GenerationBridge()
    connect = Mock(side_effect=AssertionError('remote connection must not open'))
    monkeypatch.setattr(b, '_connect_comfyui', connect)
    path = image(tmp_path, 'target.png')
    with use_route(Route('RUNPOD', 'https://remote.example')):
        b._run_face_swap(path, path, (Mock(), Mock()))
    connect.assert_not_called()
    assert 'local-only' in b.status


def test_stage_three_refuses_remote_only_backend_without_face_dialog(tmp_path, monkeypatch):
    b = c.GenerationBridge()
    b.backend_router = SimpleNamespace(resolve_operation=lambda op: (_ for _ in ()).throw(ValueError('Face swapping is local-only')))
    b._set_busy(True)
    b._pending_stage_three = True
    target = image(tmp_path, 'generated.png')
    source = image(tmp_path, 'source.png')
    selector = Mock(side_effect=AssertionError('No face dialog without local backend'))
    monkeypatch.setattr('genesis.person_a_targeting.choose_face_region', selector)
    b._choose_stage_three_faces(str(target), str(source))
    assert 'local-only' in b.status and 'Stage 3' in b.status
    assert not b.busy and not b._pending_stage_three
    selector.assert_not_called()
    assert target.is_file()


def test_queued_stage_three_engine_snapshot_and_busy_lock(monkeypatch):
    b = c.GenerationBridge()
    b.backend_router = SimpleNamespace(mode='LOCAL', endpoint='', resolve=lambda m: Route('LOCAL', ''))
    original_dispatch = b._dispatch_next_generation
    monkeypatch.setattr(b, '_dispatch_next_generation', lambda: None)
    args = ('portrait', '', 512, 512, c.FOUR_B_MODEL, 'None', 'None', '', '',
            False, True, False, 4, 1.0, -1, 1.0, 'euler', 'simple',
            'None', 0.5, 0.5, 0.5)
    b.setStageThreeEngine('reactor_inswapper')
    b.enqueueGenerateAdvanced(*args)
    assert b._pending_generations[0]['stage3_engine'] == 'reactor_inswapper'
    b.setStageThreeEngine('reactor_hyperswap')
    observed = []
    monkeypatch.setattr(b, 'queueGenerateAdvanced', lambda *unused: observed.append(b._active_stage_three_engine))
    original_dispatch()
    assert observed == ['reactor_inswapper']
    assert b._stage_three_engine == 'reactor_hyperswap'  # UI choice remains unchanged
    b._set_busy(True)
    b.setStageThreeEngine('reactor_reswapper')
    assert b._stage_three_engine == 'reactor_hyperswap'
    b._set_busy(False)
    b._queue_busy_transition()
    assert b._active_stage_three_engine is None


def test_new_character_reference_pending_and_approved_only_after_review(tmp_path):
    idx = tmp_path / 'characters.json'
    master, candidate = image(tmp_path, 'master.png'), image(tmp_path, 'candidate.png')
    row = save_character('Character A', str(master), adult_confirmed=True, path=idx)
    add_reference(row['id'], str(candidate), role='Profile', path=idx)
    saved = get_character(row['id'], idx)
    assert saved['reference_approved'][str(candidate)] is False
    assert not reference_is_approved(saved, str(candidate))
    assert preferred_reference(row['id'], 'Profile', idx) == str(master)
    set_reference_details(row['id'], str(candidate), 'face', True, path=idx)
    assert preferred_reference(row['id'], 'Profile', idx) == str(candidate)


def test_replacing_approved_reference_requires_fresh_approval(tmp_path):
    idx = tmp_path / 'characters.json'
    master, old, new = (image(tmp_path, name) for name in ('master.png', 'old.png', 'new.png'))
    row = save_character('A', str(master), adult_confirmed=True, path=idx)
    add_reference(row['id'], str(old), role='Profile', category='face', approved=True, path=idx)
    assert reference_is_approved(get_character(row['id'], idx), str(old))
    update_reference(row['id'], str(old), str(new), path=idx)
    saved = get_character(row['id'], idx)
    assert saved['reference_approved'][str(new)] is False
    assert not reference_is_approved(saved, str(new))
    assert str(old) not in saved.get('reference_approved', {})
    assert saved['reference_categories'][str(new)] == 'face'
    assert preferred_reference(row['id'], 'Profile', idx) == str(master)
    set_reference_details(row['id'], str(new), 'face', True, path=idx)
    assert preferred_reference(row['id'], 'Profile', idx) == str(new)


def test_master_replacement_needs_explicit_confirmation(tmp_path):
    idx = tmp_path / 'characters.json'
    master, new = image(tmp_path, 'master.png'), image(tmp_path, 'new.png')
    row = save_character('A', str(master), adult_confirmed=True, path=idx)
    with pytest.raises(ValueError, match='explicit confirmation'):
        update_reference(row['id'], str(master), str(new), path=idx)
    assert get_character(row['id'], idx)['primary_image'] == str(master)
    approved = update_reference(row['id'], str(master), str(new), confirm_master=True, path=idx)
    assert approved['primary_image'] == str(new)
    assert reference_is_approved(approved, str(new))


def test_existing_legacy_references_still_readable_without_modifying_flags(tmp_path):
    idx = tmp_path / 'characters.json'
    master, legacy, new = (image(tmp_path, name) for name in ('master.png', 'legacy.png', 'new.png'))
    row = save_character('A', str(master), adult_confirmed=True, path=idx)
    payload = json.loads(idx.read_text())
    payload['characters'][0]['references'].append(str(legacy))
    payload['characters'][0]['reference_roles'] = {str(legacy): 'Profile'}
    idx.write_text(json.dumps(payload))
    assert reference_is_approved(get_character(row['id'], idx), str(legacy))
    add_reference(row['id'], str(new), role='Profile', path=idx)
    saved = get_character(row['id'], idx)
    assert reference_is_approved(saved, str(legacy))
    assert not reference_is_approved(saved, str(new))
