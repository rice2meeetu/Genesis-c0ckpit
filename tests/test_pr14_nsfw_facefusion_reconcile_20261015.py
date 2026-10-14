"""Local-only NSFW FaceFusion Stage 3 integration, no GPU/model/personal data."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from PIL import Image
from PyQt6.QtCore import QCoreApplication, QUrl
import pytest

import qt_cockpit as c
from genesis import integrations
from genesis.backend_routing import Route, use_route


def make_runtime(tmp_path):
    root = tmp_path / 'facefusion-nsfw-modern'
    ffpython = root / '.venv/bin/python'
    ffpython.parent.mkdir(parents=True)
    for file in (ffpython, root/'facefusion.py', root/'facefusion.ini'):
        file.write_text('synthetic runtime fixture')
    return root, ffpython


def make_bridge(monkeypatch, tmp_path):
    QCoreApplication.instance() or QCoreApplication([])
    b = c.GenerationBridge()
    root, py = make_runtime(tmp_path)
    monkeypatch.setattr(integrations, 'FACEFUSION_ROOT', root)
    b._output_dir = tmp_path/'outputs'
    b._stage_three_engine = 'facefusion_nsfw'
    return b, root, py


def test_strict_nsfw_runtime_path_and_stage_three_picker():
    assert len(integrations.FACEFUSION_ROOT_CANDIDATES) == 1
    assert integrations.FACEFUSION_ROOT_CANDIDATES[0].name == 'facefusion-nsfw-modern'
    qml = (c.PROJECT_ROOT/'genesis/qt_ui/MainPremiumLinux.qml').read_text()
    assert 'engine:"facefusion_nsfw", available:genesisBridge.faceFusionAvailable' in qml
    assert 'stageThreeEngine === "facefusion_nsfw" && genesisBridge.faceFusionAvailable' in qml


def test_local_facefusion_route_does_not_require_connected_comfyui(monkeypatch,tmp_path):
    b, root, ffpy=make_bridge(monkeypatch,tmp_path)
    b.backend_router = SimpleNamespace(resolve_operation=Mock(side_effect=ValueError('ComfyUI disconnected')))
    assert b.faceFusionAvailable
    route = b._person_a_face_swap_route()
    assert route.destination == 'LOCAL'
    b.backend_router.resolve_operation.assert_not_called()
    b._stage_three_engine = 'reactor_inswapper'
    with pytest.raises(ValueError,match='ComfyUI disconnected'):
        b._person_a_face_swap_route()


def test_finishing_identity_action_available_without_comfy_for_local_facefusion(monkeypatch,tmp_path):
    b,root,ffpy=make_bridge(monkeypatch,tmp_path)
    preview=tmp_path/'generated.png';Image.new('RGB',(32,32)).save(preview)
    master=tmp_path/'master.png';Image.new('RGB',(32,32)).save(master)
    b._preview=QUrl.fromLocalFile(str(preview)).toString()
    b._finish_info={'runtime_schema': {}}
    b.backend_router=SimpleNamespace(_connected=False,_remote_status={'ready':False},_local_safe=False,
                                      _local_status={'ready':False,'identityEngines':[]},_endpoint='')
    monkeypatch.setattr(b,'_identity_master',lambda _:master)
    assert b.finishingAvailability('',QUrl.fromLocalFile(str(master)).toString(),2)['identity'] is True


@pytest.mark.parametrize('provider', ['cpu','migraphx'])
def test_facefusion_stage_three_keeps_crops_local_and_preserves_original(monkeypatch,tmp_path,provider):
    b,root,ffpy=make_bridge(monkeypatch,tmp_path)
    b._facefusion_provider=provider
    source=tmp_path/'source.png'; target=tmp_path/'target.png'
    Image.new('RGB',(48,36),(25,25,25)).save(source)
    Image.new('RGB',(48,36),(40,40,40)).save(target)
    original=target.read_bytes()
    # Stage 3 must use the engine captured when a job was queued, even if the
    # user has since selected ReActor for a different job.
    b._stage_three_engine='reactor_inswapper'
    b._active_stage_three_engine='facefusion_nsfw'
    selected_region=object()
    regions=(selected_region,object())
    records=[]
    uploads=Mock(side_effect=AssertionError('No Comfy or RunPod connection is allowed'))
    monkeypatch.setattr(b,'_connect_comfyui',uploads)
    monkeypatch.setattr(integrations,'gpu_kernel_preflight',lambda:(True,'gpu-ok'))
    from genesis import person_a_targeting as pt
    def fake_crops(t,s,r,d):
        assert t==target and s==source and r==regions
        dc=Path(d)
        ct=dc/'target-crop.png'; cs=dc/'source-crop.png'
        Image.new('RGB',(16,16),(44,44,44)).save(ct)
        Image.new('RGB',(16,16),(22,22,22)).save(cs)
        return ct,cs
    monkeypatch.setattr(pt,'prepare_crops',fake_crops)
    def fake_composite(t,region,swapped,out):
        assert t==target and region is selected_region and swapped.name=='facefusion-result.png'
        out.parent.mkdir(parents=True,exist_ok=True)
        Image.open(t).save(out)
        records.append(('composite',out))
        return out
    monkeypatch.setattr(pt,'composite_crop',fake_composite)
    commands=[]
    def fake_run(command,**kw):
        commands.append((list(command),kw))
        assert '--source-paths' in command and '--target-path' in command
        assert source.as_posix() not in command and target.as_posix() not in command
        assert '--execution-providers' in command
        assert command[command.index('--execution-providers')+1]==provider
        assert Path(kw['cwd'])==root
        Image.new('RGB',(16,16),(90,90,90)).save(command[command.index('--output-path')+1])
        return SimpleNamespace(returncode=0,stdout='complete')
    monkeypatch.setattr(b,'_run_local_facefusion_command',fake_run)
    monkeypatch.setattr(b,'_record_finish',lambda *a,**k:records.append(('record',a,k)))
    monkeypatch.setattr(b,'_adopt_operation_result',lambda *a,**k:records.append(('adopt',a,k)))
    with use_route(Route('LOCAL','')):
        b._run_face_swap(target,source,regions)
    assert len(commands)==1 and commands[0][0][0]==str(ffpy)
    uploads.assert_not_called()
    assert target.read_bytes()==original and source.is_file()
    assert [r[0] for r in records]==['composite','adopt','record']
    assert 'reviewed Person A region' in b.status
    assert not b.busy


def test_failed_local_facefusion_does_not_composite_or_edit_original(monkeypatch,tmp_path):
    b,root,ffpy=make_bridge(monkeypatch,tmp_path)
    b._facefusion_provider='cpu'
    a=tmp_path/'a.png';t=tmp_path/'t.png'
    Image.new('RGB',(16,16)).save(a);Image.new('RGB',(16,16)).save(t)
    before=t.read_bytes()
    from genesis import person_a_targeting as pt
    monkeypatch.setattr(pt,'prepare_crops',lambda target,source,regions,d:(a,t))
    monkeypatch.setattr(pt,'composite_crop',Mock(side_effect=AssertionError('Must never composite a failed result')))
    monkeypatch.setattr(b,'_connect_comfyui',Mock(side_effect=AssertionError('No ComfyUI contact')))
    monkeypatch.setattr(b,'_run_local_facefusion_command',lambda *args,**kw:SimpleNamespace(returncode=1,stdout='failed'))
    with use_route(Route('LOCAL','')):
        b._run_face_swap(t,a,(object(),object()))
    assert t.read_bytes()==before
    assert 'Face swap failed' in b.status
    assert not b.busy


def test_stage_three_face_picker_pins_local_route_without_online_comfy(monkeypatch,tmp_path):
    b,root,ffpy=make_bridge(monkeypatch,tmp_path)
    b.backend_router=SimpleNamespace(resolve_operation=Mock(side_effect=ValueError('ComfyUI disconnected')))
    src=tmp_path/'source.png'; target=tmp_path/'target.png'
    Image.new('RGB',(24,24)).save(src);Image.new('RGB',(24,24)).save(target)
    seen=[]
    from genesis import person_a_targeting as pt
    class Region:
        def checked_image(self,photo): seen.append(('confirm',photo))
    monkeypatch.setattr(pt,'choose_face_region',lambda photo,label:Region())
    started=[]
    class FakeThread:
        def __init__(self,*a,**kw):started.append(kw)
        def start(self): pass
    monkeypatch.setattr(c.threading,'Thread',FakeThread)
    b._pending_stage_three=True
    b._set_busy(True)
    b._choose_stage_three_faces(str(target),str(src))
    assert [item[1] for item in seen] == [target, src]
    assert len(started)==1 and started[0]['args'][0].destination=='LOCAL'
    assert not b._pending_stage_three
    b._set_busy(False)
