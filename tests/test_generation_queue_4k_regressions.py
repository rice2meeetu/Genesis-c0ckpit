"""No-GPU tests: model-resolution controls, queued state snapshots, and 2K/4K output."""
import json
import re
from pathlib import Path
from unittest.mock import Mock

import pytest
from PIL import Image
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtQml import QJSEngine

import qt_cockpit as c


def job(model=None, prompt='one', seed=111):
    return (prompt, '', 1024, 1024, model or c.REMOTE_DONUTS_MODEL,
            'None','None','file:///tmp/person.png','file:///tmp/bones.png',
            False,False,False,25,4.0,seed,0.55,'dpmpp_sde','karras','None',0.0,0.0,0.0)


def test_model_quality_not_smaller_than_model_native_baseline():
    for model in c.SUPPORTED_CREATE_MODELS:
        for remote in (False,True):
            p=c.model_profile_settings(model,remote=remote)
            for source, presets in (('createDefaults', 'createQualityPresets'),('sourceDefaults','sourceQualityPresets')):
                d=p[source]; sizes=p[presets]
                assert (sizes['Quality']['width'], sizes['Quality']['height']) == (d['defaultWidth'], d['defaultHeight'])
                assert sizes['Fast']['width'] <= sizes['Balanced']['width'] <= sizes['Quality']['width']
                assert sizes['Fast']['height'] <= sizes['Balanced']['height'] <= sizes['Quality']['height']
            assert p['sourceQualityPresets']['Quality']['width']==p['sourceDefaults']['defaultWidth']
    p=c.model_profile_settings(c.REMOTE_MIRACLEIN_9B_MODEL,remote=True)
    assert p['sourceQualityPresets']['Quality']=={'width':1920,'height':1520}
    p=c.model_profile_settings(c.REMOTE_PHR00T_V23_GGUF_MODEL,remote=True)
    assert (p['sourceQualityPresets']['Quality']['width'],p['sourceQualityPresets']['Quality']['height']) == (2264,1360)
    assert p['sourceQualityPresets']['Quality']['cfg'] == 1.2
    assert p['sourceQualityPresets']['Balanced']['cfg'] == 1.0


def test_quality_and_2k_4k_buttons_keep_dimensions_and_model_defaults():
    qml=(c.PROJECT_ROOT/'genesis/qt_ui/MainPremiumLinux.qml').read_text()
    e=QJSEngine()
    for name in ('applyGenerationDefaults','applyQualityPreset','qualityPresetActive','applyOutputTarget'):
        match=re.search(r'    function '+name+r'\(.*?\n    }',qml,re.S)
        assert match,name
        assert not e.evaluate(match.group()).isError(),name
    p=c.model_profile_settings(c.REMOTE_PHR00T_V23_GGUF_MODEL,remote=True)
    e.evaluate('var selectedGenerationProfile='+json.dumps(p)+'; var generationSource="file:///reference.png"; var activeSourceImage=true;'+
        'var generationWidth, generationHeight, generationSteps, generationCfg, generationDenoise, generationSampler, generationScheduler, generationReferenceMegapixels; var selectedPresetPayload=null;'+
        'var generationSeed=11, generationOutputTarget=0, useUpscale=false, sdxlFaceIDEnabled=false, outputUpscaleReady=true; var genesisBridge={busy:false};')
    assert not e.evaluate('applyGenerationDefaults(selectedGenerationProfile)').isError()
    assert not e.evaluate('applyQualityPreset("Quality",1024,1024)').isError()
    assert e.evaluate('generationWidth').toInt()==2264
    assert e.evaluate('generationHeight').toInt()==1360
    assert e.evaluate('generationSteps').toInt()==4
    for target in (2560,3840):
        assert not e.evaluate(f'applyOutputTarget({target})').isError()
        assert e.evaluate('generationWidth').toInt()==2264
        assert e.evaluate('generationHeight').toInt()==1360
        assert e.evaluate('generationOutputTarget').toInt()==target
        assert e.evaluate('useUpscale').toBool()
    assert not e.evaluate('applyQualityPreset("Balanced",1024,1024)').isError()
    assert e.evaluate('generationOutputTarget').toInt()==0
    assert not e.evaluate('useUpscale').toBool()


