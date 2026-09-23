"""Static route decisions never start a GPU service or submit a job."""
from unittest.mock import Mock
import pytest
from genesis.backend_routing import Route, choose_route, normalize_endpoint, remote_url, use_route


def test_endpoint_accepts_pod_id_and_rejects_embedded_credentials():
    assert normalize_endpoint('z58et1sa2stn1g') == 'https://z58et1sa2stn1g-8188.proxy.runpod.net'
    with pytest.raises(ValueError): normalize_endpoint('https://user:secret@pod.example')
    with pytest.raises(ValueError): normalize_endpoint('http://pod.example')


def test_auto_selects_ready_safe_local_then_remote():
    local = {'four-b'}
    remote = {'four-b', 'nine-b'}
    endpoint = 'https://pod.example'
    assert choose_route('AUTO', 'four-b', local, remote, True, True, endpoint).destination == 'LOCAL'
    assert choose_route('AUTO', 'four-b', local, remote, False, True, endpoint).destination == 'RUNPOD'
    assert choose_route('AUTO', 'nine-b', local, remote, True, True, endpoint, local_safe=False).destination == 'RUNPOD'
    with pytest.raises(ValueError, match='safety'):
        choose_route('LOCAL', 'nine-b', local, remote, True, True, endpoint, local_safe=False)
    with pytest.raises(ValueError, match='no ready'):
        choose_route('RUNPOD', 'nine-b', local, remote, True, False, endpoint)


def test_local_auto_does_not_start_offline_service(monkeypatch):
    import qt_cockpit
    from genesis import integrations
    monkeypatch.setattr(integrations, 'gpu_kernel_preflight', lambda: (True, 'safe'))
    monkeypatch.setattr(integrations, 'endpoint_online', lambda *args, **kwargs: False)
    start = Mock(side_effect=AssertionError('AUTO must not start local GPU'))
    monkeypatch.setattr(integrations, 'start_user_service', start)
    bridge = qt_cockpit.GenerationBridge()
    with use_route(Route('LOCAL', '', allow_start=False)):
        with pytest.raises(qt_cockpit.workflow_lab.ComfyError, match='went offline'):
            bridge._connect_comfyui()
    start.assert_not_called()


def test_route_is_job_scoped(monkeypatch):
    monkeypatch.setenv('GENESIS_COMFY_URL', 'https://legacy.example')
    with use_route(Route('LOCAL', '')):
        assert remote_url() == ''
    with use_route(Route('RUNPOD', 'https://new.example')):
        assert remote_url() == 'https://new.example'
    assert remote_url() == 'https://legacy.example'
