"""Verify bundled pose discovery and the actual premium Qt pose UI."""
import json
import os
from pathlib import Path
import subprocess
import sys

import qt_cockpit as cockpit


def test_bundled_library_wins_over_legacy_index(tmp_path, monkeypatch):
    bundled = tmp_path / 'genesis/reference/assets/pose_library'
    bundled.mkdir(parents=True)
    (bundled / 'control.png').write_bytes(b'control')
    (bundled / 'index.json').write_text(json.dumps([
        {'path': 'control.png', 'name': 'Imported control', 'category': 'Imported'}]))
    monkeypatch.setattr(cockpit, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(cockpit, 'POSE_INDEX', tmp_path / 'missing-legacy.json')
    rows = cockpit.load_pose_items(limit=600)
    assert len(rows) == 1
    assert rows[0]['source'] == (bundled / 'control.png').as_uri()


def test_legacy_library_fallback(tmp_path, monkeypatch):
    legacy = tmp_path / 'AI/GENESIS_POSE_MAKER/assets/pose_library'
    legacy.mkdir(parents=True)
    (legacy / 'control.png').write_bytes(b'control')
    index = tmp_path / 'legacy.json'
    index.write_text(json.dumps([{'path': 'control.png', 'name': 'Legacy'}]))
    monkeypatch.setattr(cockpit, 'PROJECT_ROOT', tmp_path / 'unbundled-project')
    monkeypatch.setattr(cockpit, 'POSE_INDEX', index)
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: tmp_path))
    assert cockpit.load_pose_items()[0]['source'] == (legacy / 'control.png').as_uri()


def test_imported_collection_in_premium_ui(tmp_path):
    script = r'''
import sys
from pathlib import Path
from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQml import QQmlExpression
import qt_cockpit_linux_premium as launcher
launcher.load_grok_preset_items = lambda: []
launcher.load_curated_pose_presets = lambda **kwargs: []
launcher.BackendBridge.start = lambda self: None
real_engine = launcher.QQmlApplicationEngine
engines = []
def make_engine():
    engine = real_engine()
    engines.append(engine)
    return engine
launcher.QQmlApplicationEngine = make_engine

def verify():
    try:
        engine = engines[0]
        window = engine.rootObjects()[0]
        def evaluate(code):
            expression = QQmlExpression(engine.rootContext(), window, code)
            value, _ = expression.evaluate()
            assert not expression.hasError(), expression.error().toString()
            return value
        assert evaluate('poseModel.length') == 587
        window.setProperty('poseSearch', '100Lewd')
        assert evaluate('filteredPoses().length') == 101
        window.setProperty('poseCategory', '100Lewd')
        assert evaluate('filteredPoses().length') == 101
        rows = launcher.load_pose_items(limit=600)
        imported = [r for r in rows if '100Lewd' in r['category']]
        assert len(imported) == 101
        for row in imported:
            path = Path(QUrl(row['source']).toLocalFile())
            assert '/poses/' in str(path) and '/references/' not in str(path)
            assert not QImage(str(path)).isNull(), str(path)
        window.setProperty('generationSource', QUrl('file:///untouched-master.png'))
        for i in range(101):
            evaluate(f'applyPose(filteredPoses()[{i}])')
            assert 'NSFW_100Lewd_v20/poses/' in window.property('selectedPoseSource').toString()
            assert window.property('generationSource').toString() == 'file:///untouched-master.png'
        window.setProperty('poseSearch', '100Lewd 101')
        assert evaluate('filteredPoses().length') == 1
        window.setProperty('poseSearch', '')
        window.setProperty('poseCategory', 'All')
        assert evaluate('filteredPoses().length') == 587
        assert not engine.rootContext().contextProperty('genesisBridge').busy
        print('POSE_UI_OK: 587 browsable, 101 imported controls selectable', flush=True)
        QApplication.instance().exit(0)
    except Exception:
        import traceback
        traceback.print_exc()
        QApplication.instance().exit(1)
class CheckedApplication(QApplication):
    def exec(self):
        QTimer.singleShot(600, verify)
        QTimer.singleShot(12000, lambda: self.exit(2))
        return super().exec()
launcher.QApplication = CheckedApplication
sys.argv = ['genesis-pose-check', '--page', 'poses']
sys.exit(launcher.main())
'''
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
               QSG_RHI_BACKEND='software', LIBGL_ALWAYS_SOFTWARE='1',
               XDG_RUNTIME_DIR=str(tmp_path / 'runtime'))
    result = subprocess.run([sys.executable, '-c', script],
                            cwd=Path(__file__).resolve().parents[1], env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'POSE_UI_OK' in result.stdout
