from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = PROJECT_ROOT / "qt_cockpit_premium.py"
QML = PROJECT_ROOT / "genesis" / "qt_ui" / "MainPremium.qml"
POSE_BROWSER = PROJECT_ROOT / "genesis" / "qt_ui" / "PremiumPoseBrowser.qml"


def test_premium_launcher_exposes_full_pose_library():
    source = LAUNCHER.read_text(encoding="utf-8")
    assert "load_pose_items(limit=600)" in source
    assert 'setContextProperty("curatedPosePresets", load_curated_pose_presets())' in source
    assert 'setContextProperty("grokPresetItems", load_grok_preset_items())' in source


def test_premium_launcher_uses_windows_native_bridge():
    source = LAUNCHER.read_text(encoding="utf-8")
    required = [
        "class PremiumModuleBridge",
        "taskmgr.exe",
        "integrations.COMFYUI_URL",
        "integrations.GO2RTC_URL",
        "integrations.JELLYFIN_URL",
        "integrations.SILLYTAVERN_URL",
        "PremiumModuleBridge(app)",
    ]
    for marker in required:
        assert marker in source, marker


def test_premium_pose_ui_keeps_preset_collections_visible():
    source = QML.read_text(encoding="utf-8")
    assert "Pose Library" in source
    assert "Full 70" in source
    assert "Curated 18" in source
    assert "Grok Camera Presets" in source


def test_virtualized_pose_browser_contract():
    assert POSE_BROWSER.is_file()
    source = POSE_BROWSER.read_text(encoding="utf-8")
    required = [
        "GridView",
        "curatedPosePresets",
        "poseItems",
        'browserMode: "Presets"',
        '"Full 70"',
        '"Curated 18"',
        '"OpenPose"',
        "searchText",
        "collectionFilter",
        "categoryFilter",
        "useInCreate",
        "sourceImageRequested",
    ]
    for marker in required:
        assert marker in source, marker


def test_pose_browser_does_not_use_repeater_for_full_pose_grid():
    source = POSE_BROWSER.read_text(encoding="utf-8")
    grid_start = source.index("GridView {")
    grid_end = source.index("Text {\n                    anchors.centerIn: parent", grid_start)
    grid_source = source[grid_start:grid_end]
    assert "model: root.visibleItems" in grid_source
    assert "Repeater" not in grid_source


def test_launcher_composes_pose_browser_into_reviewed_shell():
    source = LAUNCHER.read_text(encoding="utf-8")
    required = [
        "compose_premium_qml",
        "POSE_PAGE_HEADER",
        "WORKFLOW_PAGE_HEADER",
        "PremiumPoseBrowser {",
        "engine.loadData(",
        "onUseInCreate",
    ]
    for marker in required:
        assert marker in source, marker
