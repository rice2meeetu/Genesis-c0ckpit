"""Automatic post-generation Stage 3 must honor a pinned local FaceFusion engine.

No live GPU workloads, ComfyUI networking or personal photos are involved.
"""
from pathlib import Path
from unittest.mock import Mock
from types import SimpleNamespace

import pytest
from PIL import Image
from PyQt6.QtCore import QCoreApplication

import qt_cockpit as c
from genesis.backend_routing import Route
from genesis import integrations


def runtime(monkeypatch, tmp_path):
    root=tmp_path/'facefusion-nsfw-modern'
    (root/'.venv/bin').mkdir(parents=True)
    for name in ['.venv/bin/python', 'facefusion.py', 'facefusion.ini']:
        (root/name).write_text('synthetic')
    monkeypatch.setattr(integrations,'FACEFUSION_ROOT',root)


def setup_generation(monkeypatch,tmp_path):
    QCoreApplication.instance() or QCoreApplication([])
    b=c.GenerationBridge()
    b._output_dir=tmp_path
    original=tmp_path/'original.png'; result=tmp_path/'generated.png'
    Image.new('RGB',(32,32),(60,60,60)).save(original)
    Image.new('RGB',(32,32),(80,80,80)).save(result)
    client=Mock()
    monkeypatch.setattr(b,'_connect_comfyui',lambda:(client,{}))
    monkeypatch.setattr(c,'remote_url',lambda:'https://unit-test.invalid')
    monkeypatch.setattr(c,'load_remote_catalog',lambda *args,**kw:{})
    monkeypatch.setattr(c,'validate_remote_workflow_assets',lambda *a,**kw:None)
    monkeypatch.setattr(b,'_run_reference_stage',lambda *a,**kw:result)
    b.backend_router=SimpleNamespace(resolve_operation=Mock(side_effect=ValueError('local ReActor backend offline')))
    signals=[]
    b.stageThreeSelectionRequired.disconnect(b._choose_stage_three_faces)
    b.stageThreeSelectionRequired.connect(lambda *a:signals.append(a))
    return b,original,result,signals,client


def generate(b,original):
    # Real queueGenerate sets Busy before its worker enters _run_generate.
    b._set_busy(True)
    return b._run_generate('a neutral portrait','',512,768,c.REMOTE_PHR00T_V22_GGUF_MODEL,
            'None','None','None',0.0,0.0,0.0,original,None,
            False,True,False,{'seed':4,'steps':4})


def test_saved_generation_keeps_facefusion_stage3_when_local_reactor_is_offline(monkeypatch,tmp_path):
    runtime(monkeypatch,tmp_path)
    b,original,result,signals,client=setup_generation(monkeypatch,tmp_path)
    b._active_stage_three_engine='facefusion_nsfw'
    b._stage_three_engine='reactor_inswapper'  # newer UI selection must not replace queued job
    assert b.faceFusionAvailable is True
    assert generate(b,original)==result
    assert signals==[(str(result),str(original))]
    assert b._pending_stage_three and b.busy
    assert 'confirm Person A' in b.status
    b.backend_router.resolve_operation.assert_not_called()
    b.cancelGeneration()
    assert not b.busy and not b._pending_stage_three


def test_reactor_only_generation_still_fails_closed_if_local_route_unavailable(monkeypatch,tmp_path):
    runtime(monkeypatch,tmp_path)
    b,original,result,signals,client=setup_generation(monkeypatch,tmp_path)
    b._active_stage_three_engine='reactor_inswapper'
    assert generate(b,original)==result
    assert not signals and not b._pending_stage_three and not b.busy
    assert 'Stage 3 skipped: local ReActor backend offline' in b.status
    b.backend_router.resolve_operation.assert_called_once_with('face_swap')


def test_failed_person_a_thread_start_releases_busy_and_preserves_saved_image(monkeypatch,tmp_path):
    runtime(monkeypatch,tmp_path)
    b,original,result,_,_=setup_generation(monkeypatch,tmp_path)
    b._active_stage_three_engine='facefusion_nsfw'
    b._stage_three_engine='reactor_inswapper'
    b._pending_stage_three=True
    b._set_busy(True)
    from genesis import person_a_targeting
    selected=[]
    class Region:
        def checked_image(self,path):selected.append(Path(path))
    monkeypatch.setattr(person_a_targeting,'choose_face_region',lambda *a:Region())
    class FailStart:
        def __init__(self,*args,**kwargs):pass
        def start(self):raise RuntimeError('simulated thread resource exhaustion')
    monkeypatch.setattr(c.threading,'Thread',FailStart)
    b._choose_stage_three_faces(str(result),str(original))
    assert selected==[result,original]
    assert not b._pending_stage_three and not b.busy
    assert 'Stage 3 selection failed' in b.status
    assert 'simulated thread resource exhaustion' in b.status
    assert result.is_file() and original.is_file()
    b.backend_router.resolve_operation.assert_not_called()
