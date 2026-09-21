import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: chat
    required property var bridge
    property bool compact: false
    signal expandRequested()
    signal collapseRequested()
    color: "#0b0b0b"
    radius: 16
    border.color: "#876536"
    clip: true

    component GoldButton: Button {
        id: control
        implicitHeight: 36
        padding: 10
        contentItem: Text {
            text: control.text; color: control.enabled ? "#eed3a0" : "#77736b"
            font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 9; color: control.down ? "#40311b" : (control.hovered ? "#2c251a" : "#151412")
            border.color: control.enabled ? "#a27b43" : "#44413b"
        }
    }

    Image {
        anchors.fill: parent
        source: "../assets/feefee-scene-reference.jpg"
        // Only the scene: excludes the reference's navigation and fake controls.
        sourceClipRect: Qt.rect(215, 156, 1065, 652)
        fillMode: Image.PreserveAspectCrop
        opacity: chat.compact ? 0.18 : 1
        visible: chat.bridge.messages.length === 0
    }
    Rectangle {
        anchors.fill: parent
        visible: chat.bridge.messages.length === 0
        gradient: Gradient {
            GradientStop { position: 0; color: "#70000000" }
            GradientStop { position: 0.6; color: "#00000000" }
            GradientStop { position: 1; color: "#ef080808" }
        }
    }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: chat.compact ? 14 : 24; spacing: 12
        RowLayout {
            Layout.fillWidth: true
            Rectangle {
                width: 42; height: 42; radius: 21; color: "#1c1913"; border.color: "#b68a47"; clip: true
                Image {
                    anchors.fill: parent; anchors.margins: 3
                    source: "../assets/feefee-avatar-reference.jpg"
                    sourceClipRect: Qt.rect(164, 0, 514, 514)
                    fillMode: Image.PreserveAspectFit
                }
            }
            ColumnLayout {
                spacing: 2; Layout.fillWidth: true
                Text { text: "FEEFEE"; color: "#f4d8a2"; font.pixelSize: chat.compact ? 17 : 24; font.letterSpacing: 2; font.bold: true }
                Text { text: "Your AI companion"; color: "#c7bba5"; font.pixelSize: 12 }
            }
            GoldButton { text: chat.compact ? "Expand ↗" : "Quick chat ↘"; onClicked: chat.compact ? chat.expandRequested() : chat.collapseRequested() }
            GoldButton { visible: chat.compact; text: "×"; onClicked: chat.collapseRequested(); Accessible.name: "Close FeeFee chat" }
        }

        ListView {
            id: conversation
            objectName: chat.compact ? "feefeeQuickMessages" : "feefeeFullMessages"
            Layout.fillWidth: true; Layout.fillHeight: true
            clip: true; spacing: 12
            model: chat.bridge.messages
            onCountChanged: Qt.callLater(positionViewAtEnd)
            delegate: Item {
                required property var modelData
                width: conversation.width
                height: bubble.height
                Rectangle {
                    id: bubble
                    anchors.right: modelData.role === "user" ? parent.right : undefined
                    width: Math.min(parent.width * 0.92, 820)
                    height: messageColumn.implicitHeight + 24
                    color: modelData.role === "user" ? "#30281b" : "#191919"
                    radius: 12; border.color: modelData.role === "user" ? "#806238" : "#343434"
                    Column {
                        id: messageColumn
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        anchors.margins: 12; spacing: 7
                        Text { text: modelData.role === "user" ? "You" : "FeeFee"; color: "#cfaa6d"; font.bold: true; font.pixelSize: 12 }
                        TextEdit {
                            width: parent.width; text: modelData.content
                            readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap
                            textFormat: TextEdit.PlainText; color: "#e9e7e3"; font.pixelSize: chat.compact ? 13 : 15
                        }
                    }
                }
            }
            ScrollBar.vertical: ScrollBar {}
        }
        Text {
            visible: chat.bridge.messages.length === 0 && chat.compact
            Layout.fillWidth: true; text: "Small cat. Big ideas.\nWhat are we working on?"
            color: "#e7d1ac"; font.pixelSize: 19; wrapMode: Text.Wrap
        }
        RowLayout {
            Layout.fillWidth: true
            visible: !chat.compact
            Repeater {
                model: [
                    {label:"Help with a prompt", prompt:"Help me improve this image prompt: "},
                    {label:"Find a LoRA", prompt:"Help me choose a compatible local LoRA for: "},
                    {label:"Explain workflow", prompt:"Explain this GENESIS workflow: "},
                    {label:"System info", prompt:"Explain my current GENESIS system status: "}
                ]
                GoldButton { Layout.fillWidth: true; text: modelData.label; onClicked: { chat.bridge.setDraft(modelData.prompt); input.forceActiveFocus() } }
            }
        }
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: chat.compact ? 94 : 86
            color: "#ed0d0d0d"; radius: 13; border.color: "#b28a50"; border.width: 1
            RowLayout {
                anchors.fill: parent; anchors.margins: 10
                ScrollView {
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                    TextArea {
                        id: input
                        objectName: chat.compact ? "feefeeQuickInput" : "feefeeFullInput"
                        text: chat.bridge.draft
                        onTextChanged: if (activeFocus) chat.bridge.setDraft(text)
                        placeholderText: "Ask FeeFee anything…"
                        color: "#f0ede6"; placeholderTextColor: "#aaa393"; font.pixelSize: 15
                        wrapMode: TextEdit.Wrap; background: Item {}
                        Keys.onReturnPressed: function(event) {
                            if (!(event.modifiers & Qt.ShiftModifier)) { chat.bridge.sendDraft(); event.accepted = true }
                            else event.accepted = false
                        }
                    }
                }
                GoldButton {
                    text: chat.bridge.busy ? "…" : "Send ↑"
                    enabled: !chat.bridge.busy && !chat.bridge.inferencePaused && chat.bridge.draft.trim().length > 0
                    onClicked: chat.bridge.sendDraft()
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 6
            ComboBox {
                model: ["CHAT", "BUILD", "STUDIO"]
                currentIndex: model.indexOf(chat.bridge.mode)
                onActivated: chat.bridge.setMode(currentText)
                implicitWidth: 104
                palette.button: "#191919"; palette.buttonText: "#eed3a0"
                palette.base: "#191919"; palette.text: "#eed3a0"; palette.window: "#191919"
            }
            ComboBox {
                visible: !chat.compact
                model: ["AUTO", "LOCAL", "CLOUD"]
                currentIndex: model.indexOf(chat.bridge.provider)
                onActivated: chat.bridge.setProvider(currentText)
                implicitWidth: 112
                palette.button: "#191919"; palette.buttonText: "#eed3a0"
                palette.base: "#191919"; palette.text: "#eed3a0"; palette.window: "#191919"
            }
            Text {
                Layout.fillWidth: true; text: chat.bridge.inferencePaused ? "AI replies paused · GPU investigation" : chat.bridge.status
                color: "#c4b89f"; font.pixelSize: 11; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
            }
            GoldButton { text: "Clear"; enabled: !chat.bridge.busy; onClicked: chat.bridge.clearChat() }
        }
    }
}
