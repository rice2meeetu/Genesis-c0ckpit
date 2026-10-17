"""Focused, no-GPU checks for Full 70 family prompts, pose routing and internal LoRA."""
import re

import pytest
from PyQt6.QtQml import QJSEngine

import qt_cockpit as c
from genesis.pose_preset_payload import preset_payload
from genesis.model_compatibility import compatible_loras, is_compatible


FAMILIES = [
    c.REMOTE_PHR00T_V19_MODEL, c.REMOTE_PHR00T_V22_GGUF_MODEL,
    c.REMOTE_PHR00T_V23_GGUF_MODEL, c.QWEN21_MODEL,
    c.REMOTE_DONUTS_MODEL, c.REMOTE_MOP_MODEL,
    c.REMOTE_PONY_MODEL, c.REMOTE_REALISTIC_VISION_MODEL,
    c.REMOTE_MIRACLEIN_9B_MODEL, c.FOUR_B_MODEL, c.REMOTE_AISHA_BF16_MODEL,
]


@pytest.mark.parametrize('model', FAMILIES)
def test_all_70_use_family_adaptation_and_model_defaults(model):
    rows = [p for p in c.load_curated_pose_presets() if p['id'].startswith('full70:')]
    assert len(rows) == 70
    for row in rows:
        result = preset_payload(row, model)
        assert result['promptSource'] == 'GENESIS_FAMILY_ADAPTED', (model,row['id'])
        assert result['settings'] == {}
        assert result['settingsSource'] == 'MODEL_DEFAULT'
        assert result['prompt'] and 'Keep the exact same person, face, hair' not in result['prompt']
        assert 'pixel-perfect fidelity' not in result['prompt']
    profiles = c.model_profile_settings(model, remote=True)
    assert profiles['createDefaults']['defaultSteps'] >= 1
    assert profiles['createDefaults']['defaultSampler']


def test_family_profiles_differ_and_mop_steps_preserved():
    row = c.load_curated_pose_presets()[0]
    prompts = [preset_payload(row, model)['prompt'] for model in [
        c.REMOTE_MOP_MODEL, c.REMOTE_PHR00T_V19_MODEL,
        c.REMOTE_PHR00T_V23_GGUF_MODEL, c.REMOTE_MIRACLEIN_9B_MODEL,
        c.REMOTE_PONY_MODEL]]
    assert len(set(prompts)) == len(prompts)
    mop = c.model_generation_settings(c.REMOTE_MOP_MODEL)
    assert (mop['defaultSteps'], mop['defaultCfg'], mop['defaultSampler'], mop['defaultScheduler']) == (10,1.0,'lcm','ddim_uniform')


def test_internal_faceid_adapter_cannot_be_double_stack_selected():
    identity = c.FACEID_SDXL_LORA
    assert all(not is_compatible(model,identity) for model in [c.REMOTE_MOP_MODEL,c.REMOTE_DONUTS_MODEL,c.REMOTE_PONY_MODEL])
    names = compatible_loras(c.REMOTE_MOP_MODEL,[identity,'add-detail-xl.safetensors','face_xl_v0_1.safetensors'])
    assert identity not in names
    assert 'add-detail-xl.safetensors' in names


def qml_scope():
    qml = (c.PROJECT_ROOT/'genesis/qt_ui/MainPremiumLinux.qml').read_text()
    engine = QJSEngine()
    for name in ('applyGenerationDefaults','applyQualityPreset','applyPresetPayload','presetSelectionKey','applyPreset','applyPose','defaultLoraStrength'):
        fn = re.search(r'    function ' + name + r'\(.*?\n    }',qml,re.S).group()
        assert not engine.evaluate(fn).isError(),name
    engine.evaluate('''
        var activeSourceImage=true, generationSource='master.png', selectedPoseSource='bone.png',selectedPoseThumbnail='bone.png',
        selectedPoseName='Standing',selectedPoseCategory='',selectedPosePrompt='',selectedPresetName='',selectedPresetId='',pageIndex=0,
        selectedPresetPayload=null,selectedGenerationProfile={},sdxlFaceIDEnabled=false,
        sdxlFaceIDActive=false,generationNegativePrompt='',generationPrompt='',presetAttribution='',presetSettingsNote='',
        generationWidth=1024,generationHeight=1024,generationSteps=25,generationCfg=4.0,
        generationDenoise=0.65,generationSampler='euler',generationScheduler='simple',generationSeed=121,
        genesisBridge={posePresetPayload:function(row,model){return {prompt: model+' family-specific '+row.label,negativePrompt:'',
           promptSource:'GENESIS_FAMILY_ADAPTED', settingsSource:'MODEL_DEFAULT',attribution:'Family profile',settings:{},settingsNote:'Uses model defaults'}}};
    ''')
    return engine


def test_text_preset_preserves_selected_skeleton_and_model_settings():
    import json
    eng = qml_scope()
    settings=c.model_profile_settings(c.REMOTE_MOP_MODEL,remote=True)
    eng.evaluate('selectedGenerationProfile='+json.dumps({'model':c.REMOTE_MOP_MODEL,**settings}))
    eng.evaluate('selectedGenerationProfile.sourceDefaults='+json.dumps(settings['sourceDefaults']))
    # Selecting the model first establishes its sampler, scheduler and
    # step defaults. The text pose must not clobber subsequent manual edits.
    assert not eng.evaluate('applyGenerationDefaults(selectedGenerationProfile)').isError()
    assert not eng.evaluate('applyPreset({id:"full70:test",label:"Pose A",prompt:"original"})').isError()
    assert eng.evaluate('selectedPoseSource').toString()=='bone.png'
    assert eng.evaluate('generationPrompt').toString().startswith(c.REMOTE_MOP_MODEL+' family-specific')
    assert eng.evaluate('generationSteps').toInt()==10
    assert eng.evaluate('generationSampler').toString()=='lcm'
    assert eng.evaluate('generationScheduler').toString()=='ddim_uniform'
    assert not eng.evaluate('applyQualityPreset("Quality",1024,1024)').isError()
    assert eng.evaluate('selectedPoseSource').toString()=='bone.png'
    assert eng.evaluate('generationSteps').toInt()==10
    assert 'skeleton retained' in eng.evaluate('presetSettingsNote').toString()
    eng.evaluate('selectedGenerationProfile.model="mopMixtureOfPerverts_instaV10DMD.safetensors"')
    assert eng.evaluate('defaultLoraStrength("add-detail-xl.safetensors")').toNumber()==0.35


def test_pick_skeleton_after_text_preset_keeps_instruction():
    eng=qml_scope()
    eng.evaluate('selectedGenerationProfile={model:"sdxl",sourceDefaults:{defaultSteps:25},createDefaults:{defaultSteps:25}}')
    eng.evaluate('selectedPoseSource=""')
    assert not eng.evaluate('applyPreset({id:"full70:pose",label:"Pose A"})').isError()
    assert 'Text-only pose description' in eng.evaluate('presetSettingsNote').toString()
    assert not eng.evaluate('applyPose({source:"a-different-skeleton.png",name:"Bones",category:"standing"})').isError()
    assert eng.evaluate('selectedPoseSource').toString()=='a-different-skeleton.png'
    assert eng.evaluate('selectedPresetName').toString()=='Pose A'
    assert 'family-specific Pose A' in eng.evaluate('generationPrompt').toString()
