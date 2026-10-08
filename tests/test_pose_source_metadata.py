import copy
import json
import pytest
from genesis.pose_preset_payload import preset_payload, source_metadata, pose_preset_references
from genesis.generation_pipeline import adapt_prompt, REFCONTROL_TRIGGER

PHR19 = 'Qwen-Rapid-AIO-NSFW-v19.safetensors'
PHR23 = 'Qwen-Rapid-AIO-NSFW-v23.safetensors'
K9 = 'flux-2-klein-base-9b-Q4_K_M.gguf'
K4 = 'flux-2-klein-base-4b-Q4_K_M.gguf'


def test_source_wins_without_merging_grok():
    row = {'prompt': 'Old fallback wording', 'sourceMetadata': {'prompt': 'Turn toward the window', 'attribution': 'Original author'}}
    before = copy.deepcopy(row)
    payload = preset_payload(row, PHR19)
    assert payload['prompt'] == 'Turn toward the window'
    assert payload['promptSource'] == 'SOURCE_PACK'
    assert payload['attribution'] == 'Original author'
    assert row == before


def test_fallback_when_original_not_suitable():
    row = {'prompt': 'Fallback pose', 'promptSource': 'GROK_KLEIN_MAP', 'sourceMetadata': {'prompt': 'SDXL tested pose', 'models': ['sdxl']}}
    assert preset_payload(row, PHR19)['prompt'] == 'Fallback pose'
    assert preset_payload(row, PHR19)['promptSource'] == 'GROK_KLEIN_MAP'


@pytest.mark.parametrize('model,steps,sampler', [(PHR19,6,'er_sde'),(PHR23,4,'euler_ancestral')])
def test_exact_model_variants_keep_v19_v23_separate(model, steps, sampler):
    row = {'prompt':'Fallback', 'sourceMetadata': {'attribution':'Pack', 'model_prompts': {
        PHR19: {'prompt':'Turn left','settings':{'steps':6,'sampler':'er_sde','scheduler':'beta'}},
        PHR23: {'prompt':'Look right','settings':{'steps':4,'sampler':'euler_ancestral','scheduler':'beta'}}}}}
    p = preset_payload(row, model)
    assert p['settings']['steps'] == steps
    assert p['settings']['sampler'] == sampler
    assert p['attribution'] == 'Pack'


def test_unscoped_settings_and_triggers_do_not_leak():
    p = preset_payload({'sourceMetadata': {'prompt':'Sit on the chair', 'trigger_words':['adapterword'], 'settings':{'cfg':7}}}, PHR19)
    assert p['settings'] == {}
    assert 'adapterword' not in p['prompt']


@pytest.mark.parametrize('model', [PHR19,PHR23,K4,K9,'aisha_nsfw_beta_v9_7_distilled_bf16.safetensors','biglustydonutmixNSFW_v12.safetensors'])
def test_refcontrol_syntax_reserved_for_executable_route(model):
    row={'sourceMetadata':{'prompt': REFCONTROL_TRIGGER+'. Turn left','model_prompts':{model:{'trigger_words':[REFCONTROL_TRIGGER]}}}}
    assert REFCONTROL_TRIGGER not in preset_payload(row, model)['prompt']


def test_source_negative_kept_for_sdxl_zeroed_for_phr00t():
    row={'sourceMetadata':{'prompt':'Natural seated portrait','negative_prompt':'blurry geometry'}}
    assert preset_payload(row, PHR19)['negativePrompt'] == ''
    assert preset_payload(row, 'biglustydonutmixNSFW_v12.safetensors')['negativePrompt'] == 'blurry geometry'


def test_invalid_settings_rejected():
    row={'sourceMetadata':{'prompt':'Turn left','models':[K9],'settings':{'steps':-9,'cfg':float('inf'),'denoise':2,'sampler':'bad','scheduler':'bad','seed':False}}}
    assert preset_payload(row,K9)['settings'] == {}


def test_metadata_sidecar_preserved_without_reading_image(tmp_path):
    image=tmp_path/'control.png';image.write_bytes(b'not an image')
    sidecar=image.with_suffix('.json');sidecar.write_text(json.dumps({'prompt':'Turn left','attribution':'Author','models':[K9]}))
    before=sidecar.read_bytes()
    data=source_metadata({},image)
    assert data['attribution']=='Author'
    assert sidecar.read_bytes()==before
    assert image.read_bytes()==b'not an image'


def test_preset_sections_reference_without_duplicate_pose_data():
    row={'poseId':'standing/pose1','source':'file:///original/control.png','name':'Standing','sourceMetadata':{'attribution':'Author'}}
    rows=pose_preset_references([row,dict(row)])
    assert len(rows)==1
    assert rows[0]['source']==row['source']
    assert rows[0]['collection']=='Imported poses'
    assert 'collection' not in row


def test_model_prompt_template_applied_once_at_generation():
    payload=preset_payload({'sourceMetadata':{'prompt':'Turn left'}},PHR19)
    prompt=adapt_prompt(payload['prompt'], PHR19, source_image=True, pose_image=True)
    assert 'Turn left' in prompt
    assert REFCONTROL_TRIGGER not in prompt


