"""Launch the premium Linux GENESIS c0ckpit UI.

This launcher reuses the established Linux generation/backend bridges from
``qt_cockpit.py`` while loading the premium task-first QML shell. It keeps the
full local pose index available, restores the local GENESIS AI workspace, and
exposes the same validated model, LoRA, workflow, media and service actions as
the existing cockpit backend.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from PyQt6.QtCore import QObject, QLockFile, QTimer, QUrl
from PyQt6.QtGui import QIcon
from PyQt6.QtQml import QQmlApplicationEngine, QQmlExpression
from PyQt6.QtWidgets import QApplication

from genesis.assistant_bridge import AssistantBridge
from genesis.media_bridge import MediaBridge
from genesis.canvas_bridge import CanvasBridge
from genesis.backend_bridge import BackendBridge
from qt_cockpit import (
    ASSET_ROOT,
    PROJECT_ROOT,
    UI_ROOT,
    GenerationBridge,
    LayoutSettingsBridge,
    ModuleBridge,
    RemoteRuntimeMonitor,
    load_curated_pose_presets,
    load_generation_profiles,
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
    "ai": 11,
    "face-swap": 12,
}

AI_NAV_MARKER = '        {icon:"☷", label:"Settings", page:10}'
STACK_END_MARKER = "\n            }\n        }\n    }\n}"
FACE_SWAP_STACK_MARKER = "\n                // GENESIS_FACE_SWAP_PAGE"

AI_PAGE_QML = r'''
                Item {
                    objectName: "assistantWorkspace"
                    FeeFeeChat {
                        anchors.fill: parent
                        bridge: assistantBridge
                        onCollapseRequested: { appRoot.pageIndex = appRoot.lastWorkspacePage; appRoot.feefeeOpen = true }
                    }
                }
'''



FEEFEE_OVERLAY_QML = '\n    Item {\n        id: feefeeDock\n        parent: genesisScene\n        objectName: "feefeeDock"\n        anchors.left: parent.left; anchors.bottom: parent.bottom\n        anchors.leftMargin: 20; anchors.bottomMargin: 22\n        width: 76; height: 76; z: 100\n        visible: appRoot.pageIndex !== 11\n        Rectangle {\n            anchors.fill: parent; radius: 38\n            color: "#15130f"; border.color: "#c59b58"; border.width: 2\n            Image { anchors.fill: parent; anchors.margins: 7; source: "../assets/feefee-avatar-reference.jpg"; sourceClipRect: Qt.rect(164,0,514,514); fillMode: Image.PreserveAspectFit }\n        }\n        MouseArea {\n            anchors.fill: parent; cursorShape: Qt.PointingHandCursor\n            onClicked: appRoot.feefeeOpen = !appRoot.feefeeOpen\n        }\n        Accessible.name: "Open FeeFee chat"\n        Keys.onReturnPressed: appRoot.feefeeOpen = !appRoot.feefeeOpen\n        activeFocusOnTab: true\n        Text { anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; anchors.bottomMargin: -15; text: "FeeFee"; color: "#e3c68f"; font.pixelSize: 11 }\n    }\n    FeeFeeChat {\n        id: feefeeQuickChat\n        parent: genesisScene\n        objectName: "feefeeQuickChat"\n        anchors.left: parent.left; anchors.bottom: parent.bottom\n        anchors.leftMargin: 108; anchors.bottomMargin: 22\n        width: Math.min(460, appRoot.width - 140)\n        height: Math.min(590, appRoot.height - 130)\n        z: 101\n        compact: true; bridge: assistantBridge\n        visible: appRoot.feefeeOpen && appRoot.pageIndex !== 11\n        onExpandRequested: { appRoot.feefeeOpen = false; appRoot.pageIndex = 11 }\n        onCollapseRequested: appRoot.feefeeOpen = false\n    }\n'

def compose_premium_qml(source: str) -> str:
    """Inject the dedicated GENESIS AI nav entry and page into the premium shell."""
    if AI_NAV_MARKER not in source:
        raise ValueError("Premium Linux QML settings nav marker changed.")
    source = source.replace(
        AI_NAV_MARKER,
        '        {icon:"🐾", label:"AI Assistant", page:11},\n' + AI_NAV_MARKER,
        1,
    )
    face_swap_start = source.find(FACE_SWAP_STACK_MARKER)
    if source.count(FACE_SWAP_STACK_MARKER) != 1:
        raise ValueError("Premium Linux QML Face Swap page boundary changed.")
    # Insert before the complete top-level page, never inside its layout.
    source = source[:face_swap_start] + AI_PAGE_QML + source[face_swap_start:]
    root_end = source.rfind("\n}")
    return source[:root_end] + FEEFEE_OVERLAY_QML + source[root_end:]


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--screenshot")
    parser.add_argument("--review-image", help="Local image for CPU-only screenshot review")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--page", choices=tuple(PAGE_INDEXES), default="create")
    args, qt_args = parser.parse_known_args()

    runtime_dir = Path(os.environ.get("XDG_RUNTIME_DIR") or "/tmp")
    runtime_dir.mkdir(parents=True, exist_ok=True)
    singleton_lock = QLockFile(str(runtime_dir / "genesis-cockpit-premium.lock"))
    singleton_lock.setStaleLockTime(0)
    if not singleton_lock.tryLock(0):
        return 0

    sys.argv = [sys.argv[0], *qt_args]
    app = QApplication(sys.argv)
    app.setApplicationName("GENESIS c0ckpit")
    app.setWindowIcon(QIcon(str(PROJECT_ROOT / "genesis/assets/genesis-cockpit-icon-balanced-final.png")))

    engine = QQmlApplicationEngine()
    context = engine.rootContext()
    context.setContextProperty("genesisAssetRoot", QUrl.fromLocalFile(str(ASSET_ROOT) + "/"))
    context.setContextProperty("genesisUiRoot", QUrl.fromLocalFile(str(UI_ROOT) + "/"))
    context.setContextProperty("poseItems", load_pose_items(limit=600))
    context.setContextProperty("grokPresetItems", load_grok_preset_items())
    context.setContextProperty("curatedPosePresets", load_curated_pose_presets())
    context.setContextProperty("generationProfiles", [])
    context.setContextProperty("runtimeStatus", load_runtime_status(probe_remote=False))

    generation_bridge = GenerationBridge(app)
    backend_bridge = BackendBridge(generation_bridge, app)
    generation_bridge.backend_router = backend_bridge
    context.setContextProperty("backendBridge", backend_bridge)
    layout_bridge = LayoutSettingsBridge(app)
    module_bridge = ModuleBridge(app)
    assistant_bridge = AssistantBridge(app)
    media_bridge = MediaBridge(app)
    media_bridge.backend_router = backend_bridge
    canvas_bridge = CanvasBridge(app)
    context.setContextProperty("genesisBridge", generation_bridge)
    context.setContextProperty("genesisLayout", layout_bridge)
    context.setContextProperty("moduleBridge", module_bridge)
    context.setContextProperty("assistantBridge", assistant_bridge)
    context.setContextProperty("mediaBridge", media_bridge)
    context.setContextProperty("canvasBridge", canvas_bridge)

    qml_path = UI_ROOT / "MainPremiumLinux.qml"
    qml_source = compose_premium_qml(qml_path.read_text(encoding="utf-8"))
    engine.loadData(qml_source.encode("utf-8"), QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1

    runtime_monitor = None
    if not args.screenshot:
        runtime_monitor = backend_bridge
        runtime_monitor.statusReady.connect(
            lambda status: context.setContextProperty("runtimeStatus", status)
        )
        runtime_monitor.profilesReady.connect(
            lambda profiles: context.setContextProperty("generationProfiles", profiles)
        )
        QTimer.singleShot(0, runtime_monitor.start)

    window = engine.rootObjects()[0]
    window.setProperty("pageIndex", PAGE_INDEXES[args.page])
    if args.screenshot and args.review_image:
        review_image = Path(args.review_image).expanduser().resolve()
        if not review_image.is_file():
            raise ValueError("Review image must be an existing local file")
        review_url = QUrl.fromLocalFile(str(review_image))
        window.setProperty("viewerSource", review_url)
        window.setProperty("editSource", review_url)
    if args.width or args.height:
        window.resize(max(1120, args.width or window.width()), max(720, args.height or window.height()))

    if args.screenshot:
        window.show()
        target = Path(args.screenshot).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        def save_screenshot() -> None:
            # Capture our own scene graph. This also works when the distro has
            # Qt Quick QML plugins but no Python PyQt6.QtQuick bindings.
            capture_item = window.findChild(QObject, "genesisScene")
            if capture_item is None:
                app.exit(2)
                return
            expression = QQmlExpression(
                engine.rootContext(), capture_item,
                "grabToImage(function(result) { "
                "result.saveToFile(" + json.dumps(str(target)) + "); Qt.quit(); })",
            )
            expression.evaluate()
            if expression.hasError():
                print(expression.error().toString(), file=sys.stderr)
                app.exit(2)

        QTimer.singleShot(2500, save_screenshot)
        QTimer.singleShot(15000, lambda: app.exit(2))
    else:
        window.showMaximized()

    result = app.exec()
    if args.screenshot and not target.is_file():
        return 2
    return result


if __name__ == "__main__":
    raise SystemExit(main())
