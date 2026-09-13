"""Launch the premium section-by-section GENESIS Windows UI.

This entry point deliberately reuses the established GENESIS generation bridge
from ``qt_cockpit.py`` while providing Windows-native module launching and the
full local pose index to the premium QML.  The original ``Main.qml`` remains a
recovery path until the premium frontend passes Windows smoke verification.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QTimer, QUrl, pyqtSlot
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWidgets import QApplication

from genesis import integrations
from qt_cockpit import (
    ASSET_ROOT,
    OUTPUT_DIR,
    PROJECT_ROOT,
    UI_ROOT,
    GenerationBridge,
    LayoutSettingsBridge,
    ModuleBridge,
    load_curated_pose_presets,
    load_generation_profiles,
    load_grok_preset_items,
    load_pose_items,
    load_runtime_status,
)


PAGE_INDEXES = {
    "home": 0,
    "create": 1,
    "poses": 2,
    "workflow": 3,
    "media": 4,
    "library": 5,
    "cameras": 6,
    "entertainment": 7,
    "system": 8,
    "edit": 9,
    "posemaker": 10,
    "settings": 11,
}


class PremiumModuleBridge(ModuleBridge):
    """Windows-safe launcher routes for the premium frontend.

    The legacy bridge contains Linux service-manager and Flatpak assumptions.
    This subclass keeps the same QML API but uses endpoint checks, Explorer,
    Task Manager, and the current repository location on Windows. Unknown
    creative-tool actions still open the preserved GENESIS workspace rather
    than pretending a native implementation exists.
    """

    def _open_path_or_url(self, target: str | Path, label: str) -> None:
        text = str(target)
        url = QUrl(text) if text.startswith(("http://", "https://")) else QUrl.fromLocalFile(text)
        ok = QDesktopServices.openUrl(url)
        self._set_status(f"{label} opened" if ok else f"Could not open {label}")

    def _launch_legacy_workspace(self, action: str) -> None:
        try:
            kwargs: dict = {
                "cwd": str(PROJECT_ROOT),
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
            }
            if os.name == "nt":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            else:
                kwargs["start_new_session"] = True
            subprocess.Popen([sys.executable, str(PROJECT_ROOT / "main.py")], **kwargs)
            self._set_status(f"{action} · GENESIS workspace opened")
        except OSError as exc:
            self._set_status(f"{action} failed · {exc}")

    def _open_endpoint(self, url: str, health_path: str, label: str) -> None:
        def worker() -> None:
            if integrations.endpoint_online(url, health_path):
                self._open_path_or_url(url, label)
            else:
                self._set_status(f"{label} is offline · start its local service, then retry")

        self._set_status(f"Checking {label}…")
        threading.Thread(target=worker, daemon=True).start()

    @pyqtSlot(str)
    def triggerAction(self, action: str) -> None:
        key = action.strip().lower()
        if not key:
            return
        if key in {"refresh", "health check"}:
            self.refresh()
            return
        if any(word in key for word in ("output", "export", "save current", "save all")):
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            self._open_path_or_url(OUTPUT_DIR, "GENESIS exports")
            return
        if any(word in key for word in ("workflow", "json", "nodes", "preflight", "validate")):
            self._open_path_or_url(PROJECT_ROOT / "genesis" / "reference" / "pose_workflows", "GENESIS workflows")
            return
        if any(word in key for word in ("camera", "recordings", "go2rtc")):
            self._open_endpoint(integrations.GO2RTC_URL, "/api/streams", "Camera Hub")
            return
        if any(word in key for word in ("jellyfin", "movie", "video library")):
            self._open_endpoint(integrations.JELLYFIN_URL, "/System/Info/Public", "Jellyfin")
            return
        if any(word in key for word in ("sillytavern", "web app", "web apps")):
            self._open_endpoint(integrations.SILLYTAVERN_URL, "/", "SillyTavern")
            return
        if "comfyui" in key or key == "manage service":
            self._open_endpoint(integrations.COMFYUI_URL, "/system_stats", "ComfyUI")
            return
        if "ai settings" in key or "ai assistant" in key or key == "genesis ai":
            self._open_endpoint(integrations.QWEN_URL, "/health", "GENESIS AI")
            return
        if "monitor" in key:
            try:
                if os.name == "nt":
                    subprocess.Popen(["taskmgr.exe"])
                else:
                    subprocess.Popen(["gnome-system-monitor"], start_new_session=True)
                self._set_status("System monitor opened")
            except OSError as exc:
                self._set_status(f"System monitor failed · {exc}")
            return
        if "backup" in key or "recovery" in key:
            target = PROJECT_ROOT / "backups"
            self._open_path_or_url(target if target.exists() else PROJECT_ROOT, "GENESIS recovery")
            return
        if "storage" in key or "model" in key:
            self._open_path_or_url(PROJECT_ROOT.parent, "AI storage")
            return
        if "settings" in key:
            self._open_path_or_url(PROJECT_ROOT, "GENESIS settings")
            return
        self._launch_legacy_workspace(action)


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--page", choices=tuple(PAGE_INDEXES), default="home")
    parser.add_argument("--screenshot")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    args, qt_args = parser.parse_known_args()
    sys.argv = [sys.argv[0], *qt_args]

    app = QApplication(sys.argv)
    app.setApplicationName("GENESIS c0ckpit Premium")
    app.setWindowIcon(QIcon(str(PROJECT_ROOT / "genesis/assets/genesis-cockpit-icon-balanced-final.png")))

    engine = QQmlApplicationEngine()
    context = engine.rootContext()
    context.setContextProperty("genesisAssetRoot", QUrl.fromLocalFile(str(ASSET_ROOT) + "/"))
    context.setContextProperty("genesisUiRoot", QUrl.fromLocalFile(str(UI_ROOT) + "/"))
    # GridView in the premium UI virtualizes delegates, so exposing the complete
    # indexed pose collection is safe and avoids the old 12-pose preview limit.
    context.setContextProperty("poseItems", load_pose_items(limit=600))
    context.setContextProperty("grokPresetItems", load_grok_preset_items())
    context.setContextProperty("curatedPosePresets", load_curated_pose_presets())
    context.setContextProperty("generationProfiles", load_generation_profiles())
    context.setContextProperty("runtimeStatus", load_runtime_status())

    generation_bridge = GenerationBridge(app)
    layout_bridge = LayoutSettingsBridge(app)
    module_bridge = PremiumModuleBridge(app)
    context.setContextProperty("genesisBridge", generation_bridge)
    context.setContextProperty("genesisLayout", layout_bridge)
    context.setContextProperty("moduleBridge", module_bridge)

    engine.load(QUrl.fromLocalFile(str(UI_ROOT / "MainPremium.qml")))
    if not engine.rootObjects():
        return 1

    window = engine.rootObjects()[0]
    window.setProperty("pageIndex", PAGE_INDEXES[args.page])
    if args.width or args.height:
        window.resize(max(1100, args.width or window.width()), max(700, args.height or window.height()))
    if args.screenshot:
        window.show()
        target = Path(args.screenshot).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        def save_screenshot() -> None:
            def finish_capture(result) -> None:
                image = result.image()
                if image.isNull() or not image.save(str(target)):
                    app.exit(2)
                    return
                app.quit()

            if not window.contentItem().grabToImage(finish_capture):
                app.exit(2)

        QTimer.singleShot(2500, save_screenshot)
    else:
        window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
