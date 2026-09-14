from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QML = PROJECT_ROOT / "genesis" / "qt_ui" / "MainPremium.qml"
LAUNCHER = PROJECT_ROOT / "qt_cockpit_premium.py"
BAT = PROJECT_ROOT / "START_GENESIS_PREMIUM_WINDOWS.bat"
BUILD_SCRIPT = PROJECT_ROOT / "build-windows.ps1"
REQUIREMENTS = PROJECT_ROOT / "requirements-windows.txt"
WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "windows-premium-ui.yml"
INSTALLER = PROJECT_ROOT / "installer" / "GENESIS-c0ckpit.iss"


def test_premium_ui_files_exist():
    assert QML.is_file()
    assert LAUNCHER.is_file()
    assert BAT.is_file()
    assert BUILD_SCRIPT.is_file()
    assert REQUIREMENTS.is_file()
    assert WORKFLOW.is_file()
    assert INSTALLER.is_file()


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
    assert "source: appRoot.generationSource" in source
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


def test_premium_launcher_has_deterministic_smoke_mode():
    source = LAUNCHER.read_text(encoding="utf-8")
    assert 'parser.add_argument("--smoke", action="store_true")' in source
    assert "elif args.smoke:" in source
    assert "QTimer.singleShot(1200, app.quit)" in source


def test_packaged_tool_routes_relaunch_same_executable():
    source = LAUNCHER.read_text(encoding="utf-8")
    assert 'parser.add_argument("--legacy-page", choices=LEGACY_TOOL_PAGES)' in source
    assert 'parser.add_argument("--tool-smoke", action="store_true")' in source
    assert 'command = [sys.executable, "--legacy-page", page]' in source
    assert 'str(PROJECT_ROOT / "qt_cockpit_premium.py")' in source
    assert '[sys.executable, str(PROJECT_ROOT / "main.py")]' not in source
    assert 'from main import PhotoStudio' in source
    assert 'legacy._show_photo_tools_mode(requested)' in source


def test_packaged_tool_action_mapping_covers_media_requirements():
    source = LAUNCHER.read_text(encoding="utf-8")
    for token in (
        '"background"',
        '"batch"',
        '"enhance"',
        '"upscale"',
        '"canvas"',
        '"duplicate"',
        '"face organiser"',
        '"media viewer"',
        '"photos"',
    ):
        assert token in source


def test_windows_background_removal_backend_is_packaged():
    requirements = REQUIREMENTS.read_text(encoding="utf-8")
    build = BUILD_SCRIPT.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "rembg[cpu]==2.0.84" in requirements
    assert "CPUExecutionProvider" in build
    assert "--collect-all rembg" in build
    assert "Verify background removal backend" in workflow
    assert "CPUExecutionProvider" in workflow
    assert "--collect-all rembg" in workflow


def test_windows_package_uses_premium_entry_point_and_reference_data():
    source = BUILD_SCRIPT.read_text(encoding="utf-8")
    package_line = next(line for line in source.splitlines() if "pyinstaller.exe" in line)
    assert package_line.rstrip().endswith("qt_cockpit_premium.py")
    assert not package_line.rstrip().endswith("qt_cockpit.py")
    assert "genesis\\qt_ui;genesis\\qt_ui" in package_line
    assert "genesis\\assets;genesis\\assets" in package_line
    assert "genesis\\reference;genesis\\reference" in package_line


def test_windows_ci_smokes_integrated_and_packaged_premium_app():
    source = WORKFLOW.read_text(encoding="utf-8")
    assert "Smoke integrated premium QML pages" in source
    assert "--page home --width 1400 --height 900 --smoke" in source
    assert "--page poses --width 1400 --height 900 --smoke" in source
    assert "--page create --width 1400 --height 900 --smoke" in source
    assert "Build packaged premium Windows app" in source
    assert "Smoke packaged premium Windows app" in source
    assert "--tool-smoke" in source
    assert "GENESIS-c0ckpit-Windows.zip" in source


def test_windows_installer_is_built_and_smoked():
    installer = INSTALLER.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    build = BUILD_SCRIPT.read_text(encoding="utf-8")
    assert 'Source: "..\\dist\\GENESIS-c0ckpit\\*"' in installer
    assert "GENESIS-c0ckpit-Setup" in installer
    assert "PrivilegesRequired=lowest" in installer
    assert "Create a desktop shortcut" in installer
    assert "Build Windows installer" in workflow
    assert "Smoke installed Windows app" in workflow
    assert "installer-output/GENESIS-c0ckpit-Setup.exe" in workflow
    assert "[switch]$Installer" in build
    assert "Inno Setup 6 is required for -Installer" in build
