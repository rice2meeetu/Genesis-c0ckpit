"""Exercise actual composed QML routing without starting model services."""
import os
from pathlib import Path
import subprocess
import sys


def test_assistant_and_face_swap_are_distinct_top_level_pages(tmp_path):
    script = r'''
import sys
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QApplication
from PyQt6.QtQml import QQmlExpression
import qt_cockpit_linux_premium as launcher
# Keep real user presets and backend discovery outside this UI test.
launcher.load_pose_items = lambda **kwargs: [{"name": "Standing", "source": "file:///test-pose.png", "prompt": "Standing upright"}]
launcher.load_grok_preset_items = lambda: []
launcher.load_curated_pose_presets = lambda: []
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
        window = engines[0].rootObjects()[0]
        assert not window.property("selectedPoseSource").toString()
        expression = QQmlExpression(engines[0].rootContext(), window,
            "applyPose({name:'Standing', source:'file:///test-pose.png', prompt:'Standing upright'})")
        expression.evaluate()
        assert window.property("selectedPoseName") == "Standing"
        expression = QQmlExpression(engines[0].rootContext(), window,
            "applyPreset({label:'Seated', prompt:'A person seated on a chair'})")
        expression.evaluate()
        assert not window.property("selectedPoseSource").toString()
        assert window.property("generationPrompt") == "A person seated on a chair"
        expression = QQmlExpression(engines[0].rootContext(), window,
            "applyPose({name:'Standing', source:'file:///test-pose.png', prompt:'Standing upright'})")
        expression.evaluate()
        assert window.property("selectedPresetName") == ""
        assert window.property("generationPrompt") == "Standing upright"
        QQmlExpression(engines[0].rootContext(), window,
            "applyPose({name:'Unmapped', source:'file:///test-pose.png', prompt:''})").evaluate()
        assert window.property("generationPrompt") == ""
        QQmlExpression(engines[0].rootContext(), window, "clearPose()").evaluate()
        assistant = window.findChild(QObject, "assistantWorkspace")
        face_swap = window.findChild(QObject, "faceSwapWorkspace")
        assert assistant is not None and face_swap is not None
        assert assistant.parent() is face_swap.parent()
        for index, expected, hidden in [(11, assistant, face_swap), (12, face_swap, assistant)]:
            window.setProperty("pageIndex", index)
            QApplication.processEvents()
            assert expected.property("visible"), (index, "expected page hidden")
            assert not hidden.property("visible"), (index, "wrong page visible")
        window.setProperty("pageIndex", 3)
        media = engines[0].rootContext().contextProperty("mediaBridge")
        workspace = window.findChild(QObject, "mediaToolWorkspace")
        assert workspace is not None
        for key in ["background remover", "batch background", "upscale", "standard resize",
                    "batch upscale", "extract audio", "extract video", "duplicate finder", "face organiser"]:
            media._result_url = "file:///previous-tool-result.png"
            media._duplicate_pairs = [{"left": "/old", "right": "/copy"}]
            expression = QQmlExpression(engines[0].rootContext(), window,
                "openMediaTool(" + repr(key) + ", 'Tool', 'Description', 'Ready')")
            expression.evaluate()
            assert not expression.hasError(), expression.error().toString()
            QApplication.processEvents()
            assert workspace.property("visible"), key
            assert window.property("mediaToolKey") == key
            assert media.resultUrl == "" and media.duplicatePairs == []
            expression = QQmlExpression(engines[0].rootContext(), window, "closeMediaTool()")
            expression.evaluate()
            QApplication.processEvents()
            assert not workspace.property("visible"), key
        window.setProperty("pageIndex", 3)
        QApplication.processEvents()
        keys = ["canvas", "audio video", "media viewer", "organisation", "face swap"]
        repeater = window.findChild(QObject, "mediaCardRepeater")
        assert repeater.property("count") == 5
        cards = []
        for index in range(5):
            value, undefined = QQmlExpression(engines[0].rootContext(), repeater, f"itemAt({index})").evaluate()
            cards.append(value.toQObject() if hasattr(value, "toQObject") else value)
        assert all(card is not None for card in cards)
        window.setProperty("privacyMode", True)
        QApplication.processEvents()
        for card in cards:
            assert not card.findChild(QObject, "mediaArtwork").property("source").toString()
        window.setProperty("privacyMode", False)
        QApplication.processEvents()
        for card in cards:
            assert card.findChild(QObject, "mediaArtwork").property("source").toString()
        for removed in ["upscale", "standard resize", "batch upscale"]:
            assert window.findChild(QObject, "mediaOpen_" + removed) is None
        for key, actions in [("canvas", ["canvas", "background remover", "batch background"]),
                             ("audio video", ["extract audio", "extract video"]),
                             ("organisation", ["duplicate finder", "face organiser"])]:
            menu = cards[keys.index(key)].findChild(QObject, "mediaMenu_" + key)
            assert menu.property("count") == len(actions), (key, menu.property("count"))
            for index, action in enumerate(actions):
                expression = QQmlExpression(engines[0].rootContext(), menu, f"itemAt({index}).triggered()")
                expression.evaluate()
                assert not expression.hasError(), expression.error().toString()
                if action == "canvas":
                    assert window.property("pageIndex") == 8
                else:
                    assert window.property("mediaToolKey") == action
                window.setProperty("pageIndex", 3)
                QQmlExpression(engines[0].rootContext(), window, "closeMediaTool()").evaluate()
        for key, page in [("media viewer", 4), ("face swap", 12)]:
            button = cards[keys.index(key)].findChild(QObject, "mediaOpen_" + key)
            QQmlExpression(engines[0].rootContext(), button, "clicked()").evaluate()
            assert window.property("pageIndex") == page
        window.setProperty("pageIndex", 3)
        for width in [1120, 1600, 2048]:
            window.resize(width, 1000)
            QApplication.processEvents()
            # Let Qt Quick polish the responsive layout before checking bounds.
            from PyQt6.QtTest import QTest
            QTest.qWait(50)
            for card in cards:
                assert card.property("width") > 250
                assert card.property("height") >= 250
            if width >= 1600:
                assert abs(cards[0].property("width") - cards[1].property("width")) < 2
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
               QSG_RHI_BACKEND="software", LIBGL_ALWAYS_SOFTWARE="1",
               XDG_RUNTIME_DIR=str(tmp_path / "runtime"))
    result = subprocess.run([sys.executable, "-c", script],
                            cwd=Path(__file__).resolve().parents[1], env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "NAVIGATION_OK" in result.stdout
