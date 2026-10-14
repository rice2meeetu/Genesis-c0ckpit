"""Offscreen QML regression: mode switching must route the actual image inputs."""
import os
import subprocess
import sys
from pathlib import Path


def test_text_image_modes_preserve_loaded_photo_but_route_only_requested_inputs(tmp_path):
    script = r'''
import sys
from PyQt6.QtCore import QTimer, QUrl, QObject, pyqtSlot
from PyQt6.QtQml import QQmlExpression
from PyQt6.QtWidgets import QApplication
import qt_cockpit as c
import qt_cockpit_linux_premium as l

calls = []
class RecordingBridge(c.GenerationBridge):
    @pyqtSlot(str,str,int,int,str,str,str,str,str,bool,bool,bool,int,float,int,float,str,str,str,float,float,float)
    def queueGenerateAdvanced(self,*args):
        calls.append(args)

l.GenerationBridge=RecordingBridge
l.load_pose_items=lambda **kwargs: []
l.load_curated_pose_presets=lambda **kwargs: []
l.load_grok_preset_items=lambda: []
l.load_runtime_status=lambda **kwargs: {}
l.BackendBridge.start=lambda self: None
engines=[]
real_engine=l.QQmlApplicationEngine
l.QQmlApplicationEngine=lambda:(engines.append(real_engine()) or engines[-1])

def run():
    try:
        eng=engines[0]
        win=eng.rootObjects()[0]
        context=eng.rootContext()
        def evalqml(expr):
            q=QQmlExpression(context,win,expr)
            value,_=q.evaluate()
            assert not q.hasError(),q.error().toString()
            QApplication.processEvents()
            return value
        model=c.REMOTE_MIRACLEIN_9B_MODEL
        row=dict(model=model,label='Miraclein',runnable=True,routeReady=True,
                 sourceSupported=True,sourceRequired=False,poseReady=True,
                 poseMethod='Klein image reference',loras=['None'])
        row.update(c.model_profile_settings(model,remote=True))
        win.setProperty('generationModel',[row])
        win.setProperty('generationPrompt','Neutral landscape test')
        source=QUrl.fromLocalFile('/tmp/genesis-mode-source.png').toString()
        pose=QUrl.fromLocalFile('/tmp/genesis-mode-pose.png').toString()
        win.setProperty('generationSource',QUrl(source))
        QApplication.processEvents()
        assert not win.property('useSourceImageMode')
        assert bool(win.property('modeInputsReady'))
        evalqml('generateCurrent(false)')
        assert len(calls)==1 and calls[-1][7]==''
        assert win.findChild(QObject,'textToImageModeButton') is not None
        assert win.findChild(QObject,'imageToImageModeButton') is not None
        win.setProperty('useSourceImageMode',True)
        QApplication.processEvents()
        assert bool(win.property('modeInputsReady'))
        evalqml('generateCurrent(false)')
        assert len(calls)==2 and calls[-1][7]==source
        win.setProperty('selectedPoseSource',QUrl(pose))
        evalqml('generateCurrent(false)')
        assert len(calls)==3 and calls[-1][7]==source and calls[-1][8]==pose
        win.setProperty('useSourceImageMode',False)
        QApplication.processEvents()
        evalqml('generateCurrent(false)')
        assert len(calls)==4 and calls[-1][7]=='' and calls[-1][8]==pose
        assert win.property('generationSource').toString()==source
        win.setProperty('useSourceImageMode',True)
        win.setProperty('generationSource',QUrl())
        QApplication.processEvents()
        assert not win.property('modeInputsReady')
        evalqml('generateCurrent(false)')
        assert len(calls)==4
        assert not win.findChild(QObject,'generateButton').property('enabled')
        print('MODE_INPUT_ROUTE_VERIFIED',flush=True)
        QApplication.instance().exit(0)
    except Exception:
        import traceback
        traceback.print_exc()
        QApplication.instance().exit(1)

class CheckedApplication(QApplication):
    def exec(self):
        QTimer.singleShot(150,run)
        QTimer.singleShot(15000,lambda:self.exit(2))
        return super().exec()
l.QApplication=CheckedApplication
sys.argv=['genesis-mode-test','--page','create']
sys.exit(l.main())
'''
    runtime=tmp_path/'runtime'
    runtime.mkdir(mode=0o700)
    env=dict(os.environ,QT_QPA_PLATFORM='offscreen',XDG_RUNTIME_DIR=str(runtime),
             QTWEBENGINE_DISABLE_SANDBOX='1',QT_QUICK_BACKEND='software',
             QSG_RHI_BACKEND='software',LIBGL_ALWAYS_SOFTWARE='1',
             GENESIS_RUNPOD_AUTOCONNECT='0')
    r=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).resolve().parents[1],
                     env=env,capture_output=True,text=True,timeout=30)
    assert r.returncode==0,r.stdout+'\n'+r.stderr
    assert 'MODE_INPUT_ROUTE_VERIFIED' in r.stdout
