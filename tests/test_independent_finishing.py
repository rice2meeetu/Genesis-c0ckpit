"""Offline finishing routing tests; no image decoding or GPU submission."""
from pathlib import Path
from unittest.mock import Mock
import pytest
from PyQt6.QtCore import QUrl
import qt_cockpit as c
from genesis.finishing import finishing_plan, run_finishing
from genesis.backend_routing import Route, normalize_endpoint

CASES = [(True,False,0), (False,True,0), (False,False,2),
         (True,True,0), (True,False,4), (False,True,2), (True,True,4)]

@pytest.mark.parametrize('refine,identity,scale', CASES)
def test_each_supported_finish_combination_keeps_master_and_intermediates(tmp_path, monkeypatch, refine, identity, scale):
    selected = tmp_path/'selected.png'; selected.write_bytes(b'selected untouched')
    master = tmp_path/'master.png'; master.write_bytes(b'master untouched')
    bridge = c.GenerationBridge()
    bridge._original_master = master
    bridge._upscale_model = "4x-UltraSharp.pth"
    bridge._finish_route = Route('RUNPOD', 'https://offline-8189.proxy.runpod.net')
    bridge._finish_info = {'catalog': True}
    bridge._set_preview(QUrl.fromLocalFile(str(selected)).toString())
    client=Mock(); client.upload_image.side_effect=lambda path: {'name': path.name}
    monkeypatch.setattr(bridge, '_connect_comfyui', lambda: (client, {}))
    monkeypatch.setattr(bridge, 'finishingAvailability', lambda *args: dict(refine=True,identity=True,upscale=True,reason=''))
    calls=[]
    def output(stage, current, identity_source=None):
        calls.append((stage,current,identity_source))
        path=tmp_path/(stage+'.png');path.write_bytes(stage.encode());return path
    monkeypatch.setattr(bridge, '_refine_result', lambda client,info,current,*args: output('refine', current))
    monkeypatch.setattr(bridge, '_run_reference_stage', lambda client,info,workflow,current,*args,**kwargs: output('identity',current,kwargs['secondary_image']))
    monkeypatch.setattr(c, 'validate_operation_prompt', lambda *args: None)
    def upscale(client,graph,*args):
        assert graph['2']['inputs']['model_name'] == '4x-UltraSharp.pth'
        assert graph['4']['inputs']['scale_by'] == scale / 4
        return output('upscale',client.upload_image.call_args.args[0])
    monkeypatch.setattr(bridge, '_submit_and_save', upscale)
    bridge._run_finish(selected,master,finishing_plan(refine,identity,scale),scale,c.REMOTE_MIRACLEIN_9B_MODEL,'None',0)
    assert [x[0] for x in calls] == finishing_plan(refine,identity,scale)
    for previous, following in zip(calls, calls[1:]):
        assert following[1] == tmp_path/(previous[0]+'.png')
    assert selected.read_bytes()==b'selected untouched'
    assert master.read_bytes()==b'master untouched'
    for stage,current,identity_source in calls:
        if stage=='identity': assert identity_source == master
    assert len(bridge.finishingResults)==len(calls)
    assert not bridge.busy


def test_stage3_does_not_require_stage2():
    assert finishing_plan(False,True,0)==['identity']


def test_original_master_cannot_be_replaced_by_selected_preview(tmp_path):
    bridge=c.GenerationBridge(); master=tmp_path/'master'; master.write_bytes(b'original')
    bridge._original_master=master
    bridge._set_preview(QUrl.fromLocalFile(str(tmp_path/'refined')).toString())
    assert bridge._identity_master(bridge.previewUrl)==master


def test_missing_capability_blocks_queue_before_worker(monkeypatch,tmp_path):
    bridge=c.GenerationBridge();thread=Mock();monkeypatch.setattr(c.threading,'Thread',thread)
    monkeypatch.setattr(bridge,'finishingAvailability',lambda *args: dict(refine=False,identity=False,upscale=False,reason='Missing node or asset'))
    bridge.queueFinish(False,True,0,'',c.REMOTE_MIRACLEIN_9B_MODEL,'None',0)
    assert 'Missing node or asset' in bridge.status
    thread.assert_not_called()


def test_failed_stage_preserves_successful_intermediate(tmp_path):
    selected=tmp_path/'selected';selected.write_bytes(b's');master=tmp_path/'master';master.write_bytes(b'm')
    refined=tmp_path/'refined';records=[]
    def execute(stage,current,identity):
        if stage=='identity': raise ValueError('backend unavailable')
        refined.write_bytes(b'r');return refined
    with pytest.raises(ValueError,match='backend unavailable'):
        run_finishing(selected,master,['refine','identity'],execute,lambda stage,path:records.append(path))
    assert records==[refined] and selected.exists() and master.exists()

