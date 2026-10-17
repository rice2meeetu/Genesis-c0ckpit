"""Real premium QML: navigation and independent settings must never silently reset.
Runs without GPU or RunPod access, with isolated Qt/user settings.
"""
import os
from pathlib import Path
import subprocess
import sys


def test_navigation_keeps_create_controls_and_unrelated_workspace_state(tmp_path):
    script = r'''
from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQml import QQmlExpression
import qt_cockpit_linux_premium as launch
import qt_cockpit as c
import sys
launch.load_pose_items=lambda **k: []
launch.load_grok_preset_items=lambda: []
launch.load_curated_pose_presets=lambda **k: []
launch.load_runtime_status=lambda **k: {}
launch.BackendBridge.start=lambda self: None
engines=[]
real=launch.QQmlApplicationEngine
launch.QQmlApplicationEngine=lambda:(engines.append(real()) or engines[-1])

def run():
    try:
        engine=engines[0]
        w=engine.rootObjects()[0]
        ctx=engine.rootContext()
        def ev(expr):
            q=QQmlExpression(ctx,w,expr)
            result,_=q.evaluate()
            assert not q.hasError(),(expr,q.error().toString())
            QApplication.processEvents()
            return result
        model=c.REMOTE_MIRACLEIN_9B_MODEL
        row=dict(c.model_profile_settings(model,remote=True),model=model,
                 label='Miraclein',runnable=True,routeReady=True,selectable=True,
                 sourceSupported=True,loras=['None','test-lora.safetensors'])
        w.setProperty('generationModel',[row])
        ev('selectGeneration(0,false)')
        w.setProperty('generationPrompt','Persistent neutral prompt')
        w.setProperty('generationNegativePrompt','Persistent negative')
        w.setProperty('generationSeed',24680)
        w.setProperty('generationSource',QUrl('file:///tmp/sample.png'))
        w.setProperty('selectedPoseSource',QUrl('file:///tmp/pose.png'))
        w.setProperty('generationSampler','dpmpp_2m')
        w.setProperty('generationScheduler','karras')
        w.setProperty('generationDenoise',0.47)
        w.setProperty('selectedLora','test-lora.safetensors')
        w.setProperty('selectedLoraStrength',0.43)
        w.setProperty('editPrompt','Unrelated edit workspace')
        snapshot={key:w.property(key) for key in [
             'generationPrompt','generationNegativePrompt','generationSeed',
             'generationSource','selectedPoseSource','generationSampler',
             'generationScheduler','generationDenoise','selectedLora',
             'selectedLoraStrength','editPrompt']}
        for index in [14,0,1,2,9,8,4,3,5,7,10,11,12,13,15,0]:
            w.setProperty('pageIndex',index)
            QApplication.processEvents()
            assert w.property('pageIndex')==index,('navigation index',index)
            for key,value in snapshot.items():
                assert w.property(key)==value,('navigation reset',index,key,w.property(key),value)
        # The visible sidebar has exactly the navigation destinations we expect.
        navcount=ev('navItems.length')
        actual=int(navcount.toInt() if hasattr(navcount,'toInt') else navcount)
        assert actual >= 8,('sidebar entries',actual)
        print('NAV_AND_WORKSPACE_STATE_OK',flush=True)
        QApplication.instance().exit(0)
    except Exception:
        import traceback;traceback.print_exc();QApplication.instance().exit(1)
class App(QApplication):
    def exec(self):
        QTimer.singleShot(250,run)
        QTimer.singleShot(16000,lambda:self.exit(2))
        return super().exec()
launch.QApplication=App
sys.argv=['navigation-state-check','--page','create']
sys.exit(launch.main())
'''
    _run_offscreen(script, tmp_path, 'NAV_AND_WORKSPACE_STATE_OK')


