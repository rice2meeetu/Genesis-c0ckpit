import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: workspace
    property bool canvasMode: false
    property url sourceUrl: ""
    property url resultUrl: ""
    property string prompt: ""
    property string statusText: "Browse local images to begin."
    property bool busy: false
    property bool showResult: false
    property real zoom: 1
    readonly property url displayedUrl: showResult ? resultUrl : sourceUrl
    signal browseRequested()
    signal canvasRequested(url imageUrl)
    signal resultsRequested()
    signal editRequested(string instructions)
    onSourceUrlChanged: { showResult = false; zoom = 1 }
    onDisplayedUrlChanged: zoom = 1

    component Action: Button {
        palette.buttonText: "#e9e6df"
        background: Rectangle {
            color: parent.down ? "#51412b" : parent.hovered ? "#302719" : "#202020"
            radius: 5; border.color: parent.enabled ? "#635035" : "#343434"
        }
        padding: 9
    }
    component Caption: Label { color: "#c5a267"; font.pixelSize: 11; font.letterSpacing: 1.4 }

    ColumnLayout {
        anchors.fill: parent; spacing: 12
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true; spacing: 4
                Label { text: workspace.canvasMode ? "CANVAS" : "MEDIA VIEWER"; color: "#f3d28b"; font.pixelSize: 23; font.bold: true; font.letterSpacing: 2 }
                Label { text: workspace.canvasMode ? "Compose your edit. Inspect the source and result." : "A quiet space to browse, inspect and choose your next image."; color: "#aaa7a1"; font.pixelSize: 12 }
            }
            Action { text: "Browse images"; onClicked: workspace.browseRequested() }
            Action { text: "Saved results"; onClicked: workspace.resultsRequested() }
            Action { text: "Send to Canvas"; visible: !workspace.canvasMode; enabled: workspace.displayedUrl.toString().length > 0; onClicked: workspace.canvasRequested(workspace.displayedUrl) }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
            Rectangle {
                Layout.preferredWidth: 150; Layout.fillHeight: true
                color: "#141414"; radius: 8; border.color: "#343434"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 12
                    Caption { text: "WORKING IMAGES"; font.pixelSize: 9 }
                    Repeater {
                        model: [{name: "Source", url: workspace.sourceUrl, result: false}, {name: "Latest result", url: workspace.resultUrl, result: true}]
                        delegate: ColumnLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            Rectangle {
                                Layout.fillWidth: true; Layout.preferredHeight: 118
                                color: "#090909"; radius: 5
                                border.color: workspace.showResult === modelData.result ? "#c5a267" : "#343434"
                                Image { anchors.fill: parent; anchors.margins: 6; source: modelData.url; fillMode: Image.PreserveAspectFit; asynchronous: true; sourceSize.width: 220; sourceSize.height: 220 }
                                Label { anchors.centerIn: parent; visible: !modelData.url.toString().length; text: "—"; color: "#666666" }
                                MouseArea { anchors.fill: parent; enabled: modelData.url.toString().length > 0; onClicked: workspace.showResult = modelData.result }
                            }
                            Label { text: modelData.name; color: "#aaa7a1"; font.pixelSize: 11 }
                        }
                    }
                    Item { Layout.fillHeight: true }
                    Label { Layout.fillWidth: true; text: "Source files remain unchanged."; color: "#aaa7a1"; wrapMode: Text.Wrap; font.pixelSize: 11 }
                }
            }
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true
                color: "#090909"; radius: 8; border.color: "#343434"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        Caption { Layout.fillWidth: true; text: workspace.showResult ? "RESULT" : "SOURCE" }
                        Action { text: "−"; enabled: workspace.zoom > 0.25; onClicked: workspace.zoom = Math.max(0.25, workspace.zoom / 1.25) }
                        Label { text: Math.round(workspace.zoom * 100) + "%"; color: "#aaa7a1"; Layout.preferredWidth: 45; horizontalAlignment: Text.AlignHCenter }
                        Action { text: "+"; enabled: workspace.zoom < 4; onClicked: workspace.zoom = Math.min(4, workspace.zoom * 1.25) }
                        Action { text: "Fit"; onClicked: workspace.zoom = 1 }
                    }
                    Flickable {
                        id: stage
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                        contentWidth: Math.max(width, width * workspace.zoom)
                        contentHeight: Math.max(height, height * workspace.zoom)
                        boundsBehavior: Flickable.StopAtBounds
                        Image {
                            id: hero
                            anchors.centerIn: parent
                            width: stage.width * workspace.zoom; height: stage.height * workspace.zoom
                            source: workspace.displayedUrl; fillMode: Image.PreserveAspectFit; asynchronous: true
                            sourceSize.width: 1800; sourceSize.height: 1800
                        }
                        Column {
                            anchors.centerIn: parent; spacing: 14
                            visible: !workspace.displayedUrl.toString().length
                            Label { anchors.horizontalCenter: parent.horizontalCenter; text: "▧"; font.pixelSize: 52; color: "#635035" }
                            Label { anchors.horizontalCenter: parent.horizontalCenter; text: workspace.canvasMode ? "Your next edit starts here" : "Make room for the image"; color: "#e9e6df"; font.pixelSize: 18 }
                            Label { anchors.horizontalCenter: parent.horizontalCenter; text: "Choose an image from the thumbnail browser"; color: "#aaa7a1"; font.pixelSize: 11 }
                        }
                        Label { anchors.centerIn: parent; visible: hero.status === Image.Error; text: "Image unavailable — choose another file"; color: "#f3d28b" }
                        ScrollBar.vertical: ScrollBar { }
                        ScrollBar.horizontal: ScrollBar { }
                    }
                    Label { Layout.fillWidth: true; text: workspace.displayedUrl.toString().split('/').pop() || "No image selected"; color: "#aaa7a1"; elide: Text.ElideMiddle; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 11 }
                }
            }
            Rectangle {
                Layout.preferredWidth: workspace.canvasMode ? 270 : 220; Layout.fillHeight: true
                color: "#141414"; radius: 8; border.color: "#343434"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 14
                    Caption { text: workspace.canvasMode ? "EDIT DIRECTION" : "IMAGE DETAILS" }
                    Label { Layout.fillWidth: true; visible: !workspace.canvasMode; text: workspace.displayedUrl.toString().split('/').pop() || "Nothing selected"; color: "#e9e6df"; wrapMode: Text.WrapAnywhere }
                    Label { Layout.fillWidth: true; visible: !workspace.canvasMode; text: "Fit and zoom to inspect. Drag the enlarged image to pan. Browse images opens the grid with full dimensions and a large preview."; color: "#aaa7a1"; wrapMode: Text.Wrap; font.pixelSize: 12 }
                    ScrollView {
                        Layout.fillWidth: true; Layout.fillHeight: true; visible: workspace.canvasMode
                        TextArea {
                            id: instructions
                            text: workspace.prompt
                            onTextChanged: if (activeFocus) workspace.prompt = text
                            placeholderText: "Describe what you want to change…"
                            placeholderTextColor: "#aaa7a1"
                            wrapMode: TextEdit.Wrap; color: "#e9e6df"; padding: 12
                            background: Rectangle { color: "#090909"; radius: 5; border.color: "#343434" }
                        }
                    }
                    Label { Layout.fillWidth: true; visible: workspace.canvasMode; text: "Layout preview · local AI edits are on hold until supported-system validation. Layers and cutout compositing are planned."; color: "#c5a267"; wrapMode: Text.Wrap; font.pixelSize: 11 }
                    Action { Layout.fillWidth: true; visible: workspace.canvasMode; text: "AI editing on hold"; enabled: false }
                    Item { Layout.fillHeight: true; visible: !workspace.canvasMode }
                    Caption { text: "SESSION" }
                    Label { Layout.fillWidth: true; text: workspace.statusText; color: "#aaa7a1"; wrapMode: Text.Wrap; font.pixelSize: 11 }
                }
            }
        }
        Label { Layout.fillWidth: true; text: "GENESIS   /   " + (workspace.canvasMode ? "CANVAS" : "MEDIA VIEWER") + "                                      DESIGN REVIEW · PAUL"; color: "#81796b"; font.pixelSize: 10; font.letterSpacing: 1 }
    }
}
