from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = PROJECT_ROOT / "qt_cockpit_premium.py"
QML = PROJECT_ROOT / "genesis" / "qt_ui" / "MainPremium.qml"


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