@pytest.mark.parametrize('url',['https://abcdefghij-8188.proxy.runpod.net','http://127.0.0.1:8188'])
def test_brothers_endpoint_blocked(url):
    with pytest.raises(ValueError,match='8189'):normalize_endpoint(url)


def test_bare_pod_id_uses_user_8189():
    assert normalize_endpoint('abcdefghij')=='https://abcdefghij-8189.proxy.runpod.net'


def test_refine_choices_exclude_obsolete_models():
    assert c.REFINEMENT_MODELS
    assert all('lustify' not in x.lower() and 'juggernaut' not in x.lower() for x in c.REFINEMENT_MODELS)
    assert c.REMOTE_DONUTS_MODEL in c.REFINEMENT_MODELS


def test_missing_upscale_model_keeps_action_disabled(tmp_path):
    bridge=c.GenerationBridge();source=tmp_path/'result';source.write_bytes(b'result')
    bridge._set_preview(QUrl.fromLocalFile(str(source)).toString())
    bridge._finish_info={name:{} for name in ['LoadImage','UpscaleModelLoader','ImageUpscaleWithModel','ImageScaleBy','SaveImage']}
    assert not bridge.finishingAvailability(c.REMOTE_MIRACLEIN_9B_MODEL,'',2)['upscale']


def test_character_a_references_component_loads_without_photos():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from PyQt6.QtQml import QQmlEngine, QQmlComponent
    engine=QQmlEngine();component=QQmlComponent(engine,QUrl.fromLocalFile(str(c.PROJECT_ROOT/'genesis/qt_ui/CharacterReferences.qml')))
    obj=component.createWithInitialProperties({'bridge':c.GenerationBridge(),'privatePreview':True})
    assert obj is not None, [error.toString() for error in component.errors()]
    assert obj.property('privatePreview') is True


def test_modern_combo_upscale_weights_enable_supported_action(tmp_path):
    bridge=c.GenerationBridge();source=tmp_path/'result';source.write_bytes(b'result')
    bridge._set_preview(QUrl.fromLocalFile(str(source)).toString())
    bridge._finish_info={name:{} for name in ['LoadImage','UpscaleModelLoader','ImageUpscaleWithModel','ImageScaleBy','SaveImage']}
    bridge._finish_info['UpscaleModelLoader']={'input':{'required':{'model_name':['COMBO',{'options':['4x-UltraSharp.pth']}]}}}
    assert bridge.finishingAvailability(c.REMOTE_MIRACLEIN_9B_MODEL,'',2)['upscale']
    assert bridge._upscale_model == '4x-UltraSharp.pth'


def test_reject_selects_previous_without_deleting_files(tmp_path):
    bridge=c.GenerationBridge();before=tmp_path/'before';after=tmp_path/'after'
    before.write_bytes(b'before');after.write_bytes(b'after')
    bridge._record_finish('Generated',before);bridge._record_finish('Refine',after)
    bridge.rejectFinishingResult()
    assert bridge.previewUrl == QUrl.fromLocalFile(str(before)).toString()
    assert before.exists() and after.exists()


def test_history_selection_recovers_its_untouched_identity_source(tmp_path):
    bridge=c.GenerationBridge()
    first=tmp_path/'first-master';first.write_bytes(b'first')
    second=tmp_path/'second-master';second.write_bytes(b'second')
    first_result=tmp_path/'first-result';first_result.write_bytes(b'result')
    second_result=tmp_path/'second-result';second_result.write_bytes(b'result2')
    bridge._original_master=first;bridge._record_finish('Generated',first_result)
    bridge._original_master=second;bridge._record_finish('Generated',second_result)
    bridge.selectFinishingResult(QUrl.fromLocalFile(str(first_result)).toString())
    assert bridge._identity_master()==first
    bridge.selectFinishingResult(QUrl.fromLocalFile(str(second_result)).toString())
    assert bridge._identity_master()==second
    assert first.read_bytes()==b'first' and second.read_bytes()==b'second'


def test_repository_tunnel_targets_only_genesis_8189():
    root=Path(__file__).resolve().parents[1]
    helper=(root/'scripts/ensure-runpod-8189-tunnel.sh').read_text()
    unit=(root/'systemd/genesis-runpod-tunnel.service').read_text()
    assert '-L 127.0.0.1:18189:127.0.0.1:8189' in helper
    assert '-L 127.0.0.1:18189:127.0.0.1:8189' in unit
    assert ':127.0.0.1:8188' not in helper+unit
