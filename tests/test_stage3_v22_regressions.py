"""Stage 3 only runs after save and explicit face confirmation; v22 is v22."""
from pathlib import Path
from unittest.mock import Mock

import pytest
from PIL import Image
from PyQt6.QtCore import QCoreApplication
import qt_cockpit as c
from genesis.person_a_targeting import FaceRegion, image_snapshot


def pic(p):
    Image.new('RGB',(256,256),'white').save(p)
    return p


def patched_generation(monkeypatch,tmp_path,model,stage3):
    source=pic(tmp_path/'source.png')
    result=pic(tmp_path/'generated.png')
    bridge=c.GenerationBridge();bridge._output_dir=tmp_path
    bridge._finish_route=None
    client=Mock()
    monkeypatch.setattr(bridge,'_connect_comfyui',lambda:(client,{}))
    monkeypatch.setattr(c,'remote_url',lambda:'https://placeholder.example')
    schema = {'ReActorFaceSwapOpt': {'input': {'required': {'swap_model': [['inswapper_128.onnx']]}}},
              'ReActorOptions': {'input': {'required': {}}}}
    monkeypatch.setattr(c,'load_remote_catalog',lambda *a,**k:schema)
    monkeypatch.setattr(c,'validate_remote_workflow_assets',lambda *a,**k:None)
    calls=[]
    monkeypatch.setattr(bridge,'_run_reference_stage',lambda client,info,workflow,input_image,text,stamp,stage,**kwargs:(calls.append((stage,workflow,kwargs.get('model_override'))) or result))
    signals=[]
    bridge.stageThreeSelectionRequired.disconnect(bridge._choose_stage_three_faces)
    bridge.stageThreeSelectionRequired.connect(lambda *args:signals.append(args))
    bridge._set_busy(True)
    returned=bridge._run_generate('adult woman fully clothed','',512,768,model,'None','None','None',0,0,0,source,None,False,stage3,False,{'seed':9,'steps':4})
    return bridge,returned,signals,calls,source,result


def test_v22_uses_exact_checkpoint_and_label(monkeypatch,tmp_path):
    bridge,result,signals,calls,source,expected=patched_generation(monkeypatch,tmp_path,c.REMOTE_PHR00T_V22_GGUF_MODEL,False)
    assert result==expected
    assert calls==[('Phr00t-v22-GGUF',c.STAGE_1_WORKFLOW,c.REMOTE_PHR00T_V22_GGUF_MODEL)]
    assert not signals
    assert bridge.status.startswith('Complete')


def test_v23_still_reports_v23(monkeypatch,tmp_path):
    bridge,result,_,calls,_,_=patched_generation(monkeypatch,tmp_path,c.REMOTE_PHR00T_V23_GGUF_MODEL,False)
    assert calls[0][0]=='Phr00t-v23-GGUF'
    assert calls[0][2]==c.REMOTE_PHR00T_V23_GGUF_MODEL


def test_stage3_is_deferred_not_aborted_or_index_zero(monkeypatch,tmp_path):
    bridge,result,signals,calls,source,expected=patched_generation(monkeypatch,tmp_path,c.REMOTE_PHR00T_V22_GGUF_MODEL,True)
    assert result==expected and result.is_file()
    assert calls==[('Phr00t-v22-GGUF',c.STAGE_1_WORKFLOW,c.REMOTE_PHR00T_V22_GGUF_MODEL)]
    assert signals==[(str(expected),str(source))]
    assert bridge.busy and bridge._pending_stage_three
    assert 'confirm Person A' in bridge.status


def test_stage3_cancel_keeps_result_and_releases_queue(monkeypatch,tmp_path):
    bridge,result,signals,calls,source,_=patched_generation(monkeypatch,tmp_path,c.REMOTE_PHR00T_V22_GGUF_MODEL,True)
    monkeypatch.setattr('genesis.person_a_targeting.choose_face_region',lambda *args:None)
    bridge._choose_stage_three_faces(*signals[0])
    assert result.exists()
    assert not bridge.busy and not bridge._pending_stage_three
    assert 'skipped' in bridge.status


