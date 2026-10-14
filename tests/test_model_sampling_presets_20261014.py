"""Regression coverage for route-aware GENESIS model sampling and speed presets.

Proposed Fast/Balanced counts are draft-performance choices, not certified
quality benchmarks; this suite protects the route-specific publisher baselines.
"""
import json
import re

import pytest
from PyQt6.QtQml import QJSEngine
import qt_cockpit as c


@pytest.mark.parametrize('model,remote,create_steps,create_cfg,source_steps,source_cfg', [
    (c.LOCAL_AISHA_9B_MODEL,False,50,4.0,50,4.0),
    (c.REGULAR_9B_MODEL,False,50,4.0,50,4.0),
    (c.REMOTE_AISHA_9B_MODEL,True,4,1.0,5,1.0),
    (c.REMOTE_AISHA_BF16_MODEL,True,4,1.0,5,1.0),
    (c.REMOTE_KLEIN_9B_MODEL,True,4,1.0,5,1.0),
    (c.REMOTE_DARKBEAST_9B_MODEL,True,5,1.0,5,1.0),
    (c.REMOTE_PORNMASTER_9B_MODEL,True,50,4.0,5,1.0),
    (c.REMOTE_MIRACLEIN_9B_MODEL,True,12,1.1,12,1.1),
    (c.LOCAL_PORNMASTER_9B_MODEL,False,8,1.5,4,2.0),
    (c.REMOTE_MOP_MODEL,True,10,1.0,10,1.0),
])
def test_model_sampling_defaults_are_variant_specific(model,remote,create_steps,create_cfg,source_steps,source_cfg):
    create=c.model_generation_settings(model,remote=remote)
    source=c.model_generation_settings(model,remote=remote,source=True)
    assert (create['defaultSteps'],create['defaultCfg'])==(create_steps,create_cfg)
    assert (source['defaultSteps'],source['defaultCfg'])==(source_steps,source_cfg)


@pytest.mark.parametrize('model,remote,expected', [
    (c.LOCAL_AISHA_9B_MODEL,False,(24,36,50)),
    (c.REGULAR_9B_MODEL,False,(24,36,50)),
    (c.REMOTE_PORNMASTER_9B_MODEL,True,(24,36,50)),
    (c.QWEN21_MODEL,False,(20,30,40)),
    (c.REMOTE_MOP_MODEL,True,(6,8,10)),
    (c.REMOTE_DONUTS_MODEL,True,(12,18,25)),
    (c.REMOTE_PONY_MODEL,True,(12,18,25)),
    (c.REMOTE_DARKBEAST_9B_MODEL,True,(5,5,5)),
    (c.REMOTE_AISHA_9B_MODEL,True,(4,4,4)),
    (c.REMOTE_MIRACLEIN_9B_MODEL,True,(12,12,12)),
    (c.LOCAL_PORNMASTER_9B_MODEL,False,(4,8,8)),
])
def test_text_presets_use_model_specific_step_budget(model,remote,expected):
    profile=c.model_profile_settings(model,remote=remote)
    actual=tuple(profile['createQualityPresets'][n].get('steps',profile['createDefaults']['defaultSteps'])
                 for n in ('Fast','Balanced','Quality'))
    assert actual==expected
    assert profile['createDefaults']['defaultSteps']==expected[-1]


def test_pornmaster_v3_reference_not_replaced_by_base_t2i_shortcuts():
    p=c.model_profile_settings(c.REMOTE_PORNMASTER_9B_MODEL,remote=True)
    assert p['sourceDefaults']['defaultSteps']==5
    assert not any('steps' in v for v in p['sourceQualityPresets'].values())


def test_qml_applies_and_restores_model_sampling_presets():
    qml=(c.PROJECT_ROOT/'genesis/qt_ui/MainPremiumLinux.qml').read_text()
    engine=QJSEngine()
    for name in ('applyGenerationDefaults','applyQualityPreset','qualityPresetActive'):
        function=re.search(r'    function '+name+r'\(.*?\n    }',qml,re.S).group()
        assert not engine.evaluate(function).isError(),name
    engine.evaluate('var selectedGenerationProfile; var activeSourceImage=false; var generationSource=""; var generationWidth,generationHeight,generationSteps,generationCfg,generationDenoise,generationSampler,generationScheduler,generationReferenceMegapixels,generationOutputTarget,useUpscale; var selectedPresetPayload=null,sdxlFaceIDEnabled=false;')
    for model,fast,quality in ((c.LOCAL_AISHA_9B_MODEL,24,50),(c.REMOTE_DONUTS_MODEL,12,25)):
        profile=c.model_profile_settings(model)
        engine.evaluate('selectedGenerationProfile='+json.dumps(profile))
        for name,count in (('Fast',fast),('Quality',quality)):
            assert not engine.evaluate('applyQualityPreset("'+name+'",512,512)').isError()
            assert engine.evaluate('generationSteps').toInt()==count
            assert engine.evaluate('qualityPresetActive("'+name+'",512,512)').toBool()


def test_stage_one_picker_shares_selected_model_catalog():
    qml=(c.PROJECT_ROOT/'genesis/qt_ui/MainPremiumLinux.qml').read_text()
    assert 'readonly property var stageOneChoices: generationModel\n' in qml
    assert 'readonly property var stageOneSelectableChoices: stageOneChoices' in qml
    assert 'if (stageOneSelectableChoices[i].model === selectedGenerationProfile.model) return i' in qml


@pytest.mark.parametrize('model,steps,cfg',[
    (c.REGULAR_9B_MODEL,50,4.0),
    (c.REMOTE_AISHA_9B_MODEL,4,1.0),
    (c.REMOTE_DARKBEAST_9B_MODEL,5,1.0),
    (c.REMOTE_PORNMASTER_9B_MODEL,50,4.0),
])
def test_actual_create_graph_uses_model_not_template_sampling(monkeypatch,model,steps,cfg):
    # Regression for old Klein Base hard-coded 4/1 and RunPod reuse of
    # Miraclein's 12/1.1 template irrespective of the selected checkpoint.
    import copy
    graph={
        '126':{'class_type':'UNETLoader','inputs':{'unet_name':'template','weight_dtype':'default'}},
        '136':{'class_type':'CLIPLoader','inputs':{'clip_name':'encoder','type':'flux2'}},
        '107':{'class_type':'CLIPTextEncode','inputs':{'text':'old','clip':['136',0]}},
        '134':{'class_type':'KSampler','inputs':{'steps':12,'cfg':1.1,'sampler_name':'euler','scheduler':'simple','model':['126',0]}},
        '105':{'class_type':'EmptyLatentImage','inputs':{'width':1024,'height':1024,'batch_size':1}},
        '102':{'class_type':'VAELoader','inputs':{'vae_name':'old'}},
        '9':{'class_type':'SaveImage','inputs':{'filename_prefix':'old'}},
    }
    monkeypatch.setattr(c,'REGULAR_9B_WORKFLOWS',[c.LOCAL_AISHA_9B_WORKFLOW])
    monkeypatch.setattr(c.workflow_lab,'workflow_to_prompt',lambda *args:copy.deepcopy(graph))
    monkeypatch.setattr(c.workflow_lab,'validate_prompt',lambda *args:{'valid':True,'missing_nodes':[],'missing_inputs':[]})
    result=c.build_create_prompt({},'A mountain at sunrise',768,768,model)
    sampler=result['134']['inputs']
    assert (sampler['steps'],sampler['cfg'])==(steps,cfg)
    assert result['105']['inputs']['width']==768
