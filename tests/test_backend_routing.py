"""Static route decisions never start a GPU service or submit a job."""
from unittest.mock import Mock
import pytest
from genesis.backend_routing import Route, choose_route, normalize_endpoint, remote_url, use_route


def test_endpoint_accepts_pod_id_and_rejects_embedded_credentials():
    assert normalize_endpoint('z58et1sa2stn1g') == 'https://z58et1sa2stn1g-8189.proxy.runpod.net'
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


@pytest.mark.parametrize("model_name", ["QWEN_MODEL", "QWEN21_MODEL"])
def test_verified_qwen_is_local_but_still_obeys_fault_guard(model_name):
    import qt_cockpit
    from genesis.backend_bridge import BackendBridge
    bridge = object.__new__(type("RouteProbe", (), {"resolve": BackendBridge.resolve}))
    model = getattr(qt_cockpit, model_name)
    bridge._mode = "LOCAL"
    bridge._local = [{"model": model, "runnable": True}]
    bridge._remote = []
    bridge._local_status = {"ready": True}
    bridge._remote_status = {}
    bridge._endpoint = ""
    bridge._local_safe = True
    assert bridge.resolve(model).destination == "LOCAL"
    bridge._local_safe = False
    with pytest.raises(ValueError, match="safety"):
        bridge.resolve(model)


@pytest.mark.parametrize('endpoint', ['http://127.0.0.1:18189',
    'http://localhost:8189', 'https://pod-8189.proxy.runpod.net'])
def test_explicit_b2_endpoint_is_accepted(endpoint):
    assert normalize_endpoint(endpoint) == endpoint


def test_new_runpod_environment_takes_precedence(monkeypatch):
    monkeypatch.setenv('GENESIS_RUNPOD_URL', 'https://paul-8189.proxy.runpod.net')
    monkeypatch.setenv('GENESIS_COMFY_URL', 'http://127.0.0.1:18189')
    assert remote_url() == 'https://paul-8189.proxy.runpod.net'


def test_remote_identity_engines_fail_closed_without_reactor():
    from genesis.backend_bridge import remote_identity_engines
    assert remote_identity_engines({}) == []
    assert remote_identity_engines({'SomeFaceNode': {'input': {}}}) == []


def test_remote_identity_engines_require_advertised_swap_weights():
    from genesis.backend_bridge import remote_identity_engines
    info = {'ReActorFaceSwapOpt': {'input': {'required': {'swap_model': [[
        'inswapper_128.onnx', 'hyperswap_1a_256.onnx'
    ]]}}}, 'ReActorOptions': {}, 'LoadImage': {}, 'SaveImage': {}}
    assert remote_identity_engines(info) == ['reactor_inswapper', 'reactor_hyperswap']
    assert remote_identity_engines({'ReActorFaceSwap': info['ReActorFaceSwapOpt']}) == []
    for missing in ('ReActorFaceSwapOpt', 'ReActorOptions', 'LoadImage', 'SaveImage'):
        assert remote_identity_engines({k: v for k,v in info.items() if k != missing}) == []


@pytest.mark.parametrize("ready, outcome, expected", [
    (True, "installed", ["reactor_inswapper"]),
    (True, "missing", []),
    (True, "error", []),
    (False, "installed", []),
])
def test_local_probe_publishes_identity_without_remote_contact(monkeypatch, ready, outcome, expected):
    from types import SimpleNamespace
    import qt_cockpit as cockpit
    from genesis.backend_bridge import BackendBridge
    rows = [{"model": "existing", "runnable": True}]
    monkeypatch.setattr(cockpit, "load_generation_profiles", lambda: rows)
    monkeypatch.setattr(cockpit, "load_runtime_status", lambda: {"ready": ready, "remote": False})
    monkeypatch.setattr(cockpit.integrations, "gpu_kernel_preflight", lambda: (True, "safe"))
    info = {"ReActorFaceSwapOpt": {"input": {"required": {
        "swap_model": [["inswapper_128.onnx"]]}}},
        "ReActorOptions": {}, "LoadImage": {}, "SaveImage": {}} if outcome == "installed" else {}
    client = Mock()
    client.object_info.return_value = info
    if outcome == "error":
        client.object_info.side_effect = RuntimeError("catalog unavailable")
    factory = Mock(return_value=client)
    monkeypatch.setattr(cockpit.workflow_lab, "ComfyClient", factory)
    received = Mock()
    BackendBridge._probe(SimpleNamespace(_received=received), 7, "")
    result = received.emit.call_args.args[0]
    assert result["local"] == rows
    assert result["local_status"]["ready"] == ready
    assert result["local_status"]["identityEngines"] == expected
    assert result["local_status"]["identityReady"] == bool(expected)
    assert result["remote"] == []
    if ready:
        factory.assert_called_once_with(cockpit.workflow_lab.COMFY_URL, timeout=8)
    else:
        factory.assert_not_called()
    assert ("identityError" in result["local_status"]) == (ready and outcome == "error")