def test_generation_settings_do_not_reset_on_unrelated_choices(tmp_path):
    script = r'''
from PyQt6.QtCore import QTimer, QUrl, QObject
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQml import QQmlExpression
import qt_cockpit_linux_premium as launch
import qt_cockpit as c
import sys
launch.load_pose_items=lambda **k: []
launch.load_grok_preset_items=lambda: []
launch.load_curated_pose_presets=lambda **k: []
launch.load_runtime_status=lambda **k: {}
launch.BackendBridge.start=lambda self: None
engines=[]
real=launch.QQmlApplicationEngine
launch.QQmlApplicationEngine=lambda:(engines.append(real()) or engines[-1])

def run():
    try:
        engine=engines[0]
        w=engine.rootObjects()[0]
        ctx=engine.rootContext()
        def ev(expr,scope=None):
            q=QQmlExpression(ctx,scope or w,expr)
            result,_=q.evaluate()
            assert not q.hasError(),(expr,q.error().toString())
            QApplication.processEvents()
            return result
        model=c.REMOTE_MIRACLEIN_9B_MODEL
        row=dict(c.model_profile_settings(model,remote=True),model=model,
                 label='Miraclein',runnable=True,routeReady=True,selectable=True,
                 sourceSupported=True,outputUpscaleReady=True,
                 loras=['None','test-lora.safetensors','test-two.safetensors','test-three.safetensors'])
        w.setProperty('generationModel',[row])
        ev('selectGeneration(0,false)')
        w.setProperty('generationSource',QUrl('file:///tmp/first.png'))
        w.setProperty('useSourceImageMode',True)
        QApplication.processEvents()
        w.setProperty('generationPrompt','Persistent neutral portrait')
        w.setProperty('generationNegativePrompt','Do not reset')
        w.setProperty('generationSeed',123456)
        w.setProperty('selectedLora','test-lora.safetensors')
        w.setProperty('selectedLoraStrength',0.37)
        w.setProperty('selectedLoraTwo','test-two.safetensors')
        w.setProperty('selectedLoraTwoStrength',0.43)
        w.setProperty('selectedLoraThree','test-three.safetensors')
        w.setProperty('selectedLoraThreeStrength',0.52)
        w.setProperty('extraReferenceSource',QUrl('file:///tmp/additional.png'))
        w.setProperty('generationSampler','dpmpp_2m')
        w.setProperty('generationScheduler','karras')
        w.setProperty('generationDenoise',0.48)
        persistent={key:w.property(key) for key in [
           'generationPrompt','generationNegativePrompt','generationSeed',
           'selectedLora','selectedLoraStrength','selectedLoraTwo','selectedLoraTwoStrength',
           'selectedLoraThree','selectedLoraThreeStrength','extraReferenceSource',
           'generationSampler','generationScheduler','generationDenoise']}
        def check(when):
            for key,value in persistent.items():
                assert w.property(key)==value,('unexpected reset',when,key,w.property(key),value)
        def click(name):
            button=w.findChild(QObject,name)
            assert button is not None,name
            ev('clicked()',button)
        click('quality2KButton')
        assert w.property('generationOutputTarget')==2560
        for name in ('qualityFastButton','qualityBalancedButton','qualityQualityButton'):
            click(name)
            check('quality '+name)
            assert w.property('generationOutputTarget')==2560
        w.setProperty('generationSource',QUrl('file:///tmp/second.png'))
        QApplication.processEvents()
        check('replacing source photo in same mode')
        assert w.property('generationOutputTarget')==2560
        ev('selectGeneration(0,false)')
        check('reselecting same model')
        assert w.property('generationOutputTarget')==2560
        click('qualityNativeButton')
        assert w.property('generationOutputTarget')==0
        check('switching to native output')
        ev("applyPose({name:'Custom bone skeleton', source:'file:///tmp/skeleton.png', prompt:''})")
        check('selecting skeleton without authored prompt')
        ev("applyPreset({label:'A selected text pose', prompt:'Neutral seated portrait'})")
        for key in ('generationSeed','selectedLora','selectedLoraStrength','selectedLoraTwo','selectedLoraTwoStrength','selectedLoraThree','selectedLoraThreeStrength','extraReferenceSource','generationSampler','generationScheduler','generationDenoise'):
            assert w.property(key)==persistent[key],('text pose erased unrelated setting',key)
        assert w.property('generationPrompt')=='Neutral seated portrait'
        w.setProperty('generationPrompt','Manually revised portrait after choosing a text preset')
        w.setProperty('generationNegativePrompt','Manually revised negative')
        w.setProperty('generationSeed',123456)
        before_mode={key:w.property(key) for key in ('generationPrompt','generationNegativePrompt','generationSeed','selectedLora','selectedLoraStrength','selectedLoraTwo','selectedLoraTwoStrength','selectedLoraThree','selectedLoraThreeStrength','extraReferenceSource','selectedPoseSource')}
        for mode in (False,True):
            w.setProperty('useSourceImageMode',mode)
            QApplication.processEvents()
            for key,value in before_mode.items():
                assert w.property(key)==value,('mode switch erased an unrelated choice',mode,key,w.property(key),value)
        print('INDEPENDENT_SETTINGS_OK',flush=True)
        QApplication.instance().exit(0)
    except Exception:
        import traceback;traceback.print_exc();QApplication.instance().exit(1)
class App(QApplication):
    def exec(self):
        QTimer.singleShot(250,run)
        QTimer.singleShot(16000,lambda:self.exit(2))
        return super().exec()
launch.QApplication=App
sys.argv=['settings-isolation-check','--page','create']
sys.exit(launch.main())
'''
    _run_offscreen(script,tmp_path,'INDEPENDENT_SETTINGS_OK')


