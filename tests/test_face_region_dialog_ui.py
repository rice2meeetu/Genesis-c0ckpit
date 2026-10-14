"""Open the actual PyQt Person A selector and exercise both accept/cancel."""
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image


def test_actual_face_region_dialog_accept_and_cancel(tmp_path):
    photo = tmp_path/'test_photo.png'
    Image.new('RGB',(320,240),'silver').save(photo)
    script = '''
import sys
from PyQt6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QLabel, QCheckBox
from PyQt6.QtCore import QTimer, QPoint, Qt
from PyQt6.QtTest import QTest
from genesis.person_a_targeting import choose_face_region, FaceRegion
app=QApplication([])
photo=sys.argv[1]
seen=[]
def interact(accept):
    dialog=next(x for x in app.topLevelWidgets() if isinstance(x,QDialog) and 'Person A' in x.windowTitle())
    button=dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok)
    assert button is not None and not button.isEnabled()
    if accept:
        target=next(x for x in dialog.findChildren(QLabel) if x.pixmap() is not None and x.pixmap().width() > 100)
        QTest.mousePress(target,Qt.MouseButton.LeftButton,pos=QPoint(30,30))
        QTest.mouseRelease(target,Qt.MouseButton.LeftButton,pos=QPoint(135,135))
        check=dialog.findChild(QCheckBox)
        assert not button.isEnabled() and not check.isChecked()
        check.setChecked(True)
        assert button.isEnabled()
        button.click()
    else:
        dialog.reject()
QTimer.singleShot(50,lambda:interact(True))
first=choose_face_region(photo,'source')
assert isinstance(first,FaceRegion),first
assert first.box[0] < first.box[2] and first.box[1] < first.box[3]
first.checked_image(photo)
QTimer.singleShot(50,lambda:interact(False))
second=choose_face_region(photo,'target')
assert second is None
print('FACE_REGION_UI_ACCEPT_CANCEL_OK',first.box)
'''
    env=os.environ.copy()
    env.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software')
    result=subprocess.run([sys.executable,'-c',script,str(photo)],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True,env=env,timeout=20)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'FACE_REGION_UI_ACCEPT_CANCEL_OK' in result.stdout
