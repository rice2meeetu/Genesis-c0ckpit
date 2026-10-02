import json
from unittest.mock import Mock
import pytest
from genesis import runpod_cache_manager as manager


def test_queue_errors_and_missing_fields_fail_closed(monkeypatch):
    urlopen = Mock(side_effect=OSError('offline'))
    monkeypatch.setattr(manager.urllib.request, 'urlopen', urlopen)
    with pytest.raises(OSError):
        manager.queue_empty()
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read = Mock(return_value=b'{}')
    urlopen.side_effect = None
    urlopen.return_value = response
    with pytest.raises(RuntimeError, match='unknown'):
        manager.queue_empty()
    assert urlopen.call_args.args[0] == 'http://127.0.0.1:8188/queue'


def test_busy_job_prevents_staging_or_stop(monkeypatch, tmp_path):
    monkeypatch.setattr(manager, 'CACHE', tmp_path)
    monkeypatch.setattr(manager, 'current_pid', lambda: 123)
    monkeypatch.setattr(manager, 'queue_empty', lambda: False)
    stage = Mock()
    stop = Mock()
    monkeypatch.setattr(manager, 'stage', stage)
    monkeypatch.setattr(manager, 'stop_paul', stop)
    with pytest.raises(RuntimeError, match='idle'):
        manager.switch('aisha')
    stage.assert_not_called()
    stop.assert_not_called()


def test_activation_failure_restores_models_and_manifest(monkeypatch, tmp_path):
    monkeypatch.setattr(manager, 'CACHE', tmp_path)
    monkeypatch.setattr(manager, 'current_pid', lambda: 123)
    monkeypatch.setattr(manager, 'queue_empty', lambda: True)
    (tmp_path / 'models').mkdir()
    (tmp_path / 'models/old').write_text('original')
    (tmp_path / 'manifest.json').write_text('original manifest')
    staged = tmp_path / '.staging-test'
    (staged / 'models').mkdir(parents=True)
    (staged / 'models/new').write_text('replacement')
    (staged / 'manifest.json').write_text('replacement manifest')
    (staged / 'profile.json').write_text('{}')
    monkeypatch.setattr(manager, 'stage', lambda name: staged)
    stop = Mock()
    start = Mock(side_effect=[RuntimeError('not ready'), None])
    monkeypatch.setattr(manager, 'stop_paul', stop)
    monkeypatch.setattr(manager, 'start_paul', start)
    with pytest.raises(RuntimeError, match='not ready'):
        manager.switch('aisha')
    assert (tmp_path / 'models/old').read_text() == 'original'
    assert (tmp_path / 'manifest.json').read_text() == 'original manifest'
    assert not (tmp_path / 'profile.json').exists()
    assert start.call_count == 2