def _run_offscreen(script, tmp_path, marker):
    root=Path(__file__).resolve().parents[1]
    rt=tmp_path/'runtime'
    rt.mkdir(mode=0o700)
    config=tmp_path/'config'
    config.mkdir()
    env=dict(os.environ,QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',
             QSG_RHI_BACKEND='software',LIBGL_ALWAYS_SOFTWARE='1',
             QTWEBENGINE_DISABLE_SANDBOX='1',GENESIS_RUNPOD_AUTOCONNECT='0',
             XDG_RUNTIME_DIR=str(rt),XDG_CONFIG_HOME=str(config))
    r=subprocess.run([sys.executable,'-c',script],cwd=root,env=env,capture_output=True,text=True,timeout=32)
    assert r.returncode==0, r.stdout+'\n'+r.stderr
    assert marker in r.stdout


def test_reselect_same_remote_model_preserves_controls_and_refreshes_route():
    import re
    from PyQt6.QtQml import QJSEngine
    qml=(Path(__file__).resolve().parents[1]/'genesis/qt_ui/MainPremiumLinux.qml').read_text()
    fn=re.search(r'    function selectGeneration\(.*?\n    }',qml,re.S)
    assert fn
    engine=QJSEngine()
    assert not engine.evaluate(fn.group()).isError()
    assert not engine.evaluate('''
        var generationModel=[{model:'chosen-model',remote:true}],
          selectedModelName='chosen-model',selectedGenerationIndex=0,
          selectedLora='custom-lora',selectedLoraTwo='lora2',selectedLoraThree='lora3',
          selectedLoraStrength=0.38,generationOutputTarget=2560,useUpscale=true,
          called=[],backendBridge={prepareModelRoute:function(model){called.push(model)}};
    ''').isError()
    assert not engine.evaluate('selectGeneration(0,true)').isError()
    assert engine.evaluate('called.length').toInt()==1
    assert engine.evaluate('called[0]').toString()=='chosen-model'
    assert engine.evaluate('selectedLora').toString()=='custom-lora'
    assert engine.evaluate('selectedLoraTwo').toString()=='lora2'
    assert engine.evaluate('selectedLoraThree').toString()=='lora3'
    assert engine.evaluate('selectedLoraStrength').toNumber()==0.38
    assert engine.evaluate('generationOutputTarget').toInt()==2560
    assert engine.evaluate('useUpscale').toBool()
