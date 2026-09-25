"""Standalone Windows/Intel GENESIS image-generation wrapper.

The wrapper deliberately reuses the tested GENESIS generation bridge while
loading the current premium image-generation QML without Linux-only AI/Grok
injections. It supports either a local ComfyUI endpoint or a configured HTTPS
remote endpoint and keeps model discovery backend-driven.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from PyQt6.QtCore import QLockFile, QTimer, QUrl, pyqtSlot
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWidgets import QApplication

from genesis.backend_bridge import BackendBridge
from genesis.canvas_bridge import CanvasBridge
from genesis.media_bridge import MediaBridge
from qt_cockpit import (
    ASSET_ROOT,
    PROJECT_ROOT,
    UI_ROOT,
    GenerationBridge,
    LayoutSettingsBridge,
    ModuleBridge,
    load_curated_pose_presets,
    load_grok_preset_items,
    load_pose_items,
    load_runtime_status,
)

PAGE_INDEXES = {
    "create": 0,
    "poses": 1,
    "workflow": 2,
    "media": 3,
    "photos": 4,
    "cameras": 5,
    "entertainment": 6,
    "system": 7,
    "edit": 8,
    "posemaker": 9,
    "settings": 10,
    "face-swap": 11,
}


class StandaloneModuleBridge(ModuleBridge):
    """Portable Windows actions; never invokes Linux services or shell tools."""

    @pyqtSlot(str)
    def triggerAction(self, action: str) -> None:
        key = action.strip().lower()
        if not key:
            return
        if any(word in key for word in ("output", "export")):
            target = Path.home() / "GENESIS-Exports"
            target.mkdir(parents=True, exist_ok=True)
            ok = QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
            self._set_status("GENESIS exports opened" if ok else "Could not open GENESIS exports")
            return
        if any(word in key for word in ("workflow", "json", "nodes", "preflight", "validate")):
            root = Path(os.environ.get("GENESIS_COMFYUI_ROOT") or (Path.home() / "ComfyUI"))
            target = Path(os.environ.get("GENESIS_WORKFLOW_ROOT") or (root / "user" / "default" / "workflows"))
            target.mkdir(parents=True, exist_ok=True)
            ok = QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
            self._set_status("ComfyUI workflows opened" if ok else "Could not open ComfyUI workflows")
            return
        if "settings" in key:
            target = Path(os.environ.get("APPDATA") or Path.home()) / "GENESIS"
            target.mkdir(parents=True, exist_ok=True)
            ok = QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
            self._set_status("GENESIS settings opened" if ok else "Could not open GENESIS settings")
            return
        if "comfyui" in key or "backend" in key or key == "refresh":
            self._set_status("Use the Backend controls on Create to refresh or change the ComfyUI endpoint.")
            return
        self._set_status(f"{action} is not included in this standalone image wrapper.")


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--page", choices=tuple(PAGE_INDEXES), default="create")
    parser.add_argument("--smoke", action="store_true")
    args, qt_args = parser.parse_known_args()

    sys.argv = [sys.argv[0], *qt_args]
    app = QApplication(sys.argv)
    app.setApplicationName("GENESIS Brother Image Wrapper")
    icon = PROJECT_ROOT / "genesis/assets/genesis-cockpit-icon-balanced-final.png"
    if icon.is_file():
        app.setWindowIcon(QIcon(str(icon)))

    lock_dir = Path(tempfile.gettempdir())
    lock = QLockFile(str(lock_dir / "genesis-brother-image-wrapper.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        return 0

    engine = QQmlApplicationEngine()
    context = engine.rootContext()
    context.setContextProperty("genesisAssetRoot", QUrl.fromLocalFile(str(ASSET_ROOT) + os.sep))
    context.setContextProperty("genesisUiRoot", QUrl.fromLocalFile(str(UI_ROOT) + os.sep))
    context.setContextProperty("poseItems", load_pose_items(limit=600))
    context.setContextProperty("grokPresetItems", load_grok_preset_items())
    context.setContextProperty("curatedPosePresets", load_curated_pose_presets())
    context.setContextProperty("generationProfiles", [])
    context.setContextProperty("runtimeStatus", load_runtime_status(probe_remote=False))

    generation = GenerationBridge(app)
    backend = BackendBridge(generation, app)
    generation.backend_router = backend
    media = MediaBridge(app)
    media.backend_router = backend
    canvas = CanvasBridge(app)
    layout = LayoutSettingsBridge(app)
    modules = StandaloneModuleBridge(app)

    context.setContextProperty("genesisBridge", generation)
    context.setContextProperty("backendBridge", backend)
    context.setContextProperty("mediaBridge", media)
    context.setContextProperty("canvasBridge", canvas)
    context.setContextProperty("genesisLayout", layout)
    context.setContextProperty("moduleBridge", modules)

    backend.statusReady.connect(lambda value: context.setContextProperty("runtimeStatus", value))
    backend.profilesReady.connect(lambda value: context.setContextProperty("generationProfiles", value))

    qml_path = UI_ROOT / "MainPremiumWindows.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1

    window = engine.rootObjects()[0]
    window.setProperty("pageIndex", PAGE_INDEXES[args.page])
    if args.width or args.height:
        window.resize(max(1120, args.width or window.width()), max(720, args.height or window.height()))

    if args.smoke:
        window.show()
        QTimer.singleShot(1400, app.quit)
    else:
        backend.start()
        window.showMaximized()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