def test_stage3_manual_target_source_review_and_route(monkeypatch,tmp_path):
    bridge,result,signals,calls,source,_=patched_generation(monkeypatch,tmp_path,c.REMOTE_PHR00T_V22_GGUF_MODEL,True)
    picked=[]
    def choose(path,role):
        picked.append((path,role));return FaceRegion(image_snapshot(path)[1],(32,32,150,150))
    monkeypatch.setattr('genesis.person_a_targeting.choose_face_region',choose)
    routed=[]
    def route(route,op,*args):
        routed.append((route,op,args))
        bridge._set_busy(False)
    monkeypatch.setattr(bridge,'_run_routed_operation',route)
    class SynchronousThread:
        def __init__(self,target,args,daemon):self.target=target;self.args=args
        def start(self):self.target(*self.args)
    monkeypatch.setattr(c.threading,'Thread',SynchronousThread)
    bridge._choose_stage_three_faces(*signals[0])
    assert len(picked)==2 and picked[0][0]==result and picked[1][0]==source
    assert routed and routed[0][1]==bridge._run_face_swap
    # Stage 3 remains LOCAL even when its Stage 1 image came from RunPod.
    from genesis.backend_routing import Route
    assert routed[0][0] == Route('LOCAL', '')
    target_region,source_region=routed[0][2][-1]
    assert target_region.checked_image(result) and source_region.checked_image(source)
    assert not bridge.busy


def test_finish_button_enabled_only_for_verified_manual_reactor(tmp_path):
    from PyQt6.QtCore import QUrl
    b=c.GenerationBridge()
    source=pic(tmp_path/'master.png');output=pic(tmp_path/'finished.png')
    b._original_master=source
    b._set_preview(QUrl.fromLocalFile(str(output)).toString())
    b._finish_info={'ReActorFaceSwapOpt':{'input':{'required':{'swap_model':[['inswapper_128.onnx']]}}},
                    'ReActorOptions':{'input':{'required':{}}},'LoadImage':{}}
    enabled=b.finishingAvailability(c.REMOTE_DONUTS_MODEL,'',2)
    assert enabled['identity'] and not enabled['upscale']
    b._stage_three_engine='reactor_hyperswap'
    disabled=b.finishingAvailability(c.REMOTE_DONUTS_MODEL,'',2)
    assert not disabled['identity']
    b._stage_three_engine='reactor_inswapper'
    b._original_master=None
    assert not b.finishingAvailability(c.REMOTE_DONUTS_MODEL,'',2)['identity']


def test_manual_person_a_face_swap_preserves_all_pixels_outside_target_box(monkeypatch,tmp_path):
    from genesis.backend_routing import Route,use_route
    import qt_cockpit as cockpit
    target=tmp_path/'two_people.png'
    source=tmp_path/'source.png'
    img=Image.new('RGB',(500,300),'blue')
    Image.new('RGB',(250,300),'yellow').save(tmp_path/'part.png')
    with Image.open(tmp_path/'part.png') as part:img.paste(part,(250,0))
    img.save(target)
    pic(source)
    region=FaceRegion(image_snapshot(target)[1],(40,40,180,180))
    srcregion=FaceRegion(image_snapshot(source)[1],(50,50,200,200))
    b=c.GenerationBridge();b._output_dir=tmp_path
    client=Mock()
    client.upload_image.side_effect=lambda p:{'name':Path(p).name,'subfolder':'genesis'}
    client.object_info.return_value={'ReActorFaceSwapOpt': {'input': {'required': {'swap_model':[['inswapper_128.onnx']]}}},
                                    'ReActorOptions': {'input': {'required': {}}}}
    monkeypatch.setattr(b,'_connect_comfyui',lambda:(client,{}))
    monkeypatch.setattr(c,'validate_operation_prompt',lambda *a:None)
    def fake_reactor(client,graph,*args):
        assert graph['swap']['class_type']=='ReActorFaceSwapOpt'
        assert graph['swap']['inputs']['swap_model']=='inswapper_128.onnx'
        cropped=tmp_path/'swapped_crop.png'
        Image.new('RGB',(140,140),'red').save(cropped)
        return cropped
    monkeypatch.setattr(b,'_submit_and_save',fake_reactor)
    with use_route(Route('LOCAL', '')):
        b._run_face_swap(target,source,(region,srcregion))
    output=Path(__import__('PyQt6.QtCore',fromlist=['QUrl']).QUrl(b.previewUrl).toLocalFile())
    assert output.is_file(),b.status
    with Image.open(output) as image:
        assert image.size==(500,300)
        assert image.getpixel((80,80))==(255,0,0)
        assert image.getpixel((10,10))==(0,0,255)
        assert image.getpixel((400,100))==(255,255,0)
    assert 'only the reviewed target area changed' in b.status
    assert b.finishingResults[-1]['label']=='Face Lock · Person A'
