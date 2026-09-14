from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QML = PROJECT_ROOT / "genesis" / "qt_ui" / "MainPremium.qml"
LAUNCHER = PROJECT_ROOT / "qt_cockpit_premium.py"
BAT = PROJECT_ROOT / "START_GENESIS_PREMIUM_WINDOWS.bat"
BUILD_SCRIPT = PROJECT_ROOT / "build-windows.ps1"


def test_premium_ui_files_exist():
    assert QML.is_file()
    assert LAUNCHER.is_file()
    assert BAT.is_file()
    assert BUILD_SCRIPT.is_file()


def test_premium_ui_contains_reference_driven_sections():
    source = QML.read_text(encoding="utf-8")
    required = [
        "Image Generation",
        "Pose Library",
        "Workflow Studio",
        "Media Tools",
        "Photo Library",
        "Camera Hub",
        "Entertainment",
        "System Tools",
        "Canvas / Edit",
        "Pose Maker",
        "Settings",
        "Face Organiser",
        "Duplicate Finder",
        "Background Remove",
        "Enhance",
        "Upscale",
    ]
    for label in required:
        assert label in source, label


def test_premium_ui_keeps_real_generation_and_edit_bridges():
    source = QML.read_text(encoding="utf-8")
    assert "genesisBridge.chooseSourceImage()" in source
    assert "genesisBridge.queueGenerate(" in source
    assert "genesisBridge.queueEdit(" in source
    assert "genesisBridge.openPreview()" in source
    assert "genesisBridge.openOutputFolder()" in source
    assert "moduleBridge.triggerAction(" in source


def test_premium_launcher_reuses_existing_backend_bridges():
    source = LAUNCHER.read_text(encoding="utf-8")
    assert "GenerationBridge" in source
    assert "ModuleBridge" in source
    assert 'UI_ROOT / "MainPremium.qml"' in source
    assert '"home": 0' in source
    assert '"settings": 11' in source


def test_premium_launcher_has_headless_safe_capture_path():
    source = LAUNCHER.read_text(encoding="utf-8")
    assert "QQuickWindow.setGraphicsApi" in source
    assert "GraphicsApi.Software" in source
    assert "content_item.grabToImage()" in source
    assert "result.saveToFile" in source


def test_windows_package_uses_premium_entry_point_and_reference_data():
    source = BUILD_SCRIPT.read_text(encoding="utf-8")
    package_line = next(line for line in source.splitlines() if "pyinstaller.exe" in line)
    assert package_line.rstrip().endswith("qt_cockpit_premium.py")
    assert not package_line.rstrip().endswith("qt_cockpit.py")
    assert "genesis\\qt_ui;genesis\\qt_ui" in package_line
    assert "genesis\\assets;genesis\\assets" in package_line
    assert "genesis\\reference;genesis\\reference" in package_line
