"""Local SDXL pose readiness, fallback merge, graph, and QML regressions."""
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
import qt_cockpit as c
from genesis.backend_bridge import BackendBridge


def local_row(monkeypatch, tmp_path, installed=True):
    monkeypatch.setattr(c, 'MODEL_ROOTS', [tmp_path])
    if installed:
        asset = tmp_path / 'controlnet' / c.REMOTE_SDXL_POSE_CONTROLNET
        asset.parent.mkdir(); asset.touch()
    return c.build_generation_profiles({'profiles': [{
        'name': 'Donuts', 'ready': True,
        'evidence': {'MODEL': str(tmp_path / c.REMOTE_DONUTS_MODEL)}
    }]}, [])[0]


@pytest.mark.parametrize('installed', [True, False])
def test_local_pose_evidence_survives_configured_fallback(monkeypatch, tmp_path, installed):
    row = local_row(monkeypatch, tmp_path, installed)
    assert row['poseReady'] is installed
    bridge = BackendBridge(c.GenerationBridge())
    bridge._mode = 'LOCAL'; bridge._local_safe = True
    bridge._local_status = {'ready': True}; bridge._local = [row]
    events = []; bridge.profilesReady.connect(events.append)
    bridge._publish()
    published = next(r for r in events[-1] if r['model'] == c.REMOTE_DONUTS_MODEL)
    assert published['poseReady'] is installed
    assert published['destination'] == 'LOCAL'
    assert published['runnable'] and published['routeReady']


@pytest.mark.parametrize('catalog, expected', [
    ('installed', True),
    ('missing_apply_node', False),
    ('missing_model', False),
    ('timeout', False),
])
def test_local_pose_readiness_uses_live_catalog(monkeypatch, tmp_path, catalog, expected):
    row = local_row(monkeypatch, tmp_path)
    assert row['poseReady'] is True  # The filesystem fallback must be revalidated.
    monkeypatch.setattr(c, 'load_generation_profiles', lambda: [row])
    monkeypatch.setattr(c, 'load_runtime_status', lambda: {'ready': True, 'remote': False})
    monkeypatch.setattr(c.integrations, 'gpu_kernel_preflight', lambda: (True, 'safe'))
    info = {
        'ControlNetLoader': {'input': {'required': {
            'control_net_name': [[c.REMOTE_SDXL_POSE_CONTROLNET]]}}},
        'LoadImage': {}, 'ImageScale': {}, 'ControlNetApplyAdvanced': {},
    }
    if catalog == 'missing_apply_node':
        info.pop('ControlNetApplyAdvanced')
    elif catalog == 'missing_model':
        info['ControlNetLoader']['input']['required']['control_net_name'] = [['other.safetensors']]
    client = Mock()
    client.object_info.return_value = info
    if catalog == 'timeout':
        client.object_info.side_effect = TimeoutError('catalog unavailable')
    factory = Mock(return_value=client)
    monkeypatch.setattr(c.workflow_lab, 'ComfyClient', factory)
    received = Mock()

    BackendBridge._probe(SimpleNamespace(_received=received), 7, '')

    result = received.emit.call_args.args[0]
    assert result['local'][0]['poseReady'] is expected
    assert result['local'][0]['ready'] and result['local'][0]['runnable']
    assert result['local_status']['ready']
    assert result['local_safe']
    assert result['remote'] == []
    assert result['remote_status']['ready'] is False
    factory.assert_called_once_with(c.workflow_lab.COMFY_URL, timeout=8)
    client.object_info.assert_called_once_with()
    assert ('identityError' in result['local_status']) is (catalog == 'timeout')


