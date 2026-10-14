"""Exercise FaceID controls in the real premium QML without network or GPU jobs."""
import os
from pathlib import Path
import subprocess
import sys

import qt_cockpit as cockpit


def test_faceid_profile_capability_matches_supported_models():
    for model in cockpit.REMOTE_SDXL_MODELS:
        assert cockpit.model_profile_settings(model)["faceidSupported"]
    for model in (cockpit.FOUR_B_MODEL, cockpit.QWEN_MODEL, *cockpit.REMOTE_SD15_MODELS):
        assert not cockpit.model_profile_settings(model)["faceidSupported"]


def test_faceid_source_model_and_preset_transitions(tmp_path):
    script = r'''
import sys
from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtSlot
from PyQt6.QtQml import QQmlExpression
from PyQt6.QtWidgets import QApplication
import qt_cockpit as cockpit
import qt_cockpit_linux_premium as launcher

master = "file:///tmp/person-a-front.png"
body = "file:///tmp/person-a-back.png"
substitutions = []
submissions = []


class CapturingBridge(cockpit.GenerationBridge):
    @pyqtSlot(str, str, int, int, str, str, str, str, str, bool, bool, bool,
              int, float, int, float, str, str, str, float, float, float)
    def queueGenerateAdvanced(self, *args):
        submissions.append((args, self._sdxl_faceid_enabled))

    @pyqtSlot(str, result=str)
    def characterIdentitySource(self, character_id):
        return master

    @pyqtSlot(str, str, result=str)
    def characterReferenceSource(self, character_id, instruction):
        substitutions.append(instruction)
        return body

    @pyqtSlot("QVariantMap", str, result="QVariantMap")
    def posePresetPayload(self, row, model):
        return {"prompt": "Person A full body, back view",
                "settings": {"denoise": 0.9}}


launcher.GenerationBridge = CapturingBridge
launcher.load_pose_items = lambda **kwargs: []
launcher.load_grok_preset_items = lambda: []
launcher.load_curated_pose_presets = lambda **kwargs: []
launcher.load_runtime_status = lambda **kwargs: {"identityEngines": []}
launcher.BackendBridge.start = lambda self: None
engines = []
factory = launcher.QQmlApplicationEngine
launcher.QQmlApplicationEngine = lambda: (engines.append(factory()) or engines[-1])


def verify():
    try:
        engine = engines[0]
        window = engine.rootObjects()[0]
        context = engine.rootContext()
        bridge = context.contextProperty("genesisBridge")
        bridge._character_a = "person-a"

        def evaluate(code, scope=None):
            expression = QQmlExpression(context, scope or window, code)
            value, _ = expression.evaluate()
            assert not expression.hasError(), expression.error().toString()
            QApplication.processEvents()
            return value

        rows = []
        for model in (cockpit.REMOTE_DONUTS_MODEL, cockpit.REMOTE_BIGLUSTY_DONUT_MODEL,
                      cockpit.FOUR_B_MODEL, cockpit.QWEN_MODEL):
            rows.append({"model": model, "label": model, "runnable": True,
                         "sourceSupported": True, "loras": ["None"],
                         **cockpit.model_profile_settings(model)})
        window.setProperty("generationModel", rows)
        evaluate("selectGeneration(0, false)")
        toggle = window.findChild(QObject, "sdxlFaceIDToggle")
        assert toggle is not None and toggle.property("enabled")

        # Enabling first, then picking a source, must keep the identity default.
        window.setProperty("sdxlFaceIDEnabled", True)
        window.setProperty("useSourceImageMode", True)
        window.setProperty("generationSource", QUrl(master))
        QApplication.processEvents()
        assert window.property("sdxlFaceIDActive")
        assert window.property("generationDenoise") == 0.55

        # Another source, pose preset, quality preset and SDXL model must not
        # restore the ordinary 0.65/1.0 defaults or preset denoise of 0.9.
        window.setProperty("generationSource", QUrl("file:///tmp/person-a-second.png"))
        assert window.property("generationDenoise") == 0.55
        evaluate('applyPose({source:"file:///tmp/skeleton.png", name:"Back view"})')
        assert window.property("generationDenoise") == 0.55
        evaluate('applyQualityPreset("Quality", 1024, 1024)')
        assert window.property("generationDenoise") == 0.55
        evaluate("selectGeneration(1, false)")
        assert window.property("sdxlFaceIDActive")
        assert window.property("generationDenoise") == 0.55

        # The source shown to the user stays the FaceID source, even for a
        # prompt which normally selects a character's back/body reference.
        window.setProperty("generationSource", QUrl(master))
        window.setProperty("generationPrompt", "Person A full body, back view")
        window.setProperty("generationDenoise", 0.60)
        evaluate("generateCurrent()")
        assert submissions[-1][0][7] == master
        assert submissions[-1][0][15] == 0.60
        assert submissions[-1][1] is True
        assert substitutions == []

        # A different family disables FaceID and receives its own defaults.
        evaluate("clearPose()")
        evaluate("selectGeneration(2, false)")
        assert not window.property("sdxlFaceIDEnabled")
        assert not window.property("sdxlFaceIDActive")
        assert not toggle.property("enabled")
        expected = cockpit.model_profile_settings(cockpit.FOUR_B_MODEL)["sourceDefaults"]["defaultDenoise"]
        assert window.property("generationDenoise") == expected
        evaluate("generateCurrent()")
        assert submissions[-1][1] is False
        assert submissions[-1][0][7] == body
        assert len(substitutions) == 1
        evaluate("selectGeneration(3, false)")
        assert not window.property("sdxlFaceIDActive")
        expected = cockpit.model_profile_settings(cockpit.QWEN_MODEL)["sourceDefaults"]["defaultDenoise"]
        assert window.property("generationDenoise") == expected

        # Returning to SDXL retains opt-in behavior.
        evaluate("selectGeneration(0, false)")
        assert not window.property("sdxlFaceIDActive")
        assert toggle.property("enabled")
        assert window.property("generationDenoise") == 0.65
        print("FACEID_QML_TRANSITIONS_OK")
        QApplication.instance().exit(0)
    except Exception:
        import traceback
        traceback.print_exc()
        QApplication.instance().exit(1)


class CheckedApp(QApplication):
    def exec(self):
        QTimer.singleShot(150, verify)
        QTimer.singleShot(12000, lambda: self.exit(2))
        return super().exec()


launcher.QApplication = CheckedApp
sys.argv = ["faceid-qml-test", "--page", "create"]
sys.exit(launcher.main())
'''
    runtime = tmp_path / "runtime"
    runtime.mkdir(mode=0o700)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", XDG_RUNTIME_DIR=str(runtime),
               QTWEBENGINE_DISABLE_SANDBOX="1", QT_QUICK_BACKEND="software",
               QSG_RHI_BACKEND="software", LIBGL_ALWAYS_SOFTWARE="1",
               GENESIS_RUNPOD_AUTOCONNECT="0")
    result = subprocess.run([sys.executable, "-c", script],
                            cwd=Path(__file__).resolve().parents[1], env=env,
                            text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "FACEID_QML_TRANSITIONS_OK" in result.stdout
