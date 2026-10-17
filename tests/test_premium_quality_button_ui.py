"""Boot actual premium QML, switch RunPod models, and click quality controls."""
import os
from pathlib import Path
import subprocess
import sys


def test_actual_cockpit_quality_buttons_and_2k4k(tmp_path):
    script=r'''
import json,sys
from PyQt6.QtCore import QTimer,QUrl,QObject,pyqtSlot
from PyQt6.QtQml import QQmlExpression
from PyQt6.QtWidgets import QApplication
import qt_cockpit as c
import qt_cockpit_linux_premium as launch
launch.load_pose_items=lambda **k: []
launch.load_grok_preset_items=lambda: []
launch.load_curated_pose_presets=lambda **kwargs: []
launch.load_runtime_status=lambda **k: {}
launch.BackendBridge.start=lambda self:None
captures=[]
class CaptureQueueBridge(c.GenerationBridge):
    @pyqtSlot(str,str,int,int,str,str,str,str,str,bool,bool,bool,int,float,int,float,str,str,str,float,float,float)
    def enqueueGenerateAdvanced(self,*args):
        captures.append(tuple(args))
        self._pending_generations.append({'label':str(args[0]),'model':str(args[4]),'output':self._output_target_long_edge})
        self.queueChanged.emit()
launch.GenerationBridge=CaptureQueueBridge
engines=[]
factory=launch.QQmlApplicationEngine
launch.QQmlApplicationEngine=lambda:(engines.append(factory()) or engines[-1])

def verify():
    try:
        eng=engines[0];win=eng.rootObjects()[0];ctx=eng.rootContext()
        def evaluate(code,scope=None):
            exp=QQmlExpression(ctx,scope or win,code)
            val,_=exp.evaluate()
            assert not exp.hasError(),f'{code}: {exp.error().toString()}'
            QApplication.processEvents()
            return val
        rows=[]
        for name in [c.REMOTE_PHR00T_V22_GGUF_MODEL,c.REMOTE_PHR00T_V23_GGUF_MODEL,c.REMOTE_MOP_MODEL,c.REMOTE_MIRACLEIN_9B_MODEL]:
            row={'model':name,'label':name,'runnable':True,'selectable':True,'routeReady':True,'sourceSupported':True,'loras':['None']}
            row.update(c.model_profile_settings(name,remote=True))
            rows.append(row)
        win.setProperty('generationModel',rows)
        win.setProperty('generationSource',QUrl('file:///tmp/person.png'))
        win.setProperty('useSourceImageMode',True)
        QApplication.processEvents()
        def nums():return int(win.property('generationWidth')),int(win.property('generationHeight'))
        # Use the real QML button signal instead of calling isolated helper code.
        assert win.findChild(QObject,'qualityQualityButton') is not None
        def quality_click(name):
            assert win.findChild(QObject,'quality'+name+'Button') is not None
            button=win.findChild(QObject,'quality'+name+'Button')
            evaluate('clicked()',button)
        for index,name in enumerate((c.REMOTE_PHR00T_V22_GGUF_MODEL,c.REMOTE_PHR00T_V23_GGUF_MODEL,c.REMOTE_MOP_MODEL,c.REMOTE_MIRACLEIN_9B_MODEL)):
            evaluate(f'selectGeneration({index},false)')
            default=c.model_profile_settings(name,remote=True)['sourceQualityPresets']
            assert nums()==(default['Quality']['width'],default['Quality']['height']),(name,'default',nums(),default)
            for preset in ('Fast','Balanced','Quality'):
                quality_click(preset)
                assert nums()==(default[preset]['width'],default[preset]['height']),(name,preset,nums(),default[preset])
            if name==c.REMOTE_PHR00T_V22_GGUF_MODEL:
                assert nums()==(2264,1360),('v22 quality size is wrong',nums())
                evaluate('clicked()',win.findChild(QObject,'quality2KButton'))
                assert int(win.property('generationOutputTarget'))==2560
                assert bool(win.property('useUpscale'))
                assert nums()==(2264,1360)
                evaluate('clicked()',win.findChild(QObject,'quality4KButton'))
                assert int(win.property('generationOutputTarget'))==3840
                assert nums()==(2264,1360)
        # Local Miraclein Fast changes CFG; other presets restore the model default.
        local = dict(rows[-1], **c.model_profile_settings(c.LOCAL_MIRACLEIN_9B_MODEL))
        win.setProperty('generationModel',[local])
        evaluate('selectGeneration(0,false)')
        for source_mode in (False, True):
            win.setProperty('useSourceImageMode',source_mode)
            QApplication.processEvents()
            for preset in ('Fast','Balanced','Quality'):
                quality_click(preset)
                assert float(win.property('generationCfg')) == (1.0 if preset=='Fast' else 1.1)
                assert int(win.property('generationSteps')) == 12
                assert float(win.property('generationReferenceMegapixels')) == (0.390625 if source_mode and preset=='Fast' else 0.0)
            quality_click('Fast')
            if source_mode:
                win.setProperty('generationReferenceMegapixels',0.0)
                assert not evaluate('qualityPresetActive("Fast",512,512)')
                quality_click('Fast')
            win.setProperty('generationCfg',1.1)
            assert not evaluate('qualityPresetActive("Fast",512,512)')
        quality_click('Fast')
        win.setProperty('generationPrompt','A neutral ceramic mug on a table')
        evaluate('generateCurrent(true)')
        assert float(ctx.contextProperty('genesisBridge')._source_reference_megapixels)==0.390625
        evaluate('clicked()',win.findChild(QObject,'clearWaitingQueueButton'))
        captures.clear()
        win.setProperty('generationModel',rows)
        win.setProperty('useSourceImageMode',True)
        QApplication.processEvents()
        # Exercise actual Add to Queue and Clear Waiting buttons, never GPU.
        evaluate('selectGeneration(0,false)')
        win.setProperty('generationPrompt','A neutral fully clothed portrait')
        evaluate('clicked()',win.findChild(QObject,'qualityQualityButton'))
        queue_button=win.findChild(QObject,'enqueueGenerationButton')
        assert queue_button and queue_button.property('enabled')
        evaluate('clicked()',queue_button)
        assert len(captures)==1
        assert captures[0][4]==c.REMOTE_PHR00T_V22_GGUF_MODEL
        assert captures[0][2:4]==(2264,1360)
        assert int(ctx.contextProperty('genesisBridge').pendingGenerationCount)==1
        clear=win.findChild(QObject,'clearWaitingQueueButton')
        assert clear and clear.property('enabled')
        evaluate('clicked()',clear)
        assert int(ctx.contextProperty('genesisBridge').pendingGenerationCount)==0
        print('PREMIUM_UI_QUALITY_BUTTONS_AND_QUEUE_OK')
        QApplication.instance().exit(0)
    except Exception:
        import traceback;traceback.print_exc();QApplication.instance().exit(1)
class CheckedApp(QApplication):
    def exec(self):
        QTimer.singleShot(300,verify)
        QTimer.singleShot(15000,lambda:self.exit(2))
        return super().exec()
launch.QApplication=CheckedApp
sys.argv=['quality-ui-test','--page','create']
sys.exit(launch.main())
'''
    runtime=tmp_path/'runtime';runtime.mkdir(mode=0o700)
    env=os.environ.copy();env.update(QT_QPA_PLATFORM='offscreen',XDG_RUNTIME_DIR=str(runtime),
        QTWEBENGINE_DISABLE_SANDBOX='1',QT_QUICK_BACKEND='software',QSG_RHI_BACKEND='software',
        LIBGL_ALWAYS_SOFTWARE='1',GENESIS_RUNPOD_AUTOCONNECT='0')
    result=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).resolve().parents[1],
          capture_output=True,text=True,timeout=30,env=env)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'PREMIUM_UI_QUALITY_BUTTONS_AND_QUEUE_OK' in result.stdout
