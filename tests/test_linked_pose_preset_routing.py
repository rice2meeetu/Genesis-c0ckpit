"""Linked skeleton and authored JSON prompt preset regression coverage."""
from pathlib import Path
import os
import subprocess
import sys

import pytest

import qt_cockpit as cockpit

# This locally imported pose collection is deliberately not bundled in the
# public repository. Assert full linked-pose behavior whenever it is installed.
_OPTIONAL_PACK = (
    cockpit.PROJECT_ROOT
    / 'genesis/reference/assets/pose_library/NSFW_100Lewd_v20/poses/1.png'
)
requires_optional_pose_pack = pytest.mark.skipif(
    not _OPTIONAL_PACK.is_file(),
    reason='Optional imported 100Lewd pose assets are not installed',
)


@requires_optional_pose_pack
def test_mapped_pose_prompts_are_real_bundled_skeletons():
    poses = cockpit.load_pose_items(limit=600)
    mapped = [p for p in cockpit.load_curated_pose_presets(pose_rows=poses) if p['collection']=='Linked Pose + JSON Prompt']
    assert len(poses) == 587
    assert len(mapped) == 485
    assert len({p['poseId'] for p in mapped}) == 485
    for pose in mapped:
        assert pose['promptMapped']
        assert Path(pose['source'].replace('file://','')).is_file()
        assert pose['prompt']
        assert pose['poseId'].count('/') == 2
    full70 = [p for p in cockpit.load_curated_pose_presets(pose_rows=poses) if p['id'].startswith('full70:')]
    assert len(full70)==70
    assert all(p['requiresPoseSelection'] and not p.get('source') for p in full70)
    assert all(p['poseHintCategory'] for p in full70)
    assert sum('100Lewd' in p['category'] for p in poses)==101
    assert not any('100Lewd' in p['category'] for p in mapped)


@requires_optional_pose_pack
def test_premium_linked_preset_selects_image_and_prompt_together(tmp_path):
    script=r'''
import sys
from PyQt6.QtCore import QTimer,QObject
from PyQt6.QtQml import QQmlExpression
from PyQt6.QtWidgets import QApplication
import qt_cockpit as c
import qt_cockpit_linux_premium as launch
import genesis.pose_workbench as workbench
from pathlib import Path
workbench.POSE_WORKBENCH_HANDOFF_FILE=Path(sys.argv[1])/'unused-handoff.json'
launch.BackendBridge.start=lambda self:None
launch.load_grok_preset_items=lambda: []
# Personal Curated 18 presets are optional and must not shift linked-pose fixtures.
launch.load_curated_pose_presets=lambda **kwargs: [
    row for row in c.load_curated_pose_presets(**kwargs)
    if row['collection'] != 'Curated 18'
]
launch.load_runtime_status=lambda **kwargs: {}
engines=[]
real=launch.QQmlApplicationEngine
launch.QQmlApplicationEngine=lambda:(engines.append(real()) or engines[-1])
def verify():
 try:
    e=engines[0];w=e.rootObjects()[0];ctx=e.rootContext()
    def evaluate(code):
        exp=QQmlExpression(ctx,w,code)
        value,_=exp.evaluate()
        assert not exp.hasError(),f'{code}: {exp.error().toString()}'
        QApplication.processEvents()
        return value
    assert evaluate('poseModel.length')==587
    assert evaluate('easyPresetModel.length')==555
    # Explicit linked preset loads JSON prompt plus skeleton, independently.
    selected=evaluate('easyPresetModel[70]')
    assert selected['promptMapped'] and selected['source']
    evaluate('applyPreset(easyPresetModel[70])')
    assert w.property('selectedPoseSource').toString()==selected['source']
    assert w.property('generationPrompt')==selected['prompt']
    assert w.property('selectedPresetName')==selected['label']
    # Selecting a different linked preset replaces both without mixing them.
    next_row=evaluate('easyPresetModel[71]')
    evaluate('applyPreset(easyPresetModel[71])')
    assert w.property('selectedPoseSource').toString()==next_row['source']
    assert w.property('generationPrompt')==next_row['prompt']
    # Full 70 cannot silently reuse the pose from an unrelated mapped pair.
    evaluate('applyPreset(easyPresetModel[0])')
    assert not w.property('selectedPoseSource').toString()
    assert not w.property('modeInputsReady')
    assert w.property('poseCategory')=='Kneeling'
    evaluate('clearPose()')
    assert not w.property('modeInputsReady')
    # User must select an actual indexed skeleton image.
    evaluate('applyPose(poseModel[3])')
    assert bool(w.property('selectedPoseSource').toString())
    assert w.property('generationPrompt') # original full70 adapted text retained
    assert bool(w.property('modeInputsReady'))
    print('POSE_PRESET_LINKS_OK')
    QApplication.instance().exit(0)
 except Exception:
    import traceback;traceback.print_exc();QApplication.instance().exit(1)
class App(QApplication):
 def exec(self):
    QTimer.singleShot(150,verify)
    QTimer.singleShot(15000,lambda:self.exit(2))
    return super().exec()
launch.QApplication=App
sys.argv=['pose-linked','--page','create']
sys.exit(launch.main())
'''
    runtime=tmp_path/'runtime';runtime.mkdir(mode=0o700)
    env=dict(os.environ,QT_QPA_PLATFORM='offscreen',XDG_RUNTIME_DIR=str(runtime), XDG_CONFIG_HOME=str(tmp_path/"config"),
             QTWEBENGINE_DISABLE_SANDBOX='1',QT_QUICK_BACKEND='software',QSG_RHI_BACKEND='software',
             LIBGL_ALWAYS_SOFTWARE='1',GENESIS_RUNPOD_AUTOCONNECT='0')
    r=subprocess.run([sys.executable,'-c',script,str(tmp_path)],cwd=Path(__file__).resolve().parents[1],env=env,text=True,capture_output=True,timeout=30)
    assert r.returncode==0,r.stdout+'\n'+r.stderr
    assert 'POSE_PRESET_LINKS_OK' in r.stdout