def test_explicit_source_fields_supported():
    row={'prompt':'Fallback','source_prompt':'Original pose','source_models':[PHR19], 'source_settings':{'steps':6}, 'source_attribution':'Original pack'}
    p=preset_payload(row,PHR19)
    assert p['prompt']=='Original pose'
    assert p['settings']=={'steps':6}
    assert p['attribution']=='Original pack'


def test_original_index_prompt_is_not_replaced_by_grok(tmp_path):
    row={'prompt':'Original index pose','attribution':'Original author'}
    original=source_metadata(row,tmp_path/'control.png')
    p=preset_payload({'prompt':'Grok fallback','sourceMetadata':original},PHR19)
    assert p['prompt']=='Original index pose'
    assert p['attribution']=='Original author'


def test_preset_binding_keeps_uploaded_source_and_refreshes_model_payload():
    import re
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtQml import QJSEngine
    from pathlib import Path
    app=QApplication.instance() or QApplication([])
    engine=QJSEngine()
    qml=(Path(__file__).resolve().parents[1]/'genesis/qt_ui/MainPremiumLinux.qml').read_text()
    for name in ('applyPose','applyGenerationDefaults','applyPresetPayload'):
        function=re.search(r'    function '+name+r'\(.*?\n    }',qml,re.S).group()
        assert not engine.evaluate(function).isError()
    engine.evaluate('''var generationSource="untouched-master.png", selectedGenerationProfile={model:"v19"}, activeGenerationDefaults={};
    var selectedPresetPayload=null, selectedPoseSource, selectedPoseThumbnail, selectedPoseName, selectedPoseCategory, selectedPosePrompt, selectedPresetName, generationPrompt, generationNegativePrompt, presetAttribution, presetSettingsNote, generationWidth, generationHeight, generationSteps, generationCfg, generationDenoise, generationSampler, generationScheduler, generationSeed;
    var moduleBridge={posePresetPayload:function(row,model){return {prompt:model+" original",negativePrompt:"",attribution:"Pack",settings:{steps:model==="v19"?6:4},settingsNote:"Tested"}}};''')
    assert not engine.evaluate('applyPose({source:"control.png",prompt:"fallback"})').isError()
    assert engine.evaluate('generationSource').toString()=='untouched-master.png'
    assert engine.evaluate('selectedPoseSource').toString()=='control.png'
    assert engine.evaluate('generationPrompt').toString()=='v19 original'
    assert not engine.evaluate('applyGenerationDefaults({model:"v23"})').isError()
    assert engine.evaluate('generationPrompt').toString()=='v23 original'
    assert engine.evaluate('generationSteps').toInt()==4
    assert engine.evaluate('generationSource').toString()=='untouched-master.png'


def test_phr00t_gguf_uses_installed_matching_encoder_without_other_family_fallback():
    import qt_cockpit as c
    from genesis.workflow_lab import discover_workflow_controls
    info=json.loads((c.PROJECT_ROOT/'tests/fixtures/runpod_stage_models_schema.json').read_text())
    loader=info['CLIPLoaderGGUF']['input']['required']
    loader['clip_name']=[[c.REMOTE_PHR00T_CLIP]]
    graph=c.remote_workflow_prompt(c.STAGE_1_WORKFLOW,info)
    node=next(n for n in graph.values() if n['class_type']=='CLIPLoaderGGUF')
    assert node['inputs']['clip_name']==c.REMOTE_PHR00T_CLIP
    loader['clip_name']=[['qwen_3_8b_fp8mixed.safetensors']]
    graph=c.remote_workflow_prompt(c.STAGE_1_WORKFLOW,info)
    node=next(n for n in graph.values() if n['class_type']=='CLIPLoaderGGUF')
    assert node['inputs'].get('clip_name')!='qwen_3_8b_fp8mixed.safetensors'


def test_matching_tested_settings_are_kept_when_prompt_needs_fallback():
    p=preset_payload({'prompt':'Grok fallback','sourceMetadata':{'model_target':'Qwen-Rapid-AIO-NSFW-v19','attribution':'Author','settings':{'num_steps':6,'sampler_name':'er_sde'}}}, PHR19)
    assert p['prompt']=='Grok fallback'
    assert p['settings']=={'steps':6,'sampler':'er_sde'}
    assert p['settingsSource']=='SOURCE_PACK'
    assert p['attribution']=='Author'


def test_other_architecture_settings_do_not_leak_into_variant():
    p=preset_payload({'sourceMetadata':{'models':['sdxl'],'settings':{'cfg':7},'model_prompts':{PHR19:{'prompt':'Original Phr00t instruction'}}}},PHR19)
    assert p['prompt']=='Original Phr00t instruction'
    assert p['settings']=={}


@pytest.mark.parametrize('model',[PHR19,PHR23,K4,K9,'aisha_nsfw_beta_v9_7_distilled_bf16.safetensors','biglustydonutmixNSFW_v12.safetensors'])
def test_edit_adapter_does_not_leak_unvalidated_refcontrol_phrase(model):
    p=adapt_prompt(REFCONTROL_TRIGGER+'. Turn left',model,source_image=True,pose_image=True)
    assert REFCONTROL_TRIGGER not in p
    assert 'Turn left' in p
