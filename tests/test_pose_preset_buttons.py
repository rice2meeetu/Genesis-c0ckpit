"""Actual pose-card clicks and family configuration, without services or GPU work."""
import os
from pathlib import Path
import subprocess
import sys

import pytest
import qt_cockpit as c
from genesis.pose_preset_payload import preset_payload


@pytest.mark.parametrize('model', [c.REMOTE_DONUTS_MODEL, c.REMOTE_PONY_MODEL, c.REMOTE_REALISTIC_VISION_MODEL])
def test_curated_checkpoint_prompt_drops_foreign_image_reference(model):
    row = {'id': 'curated18:test', 'prompt': 'Stand beside a chair. Preserve image1 identity.'}
    assert 'image1' not in preset_payload(row, model)['prompt']


def test_actual_pose_card_clicks_apply_skeleton_prompt_and_model_family(tmp_path):
    script=r'''
import json,sys
from pathlib import Path
from PyQt6.QtCore import QTimer,QObject,QPointF,QUrl,Qt
from PyQt6.QtQml import QQmlExpression
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
import qt_cockpit as c
import qt_cockpit_linux_premium as launch
import genesis.pose_workbench as workbench
workbench.POSE_WORKBENCH_HANDOFF_FILE=Path(sys.argv[1])/'unused-handoff.json'
a=(Path(sys.argv[1])/'a.png').as_uri(); b=(Path(sys.argv[1])/'b.png').as_uri()
poses=[{'name':'A','source':a,'category':'Standing','prompt':'Stand beside a chair'},
       {'name':'B','source':b,'category':'Sitting','prompt':'Sit in a chair'}]
presets=[
 {'id':'mapped:a','label':'Same label','source':a,'prompt':'Stand beside a chair','collection':'Linked Pose + JSON Prompt'},
 {'id':'mapped:b','label':'Same label','source':b,'prompt':'Sit in a chair','collection':'Linked Pose + JSON Prompt'},
 {'id':'full70:test','label':'Text pose','prompt':'Pose: Sitting in a chair','requiresPoseSelection':True,'poseHintCategory':'Sitting','collection':'Full 70 · select skeleton'},
 {'id':'curated18:test','label':'Configured pose','source':a,'prompt':'Stand beside a chair. Preserve image1 identity.','collection':'Curated 18',
  'sourceMetadata':{'model_prompts':{'sdxl':{'prompt':'Stand beside a chair','settings':{'steps':17,'cfg':5.5,'sampler':'dpmpp_2m','scheduler':'karras'}}}}},
]
launch.load_pose_items=lambda **kw: poses
launch.load_grok_preset_items=lambda: []
launch.load_curated_pose_presets=lambda **kw: presets
launch.load_runtime_status=lambda **kw: {}
launch.BackendBridge.start=lambda self: None
engines=[]; factory=launch.QQmlApplicationEngine
launch.QQmlApplicationEngine=lambda:(engines.append(factory()) or engines[-1])

def verify():
 try:
    engine=engines[0];w=engine.rootObjects()[0];ctx=engine.rootContext()
    def evaluate(code,scope=None):
        exp=QQmlExpression(ctx,scope or w,code); value,_=exp.evaluate()
        assert not exp.hasError(),f'{code}: {exp.error().toString()}'
        QApplication.processEvents(); return value
    families=[c.REMOTE_DONUTS_MODEL,c.REMOTE_PONY_MODEL,c.REMOTE_REALISTIC_VISION_MODEL,
              c.REMOTE_PHR00T_V19_MODEL,c.REMOTE_PHR00T_V23_GGUF_MODEL,c.QWEN21_MODEL,
              c.FOUR_B_MODEL,c.REGULAR_9B_MODEL,c.KV_9B_MODEL,c.REMOTE_AISHA_BF16_MODEL]
    rows=[{'model':m,'label':m,'runnable':True,'ready':True,'routeReady':True,'poseReady':True,
           'stageOneEligible':True,'sourceSupported':True,'loras':['None'],**c.model_profile_settings(m)} for m in families]
    w.setProperty('generationModel',rows)
    w.setProperty('generationSource',QUrl(a)); w.setProperty('useSourceImageMode',True)
    QApplication.processEvents(); QTest.qWait(80)
    def click(index):
        w.setProperty('pageIndex',0); QApplication.processEvents(); QTest.qWait(30)
        grid=w.findChild(QObject,'posePresetGrid')
        card=evaluate('itemAtIndex('+str(index)+')',grid)
        assert card is not None,('missing card',index)
        point=QPointF(evaluate('mapToItem(null,20,20).x',card),
                      evaluate('mapToItem(null,20,20).y',card)).toPoint()
        QTest.mouseClick(w,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier,point)
        QApplication.processEvents()
        return card
    # Pointer clicks on real delegates, with duplicate labels, must select one stable ID.
    first=click(0); assert w.property('selectedPoseSource').toString()==a
    assert w.property('generationPrompt')=='Stand beside a chair'
    assert first.property('presetSelected')
    second=click(1); assert w.property('selectedPoseSource').toString()==b
    assert w.property('generationPrompt')=='Sit in a chair'
    assert second.property('presetSelected') and not first.property('presetSelected')
    # Clear must clear both the applied payload and selected-card indicator.
    evaluate('clearPose()')
    assert w.property('selectedPresetId')==''
    assert w.property('selectedPresetName')=='No preset selected'
    assert w.property('selectedPresetPayload') is None
    assert not second.property('presetSelected')
    # Text-only pose buttons request geometry, then return with that instruction intact.
    click(2)
    assert w.property('pageIndex')==1 and not w.property('modeInputsReady')
    prompt=w.property('generationPrompt')
    evaluate('applyPose(poseModel[1])')
    w.setProperty('pageIndex',0)
    assert w.property('selectedPoseSource').toString()==b
    assert w.property('generationPrompt')==prompt
    assert w.property('modeInputsReady')
    # Family configuration reapplies on model switches, preserving the real skeleton/source.
    from genesis.pose_preset_payload import preset_payload
    for index,model in enumerate(families):
        evaluate(f'selectGeneration({index},false)')
        actual=preset_payload(presets[2],model)
        defaults=c.model_profile_settings(model)['sourceDefaults']
        assert w.property('generationPrompt')==actual['prompt'],model
        assert w.property('generationSteps')==defaults['defaultSteps'],model
        assert abs(w.property('generationCfg')-defaults['defaultCfg'])<0.0001,model
        assert w.property('generationSampler')==defaults['defaultSampler'],model
        assert w.property('generationScheduler')==defaults['defaultScheduler'],model
        assert w.property('generationSource').toString()==a
        assert w.property('selectedPoseSource').toString()==b
    # Exact scoped pack settings win for SDXL; other families keep their defaults.
    evaluate('selectGeneration(0,false)'); click(3)
    assert w.property('selectedPoseSource').toString()==a
    assert w.property('generationSteps')==17 and w.property('generationCfg')==5.5
    assert w.property('generationSampler')=='dpmpp_2m'
    evaluate('selectGeneration(3,false)')
    assert w.property('generationSteps')==c.model_profile_settings(families[3])['sourceDefaults']['defaultSteps']
    print('POSE_PRESET_BUTTONS_FAMILY_OK'); QApplication.instance().exit(0)
 except Exception:
    import traceback;traceback.print_exc();QApplication.instance().exit(1)
class App(QApplication):
 def exec(self):
    QTimer.singleShot(200,verify);QTimer.singleShot(12000,lambda:self.exit(2))
    return super().exec()
launch.QApplication=App
sys.argv=['pose-card-test','--page','create']
sys.exit(launch.main())
'''
    # Harmless tiny image fixtures; these tests never queue generation.
    from PIL import Image
    for name in ('a.png', 'b.png'):
        Image.new('RGB',(8,8),'black').save(tmp_path/name)
    runtime=tmp_path/'runtime';runtime.mkdir(mode=0o700)
    env=dict(os.environ,QT_QPA_PLATFORM='offscreen',XDG_RUNTIME_DIR=str(runtime),
        XDG_CONFIG_HOME=str(tmp_path/'config'),QTWEBENGINE_DISABLE_SANDBOX='1',
        QT_QUICK_BACKEND='software',QSG_RHI_BACKEND='software',LIBGL_ALWAYS_SOFTWARE='1',
        GENESIS_RUNPOD_AUTOCONNECT='0',GENESIS_BACKEND_MODE='LOCAL')
    result=subprocess.run([sys.executable,'-c',script,str(tmp_path)],cwd=Path(__file__).resolve().parents[1],
        env=env,text=True,capture_output=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'POSE_PRESET_BUTTONS_FAMILY_OK' in result.stdout


@pytest.mark.parametrize('model', [c.REMOTE_DONUTS_MODEL,c.REMOTE_PONY_MODEL,c.REMOTE_REALISTIC_VISION_MODEL,
    c.REMOTE_PHR00T_V19_MODEL,c.REMOTE_PHR00T_V23_GGUF_MODEL,c.QWEN21_MODEL,
    c.FOUR_B_MODEL,c.REGULAR_9B_MODEL,c.KV_9B_MODEL,c.REMOTE_AISHA_BF16_MODEL])
def test_curated_presets_use_selected_family_configuration(model):
    row={'id':'curated18:test','prompt':'Stand beside a chair. Preserve image1 identity.'}
    payload=preset_payload(row,model)
    assert payload['promptSource']=='GENESIS_FAMILY_ADAPTED'
    assert 'Stand beside a chair' in payload['prompt']
    assert 'image1' not in payload['prompt']
    assert payload['settingsSource']=='MODEL_DEFAULT'
    assert payload['settings']=={}
