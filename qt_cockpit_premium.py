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
from PyQt6.QtQuick import QQuickWindow, QSGRendererInterface
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

POSE_PAGE_HEADER = (
    'PageHeader { titleText: "Pose Library"; subtitleText: "Visual preset browser — '
    'choose geometry first, then send it straight to Create."; iconText: "♟" }'
)
WORKFLOW_PAGE_HEADER = (
    'PageHeader { titleText: "Workflow Studio"; subtitleText: "Inspect, validate and '
    'launch the generation pipelines behind GENESIS."; iconText: "◇" }'
)

POSE_PAGE_QML = r'''
                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 9
                        PageHeader { titleText: "Pose Library"; subtitleText: "Full preset collections and the indexed OpenPose library — searchable, visual and ready for Create."; iconText: "♟" }
                        PremiumPoseBrowser {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            gold: appRoot.gold
                            brightGold: appRoot.brightGold
                            ice: appRoot.ice
                            panel: appRoot.panel
                            raised: appRoot.raised
                            line: appRoot.line
                            textMain: appRoot.textMain
                            textDim: appRoot.textDim
                            sourceImage: appRoot.generationSource
                            onSourceImageRequested: appRoot.chooseSource()
                            onItemChosen: function(source, name, category, prompt, collection) {
                                appRoot.selectedPoseSource = source
                                appRoot.selectedPoseName = name
                                appRoot.selectedPoseCategory = category
                                appRoot.selectedPosePrompt = prompt
                            }
                            onUseInCreate: function(source, name, category, prompt, collection) {
                                appRoot.selectedPoseSource = source
                                appRoot.selectedPoseName = name
                                appRoot.selectedPoseCategory = category
                                appRoot.selectedPosePrompt = prompt
                                if (prompt.length > 0)
                                    appRoot.generationPrompt = prompt
                                appRoot.pageIndex = 1
                            }
                        }
                    }
                }

'''


def compose_premium_qml(source: str | None = None) -> str:
    """Replace only the legacy Pose Library page with the virtualized browser.

    Keeping the replacement in the launcher avoids a risky whole-file rewrite of
    the large reviewed QML shell while GitHub is the only available editor.  The
    marker check is intentionally strict: if the shell changes, startup fails
    instead of silently composing the wrong page.
    """
    if source is None:
        source = (UI_ROOT / "MainPremium.qml").read_text(encoding="utf-8")
    pose_header = source.find(POSE_PAGE_HEADER)
    workflow_header = source.find(WORKFLOW_PAGE_HEADER)
    if pose_header < 0 or workflow_header < 0 or workflow_header <= pose_header:
        raise ValueError("Premium QML page markers changed; refusing unsafe composition.")
    pose_start = source.rfind("\n                Item {", 0, pose_header)
    workflow_start = source.rfind("\n                Item {", 0, workflow_header)
    if pose_start < 0 or workflow_start < 0 or workflow_start <= pose_start:
        raise ValueError("Premium QML page boundaries are invalid; refusing unsafe composition.")
    pose_start += 1
    workflow_start += 1
    return source[:pose_start] + POSE_PAGE_QML + source[workflow_start:]


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
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    args, qt_args = parser.parse_known_args()
    sys.argv = [sys.argv[0], *qt_args]

    if args.screenshot or args.smoke:
        # Headless Windows runners need an explicit Qt Quick software renderer.
        # This must be selected before the first QQuickWindow is constructed.
        QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Software)

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

    try:
        qml_source = compose_premium_qml()
    except (OSError, ValueError) as exc:
        print(f"GENESIS premium composition failed: {exc}", file=sys.stderr)
        return 1
    engine.loadData(
        qml_source.encode("utf-8"),
        QUrl.fromLocalFile(str(UI_ROOT / "MainPremium.qml")),
    )
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
        capture_state = {"attempt": 0, "result": None}

        def retry_capture(reason: str) -> None:
            capture_state["attempt"] += 1
            if capture_state["attempt"] >= 12:
                print(f"GENESIS premium screenshot failed: {reason}", file=sys.stderr)
                app.exit(2)
                return
            QTimer.singleShot(250, start_capture)

        def finish_capture(result) -> None:
            if result.saveToFile(str(target)):
                app.quit()
                return
            retry_capture("Qt Quick item grab could not be saved")

        def start_capture() -> None:
            content_item = window.contentItem()
            if content_item is None or content_item.width() <= 0 or content_item.height() <= 0:
                retry_capture("premium content item is not ready")
                return
            window.requestUpdate()
            result = content_item.grabToImage()
            if result is None:
                retry_capture("Qt Quick item grab could not be started")
                return
            capture_state["result"] = result
            result.ready.connect(lambda: finish_capture(result))

        QTimer.singleShot(750, start_capture)
    elif args.smoke:
        # Full integrated startup validation for graphics-less CI runners.
        # The QML shell must compose, instantiate, show and process events before
        # the timer exits successfully; no fragile framebuffer capture required.
        window.show()
        QTimer.singleShot(1200, app.quit)
    else:
        window.showMaximized()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
