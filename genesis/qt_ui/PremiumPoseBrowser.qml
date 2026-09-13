import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property color gold: "#d2a34e"
    property color brightGold: "#f3d28b"
    property color ice: "#7fc4d8"
    property color panel: "#0d141d"
    property color raised: "#121c27"
    property color line: "#2d4354"
    property color textMain: "#eef3f6"
    property color textDim: "#91a2b2"

    property var openPoseModel: typeof poseItems !== "undefined" ? poseItems : []
    property var presetModel: typeof curatedPosePresets !== "undefined" ? curatedPosePresets : []
    property var grokModel: typeof grokPresetItems !== "undefined" ? grokPresetItems : []

    property string browserMode: "Presets"
    property string collectionFilter: "All collections"
    property string categoryFilter: "All"
    property string searchText: ""
    property var selectedItem: ({})
    property url sourceImage: ""

    signal sourceImageRequested()
    signal itemChosen(url source, string name, string category, string prompt, string collection)
    signal useInCreate(url source, string name, string category, string prompt, string collection)

    function normal(value) {
        return String(value === undefined || value === null ? "" : value).toLowerCase()
    }

    function categoryMatches(category) {
        if (categoryFilter === "All") return true
        var wanted = normal(categoryFilter).replace("all fours", "all fours")
        var actual = normal(category).replace("_", " ")
        if (categoryFilter === "All Fours")
            return actual.indexOf("all fours") >= 0 || actual.indexOf("all-fours") >= 0
        return actual.indexOf(wanted) >= 0
    }

    function searchMatches(item) {
        var needle = normal(searchText).trim()
        if (!needle.length) return true
        return normal(item.name || item.label).indexOf(needle) >= 0
            || normal(item.category).indexOf(needle) >= 0
            || normal(item.collection).indexOf(needle) >= 0
            || normal(item.prompt).indexOf(needle) >= 0
    }

    function visiblePresetItems() {
        var rows = []
        for (var i = 0; i < presetModel.length; ++i) {
            var item = presetModel[i]
            if (!item) continue
            if (collectionFilter !== "All collections" && String(item.collection || "") !== collectionFilter)
                continue
            if (!categoryMatches(item.category || ""))
                continue
            if (!searchMatches(item))
                continue
            rows.push({
                kind: "preset",
                name: String(item.label || "Preset"),
                category: String(item.category || "Preset"),
                collection: String(item.collection || "Preset"),
                prompt: String(item.prompt || ""),
                source: "",
                mapped: true
            })
        }
        return rows
    }

    function visibleOpenPoseItems() {
        var rows = []
        for (var i = 0; i < openPoseModel.length; ++i) {
            var item = openPoseModel[i]
            if (!item) continue
            if (!categoryMatches(item.category || ""))
                continue
            if (!searchMatches(item))
                continue
            rows.push({
                kind: "openpose",
                name: String(item.name || "Pose"),
                category: String(item.category || "Pose"),
                collection: "OpenPose library",
                prompt: String(item.prompt || ""),
                source: item.source || "",
                mapped: Boolean(item.promptMapped)
            })
        }
        return rows
    }

    readonly property var visibleItems: browserMode === "OpenPose" ? visibleOpenPoseItems() : visiblePresetItems()

    function choose(item) {
        selectedItem = item
        itemChosen(item.source || "", item.name || "Preset", item.category || "", item.prompt || "", item.collection || "")
    }

    component PButton: Button {
        id: button
        property bool active: false
        implicitHeight: 38
        leftPadding: 12
        rightPadding: 12
        font.pixelSize: 12
        font.weight: active ? Font.DemiBold : Font.Medium
        contentItem: Text {
            text: button.text
            color: !button.enabled ? "#66717b" : (button.active ? "#081017" : (button.hovered ? root.brightGold : root.textMain))
            font: button.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 8
            color: !button.enabled ? "#10161d" : (button.active ? root.gold : (button.hovered ? "#162432" : "#101923"))
            border.color: button.active ? root.brightGold : (button.hovered ? root.ice : root.line)
            border.width: button.active || button.hovered ? 1.5 : 1
        }
    }

    component CardPanel: Rectangle {
        radius: 10
        color: root.panel
        border.color: root.line
        border.width: 1
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: "#152230" }
            GradientStop { position: 0.12; color: "#101923" }
            GradientStop { position: 1.0; color: "#0a1017" }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 9

        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 46
            spacing: 7
            PButton { text: "Preset Collections"; active: root.browserMode === "Presets"; onClicked: root.browserMode = "Presets" }
            PButton { text: "OpenPose Library"; active: root.browserMode === "OpenPose"; onClicked: root.browserMode = "OpenPose" }
            Rectangle { width: 1; Layout.fillHeight: true; color: root.line }
            Repeater {
                model: ["All", "Standing", "Sitting", "Lying", "Kneeling", "All Fours"]
                PButton {
                    text: modelData
                    active: root.categoryFilter === modelData
                    onClicked: root.categoryFilter = modelData
                }
            }
            Item { Layout.fillWidth: true }
            PButton {
                text: root.sourceImage.toString().length ? "Replace Source" : "Load Source Image"
                onClicked: root.sourceImageRequested()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10

            CardPanel {
                Layout.preferredWidth: 210
                Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8
                    Text { text: "FILTERS"; color: root.brightGold; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.1 }
                    TextField {
                        Layout.fillWidth: true
                        placeholderText: "Search poses / prompts…"
                        text: root.searchText
                        onTextChanged: root.searchText = text
                    }
                    Text { text: "Collection"; color: root.textDim; font.pixelSize: 11; visible: root.browserMode === "Presets" }
                    ComboBox {
                        Layout.fillWidth: true
                        visible: root.browserMode === "Presets"
                        model: ["All collections", "Full 70", "Curated 18"]
                        onActivated: root.collectionFilter = currentText
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: root.line }
                    Text {
                        Layout.fillWidth: true
                        text: root.browserMode === "Presets"
                            ? "Prompt presets set camera / body geometry without forcing you into node wiring. Full 70 is built into the Windows repo; Curated 18 appears when its database is present."
                            : "The indexed OpenPose library is virtualized, so the full local collection can stay available without creating hundreds of QML delegates at once."
                        color: root.textDim
                        font.pixelSize: 11
                        wrapMode: Text.Wrap
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 54
                        radius: 8
                        color: "#0a1118"
                        border.color: root.line
                        Column {
                            anchors.centerIn: parent
                            spacing: 2
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: root.visibleItems.length + " visible"; color: root.brightGold; font.pixelSize: 15; font.bold: true }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: root.browserMode; color: root.textDim; font.pixelSize: 10 }
                        }
                    }
                    Item { Layout.fillHeight: true }
                    PButton {
                        Layout.fillWidth: true
                        text: "Full 70"
                        active: root.browserMode === "Presets" && root.collectionFilter === "Full 70"
                        onClicked: { root.browserMode = "Presets"; root.collectionFilter = "Full 70" }
                    }
                    PButton {
                        Layout.fillWidth: true
                        text: "Curated 18"
                        active: root.browserMode === "Presets" && root.collectionFilter === "Curated 18"
                        onClicked: { root.browserMode = "Presets"; root.collectionFilter = "Curated 18" }
                    }
                    PButton {
                        Layout.fillWidth: true
                        text: "OpenPose"
                        active: root.browserMode === "OpenPose"
                        onClicked: root.browserMode = "OpenPose"
                    }
                }
            }

            CardPanel {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true

                GridView {
                    id: poseGrid
                    anchors.fill: parent
                    anchors.margins: 10
                    clip: true
                    model: root.visibleItems
                    cellWidth: Math.max(168, Math.floor(width / Math.max(1, Math.floor(width / 190))))
                    cellHeight: 224
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                    delegate: Item {
                        required property var modelData
                        width: poseGrid.cellWidth
                        height: poseGrid.cellHeight
                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: 5
                            radius: 9
                            color: "#091017"
                            border.color: root.selectedItem.name === modelData.name
                                && root.selectedItem.collection === modelData.collection ? root.gold : root.line
                            border.width: root.selectedItem.name === modelData.name
                                && root.selectedItem.collection === modelData.collection ? 2 : 1
                            clip: true

                            Image {
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.top: parent.top
                                anchors.bottom: cardInfo.top
                                anchors.margins: 5
                                source: modelData.kind === "openpose"
                                    ? modelData.source
                                    : "../assets/page_banners/pose-library/pose-library-banner-reference.png"
                                fillMode: Image.PreserveAspectCrop
                                asynchronous: true
                                cache: true
                                opacity: modelData.kind === "openpose" ? 1.0 : 0.72
                            }
                            Rectangle {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.margins: 9
                                width: badgeText.implicitWidth + 14
                                height: 24
                                radius: 12
                                color: "#d00b121b"
                                border.color: modelData.collection === "Full 70" ? root.gold : root.ice
                                Text { id: badgeText; anchors.centerIn: parent; text: modelData.collection; color: modelData.collection === "Full 70" ? root.brightGold : root.ice; font.pixelSize: 9; font.bold: true }
                            }
                            Rectangle {
                                id: cardInfo
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                height: 58
                                color: "#ef070c12"
                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 7
                                    spacing: 2
                                    Text { width: parent.width; text: modelData.name; color: root.textMain; font.pixelSize: 11; font.bold: true; elide: Text.ElideRight }
                                    Text { width: parent.width; text: modelData.category; color: root.textDim; font.pixelSize: 9; elide: Text.ElideRight }
                                }
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.choose(modelData)
                            }
                        }
                    }
                }

                Text {
                    anchors.centerIn: parent
                    visible: root.visibleItems.length === 0
                    text: "NO MATCHING POSES\n\nClear search or change collection/category."
                    color: root.textDim
                    font.pixelSize: 14
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            CardPanel {
                Layout.preferredWidth: 300
                Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 8
                    Text { text: "SELECTED"; color: root.brightGold; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.1 }
                    Text {
                        Layout.fillWidth: true
                        text: root.selectedItem.name || "Choose a card"
                        color: root.brightGold
                        font.pixelSize: 17
                        font.bold: true
                        wrapMode: Text.Wrap
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 220
                        radius: 8
                        color: "#080d12"
                        border.color: root.selectedItem.name ? root.gold : root.line
                        Image {
                            anchors.fill: parent
                            anchors.margins: 6
                            source: root.selectedItem.kind === "openpose"
                                ? (root.selectedItem.source || "")
                                : "../assets/page_banners/pose-library/pose-library-banner-reference.png"
                            fillMode: Image.PreserveAspectFit
                            visible: root.selectedItem.name !== undefined
                        }
                        Text { anchors.centerIn: parent; visible: !root.selectedItem.name; text: "SELECT A PRESET\nOR OPENPOSE CARD"; color: root.textDim; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter }
                    }
                    Text { Layout.fillWidth: true; text: (root.selectedItem.collection || "") + (root.selectedItem.category ? "  ·  " + root.selectedItem.category : ""); color: root.textDim; font.pixelSize: 10; wrapMode: Text.Wrap }
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        TextArea {
                            readOnly: true
                            text: root.selectedItem.prompt || "Select a card to inspect its mapped prompt."
                            color: root.textMain
                            wrapMode: TextEdit.Wrap
                            background: Rectangle { color: "#080d12"; border.color: root.line; radius: 7 }
                        }
                    }
                    PButton {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 50
                        text: "USE IN CREATE"
                        active: enabled
                        enabled: Boolean(root.selectedItem.name)
                        onClicked: root.useInCreate(
                            root.selectedItem.source || "",
                            root.selectedItem.name || "Preset",
                            root.selectedItem.category || "",
                            root.selectedItem.prompt || "",
                            root.selectedItem.collection || ""
                        )
                    }
                }
            }
        }
    }
}