def test_queued_jobs_keep_faceid_output_route_and_settings(monkeypatch):
    QCoreApplication.instance() or QCoreApplication([])
    b=c.GenerationBridge()
    runs=[]
    def submit(*args):
        runs.append((tuple(args),b._sdxl_faceid_enabled,b._sdxl_faceid_strength,
                     b._output_target_long_edge,b._stage_two_model))
        b._set_busy(True)
    monkeypatch.setattr(b,'queueGenerateAdvanced',submit)
    b.setSdxlFaceID(True,0.9);b.setOutputTarget(3840)
    b.enqueueGenerateAdvanced(*job(prompt='first',seed=111))
    assert len(runs)==1
    b.setSdxlFaceID(False,0.2);b.setOutputTarget(2560)
    b.enqueueGenerateAdvanced(*job(prompt='second',seed=222))
    b.setOutputTarget(0)
    b.enqueueGenerateAdvanced(*job(prompt='third',seed=333))
    assert b.pendingGenerationCount==2
    assert [x['label'] for x in b.pendingGenerations]==['second','third']
    b._set_busy(False);QCoreApplication.processEvents()
    assert len(runs)==2 and runs[1][0][14]==222
    assert runs[1][1:4]==(False,0.2,2560)
    b.removePendingGeneration(0)
    assert not b.pendingGenerations
    b._set_busy(False);QCoreApplication.processEvents()
    assert len(runs)==2
    assert runs[0][1:4]==(True,0.9,3840)


def test_clear_waiting_does_not_cancel_active(monkeypatch):
    QCoreApplication.instance() or QCoreApplication([])
    b=c.GenerationBridge()
    monkeypatch.setattr(b,'queueGenerateAdvanced', lambda *args:b._set_busy(True))
    b.enqueueGenerateAdvanced(*job())
    b.enqueueGenerateAdvanced(*job(prompt='pending'))
    assert b.busy and b.pendingGenerationCount==1
    b.clearPendingGenerations()
    assert b.busy and b.pendingGenerationCount==0


@pytest.mark.parametrize('w,h,target,expected',[(1024,1024,2560,(2560,2560)),(1024,576,3840,(3840,2160)),(1024,576,2560,(2560,1440))])
def test_upscale_generates_exact_target_without_rerunning_sampler(monkeypatch,tmp_path,w,h,target,expected):
    b=c.GenerationBridge();src=tmp_path/'source.png'
    Image.new('RGB',(w,h)).save(src)
    info={key:{} for key in ('LoadImage','UpscaleModelLoader','ImageUpscaleWithModel','ImageScale','SaveImage')}
    info['UpscaleModelLoader']={'input':{'required':{'model_name':[['4x-UltraSharp.safetensors']]}}}
    client=Mock();client.upload_image.return_value={'name':'image.png','subfolder':'genesis'}
    graphs=[]
    monkeypatch.setattr(c,'validate_operation_prompt',lambda g,*a: graphs.append(g))
    monkeypatch.setattr(b,'_submit_and_save',lambda _,g,*a: graphs.append(g) or tmp_path/'done.png')
    result=b._upscale_to_long_edge(client,info,src,target,'stamp')
    assert result==tmp_path/'done.png'
    assert graphs[-1]['4']['inputs']['width']==expected[0]
    assert graphs[-1]['4']['inputs']['height']==expected[1]
    assert not any(v['class_type']=='KSampler' for v in graphs[-1].values())


def test_queued_phr00t_references_are_snapshotted_independently(monkeypatch):
    QCoreApplication.instance() or QCoreApplication([])
    bridge = c.GenerationBridge()
    runs=[]
    def capture(*args):
        runs.append((args[0],bridge._extra_reference_url))
        bridge._set_busy(True)
    monkeypatch.setattr(bridge,'queueGenerateAdvanced',capture)
    for i in range(3):
        bridge.setExtraReferenceSource(f'file:///tmp/reference-{i}.png')
        bridge.enqueueGenerateAdvanced(*job(model=c.REMOTE_PHR00T_V23_Q2_MODEL,prompt=f'prompt {i}'))
    assert len(runs)==1 and runs[0]==('prompt 0','file:///tmp/reference-0.png')
    bridge.setExtraReferenceSource('file:///tmp/different.png')
    bridge._set_busy(False)
    QCoreApplication.processEvents()
    assert runs[-1]==('prompt 1','file:///tmp/reference-1.png')
    bridge._set_busy(False)
    QCoreApplication.processEvents()
    assert runs[-1]==('prompt 2','file:///tmp/reference-2.png')
