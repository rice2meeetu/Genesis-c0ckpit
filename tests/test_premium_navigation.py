"""Exercise actual composed QML routing without starting model services."""
import os
from pathlib import Path
import subprocess
import sys


def test_assistant_and_face_swap_are_distinct_top_level_pages():
    script = r'''
import sys
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QApplication
import qt_cockpit_linux_premium as launcher
real_engine = launcher.QQmlApplicationEngine
engines = []
def make_engine():
    engine = real_engine()
    engines.append(engine)
    return engine
launcher.QQmlApplicationEngine = make_engine

def verify():
    try:
        window = engines[0].rootObjects()[0]
        assistant = window.findChild(QObject, "assistantWorkspace")
        face_swap = window.findChild(QObject, "faceSwapWorkspace")
        assert assistant is not None and face_swap is not None
        assert assistant.parent() is face_swap.parent()
        for index, expected, hidden in [(11, assistant, face_swap), (12, face_swap, assistant)]:
            window.setProperty("pageIndex", index)
            QApplication.processEvents()
            assert expected.property("visible"), (index, "expected page hidden")
            assert not hidden.property("visible"), (index, "wrong page visible")
        print("NAVIGATION_OK", flush=True)
        QApplication.instance().exit(0)
    except Exception:
        import traceback
        traceback.print_exc()
        QApplication.instance().exit(1)

class CheckedApplication(QApplication):
    def exec(self):
        QTimer.singleShot(100, verify)
        QTimer.singleShot(10000, lambda: self.exit(2))
        return super().exec()
launcher.QApplication = CheckedApplication
sys.argv = ["genesis-navigation-check", "--page", "ai"]
sys.exit(launcher.main())
'''
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software",
               QSG_RHI_BACKEND="software", LIBGL_ALWAYS_SOFTWARE="1")
    result = subprocess.run([sys.executable, "-c", script],
                            cwd=Path(__file__).resolve().parents[1], env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "NAVIGATION_OK" in result.stdout
