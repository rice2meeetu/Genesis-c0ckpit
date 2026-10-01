import os
from pathlib import Path
import subprocess
import sys
from PIL import Image


def test_canvas_new_size_dialog_and_transform_controls(tmp_path):
    source = tmp_path / 'layer.png'
    Image.new('RGB', (80,40), 'blue').save(source)
    script = r'''
import sys, os
from PyQt6.QtCore import QObject, QTimer, QPoint, Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQml import QQmlExpression
from PyQt6.QtTest import QTest
import qt_cockpit_linux_premium as launcher
launcher.load_pose_items = lambda **kwargs: []
launcher.load_grok_preset_items = lambda: []
launcher.load_curated_pose_presets = lambda: []
launcher.BackendBridge.start = lambda self: None
engines=[]
real_engine=launcher.QQmlApplicationEngine
def make_engine():
    e=real_engine(); engines.append(e); return e
launcher.QQmlApplicationEngine=make_engine

def verify():
    try:
        engine=engines[0]; window=engine.rootObjects()[0]
        bridge=engine.rootContext().contextProperty('canvasBridge')
        button=window.findChild(QObject,'canvasNewButton')
        QQmlExpression(engine.rootContext(),button,'clicked()').evaluate()
        dialog=window.findChild(QObject,'canvasSizeDialog')
        assert dialog.property('visible')
        window.findChild(QObject,'canvasWidthInput').setProperty('value',640)
        window.findChild(QObject,'canvasHeightInput').setProperty('value',480)
        QQmlExpression(engine.rootContext(),dialog,'accept()').evaluate()
        QTest.qWait(80)
        assert (bridge.canvasWidth,bridge.canvasHeight)==(640,480)
        assert window.findChild(QObject,'composition').property('visible')
        bridge.setCanvasSize(800,600); bridge.undo()
        assert bridge.canvasWidth==640
        bridge.addImage(os.environ['CANVAS_TEST_IMAGE'])
        tool=window.findChild(QObject,'canvasResizeTool')
        QQmlExpression(engine.rootContext(),tool,'clicked()').evaluate()
        QTest.qWait(100)
        composition=window.findChild(QObject,'composition')
        expression=QQmlExpression(engine.rootContext(),composition,
            "(function(){for(var i=0;i<children.length;i++) if(children[i].objectName==='canvasLayerItem') return children[i];})()")
        layer,_=expression.evaluate()
        if hasattr(layer,'toQObject'): layer=layer.toQObject()
        handle=layer.findChild(QObject,'layerResizeHandle')
        assert handle.property('visible')
        point,_=QQmlExpression(engine.rootContext(),handle,'mapToItem(null, width/2, height/2)').evaluate()
        if hasattr(point,'toVariant'): point=point.toVariant()
        start=QPoint(round(point['x']),round(point['y'])) if isinstance(point,dict) else QPoint(round(point.x()),round(point.y()))
        history_before = len(bridge.document._undo)
        width_before = layer.property('width')
        QTest.mousePress(window,Qt.MouseButton.LeftButton,pos=start)
        QTest.mouseMove(window,start+QPoint(30,15),delay=30)
        QTest.qWait(30)
        assert layer.property('width') > width_before, 'Resize must preview before release'
        assert bridge.selected['width'] == 80, 'Preview must not mutate document'
        assert len(bridge.document._undo) == history_before
        QTest.mouseRelease(window,Qt.MouseButton.LeftButton,pos=start+QPoint(30,15))
        QTest.qWait(50)
        assert bridge.selected['width'] > 80, bridge.selected
        assert len(bridge.document._undo) == history_before + 1
        bridge.undo()
        assert bridge.selected['width'] == 80
        print('CANVAS_UI_OK')
        QApplication.instance().exit(0)
    except Exception:
        import traceback; traceback.print_exc(); QApplication.instance().exit(1)
class App(QApplication):
    def exec(self):
        QTimer.singleShot(150,verify)
        QTimer.singleShot(8000,lambda:self.exit(2))
        return super().exec()
launcher.QApplication=App
sys.argv=['canvas-ui-test','--page','edit']
sys.exit(launcher.main())
'''
    env=dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software', XDG_RUNTIME_DIR=str(tmp_path/'runtime'), CANVAS_TEST_IMAGE=str(source))
    result=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).resolve().parents[1],env=env,capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'CANVAS_UI_OK' in result.stdout
