import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    property var bridge
    property bool privatePreview: true
    property string characterId: bridge ? bridge.selectedCharacterA : ""
    property string inputSource: ""
    property string builderModel: ""
    readonly property string masterSource: character.primaryImage || inputSource
    property int referenceIndex: 0
    property string previewSource: ""
    property string previewTitle: ""
    property var character: {
        var rows = bridge ? bridge.characters : []
        for (var i = 0; i < rows.length; ++i)
            if (rows[i].id === characterId) return rows[i]
        return ({})
    }
    property string galleryFilter: "all"
    readonly property var references: {
        var rows = character.referenceItems || []
        return rows.filter(function(row) { return root.galleryFilter === "all" || (root.galleryFilter === "review" ? !row.approved : row.category === root.galleryFilter) })
    }
    onGalleryFilterChanged: referenceIndex = 0
    readonly property var selectedReference: references[referenceIndex] || ({})
    signal useMaster(string source)
    signal buildReference(string source, string prompt)
    spacing: 8
    Label { text: "CHARACTER A · IDENTITY REFERENCES"; color: "#d9b65d"; font.bold: true }
    Label { Layout.fillWidth: true; text: "Keep original identity angles here. Realism stays on Create / Refine. Pose references describe composition only."; wrapMode: Text.Wrap; color: "#aaa" }
    RowLayout {
        Layout.fillWidth: true
        ComboBox {
            Layout.fillWidth: true
            model: root.bridge ? root.bridge.characters : []
            textRole: "name"
            enabled: root.bridge && !root.bridge.busy
            currentIndex: { for (var i=0; i<model.length; i++) if (model[i].id === root.characterId) return i; return -1 }
            onActivated: {
                root.bridge.selectCharacterA(model[currentIndex].id)
                root.referenceIndex = 0
            }
        }
        Button { text: "Use identity"; enabled: root.masterSource.length > 0 && !root.bridge.busy; onClicked: root.useMaster(root.masterSource) }
    }
    RowLayout {
        Layout.fillWidth: true
        TextField { id: characterName; placeholderText: "Character A name"; Layout.fillWidth: true }
        Button { text: "Choose master image"; onClicked: { var source = root.bridge.chooseSourceImage(); if (source.length) root.inputSource = source } }
        CheckBox { id: adult; text: "Adult 18+" }
        Button {
            text: "Save Character A"
            enabled: adult.checked && root.inputSource.length > 0 && !root.bridge.busy
            onClicked: {
                var id = root.bridge.createCharacterFromImage(characterName.text || "Character A", root.inputSource, adult.checked)
                if (id.length) { root.bridge.selectCharacterA(id); root.referenceIndex = 0 }
            }
        }
    }
    RowLayout {
        Layout.fillWidth: true
        ComboBox { id: angle; model: ["Primary/Front", "¾ Left", "¾ Right", "Profile", "Back", "Upper Body", "Full Body"]; Layout.fillWidth: true }
        Button {
            text: "Add master angle"
            enabled: root.characterId.length > 0 && !root.bridge.busy
            onClicked: { var source = root.bridge.chooseSourceImage(); if (source.length) root.bridge.addCharacterReference(root.characterId, source, angle.currentText) }
        }
    }
    RowLayout {
        Label { text: "Gallery"; color: "#d9b65d" }
        ComboBox { model: ["all", "face", "body", "pose", "review", "ignore"]; onActivated: root.galleryFilter = currentText }
        Label { text: root.references.length + " references"; color: "#aaa" }
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
                Text { width: 98; text: modelData.role === "primary" ? "Primary/Front" : modelData.role + " · " + modelData.category + (modelData.approved ? " ✓" : " · review"); color: "#ddd"; elide: Text.ElideRight }
            }
            MouseArea { anchors.fill: parent; onClicked: root.referenceIndex = index }
        }
    }
    Button { text: "Large reference preview / zoom"; enabled: root.references.length > 0; onClicked: { root.previewSource = root.selectedReference.source || ""; root.previewTitle = root.selectedReference.role || "Identity master"; preview.open() } }
    RowLayout {
        Button {
            text: "Replace gallery reference"
            enabled: !!root.selectedReference.path && !root.selectedReference.master && !root.bridge.busy
            onClicked: {
                var source = root.bridge.chooseSourceImage()
                if (source.length) root.bridge.updateCharacterReference(root.characterId, root.selectedReference.path, source, angle.currentText)
            }
        }
        Button {
            text: "Remove reference"
            enabled: !!root.selectedReference.path && root.selectedReference.path !== root.character.primaryPath && !root.bridge.busy
            onClicked: { if (root.bridge.updateCharacterReference(root.characterId, root.selectedReference.path, "", "")) root.referenceIndex = 0 }
        }
    }
    RowLayout {
        ComboBox {
            id: category
            model: ["face", "body", "pose", "ignore"]
            currentIndex: Math.max(0, model.indexOf(root.selectedReference.category || "face"))
        }
        Button { text: "Approve role"; enabled: !!root.selectedReference.path && !root.selectedReference.master && !root.bridge.busy; onClicked: root.bridge.setCharacterReferenceDetails(root.characterId, root.selectedReference.path, category.currentText, true) }
        Button { text: "Needs review"; enabled: !!root.selectedReference.path && !root.selectedReference.master && !root.bridge.busy; onClicked: root.bridge.setCharacterReferenceDetails(root.characterId, root.selectedReference.path, category.currentText, false) }
    }
    Label { text: "CHARACTER REFERENCE BUILDER"; color: "#d9b65d"; font.bold: true }
    Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: "#aaa"; text: "Prepare an angle or pose in Create using the master. Choose a reference-capable workflow there; SDXL image-to-image uses the source; lower denoise preserves more detail but does not guarantee identity. Import the saved result for review, then approve its face/body/pose role. The master stays unchanged." }
    TextField { id: builderPrompt; Layout.fillWidth: true; placeholderText: "e.g. three-quarter left view, neutral expression, same identity" }
    RowLayout {
        Button { text: "Prepare in Create"; enabled: root.characterId.length > 0 && builderPrompt.text.trim().length > 0 && !root.bridge.busy; onClicked: root.buildReference(root.masterSource, builderPrompt.text) }
        Button {
            text: "Import candidate for review"; enabled: root.characterId.length > 0 && !root.bridge.busy && !root.bridge.busy
            onClicked: {
                var source = root.bridge.chooseSourceImage()
                if (source.length) root.bridge.importCharacterCandidate(root.characterId, source, builderPrompt.text, category.currentText)
            }
        }
    }
    CheckBox { id: adultReferenceMode; checked: true; text: "Adult NSFW reference mode (18+ characters only)"; enabled: root.characterId.length > 0 && !root.bridge.busy }
    Button {
        text: root.bridge && root.bridge.busy ? "Generating…" : "Generate reference set"
        enabled: root.characterId.length > 0 && root.builderModel.length > 0 && !root.bridge.busy
        onClicked: root.bridge.queueCharacterReferenceSet(root.characterId, root.builderModel, adultReferenceMode.checked)
    }
    Button { text: "Cancel generation"; visible: root.bridge && root.bridge.busy; onClicked: root.bridge.cancelGeneration() }
    Label { Layout.fillWidth: true; color: "#aaa"; wrapMode: Text.Wrap; text: "Uses the model selected in Create. Seven separate candidates are saved for review; nothing is approved automatically. Cancel remains available in Create." }
    Button {
        text: "Preview latest generated reference sheet"
        enabled: (root.character.referenceSheets || []).length > 0
        onClicked: { var sheets = root.character.referenceSheets; root.previewSource = sheets[sheets.length - 1]; root.previewTitle = "Generated reference set · review"; preview.open() }
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
                Label { text: root.previewTitle || "Identity master"; Layout.fillWidth: true }
                Slider { id: zoom; from: 1; to: 4; value: 1 }
                Button { text: "Close"; onClicked: preview.close() }
            }
            Flickable {
                id: referenceView
                Layout.fillWidth: true; Layout.fillHeight: true
                clip: true
                contentWidth: width * zoom.value; contentHeight: height * zoom.value
                Image { width: referenceView.contentWidth; height: referenceView.contentHeight; source: root.privatePreview ? "" : root.previewSource; fillMode: Image.PreserveAspectFit }
                Label { anchors.centerIn: parent; text: "PRIVATE"; visible: root.privatePreview }
            }
        }
    }
}
