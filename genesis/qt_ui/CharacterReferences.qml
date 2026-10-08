import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    property var bridge
    property bool privatePreview: true
    property string characterId: ""
    property string inputSource: ""
    readonly property string masterSource: character.primaryImage || inputSource
    property int referenceIndex: 0
    property var character: {
        var rows = bridge ? bridge.characters : []
        for (var i = 0; i < rows.length; ++i)
            if (rows[i].id === characterId) return rows[i]
        return ({})
    }
    readonly property var references: character.referenceItems || []
    readonly property var selectedReference: references[referenceIndex] || ({})
    signal useMaster(string source)
    spacing: 8
    Label { text: "CHARACTER A · IDENTITY REFERENCES"; color: "#d9b65d"; font.bold: true }
    Label { Layout.fillWidth: true; text: "Keep original identity angles here. Realism stays on Create / Refine. Pose references describe composition only."; wrapMode: Text.Wrap; color: "#aaa" }
    RowLayout {
        Layout.fillWidth: true
        ComboBox {
            Layout.fillWidth: true
            model: root.bridge ? root.bridge.characters : []
            textRole: "name"
            onActivated: {
                root.characterId = model[currentIndex].id
                root.bridge.selectCharacterA(root.characterId)
                root.referenceIndex = 0
            }
        }
        Button { text: "Use identity"; enabled: root.masterSource.length > 0; onClicked: root.useMaster(root.masterSource) }
    }
    RowLayout {
        Layout.fillWidth: true
        TextField { id: characterName; placeholderText: "Character A name"; Layout.fillWidth: true }
        CheckBox { id: adult; text: "Adult 18+" }
        Button {
            text: "Save Character A"
            enabled: adult.checked && root.inputSource.length > 0 && !root.characterId.length
            onClicked: {
                var id = root.bridge.createCharacterFromImage(characterName.text || "Character A", root.inputSource, adult.checked)
                if (id.length) { root.characterId = id; root.bridge.selectCharacterA(id); root.referenceIndex = 0 }
            }
        }
    }
    RowLayout {
        Layout.fillWidth: true
        ComboBox { id: angle; model: ["Primary/Front", "¾ Left", "¾ Right", "Profile", "Upper Body", "Full Body"]; Layout.fillWidth: true }
        Button {
            text: "Add master angle"
            enabled: root.characterId.length > 0
            onClicked: { var source = root.bridge.chooseSourceImage(); if (source.length) root.bridge.addCharacterReference(root.characterId, source, angle.currentText) }
        }
    }
    ListView {
        Layout.fillWidth: true
        Layout.preferredHeight: 90
        orientation: ListView.Horizontal
        spacing: 8
        clip: true
        model: root.references
        delegate: Rectangle {
            width: 100; height: 86
            color: "#14171c"; border.color: index === root.referenceIndex ? "#d9b65d" : "#444"
            Column {
                anchors.fill: parent
                Image { width: 98; height: 62; source: root.privatePreview ? "" : modelData.source; fillMode: Image.PreserveAspectFit }
                Text { width: 98; text: modelData.role === "primary" ? "Primary/Front" : modelData.role; color: "#ddd"; elide: Text.ElideRight }
            }
            MouseArea { anchors.fill: parent; onClicked: root.referenceIndex = index }
        }
    }
    Button { text: "Large reference preview / zoom"; enabled: root.references.length > 0; onClicked: preview.open() }
    RowLayout {
        Button {
            text: "Replace reference"
            enabled: !!root.selectedReference.path
            onClicked: {
                var source = root.bridge.chooseSourceImage()
                if (source.length) root.bridge.updateCharacterReference(root.characterId, root.selectedReference.path, source, angle.currentText)
            }
        }
        Button {
            text: "Remove reference"
            enabled: !!root.selectedReference.path && root.selectedReference.path !== root.character.primaryPath
            onClicked: { if (root.bridge.updateCharacterReference(root.characterId, root.selectedReference.path, "", "")) root.referenceIndex = 0 }
        }
    }
    Popup {
        id: preview
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 1000)
        height: Math.min(parent.height - 40, 800)
        modal: true
        ColumnLayout {
            anchors.fill: parent
            RowLayout {
                Label { text: root.selectedReference.role || "Identity master"; Layout.fillWidth: true }
                Slider { id: zoom; from: 1; to: 4; value: 1 }
                Button { text: "Close"; onClicked: preview.close() }
            }
            Flickable {
                id: referenceView
                Layout.fillWidth: true; Layout.fillHeight: true
                clip: true
                contentWidth: width * zoom.value; contentHeight: height * zoom.value
                Image { width: referenceView.contentWidth; height: referenceView.contentHeight; source: root.privatePreview ? "" : root.selectedReference.source || ""; fillMode: Image.PreserveAspectFit }
                Label { anchors.centerIn: parent; text: "PRIVATE"; visible: root.privatePreview }
            }
        }
    }
}