def test_controlnet_conditions_both_sampler_inputs_and_preserves_latent():
    info = {'ControlNetLoader': {'input': {'required': {
        'control_net_name': [[c.REMOTE_SDXL_POSE_CONTROLNET]]}}}}
    prompt = {'5': {'inputs': {'latent_image': ['4', 0], 'denoise': 1.0}}}
    c.attach_sdxl_pose(prompt, info, {'subfolder': 'poses', 'name': 'skeleton.png'}, 832, 1024)
    assert prompt['genesis_pose_image']['inputs']['image'] == 'poses/skeleton.png'
    assert prompt['genesis_pose_scale']['inputs']['upscale_method'] == 'nearest-exact'
    assert prompt['genesis_pose_controlnet']['inputs']['control_net_name'] == c.REMOTE_SDXL_POSE_CONTROLNET
    assert prompt['5']['inputs'] == {'latent_image': ['4', 0], 'denoise': 1.0,
        'positive': ['genesis_pose_apply', 0], 'negative': ['genesis_pose_apply', 1]}
    with pytest.raises(c.workflow_lab.ComfyError, match='active ComfyUI'):
        c.attach_sdxl_pose({}, {}, {'name': 'skeleton.png'}, 832, 1024)


def test_generate_button_with_local_skeleton(tmp_path):
    script = r'''
import sys
from PyQt6.QtCore import QObject, QTimer, QUrl
from PyQt6.QtWidgets import QApplication
import qt_cockpit_linux_premium as launcher
import genesis.pose_workbench as workbench
from pathlib import Path
workbench.POSE_WORKBENCH_HANDOFF_FILE=Path(sys.argv[1])/'unused-handoff.json'
launcher.load_pose_items = lambda **kw: []
launcher.load_grok_preset_items = lambda: []
launcher.load_curated_pose_presets = lambda **kw: []
launcher.load_runtime_status = lambda **kw: {"identityEngines": []}
launcher.BackendBridge.start = lambda self: None
engines=[]; factory=launcher.QQmlApplicationEngine
launcher.QQmlApplicationEngine=lambda: (engines.append(factory()) or engines[-1])
def verify():
    try:
        w=engines[0].rootObjects()[0]
        row={"model":"donutsdeliverymixV4_v41.safetensors", "label":"Local Donuts",
             "runnable":True,"ready":True,"routeReady":True,"poseReady":True,
             "stageOneEligible":True,"sourceRequired":False,"loras":["None"]}
        w.setProperty('generationModel',[row])
        w.setProperty('useSourceImageMode',False)
        w.setProperty('selectedPoseSource',QUrl.fromLocalFile('/tmp/selected-skeleton.png'))
        QApplication.processEvents()
        b=w.findChild(QObject,'generateButton')
        assert w.property('modeInputsReady') and b.property('enabled')
        row['poseReady']=False; w.setProperty('generationModel',[dict(row)])
        QApplication.processEvents()
        assert not w.property('modeInputsReady') and not b.property('enabled')
        print('LOCAL_SDXL_POSE_QML_OK'); QApplication.instance().exit(0)
    except Exception:
        import traceback; traceback.print_exc(); QApplication.instance().exit(1)
class App(QApplication):
    def exec(self):
        QTimer.singleShot(200,verify); QTimer.singleShot(12000,lambda:self.exit(2))
        return super().exec()
launcher.QApplication=App
sys.argv=['local-pose-test','--page','create']
sys.exit(launcher.main())
'''
    runtime=tmp_path/'runtime'; runtime.mkdir(mode=0o700)
    env=dict(os.environ, QT_QPA_PLATFORM='offscreen', XDG_RUNTIME_DIR=str(runtime), XDG_CONFIG_HOME=str(tmp_path/"config"),
        QTWEBENGINE_DISABLE_SANDBOX='1', QT_QUICK_BACKEND='software',
        QSG_RHI_BACKEND='software', LIBGL_ALWAYS_SOFTWARE='1', GENESIS_RUNPOD_AUTOCONNECT='0')
    result=subprocess.run([sys.executable,'-c',script,str(tmp_path)],cwd=Path(c.__file__).parent,
        env=env,text=True,capture_output=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'LOCAL_SDXL_POSE_QML_OK' in result.stdout
