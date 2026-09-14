from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QML = ROOT / "genesis" / "qt_ui" / "MainPremiumLinux.qml"
LAUNCHER = ROOT / "qt_cockpit_linux_premium.py"
SHELL_LAUNCHER = ROOT / "launch-qt-cockpit.sh"


def source() -> str:
    return QML.read_text(encoding="utf-8")


def test_premium_linux_qml_exists():
    assert QML.is_file()
    assert "GENESIS c0ckpit · Linux" in source()
    assert "Keep walking Allan." in source()


def test_source_image_is_a_real_preview_not_filename_only():
    qml = source()
    assert 'text: "Load Source Image"' in qml
    assert "genesisBridge.chooseSourceImage()" in qml
    assert "source: appRoot.generationSource" in qml
    assert "fillMode: Image.PreserveAspectFit" in qml
    assert "DropArea" in qml
    assert "Source image stays loaded when you change presets" in qml


def test_easy_presets_are_first_class_visual_controls():
    qml = source()
    assert 'text: "2 · EASY PRESETS"' in qml
    assert 'model: ["All", "Full 70", "Curated 18"]' in qml
    assert "model: appRoot.filteredPresets()" in qml
    assert "appRoot.applyPreset(modelData)" in qml
    assert 'text: "Browse Full Visual Pose Library"' in qml


def test_full_pose_browser_and_source_controls_are_available_together():
    qml = source()
    assert "model: appRoot.filteredPoses()" in qml
    assert "appRoot.applyPose(modelData)" in qml
    assert 'titleText: "Pose Library"' in qml
    assert '"Load Source Image"' in qml
    assert 'text: "Use Pose in Create"' in qml


def test_generation_keeps_model_lora_and_stage_controls():
    qml = source()
    assert 'text: "3 · MODEL / WORKFLOW"' in qml
    assert 'text: "COMPATIBLE LORA"' in qml
    assert 'text: "Stage 2 · refine"' in qml
    assert 'text: "Stage 3 · identity lock"' in qml
    assert 'text: "Final upscale"' in qml
    assert "genesisBridge.queueGenerate(" in qml


def test_linux_launcher_loads_full_pose_index_and_premium_qml():
    launcher = LAUNCHER.read_text(encoding="utf-8")
    assert "load_pose_items(limit=600)" in launcher
    assert 'UI_ROOT / "MainPremiumLinux.qml"' in launcher
    assert '"settings": 10' in launcher


def test_shell_launcher_uses_premium_entrypoint():
    shell = SHELL_LAUNCHER.read_text(encoding="utf-8")
    assert "qt_cockpit_linux_premium.py" in shell
