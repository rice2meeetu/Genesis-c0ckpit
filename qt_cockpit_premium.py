"""Launch the premium section-by-section GENESIS Windows UI.

This entry point deliberately reuses the existing, tested GENESIS bridges from
``qt_cockpit.py``.  It gives the redesigned QML its own launch target while the
current Main.qml remains available as a recovery path.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtGui import QIcon
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWidgets import QApplication

from qt_cockpit import (
    ASSET_ROOT,
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
    context.setContextProperty("poseItems", load_pose_items())
    context.setContextProperty("grokPresetItems", load_grok_preset_items())
    context.setContextProperty("curatedPosePresets", load_curated_pose_presets())
    context.setContextProperty("generationProfiles", load_generation_profiles())
    context.setContextProperty("runtimeStatus", load_runtime_status())

    generation_bridge = GenerationBridge(app)
    layout_bridge = LayoutSettingsBridge(app)
    module_bridge = ModuleBridge(app)
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
