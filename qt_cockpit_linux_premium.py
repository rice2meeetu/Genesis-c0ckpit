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
import sys
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, QUrl
from PyQt6.QtGui import QIcon
from PyQt6.QtQml import QQmlApplicationEngine, QQmlExpression
from PyQt6.QtWidgets import QApplication

from genesis.assistant_bridge import AssistantBridge
from genesis.media_bridge import MediaBridge
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
}

AI_NAV_MARKER = '        {icon:"☷", label:"Settings", page:10}'
STACK_END_MARKER = "\n            }\n        }\n    }\n}"

AI_PAGE_QML = r'''

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 10
                        PageHeader {
                            titleText: "GENESIS AI"
                            subtitleText: "Private local assistant — chat, build and studio modes on your own GPU."
                            iconText: "AI"
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 10

                            Panel {
                                Layout.preferredWidth: 275
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 9
                                    SectionLabel { text: "ASSISTANT MODE" }
                                    GButton {
                                        Layout.fillWidth: true
                                        text: "CHAT · ROCINANTE"
                                        active: assistantBridge.mode === "CHAT"
                                        onClicked: assistantBridge.setMode("CHAT")
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: "General private conversation · Rocinante-X-12B Q5_K_M"
                                        color: appRoot.textDim
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                    }
                                    GButton {
                                        Layout.fillWidth: true
                                        text: "BUILD · QWEN CODER"
                                        active: assistantBridge.mode === "BUILD"
                                        onClicked: assistantBridge.setMode("BUILD")
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: "Coding, debugging and GENESIS engineering · Qwen3-Coder-30B-A3B"
                                        color: appRoot.textDim
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                    }
                                    GButton {
                                        Layout.fillWidth: true
                                        text: "STUDIO · QWEN"
                                        active: assistantBridge.mode === "STUDIO"
                                        onClicked: assistantBridge.setMode("STUDIO")
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: "Prompts, models, LoRAs, poses and ComfyUI workflow help"
                                        color: appRoot.textDim
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                    }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: appRoot.line }
                                    SectionLabel { text: "ACTIVE MODEL" }
                                    Text {
                                        Layout.fillWidth: true
                                        text: assistantBridge.activeModel
                                        color: appRoot.brightGold
                                        font.pixelSize: 15
                                        font.bold: true
                                        wrapMode: Text.Wrap
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: "Local only · prompts stay on this machine"
                                        color: appRoot.success
                                        font.pixelSize: 11
                                        wrapMode: Text.Wrap
                                    }
                                    Item { Layout.fillHeight: true }
                                    GButton { Layout.fillWidth: true; text: "Clear Chat"; onClicked: assistantBridge.clearChat() }
                                }
                            }

                            Panel {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 14
                                    spacing: 9
                                    RowLayout {
                                        Layout.fillWidth: true
                                        SectionLabel { text: "CONVERSATION" }
                                        Item { Layout.fillWidth: true }
                                        Text {
                                            text: assistantBridge.busy ? "● WORKING" : "● READY"
                                            color: assistantBridge.busy ? appRoot.gold : appRoot.success
                                            font.pixelSize: 10
                                            font.bold: true
                                        }
                                    }
                                    ScrollView {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        clip: true
                                        TextArea {
                                            id: assistantTranscript
                                            text: assistantBridge.transcript
                                            readOnly: true
                                            selectByMouse: true
                                            color: appRoot.textMain
                                            font.pixelSize: 13
                                            wrapMode: TextEdit.Wrap
                                            background: Rectangle { color: "#080d12"; border.color: appRoot.line; radius: 9 }
                                            onTextChanged: cursorPosition = length
                                        }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: assistantBridge.status
                                        color: assistantBridge.busy ? appRoot.gold : appRoot.textDim
                                        font.pixelSize: 11
                                        elide: Text.ElideRight
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        TextArea {
                                            id: assistantInput
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 82
                                            placeholderText: assistantBridge.mode === "CHAT" ? "Talk to GENESIS…" : (assistantBridge.mode === "BUILD" ? "What should we build or fix?" : "Ask about prompts, models, LoRAs or workflows…")
                                            color: appRoot.textMain
                                            wrapMode: TextEdit.Wrap
                                            background: Rectangle { color: "#080d12"; border.color: appRoot.line; radius: 9 }
                                        }
                                        GButton {
                                            Layout.preferredWidth: 120
                                            Layout.preferredHeight: 82
                                            text: assistantBridge.busy ? "WORKING…" : "SEND"
                                            active: !assistantBridge.busy && assistantInput.text.trim().length > 0
                                            enabled: !assistantBridge.busy && assistantInput.text.trim().length > 0
                                            onClicked: {
                                                assistantBridge.sendMessage(assistantInput.text)
                                                assistantInput.text = ""
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
'''


def compose_premium_qml(source: str) -> str:
    """Inject the dedicated GENESIS AI nav entry and page into the premium shell."""
    if AI_NAV_MARKER not in source:
        raise ValueError("Premium Linux QML settings nav marker changed.")
    source = source.replace(
        AI_NAV_MARKER,
        '        {icon:"✦", label:"GENESIS AI", page:11},\n' + AI_NAV_MARKER,
        1,
    )
    stack_end = source.rfind(STACK_END_MARKER)
    if stack_end < 0:
        raise ValueError("Premium Linux QML stack boundary changed.")
    return source[:stack_end] + AI_PAGE_QML + source[stack_end:]


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--screenshot")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--page", choices=tuple(PAGE_INDEXES), default="create")
    args, qt_args = parser.parse_known_args()

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
    context.setContextProperty("generationProfiles", load_generation_profiles())
    context.setContextProperty("runtimeStatus", load_runtime_status())

    generation_bridge = GenerationBridge(app)
    layout_bridge = LayoutSettingsBridge(app)
    module_bridge = ModuleBridge(app)
    assistant_bridge = AssistantBridge(app)
    media_bridge = MediaBridge(app)
    context.setContextProperty("genesisBridge", generation_bridge)
    context.setContextProperty("genesisLayout", layout_bridge)
    context.setContextProperty("moduleBridge", module_bridge)
    context.setContextProperty("assistantBridge", assistant_bridge)
    context.setContextProperty("mediaBridge", media_bridge)

    qml_path = UI_ROOT / "MainPremiumLinux.qml"
    qml_source = compose_premium_qml(qml_path.read_text(encoding="utf-8"))
    engine.loadData(qml_source.encode("utf-8"), QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1

    window = engine.rootObjects()[0]
    window.setProperty("pageIndex", PAGE_INDEXES[args.page])
    if args.width or args.height:
        window.resize(max(1120, args.width or window.width()), max(720, args.height or window.height()))

    if args.screenshot:
        window.show()
        target = Path(args.screenshot).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        def save_screenshot() -> None:
            # Capture our own scene graph. This also works when the distro has
            # Qt Quick QML plugins but no Python PyQt6.QtQuick bindings.
            capture_item = window.findChild(QObject, "genesisMainWorkspace")
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
