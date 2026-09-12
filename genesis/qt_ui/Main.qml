import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import QtMultimedia

ApplicationWindow {
    id: appRoot
    Component.onCompleted: restoreLayoutSettings()
    visible: true
    width: 1536
    height: 960
    minimumWidth: 900
    minimumHeight: 600
    title: "GENESIS COCKPIT"
    color: "#080d13"
    font.family: "Noto Sans Display"
    font.pixelSize: 15

    Rectangle {
        anchors.fill: parent
        z: -100
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: "#101b27" }
            GradientStop { position: 0.42; color: "#080d13" }
            GradientStop { position: 1.0; color: "#05080d" }
        }
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            height: 1
            color: "#50f7d58d"
        }
    }

    readonly property color gold: "#d3a04a"
    readonly property color brightGold: "#f7d58d"
    readonly property color blue: "#456179"
    readonly property color brightBlue: "#8bc7dc"
    readonly property color panel: "#0d141d"
    readonly property color panelSoft: "#111a25"
    readonly property color panelRaised: "#172332"
    readonly property color line: "#30475a"
    readonly property color lineSoft: "#20303d"
    readonly property color textMain: "#edf2f5"
    readonly property color textDim: "#95a5b5"
    property real uiZoom: 1.0
    property bool layoutEditMode: false
    property real createPreviewWidth: 370
    property real createPromptHeight: 106
    property real createReferenceHeight: 112
    property real createSourceHeight: 92
    property real createOutputHeight: 88

    function saveLayoutSettings() {
        genesisLayout.saveCreateLayout(createPreviewWidth, createPromptHeight, createReferenceHeight, createSourceHeight, createOutputHeight)
    }

    function restoreLayoutSettings() {
        var layout = genesisLayout.loadCreateLayout()
        if (layout.previewWidth !== undefined) createPreviewWidth = layout.previewWidth
        if (layout.promptHeight !== undefined) createPromptHeight = layout.promptHeight
        if (layout.referenceHeight !== undefined) createReferenceHeight = layout.referenceHeight
        if (layout.sourceHeight !== undefined) createSourceHeight = layout.sourceHeight
        if (layout.outputHeight !== undefined) createOutputHeight = layout.outputHeight
    }

    function resetLayoutSettings() {
        genesisLayout.resetCreateLayout()
        createPreviewWidth = 370
        createPromptHeight = 106
        createReferenceHeight = 112
        createSourceHeight = 92
        createOutputHeight = 88
    }
    readonly property real fittedScale: Math.min(
        Math.max(1, width - 20) / 1516,
        Math.max(1, height - 20) / 940
    )
    FontLoader { id: genesisDisplayFont; source: "../assets/fonts/Exo2-Black.ttf" }
    property bool privacyMode: false
    property int pageIndex: 0
    readonly property var pageNames: ["IMAGE GENERATION", "POSE LIBRARY", "WORKFLOW EDITOR", "MEDIA TOOLS", "PHOTO LIBRARY", "CAM HUB", "ENTERTAINMENT", "SYSTEM", "INPAINT / EDIT", "POSE MAKER"]
    readonly property var pageBannerSources: [
        "../assets/panel_backgrounds/panel-01-image-generate.jpg",
        "../assets/panel_backgrounds/panel-02-pose-lab.jpg",
        "../assets/panel_backgrounds/panel-04-prompt-manager.jpg",
        "../assets/panel_backgrounds/panel-06-duplicate-lab.jpg",
        "../assets/panel_backgrounds/panel-05-photo-organiser.jpg",
        "../assets/panel_backgrounds/panel-08-camera-hub.png",
        "../assets/panel_backgrounds/panel-07-photo-viewer.png",
        "../assets/panel_backgrounds/panel-03-face-studio.jpg",
        "../assets/panel_backgrounds/panel-01-image-generate.jpg",
        "../assets/panel_backgrounds/panel-02-pose-lab.jpg"
    ]
    readonly property var pageBannerVideos: [
        "../assets/panel_backgrounds/genesis-cockpit-banner.mp4",
        "../assets/panel_backgrounds/genesis-cockpit-banner-secondary.mp4",
        "../assets/panel_backgrounds/genesis-cockpit-banner-user-right.mp4",
        "../assets/panel_backgrounds/genesis-cockpit-banner-secondary.mp4",
        "../assets/panel_backgrounds/genesis-cockpit-banner.mp4",
        "../assets/panel_backgrounds/genesis-cockpit-banner-user-right.mp4",
        "../assets/panel_backgrounds/genesis-cockpit-banner-secondary.mp4",
        "../assets/panel_backgrounds/genesis-cockpit-banner.mp4",
        "../assets/panel_backgrounds/genesis-cockpit-banner-user-right.mp4",
        "../assets/panel_backgrounds/genesis-cockpit-banner-secondary.mp4"
    ]
    readonly property var grokGeometryPresets: (typeof grokPresetItems !== "undefined" && grokPresetItems.length > 0) ? grokPresetItems : [
        {label:"Grok preset…", prompt:""},
        {label:"BACK-LYING · HIGH", prompt:"Back-lying pose, legs raised or open as needed, high-angle camera looking down. Keep body geometry natural and preserve image1 identity."},
        {label:"BACK-LYING · SIDE", prompt:"Back-lying pose, legs raised, clear side-profile camera angle. Preserve image1 identity and use the pose reference only for geometry."},
        {label:"ALL-FOURS · REAR 3/4", prompt:"All-fours pose, rear three-quarter camera view, natural limb placement and body proportions. Preserve image1 identity."},
        {label:"ALL-FOURS · LOOK BACK", prompt:"All-fours pose, head turned back toward camera over the shoulder, natural anatomy and stable body geometry. Preserve image1 identity."},
        {label:"SEATED/TOP · LOW", prompt:"Seated or top-position pose, front low-angle camera looking slightly upward, balanced body geometry. Preserve image1 identity."},
        {label:"SEATED/TOP · REAR", prompt:"Seated or top-position pose, rear camera view, natural torso and limb placement. Preserve image1 identity."},
        {label:"PRONE · HIGH", prompt:"Prone face-down pose, high-angle camera, natural torso alignment and limb placement. Preserve image1 identity."},
        {label:"STANDING BENT · SIDE", prompt:"Standing bent-forward pose, clear side-profile view, stable feet and natural spine/limb geometry. Preserve image1 identity."},
        {label:"LEGS-UP · CLOSE 3/4", prompt:"Compressed legs-up pose, close three-quarter camera view, natural anatomy and body proportions. Preserve image1 identity."},
        {label:"WALL · LOW", prompt:"Standing against a wall, one leg optionally raised, low-angle camera, natural body alignment. Preserve image1 identity."}
    ]
    readonly property var posePromptPresets: [
        {label:"Natural full-body", prompt:"Natural full-body pose, balanced composition, realistic anatomy and proportions."},
        {label:"Standing portrait", prompt:"Standing pose, natural posture, full-body framing, balanced weight and realistic anatomy."},
        {label:"Seated portrait", prompt:"Seated pose, relaxed posture, natural limb placement and realistic proportions."},
        {label:"Reclining / lying", prompt:"Reclining pose, natural torso alignment, clear limb placement and realistic anatomy."},
        {label:"Kneeling", prompt:"Kneeling pose, balanced posture, clear hands and feet, realistic anatomy and proportions."},
        {label:"Squatting", prompt:"Squatting pose, stable balance, natural hip and knee alignment, realistic anatomy."},
        {label:"All fours", prompt:"All-fours pose, stable limb placement, natural spine alignment and realistic proportions."},
        {label:"Suspended / elevated", prompt:"Elevated or suspended pose, clear body silhouette, believable balance and realistic anatomy."},
        {label:"Split-leg composition", prompt:"Wide or split-leg pose, symmetrical composition, natural joint alignment and realistic anatomy."}
    ]
    readonly property var poseMakerPresets: (typeof curatedPosePresets !== "undefined" && curatedPosePresets.length > 0) ? curatedPosePresets : posePromptPresets
    readonly property var strengthProfiles: ["NATURAL", "BALANCED", "STRONG", "STRICT", "MAX POSE", "MAX IDENTITY", "HYBRID STRONG", "CUSTOM"]
    readonly property var posePromptModes: ["AUTO — prompt from selected pose", "MANUAL — keep my written prompt", "POSE ONLY — no written prompt"]
    readonly property var vramPresets: ["QUALITY · 832×1216", "BALANCED · 768×1152", "FAST SAFE · 704×1024"]
    // Editable in Qt Design Studio. Leave blank to show a framed placeholder.
    property url photoOneSource: ""
    property url photoTwoSource: ""
    property url photoThreeSource: ""
    property url photoFourSource: ""
    property url sideColumnImageSource: ""
    property url bannerLeftInput: "../assets/panel_backgrounds/genesis-cockpit-banner.mp4"
    property url bannerRightInput: "../assets/panel_backgrounds/genesis-cockpit-banner-user-right.mp4"
    property url bannerLeftPoster: "../assets/panel_backgrounds/genesis-cockpit-banner-left-poster.jpg"
    property url bannerRightPoster: "../assets/panel_backgrounds/genesis-cockpit-banner-right-poster.jpg"
    readonly property var photoBannerSources: [photoOneSource, photoTwoSource, photoThreeSource, photoFourSource]
    readonly property int bannerMode: 0 // Full-width MP4 banner
    property var poseModel: typeof poseItems !== "undefined" ? poseItems : []
    property url selectedPoseSource: poseModel.length ? poseModel[0].source : ""
    property string selectedPoseName: poseModel.length ? poseModel[0].name : "Standing 001"
    property string selectedPoseCategory: poseModel.length ? poseModel[0].category : "Standing"
    property string selectedPoseId: poseModel.length ? poseModel[0].poseId : ""
    property string selectedPosePrompt: poseModel.length ? poseModel[0].prompt : ""
    property string selectedPoseNegativePrompt: poseModel.length ? poseModel[0].negativePrompt : ""
    property string selectedPosePromptSource: poseModel.length ? poseModel[0].promptSource : "AUTO_FALLBACK"
    property string selectedPoseTemplateId: poseModel.length ? poseModel[0].promptTemplateId : ""
    property var generationModel: typeof generationProfiles !== "undefined" ? generationProfiles : []
    property int selectedGenerationIndex: 0
    readonly property var selectedGenerationProfile: generationModel.length ? generationModel[selectedGenerationIndex] : ({label:"No local model", model:"", note:"No compatible local model found", loras:["None"], ready:false, runnable:false})
    property string selectedLoraOne: "None"
    property string selectedLoraTwo: "None"
    property url generationSource: ""
    property string selectedCharacterId: ""
    property string selectedCharacterName: ""
    property url selectedCharacterImage: ""
    property string selectedAnchorRole: "close-up"
    property string newCharacterName: ""
    property bool characterAdultConfirmed: false
    property bool useStageTwo: false
    property bool useStageThree: false
    property bool useUpscale: false
    property url editSource: ""
    property url editMask: ""
    property string editPrompt: ""
    property real editStrength: 0.4
    property string activeLoraTriggers: "None"
    property int generationWidth: 512
    property int generationHeight: 512
    property int generationSteps: 4
    property real generationCfg: 1.0
    property string generationSpeed: "Fast"
    property string activePresetStatus: "Choose a Grok camera guide or pose preset."
    property string activeGrokPreset: ""

    function setGenerationSpeed(name, size) {
        generationSpeed = name
        generationWidth = size
        generationHeight = size
    }

    function selectEnginePreset(index) {
        selectedGenerationIndex = index
        generationModelPicker.currentIndex = index
        // The source, pose, prompt, and preset are deliberately preserved.
        // LoRAs are re-selected only from the new model family's filtered list.
        selectedLoraOne = "None"
        selectedLoraTwo = "None"
        loraOnePicker.currentIndex = 0
        loraTwoPicker.currentIndex = 0
        syncLoraTriggers()
    }

    function syncLoraTriggers() {
        var triggerMap = selectedGenerationProfile.triggers || ({})
        var selected = [selectedLoraOne, selectedLoraTwo]
        var words = []
        for (var i = 0; i < selected.length; ++i) {
            var triggers = triggerMap[selected[i]] || []
            for (var j = 0; j < triggers.length; ++j) {
                var word = String(triggers[j]).trim()
                if (word.length && words.indexOf(word) < 0)
                    words.push(word)
            }
        }
        activeLoraTriggers = words.length ? words.join(", ") : "Natural-language activation"
        var promptLower = selectedPosePrompt.toLowerCase()
        for (var k = 0; k < words.length; ++k) {
            if (promptLower.indexOf(words[k].toLowerCase()) < 0) {
                selectedPosePrompt = words[k] + (selectedPosePrompt.length ? ", " + selectedPosePrompt : "")
                promptLower = selectedPosePrompt.toLowerCase()
            }
        }
    }

    function applyPhotorealPreset() {
        var loras = selectedGenerationProfile.loras || []
        var selected = -1
        for (var i = 0; i < loras.length; ++i) {
            var name = String(loras[i]).toLowerCase()
            if (selected < 0 && name.indexOf("snofs") >= 0)
                selected = i
        }
        if (selected < 0) {
            for (var j = 0; j < loras.length; ++j) {
                var fallback = String(loras[j]).toLowerCase()
                if (fallback.indexOf("anatomy") >= 0 || fallback.indexOf("reality") >= 0) {
                    selected = j
                    break
                }
            }
        }
        loraOnePicker.currentIndex = selected >= 0 ? selected : 0
        loraTwoPicker.currentIndex = 0
        selectedLoraOne = loraOnePicker.currentText
        selectedLoraTwo = "None"
        syncLoraTriggers()
    }

    Popup {
        id: presetPopup
        x: Math.round((appRoot.width - width) / 2)
        y: Math.round((appRoot.height - height) / 2)
        width: Math.min(780, appRoot.width - 40)
        height: Math.min(650, appRoot.height - 40)
        padding: 18
        modal: true
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { color: appRoot.panelSoft; border.color: appRoot.gold; border.width: 2; radius: 10 }
        contentItem: ColumnLayout {
            spacing: 12
            RowLayout {
                Layout.fillWidth: true
                Column {
                    Text { text: "GROK POSE PRESETS"; color: appRoot.brightGold; font.family: genesisDisplayFont.name; font.pixelSize: 24; font.bold: true }
                    Text { text: "Original camera and geometry shortcuts"; color: appRoot.textDim; font.pixelSize: 13 }
                }
                Item { Layout.fillWidth: true }
                GoldButton { text: "✕"; Layout.preferredWidth: 48; onClicked: presetPopup.close() }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: appRoot.line }
            SmallLabel { text: "GROK CAMERA / POSE GUIDE" }
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 220
                color: "#090806"
                border.color: appRoot.line
                radius: 5
                ListView {
                    id: grokPresetList
                    anchors.fill: parent
                    anchors.margins: 6
                    clip: true
                    spacing: 7
                    model: appRoot.grokGeometryPresets.slice(1)
                    boundsBehavior: Flickable.StopAtBounds
                    flickableDirection: Flickable.VerticalFlick
                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AlwaysOn
                        active: true
                    }
                    delegate: Item {
                        required property var modelData
                        width: grokPresetList.width - 18
                        height: 42
                        GoldButton {
                            anchors.fill: parent
                            text: modelData.label
                            active: appRoot.activeGrokPreset === modelData.label
                            onClicked: {
                                // A preset changes prompt state only.  Source/model/LoRA
                                // selections intentionally survive regardless of order.
                                appRoot.selectedPosePrompt = modelData.prompt
                                appRoot.selectedPosePromptSource = "GROK_GEOMETRY_PRESET"
                                appRoot.activeGrokPreset = modelData.label
                                appRoot.activePresetStatus = "Grok guide loaded: " + modelData.label
                                presetPopup.close()
                            }
                        }
                    }
                }
            }
            SmallLabel { text: "POSE WORKFLOW CONTROLS" }
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: 10
                rowSpacing: 8
                ColumnLayout {
                    Layout.fillWidth: true
                    Text { text: "Pose prompt preset"; color: appRoot.textDim; font.pixelSize: 12 }
                    PremiumCombo {
                        Layout.fillWidth: true; model: appRoot.posePromptPresets; textRole: "label"
                        onActivated: {
                            appRoot.selectedPosePrompt = appRoot.posePromptPresets[currentIndex].prompt
                            appRoot.selectedPosePromptSource = "POSE_PROMPT_PRESET"
                            appRoot.activePresetStatus = "Pose preset loaded: " + currentText
                        }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Text { text: "Prompt / control profile"; color: appRoot.textDim; font.pixelSize: 12 }
                    PremiumCombo { Layout.fillWidth: true; model: appRoot.strengthProfiles; currentIndex: 1; onActivated: appRoot.activePresetStatus = "Control profile selected: " + currentText }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Text { text: "Pose prompt behavior"; color: appRoot.textDim; font.pixelSize: 12 }
                    PremiumCombo { Layout.fillWidth: true; model: appRoot.posePromptModes; onActivated: appRoot.activePresetStatus = "Prompt behavior: " + currentText }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Text { text: "RX 9060 XT quality / speed"; color: appRoot.textDim; font.pixelSize: 12 }
                    PremiumCombo {
                        Layout.fillWidth: true; model: appRoot.vramPresets; currentIndex: 1
                        onActivated: {
                            if (currentIndex === 0) { appRoot.generationWidth = 832; appRoot.generationHeight = 1216; appRoot.generationSpeed = "Quality" }
                            else if (currentIndex === 1) { appRoot.generationWidth = 768; appRoot.generationHeight = 1152; appRoot.generationSpeed = "Balanced" }
                            else { appRoot.generationWidth = 704; appRoot.generationHeight = 1024; appRoot.generationSpeed = "Fast Safe" }
                            appRoot.activePresetStatus = "VRAM preset loaded: " + currentText
                        }
                    }
                }
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                color: appRoot.panelRaised
                border.color: appRoot.line
                radius: 5
                Text { anchors.left: parent.left; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter; text: appRoot.activePresetStatus; color: appRoot.gold; font.pixelSize: 13 }
            }
        }
    }

    component GoldPanel: Rectangle {
        color: appRoot.panel
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: "#182533" }
            GradientStop { position: 0.08; color: "#101a25" }
            GradientStop { position: 1.0; color: "#0b1119" }
        }
        border.color: appRoot.line
        border.width: 1
        radius: 12
        antialiasing: true
        Rectangle {
            z: -1
            anchors.fill: parent
            anchors.margins: -2
            radius: 14
            color: "#28000000"
        }
        Rectangle {
            z: 39
            anchors.fill: parent
            anchors.margins: 1
            color: "transparent"
            border.color: "#18f7d58d"
            border.width: 1
            radius: 11
        }
        Rectangle {
            z: 40
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            height: 1
            color: "#55f7d58d"
        }
        Rectangle { z: 40; anchors.left: parent.left; anchors.top: parent.top; anchors.leftMargin: 7; anchors.topMargin: 7; width: 22; height: 3; radius: 1.5; color: appRoot.gold }
        Rectangle { z: 40; anchors.left: parent.left; anchors.top: parent.top; anchors.leftMargin: 7; anchors.topMargin: 7; width: 3; height: 22; radius: 1.5; color: appRoot.gold }
        Rectangle { z: 40; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.rightMargin: 7; anchors.bottomMargin: 7; width: 22; height: 3; radius: 1.5; color: appRoot.brightBlue }
        Rectangle { z: 40; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.rightMargin: 7; anchors.bottomMargin: 7; width: 3; height: 22; radius: 1.5; color: appRoot.brightBlue }
    }

    component GoldButton: Button {
        id: control
        property bool active: false
        implicitHeight: 44
        leftPadding: 14
        rightPadding: 14
        topPadding: 1
        bottomPadding: 5
        font.pixelSize: 14
        font.weight: active ? Font.DemiBold : Font.Medium
        font.letterSpacing: 0.25
        contentItem: Text {
            text: control.text
            color: !control.enabled ? "#65717e" : (control.active ? "#091017" : (control.hovered ? appRoot.brightGold : appRoot.textMain))
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Item {
            Rectangle {
                anchors.fill: parent
                anchors.topMargin: 4
                radius: 10
                color: "#50000000"
            }
            Rectangle {
                anchors.fill: parent
                anchors.topMargin: control.down ? 3 : 0
                anchors.bottomMargin: 4
                radius: 10
                color: !control.enabled ? "#111a22" : (control.active ? "#d3a04a" : (control.down ? "#152332" : (control.hovered ? "#182a38" : "#111a25")))
                border.color: !control.enabled ? appRoot.lineSoft : (control.active ? appRoot.brightGold : (control.hovered ? appRoot.brightBlue : appRoot.line))
                border.width: control.active || control.hovered ? 1.5 : 1
            }
            Rectangle {
                visible: control.enabled && control.hovered
                anchors.fill: parent
                anchors.bottomMargin: 4
                radius: 10
                color: "#12f7d58d"
            }
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.leftMargin: 4
                anchors.rightMargin: 4
                anchors.topMargin: 2
                height: 1
                radius: 1
                color: control.active ? "#aafffff0" : "#35f7d58d"
            }
        }
    }

    component PremiumCombo: ComboBox {
        id: picker
        implicitHeight: 44
        leftPadding: 14
        rightPadding: 38
        font.family: appRoot.font.family
        font.pixelSize: 13
        contentItem: Text {
            leftPadding: 2
            text: picker.displayText
            color: appRoot.textMain
            font: picker.font
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        indicator: Text {
            x: picker.width - width - 14
            y: (picker.height - height) / 2
            text: "⌄"
            color: picker.hovered ? appRoot.brightGold : appRoot.gold
            font.pixelSize: 18
        }
        background: Item {
            Rectangle { anchors.left: parent.left; anchors.right: parent.right; y: 4; height: parent.height - 4; radius: 10; color: "#0b121b" }
            Rectangle {
                anchors.left: parent.left; anchors.right: parent.right
                y: picker.pressed ? 3 : 0
                height: parent.height - 4
                color: picker.pressed ? "#1b2b38" : "#101922"
                border.color: picker.hovered || picker.popup.visible ? appRoot.brightGold : appRoot.blue
                border.width: 2
                radius: 6
                Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 2; height: 1; color: "#35f7d58d" }
                Rectangle { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.rightMargin: 7; width: 3; height: parent.height * 0.55; color: appRoot.gold; opacity: 0.75 }
            }
        }
        delegate: ItemDelegate {
            width: picker.width
            height: 40
            contentItem: Text {
                text: {
                    if (picker.textRole && typeof model !== "undefined" && model[picker.textRole] !== undefined)
                        return String(model[picker.textRole])
                    return typeof modelData !== "undefined" ? String(modelData) : ""
                }
                color: highlighted ? "#050505" : appRoot.textMain
                font.family: appRoot.font.family
                font.pixelSize: 13
                verticalAlignment: Text.AlignVCenter
            }
            background: Rectangle { color: highlighted ? appRoot.gold : appRoot.panelSoft }
            highlighted: picker.highlightedIndex === index
        }
        popup: Popup {
            y: picker.height + 3
            width: picker.width
            implicitHeight: Math.min(contentItem.implicitHeight + 8, 300)
            padding: 4
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: picker.popup.visible ? picker.delegateModel : null
                currentIndex: picker.highlightedIndex
                ScrollIndicator.vertical: ScrollIndicator { }
            }
            background: Rectangle { color: appRoot.panelSoft; border.color: appRoot.gold; radius: 6 }
        }
    }

    component FieldBox: Rectangle {
        color: "#0d151f"
        border.color: appRoot.line
        border.width: 1
        radius: 8
    }

    component SmallLabel: Text {
        color: appRoot.brightGold
        font.family: appRoot.font.family
        font.pixelSize: 12
        font.weight: Font.DemiBold
        font.bold: true
        font.letterSpacing: 0.9
    }

    component ModulePage: Item {
        property string pageTitle
        property string pageSubtitle
        property string pageIcon: "◆"
        property string sectionTitle: "Workspace"
        property var cards: []
        property var quickActions: []

        Image {
            anchors.fill: parent
            source: appRoot.pageBannerSources[appRoot.pageIndex]
            fillMode: Image.PreserveAspectCrop
            opacity: 0.09
        }
        Rectangle { anchors.fill: parent; color: "#e0000000" }

        ColumnLayout {
            anchors.fill: parent
            spacing: 8
            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 58
                Layout.maximumHeight: 58
                Text { text: pageIcon; color: appRoot.gold; font.pixelSize: 34 }
                Column {
                    Text { text: pageTitle; color: appRoot.brightGold; font.family: genesisDisplayFont.name; font.pixelSize: 27; font.bold: true; font.letterSpacing: 0.4 }
                    Text { text: pageSubtitle; color: appRoot.textDim; font.pixelSize: 14 }
                }
                Item { Layout.fillWidth: true }
                Repeater {
                    model: quickActions
                    GoldButton { text: modelData; Layout.preferredWidth: 128; enabled: false }
                }
            }
            GoldPanel {
                Layout.fillWidth: true
                Layout.preferredHeight: 54
                Layout.maximumHeight: 54
                RowLayout {
                    anchors.fill: parent; anchors.margins: 7; spacing: 8
                    SmallLabel { text: sectionTitle; Layout.preferredWidth: 170 }
                    FieldBox { Layout.fillWidth: true; Layout.fillHeight: true
                        Text { anchors.left: parent.left; anchors.leftMargin: 14; anchors.verticalCenter: parent.verticalCenter; text: "Module preview — search unavailable"; color: appRoot.textDim; font.pixelSize: 13 }
                    }
                    GoldButton { text: "Refresh"; Layout.preferredWidth: 100; enabled: false }
                    GoldButton { text: "View Options"; Layout.preferredWidth: 120; enabled: false }
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 8
                GridLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    columns: 3
                    rowSpacing: 8
                    columnSpacing: 8
                    Repeater {
                        model: cards
                        GoldPanel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 14
                                spacing: 8
                                Rectangle {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    color: index % 2 ? "#0b0b08" : "#100d07"
                                    border.color: appRoot.line
                                    radius: 4
                                    Text { anchors.centerIn: parent; text: modelData.icon; color: appRoot.gold; font.pixelSize: 46 }
                                }
                                Text { text: modelData.title; color: appRoot.brightGold; font.pixelSize: 17; font.bold: true }
                                Text { Layout.fillWidth: true; text: modelData.detail; color: appRoot.textDim; font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
                                GoldButton { Layout.fillWidth: true; text: modelData.action; enabled: false }
                            }
                        }
                    }
                }
                GoldPanel {
                    Layout.preferredWidth: 305
                    Layout.fillHeight: true
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 14; spacing: 10
                        SmallLabel { text: "GENESIS STATUS" }
                        FieldBox { Layout.fillWidth: true; Layout.preferredHeight: 110
                            Text { anchors.centerIn: parent; text: runtimeStatus.ready ? "SYSTEM READY" : "CHECK REQUIRED"; color: runtimeStatus.ready ? "#59d66f" : appRoot.gold; font.pixelSize: 18; font.bold: true }
                        }
                        SmallLabel { text: "Recent Activity" }
                        Repeater {
                            model: ["No active operation", "Queue is ready", "Local processing enabled", "Privacy controls available"]
                            Text { Layout.fillWidth: true; text: "●  " + modelData; color: appRoot.textMain; font.pixelSize: 12; wrapMode: Text.Wrap }
                        }
                        Rectangle { Layout.fillWidth: true; height: 1; color: appRoot.line }
                        SmallLabel { text: "Quick Access" }
                        GoldButton { Layout.fillWidth: true; text: "Open Output Folder"; onClicked: genesisBridge.openOutputFolder() }
                        GoldButton { Layout.fillWidth: true; text: "GENESIS AI Assistant"; enabled: false }
                        Item { Layout.fillHeight: true }
                        Text { Layout.fillWidth: true; text: "Preview module. Disabled controls are not connected to the Qt cockpit yet."; color: appRoot.textDim; font.pixelSize: 12; wrapMode: Text.Wrap }
                    }
                }
            }
        }
    }

    MediaPlayer {
        id: leftPlayer
        source: appRoot.bannerLeftInput
        loops: MediaPlayer.Infinite
        playbackRate: 0.6
        videoOutput: leftVideo
        audioOutput: AudioOutput { muted: true }
        Component.onCompleted: play()
    }
    MediaPlayer {
        id: rightPlayer
        source: appRoot.bannerRightInput
        loops: MediaPlayer.Infinite
        playbackRate: 0.6
        videoOutput: rightVideo
        audioOutput: AudioOutput { muted: true }
        Component.onCompleted: play()
    }

    Shortcut { sequence: "Ctrl+="; onActivated: appRoot.uiZoom = Math.min(1.25, appRoot.uiZoom + 0.05) }
    Shortcut { sequence: "Ctrl++"; onActivated: appRoot.uiZoom = Math.min(1.25, appRoot.uiZoom + 0.05) }
    Shortcut { sequence: "Ctrl+-"; onActivated: appRoot.uiZoom = Math.max(0.75, appRoot.uiZoom - 0.05) }
    Shortcut { sequence: "Ctrl+0"; onActivated: appRoot.uiZoom = 1.0 }

    ColumnLayout {
        width: 1516
        height: 940
        anchors.centerIn: parent
        scale: appRoot.fittedScale * appRoot.uiZoom
        transformOrigin: Item.Center
        spacing: 8

        GoldPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(390, appRoot.height * 0.41)
            Layout.maximumHeight: Math.max(390, appRoot.height * 0.41)
            clip: true

            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: "#100d07" }
                    GradientStop { position: 0.5; color: "#000000" }
                    GradientStop { position: 1; color: "#100d07" }
                }
            }

            Item {
                z: 0
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: parent.width * 0.25
                anchors.rightMargin: parent.width * 0.25
                visible: !appRoot.privacyMode

                Rectangle { anchors.fill: parent; color: "#000000" }
                Image {
                    anchors.fill: parent
                    anchors.margins: 5
                    source: "../assets/lunacy_banner/genesis-cockpit-banner-lunacy-final.png"
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                    cache: true
                }
            }

            Image {
                z: 0
                anchors.left: parent.left
                anchors.top: parent.top
                width: parent.width * 0.25
                height: parent.height
                source: appRoot.bannerLeftPoster
                fillMode: Image.PreserveAspectCrop
                visible: !appRoot.privacyMode
            }
            Image {
                z: 0
                anchors.right: parent.right
                anchors.top: parent.top
                width: parent.width * 0.25
                height: parent.height
                source: appRoot.bannerRightPoster
                fillMode: Image.PreserveAspectCrop
                visible: !appRoot.privacyMode
            }
            VideoOutput {
                id: leftVideo
                z: 0
                anchors.left: parent.left
                anchors.top: parent.top
                width: parent.width * 0.25
                height: parent.height
                fillMode: VideoOutput.PreserveAspectCrop
                visible: !appRoot.privacyMode
            }
            VideoOutput {
                id: rightVideo
                z: 0
                anchors.right: parent.right
                anchors.top: parent.top
                width: parent.width * 0.25
                height: parent.height
                fillMode: VideoOutput.PreserveAspectCrop
                visible: !appRoot.privacyMode
            }

            Rectangle {
                z: 5
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.leftMargin: 18
                anchors.topMargin: 18
                width: 312
                height: 72
                radius: 18
                color: "#b60b121b"
                border.color: "#66f7d58d"
                border.width: 1
                visible: !appRoot.privacyMode
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 12
                    spacing: 10
                    Rectangle {
                        Layout.preferredWidth: 44
                        Layout.preferredHeight: 44
                        radius: 13
                        color: appRoot.gold
                        Text {
                            anchors.centerIn: parent
                            text: "G"
                            color: "#091017"
                            font.family: genesisDisplayFont.name
                            font.pixelSize: 28
                            font.bold: true
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 1
                        Text {
                            text: "GENESIS c0ckpit"
                            color: appRoot.brightGold
                            font.family: genesisDisplayFont.name
                            font.pixelSize: 21
                            font.bold: true
                            font.letterSpacing: 0.4
                        }
                        Text {
                            text: "LOCAL WORKSPACE  ·  PRIVATE BY DEFAULT"
                            color: appRoot.textDim
                            font.pixelSize: 10
                            font.letterSpacing: 0.7
                        }
                    }
                }
            }
            Rectangle {
                z: 5
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.rightMargin: 18
                anchors.topMargin: 18
                width: 238
                height: 32
                radius: 16
                color: "#a6101824"
                border.color: "#55f7d58d"
                border.width: 1
                visible: !appRoot.privacyMode
                Text {
                    anchors.centerIn: parent
                    text: "●  LOCAL  /  PRIVATE  /  READY"
                    color: appRoot.brightBlue
                    font.pixelSize: 10
                    font.bold: true
                    font.letterSpacing: 0.8
                }
            }
            Rectangle {
                z: 5
                anchors.left: parent.left
                anchors.bottom: parent.bottom
                anchors.leftMargin: 18
                anchors.bottomMargin: 18
                width: 190
                height: 28
                radius: 14
                color: "#99101824"
                border.color: "#35f7d58d"
                border.width: 1
                visible: !appRoot.privacyMode
                Text {
                    anchors.centerIn: parent
                    text: "KEEP WALKING ALLAN"
                    color: appRoot.textDim
                    font.pixelSize: 10
                    font.letterSpacing: 1.1
                }
            }
            Rectangle {
                z: 6
                anchors.fill: parent
                color: "#000000"
                border.color: appRoot.gold
                visible: appRoot.privacyMode
                Text { anchors.centerIn: parent; text: "PRIVATE"; color: appRoot.gold; font.pixelSize: 18; font.letterSpacing: 4 }
            }
        }

        GoldPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 58
            Layout.maximumHeight: 58
            RowLayout {
                anchors.fill: parent
                anchors.margins: 7
                spacing: 7
                Repeater {
                    model: [
                        {label:"▣  Generate", page:0},
                        {label:"♟  Pose Maker", page:9},
                        {label:"✦  Photoshop", page:8},
                        {label:"▧  Photos", page:4},
                        {label:"●  Cam Hub", page:5}
                    ]
                    GoldButton {
                        text: modelData.label
                        active: appRoot.pageIndex === modelData.page
                        Layout.fillWidth: true
                        Layout.minimumWidth: 78
                        onClicked: appRoot.pageIndex = modelData.page
                    }
                }
                Item { Layout.fillWidth: true }
                GoldButton { text: "✥  GENESIS AI  ›"; Layout.preferredWidth: 160; enabled: false }
                GoldButton {
                    text: appRoot.layoutEditMode ? "✏ EDITING" : "🔒 LAYOUT"
                    active: appRoot.layoutEditMode
                    Layout.preferredWidth: 122
                    onClicked: {
                        appRoot.layoutEditMode = !appRoot.layoutEditMode
                        if (!appRoot.layoutEditMode) appRoot.saveLayoutSettings()
                    }
                }
                GoldButton {
                    text: appRoot.privacyMode ? "🔒  Privacy On" : "🔓  Privacy Mode"
                    Layout.preferredWidth: 150
                    onClicked: appRoot.privacyMode = !appRoot.privacyMode
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 8

            GoldPanel {
                Layout.preferredWidth: 156
                Layout.fillHeight: true
                Column {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 6
                    Item {
                        width: 124; height: 84
                        anchors.horizontalCenter: parent.horizontalCenter
                        Image {
                            id: sidebarLogoSource
                            anchors.fill: parent
                            anchors.margins: 2
                            source: "../assets/genesis-cockpit-icon-balanced-final.png"
                            fillMode: Image.PreserveAspectCrop
                            asynchronous: true
                            cache: true
                        }
                        Rectangle {
                            z: 2
                            anchors.fill: parent
                            color: "transparent"
                            border.color: appRoot.brightGold
                            border.width: 2
                            radius: 8
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: appRoot.pageIndex = 0
                        }
                    }
                    Repeater {
                        model: [
                            {label:"▣  Image Gen", page:0}, {label:"✂  Media Tools", page:3},
                            {label:"▧  Photo Library", page:4}, {label:"●  Cam Hub", page:5},
                            {label:"▷  Entertainment", page:6}, {label:"⚙  System", page:7}
                        ]
                        GoldButton {
                            width: 140
                            height: 38
                            text: modelData.label
                            active: appRoot.pageIndex === modelData.page
                            onClicked: appRoot.pageIndex = modelData.page
                        }
                    }
                }
                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    anchors.margins: 9
                    height: Math.min(64, parent.height * 0.14)
                    color: "#0b0905"
                    border.color: appRoot.line
                    radius: 5
                    clip: true
                    Image {
                        anchors.fill: parent
                        anchors.margins: 3
                        source: appRoot.sideColumnImageSource
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                        visible: source.toString().length > 0 && !appRoot.privacyMode
                    }
                    Column {
                        anchors.centerIn: parent
                        spacing: 5
                        visible: appRoot.sideColumnImageSource.toString().length === 0 && !appRoot.privacyMode
                        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "+"; color: appRoot.gold; font.pixelSize: 28 }
                        Text { text: "COLUMN PHOTO"; color: appRoot.textDim; font.pixelSize: 12; font.letterSpacing: 1 }
                    }
                    Text {
                        anchors.centerIn: parent
                        text: "PRIVATE"
                        color: appRoot.gold
                        font.pixelSize: 13
                        font.letterSpacing: 2
                        visible: appRoot.privacyMode
                    }
                }
            }

            StackLayout {
                currentIndex: appRoot.pageIndex
                Layout.fillWidth: true
                Layout.fillHeight: true

                Item {
                    ScrollView {
                        anchors.fill: parent
                        clip: true
                        contentWidth: availableWidth
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded
                        ColumnLayout {
                            width: parent.width
                            height: implicitHeight
                            spacing: 6
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 52
                            Layout.maximumHeight: 52
                            Text { text: "♟"; color: appRoot.gold; font.pixelSize: 32 }
                            Column {
                                Text { text: "Image Generation"; color: appRoot.brightGold; font.family: genesisDisplayFont.name; font.pixelSize: 25; font.bold: true; font.letterSpacing: 0.4 }
                                Text { text: "Create with your verified local models."; color: appRoot.textDim; font.pixelSize: 13 }
                            }
                            Item { Layout.fillWidth: true }
                            GoldButton { text: "Fast 512"; active: appRoot.generationSpeed === "Fast"; Layout.preferredWidth: 92; onClicked: appRoot.setGenerationSpeed("Fast", 512) }
                            GoldButton { text: "Balanced 768"; active: appRoot.generationSpeed === "Balanced"; Layout.preferredWidth: 112; onClicked: appRoot.setGenerationSpeed("Balanced", 768) }
                            GoldButton { text: "Quality 1024"; active: appRoot.generationSpeed === "Quality"; Layout.preferredWidth: 108; onClicked: appRoot.setGenerationSpeed("Quality", 1024) }
                            GoldButton { text: "Photoreal"; Layout.preferredWidth: 105; onClicked: appRoot.applyPhotorealPreset() }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 46
                            Layout.maximumHeight: 46
                            SmallLabel { text: "ENGINE PRESET" }
                            Repeater {
                                model: appRoot.generationModel
                                GoldButton {
                                    Layout.fillWidth: true
                                    text: modelData.label
                                    active: index === appRoot.selectedGenerationIndex
                                    enabled: modelData.runnable
                                    ToolTip.visible: hovered
                                    ToolTip.text: modelData.runnable ? modelData.note : modelData.note + " · blocked until workflow validation"
                                    onClicked: appRoot.selectEnginePreset(index)
                                }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 44
                            Layout.maximumHeight: 44
                            Repeater {
                                model: ["Create", "Pose Library", "Workflow Editor", "Compare / Test", "History"]
                                GoldButton {
                                    text: modelData
                                    active: index === 0
                                    Layout.fillWidth: true
                                    onClicked: {
                                        if (index === 1)
                                            appRoot.pageIndex = 9
                                        else if (index === 2)
                                            appRoot.pageIndex = 2
                                    }
                                }
                            }
                        }
                        GoldPanel {
                            visible: appRoot.layoutEditMode
                            Layout.fillWidth: true
                            Layout.preferredHeight: visible ? 88 : 0
                            Layout.maximumHeight: visible ? 88 : 0
                            border.color: appRoot.brightGold
                            Row {
                                anchors.centerIn: parent
                                spacing: 8
                                SmallLabel { text: "UI LAYOUT"; anchors.verticalCenter: parent.verticalCenter }
                                GoldButton { text: "Preview −"; width: 92; onClicked: appRoot.createPreviewWidth = Math.max(260, appRoot.createPreviewWidth - 20) }
                                GoldButton { text: "Preview +"; width: 92; onClicked: appRoot.createPreviewWidth = Math.min(620, appRoot.createPreviewWidth + 20) }
                                GoldButton { text: "Prompt −"; width: 88; onClicked: appRoot.createPromptHeight = Math.max(80, appRoot.createPromptHeight - 10) }
                                GoldButton { text: "Prompt +"; width: 88; onClicked: appRoot.createPromptHeight = Math.min(220, appRoot.createPromptHeight + 10) }
                                GoldButton { text: "Panels −"; width: 88; onClicked: { appRoot.createReferenceHeight=Math.max(90,appRoot.createReferenceHeight-10); appRoot.createSourceHeight=Math.max(76,appRoot.createSourceHeight-10); appRoot.createOutputHeight=Math.max(76,appRoot.createOutputHeight-10) } }
                                GoldButton { text: "Panels +"; width: 88; onClicked: { appRoot.createReferenceHeight=Math.min(180,appRoot.createReferenceHeight+10); appRoot.createSourceHeight=Math.min(160,appRoot.createSourceHeight+10); appRoot.createOutputHeight=Math.min(150,appRoot.createOutputHeight+10) } }
                                GoldButton { text: "💾 SAVE"; width: 92; onClicked: appRoot.saveLayoutSettings() }
                                GoldButton { text: "↺ RESET"; width: 92; onClicked: appRoot.resetLayoutSettings() }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 8
                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: appRoot.createPromptHeight
                                    Layout.maximumHeight: appRoot.createPromptHeight
                                    GoldPanel {
                                        Layout.fillWidth: true; Layout.fillHeight: true
                                        SmallLabel { x: 10; y: 8; text: "Prompt" }
                                        TextArea { x: 8; y: 30; width: parent.width - 16; height: parent.height - 36; wrapMode: TextEdit.Wrap; color: appRoot.textMain; font.pixelSize: 14; background: Rectangle { color: "transparent" } text: appRoot.selectedPosePrompt; placeholderText: "Select a pose or enter a prompt"; onTextChanged: if (activeFocus) appRoot.selectedPosePrompt = text }
                                    }
                                    GoldPanel {
                                        Layout.fillWidth: true; Layout.fillHeight: true
                                        SmallLabel { x: 10; y: 8; text: "Negative Prompt (inactive for distilled engines)" }
                                        TextArea { x: 8; y: 30; width: parent.width - 16; height: parent.height - 36; wrapMode: TextEdit.Wrap; readOnly: true; color: appRoot.textDim; font.pixelSize: 14; background: Rectangle { color: "transparent" } text: appRoot.selectedPoseNegativePrompt; placeholderText: "Negative conditioning is zeroed" }
                                    }
                                }
                                GoldPanel {
                                    Layout.fillWidth: true; Layout.preferredHeight: appRoot.createReferenceHeight
                                    Layout.maximumHeight: appRoot.createReferenceHeight
                                    SmallLabel { x: 12; y: 10; text: "Reference / Pose" }
                                    GoldButton { x: 12; y: 38; width: 185; text: "Select from Pose Library"; onClicked: appRoot.pageIndex = 1 }
                                    SmallLabel { x: 220; y: 10; text: "Model & LoRA Selection (Auto-filtered)" }
                                    Row { x: 220; y: 40; spacing: 10
                                        PremiumCombo {
                                            id: generationModelPicker
                                            width: 210; height: 42
                                            model: appRoot.generationModel
                                            textRole: "label"
                                            onActivated: {
                                                appRoot.selectEnginePreset(currentIndex)
                                            }
                                        }
                                        PremiumCombo {
                                            id: loraOnePicker
                                            width: 185; height: 42
                                            model: appRoot.selectedGenerationProfile.loras
                                            onActivated: {
                                                appRoot.selectedLoraOne = currentText
                                                appRoot.syncLoraTriggers()
                                            }
                                        }
                                        PremiumCombo {
                                            id: loraTwoPicker
                                            width: 185; height: 42
                                            model: ["Stacking blocked"]
                                            enabled: false
                                        }
                                    }
                                    Text { x: 220; y: 84; width: parent.width - 232; text: appRoot.selectedGenerationProfile.note + "  ·  Triggers: " + appRoot.activeLoraTriggers; color: appRoot.textDim; font.pixelSize: 12; elide: Text.ElideRight }
                                }
                                GoldPanel {
                                    Layout.fillWidth: true; Layout.preferredHeight: 194
                                    Layout.maximumHeight: 194
                                    SmallLabel { x: 12; y: 8; text: "Character / Identity" }
                                    PremiumCombo {
                                        id: characterPicker; x: 12; y: 34; width: 220; height: 42
                                        model: genesisBridge.characters
                                        textRole: "name"
                                        onActivated: {
                                            var c = genesisBridge.characters[currentIndex]
                                            if (c) {
                                                appRoot.selectedCharacterId = c.id
                                                appRoot.selectedCharacterName = c.name
                                                appRoot.selectedCharacterImage = c.primaryImage
                                                appRoot.generationSource = c.primaryImage
                                            }
                                        }
                                    }
                                    FieldBox {
                                        x: 244; y: 34; width: 190; height: 42
                                        TextField { anchors.fill: parent; anchors.margins: 2; color: appRoot.textMain; placeholderText: "Character name"; text: appRoot.newCharacterName; background: Rectangle { color: "transparent" }
                                            onTextChanged: appRoot.newCharacterName = text }
                                    }
                                    CheckBox { x: 446; y: 36; text: "Adult 18+"; checked: appRoot.characterAdultConfirmed; onToggled: appRoot.characterAdultConfirmed = checked }
                                    GoldButton {
                                        x: 565; y: 34; width: 210; height: 42; text: "Create from Source Image"
                                        enabled: appRoot.generationSource.toString().length > 0 && appRoot.characterAdultConfirmed
                                        onClicked: {
                                            var cid = genesisBridge.createCharacterFromImage(appRoot.newCharacterName, appRoot.generationSource.toString(), appRoot.characterAdultConfirmed)
                                            if (cid.length) {
                                                appRoot.selectedCharacterId = cid
                                                appRoot.selectedCharacterName = appRoot.newCharacterName.length ? appRoot.newCharacterName : appRoot.generationSource.toString().split("/").pop()
                                                appRoot.selectedCharacterImage = appRoot.generationSource
                                            }
                                        }
                                    }
                                    Text { x: 790; y: 39; width: parent.width - 802; text: appRoot.selectedCharacterName.length ? "ACTIVE: " + appRoot.selectedCharacterName + " · identity source locked" : "Load a source image, confirm adult, then save it as a reusable character."; color: appRoot.selectedCharacterName.length ? "#66dd78" : appRoot.textDim; font.pixelSize: 12; wrapMode: Text.Wrap }
                                    PremiumCombo {
                                        id: anchorRolePicker; x: 12; y: 84; width: 150; height: 42
                                        model: ["close-up", "three-quarter", "side", "mid-shot", "full-body"]
                                        onActivated: appRoot.selectedAnchorRole = currentText
                                    }
                                    GoldButton {
                                        x: 174; y: 84; width: 190; height: 42; text: "Approve Current Anchor"
                                        enabled: appRoot.selectedCharacterId.length > 0 && appRoot.generationSource.toString().length > 0
                                        onClicked: genesisBridge.addCharacterReference(appRoot.selectedCharacterId, appRoot.generationSource.toString(), appRoot.selectedAnchorRole)
                                    }
                                    GoldButton {
                                        x: 376; y: 84; width: 190; height: 42; text: "Use Role as Identity"
                                        enabled: appRoot.selectedCharacterId.length > 0
                                        onClicked: {
                                            var chosen = genesisBridge.characterIdentitySource(appRoot.selectedCharacterId, appRoot.selectedAnchorRole)
                                            if (chosen.length) appRoot.generationSource = chosen
                                        }
                                    }
                                    Text { x: 580; y: 91; width: parent.width - 592; text: "Approved anchor roles: close-up · ¾ · side · mid-shot · full-body"; color: appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap }
                                    Text { x: 12; y: 139; width: parent.width - 24; text: "IDENTITY RULE: every new pose starts from an original/approved anchor — never from the previous generated output. Contact-sheet generation will use these role-labelled anchors."; color: appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap }
                                }
                                GoldPanel {
                                    Layout.fillWidth: true; Layout.preferredHeight: appRoot.createSourceHeight
                                    Layout.maximumHeight: appRoot.createSourceHeight
                                    SmallLabel { x: 12; y: 9; text: "Optional source image (selection survives presets and model changes)" }
                                    Rectangle {
                                        x: 12; y: 34; width: parent.width - 348; height: 46
                                        color: "#0b0b08"; border.color: appRoot.line; radius: 4
                                        Text { anchors.centerIn: parent; width: parent.width - 16; text: appRoot.generationSource.toString().length ? appRoot.generationSource.toString().split("/").pop() : "Choose an image or drop it here"; color: appRoot.generationSource.toString().length ? appRoot.textMain : appRoot.textDim; elide: Text.ElideMiddle; horizontalAlignment: Text.AlignHCenter }
                                        DropArea { anchors.fill: parent; onDropped: function(drop) { if (drop.urls.length) { appRoot.generationSource = drop.urls[0]; appRoot.useStageThree = true } } }
                                    }
                                    GoldButton {
                                        anchors.right: clearSourceButton.left; anchors.rightMargin: 8; y: 34; width: 152; height: 46; text: "Load Image"
                                        onClicked: {
                                            var chosen = genesisBridge.chooseSourceImage()
                                            if (chosen.length > 0) {
                                                appRoot.generationSource = chosen
                                                appRoot.useStageThree = true
                                            }
                                        }
                                    }
                                    GoldButton { id: clearSourceButton; anchors.right: parent.right; anchors.rightMargin: 12; y: 34; width: 145; height: 46; text: "Clear"; enabled: appRoot.generationSource.toString().length > 0; onClicked: appRoot.generationSource = "" }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    Repeater {
                                        model: [
                                            {title:"Stage 1 — Phr00t (Qwen)", model:"Qwen-Rapid-AIO-v19", detail:"Steps  7\nCFG  4.5\nSampler  Euler\nDenoise  1.0"},
                                            {title:"Stage 2 — Lustify (Refine)", model:"Lustify v20 Lightning", detail:"Steps  8\nCFG  1.0\nSampler  DPM++ 2M\nDenoise  0.4"},
                                            {title:"Stage 3 — ReActor (Face)", model:"ReActor (ROCm)", detail:"Face source  Reference\nStrength  0.5\nUpscale  2x Optional"}
                                        ]
                                        GoldPanel {
                                            Layout.fillWidth: true; Layout.fillHeight: true
                                            SmallLabel { x: 10; y: 10; text: modelData.title }
                                            Rectangle { x: 10; y: 40; width: 105; height: parent.height - 82; color: "#0b0b08"; border.color: appRoot.line
                                                Text { anchors.centerIn: parent; text: "PREVIEW"; color: appRoot.textDim }
                                            }
                                            Text { x: 126; y: 42; width: parent.width - 138; text: modelData.model + "\n\n" + modelData.detail; color: appRoot.textMain; font.pixelSize: 13; lineHeight: 1.4 }
                                            CheckBox {
                                                x: 12; anchors.bottom: parent.bottom; anchors.bottomMargin: 6
                                                text: index === 0 ? "Stage 1 is the pipeline input" : "Use previous stage output"
                                                enabled: index > 0
                                                checked: index === 0 || (index === 1 ? appRoot.useStageTwo : appRoot.useStageThree)
                                                onToggled: {
                                                    if (index === 1) appRoot.useStageTwo = checked
                                                    else if (index === 2) appRoot.useStageThree = checked
                                                }
                                            }
                                        }
                                    }
                                }
                                RowLayout {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 38
                                    CheckBox {
                                        text: "Upscale final output (2× Ultimate SD Upscale)"
                                        checked: appRoot.useUpscale
                                        enabled: genesisBridge.upscaleAvailable
                                        onToggled: appRoot.useUpscale = checked
                                        ToolTip.visible: hovered
                                        ToolTip.text: enabled ? "Consumes the final enabled stage output" : "Blocked until the required checkpoint, VAE, and 4x-UltraSharp model are installed"
                                    }
                                    Item { Layout.fillWidth: true }
                                    Text { text: "Identity lock: " + (appRoot.selectedCharacterId.length ? "Saved Character → approved anchor → selected pose" : (appRoot.generationSource.toString().length ? "Source image → pose" : "add source image")); color: appRoot.generationSource.toString().length ? "#66dd78" : appRoot.textDim; font.pixelSize: 12 }
                                }
                                GoldPanel {
                                    Layout.fillWidth: true; Layout.preferredHeight: appRoot.createOutputHeight
                                    Layout.maximumHeight: appRoot.createOutputHeight
                                    SmallLabel { x: 12; y: 8; text: "Output Settings" }
                                    Row { x: 12; y: 36; spacing: 8
                                        Repeater { model: ["Width  " + appRoot.generationWidth, "Height  " + appRoot.generationHeight, "Steps  4", "CFG  1.0", "Save to  GENESIS-Exports"]
                                            FieldBox { width: index === 4 ? 220 : 118; height: 40; Text { anchors.centerIn: parent; text: modelData; color: appRoot.textMain; font.pixelSize: 13 } }
                                        }
                                    }
                                    GoldButton {
                                        anchors.right: parent.right; anchors.rightMargin: 10; y: 28
                                        width: 190; height: 50
                                        active: enabled
                                        text: genesisBridge.busy ? "Generating…" : (appRoot.selectedGenerationProfile.runnable ? "▶  Generate" : "Workflow unavailable")
                                        enabled: !genesisBridge.busy
                                            && appRoot.selectedPosePrompt.trim().length > 0
                                            && appRoot.selectedGenerationProfile.runnable
                                            && (!appRoot.selectedGenerationProfile.sourceRequired || appRoot.generationSource.toString().length > 0)
                                        onClicked: genesisBridge.queueGenerate(
                                            appRoot.selectedPosePrompt,
                                            appRoot.selectedPoseNegativePrompt,
                                            appRoot.generationWidth,
                                            appRoot.generationHeight,
                                            appRoot.selectedGenerationProfile.model,
                                            appRoot.selectedLoraOne,
                                            appRoot.selectedLoraTwo,
                                            appRoot.generationSource.toString(),
                                            appRoot.selectedPoseSource.toString(),
                                            appRoot.useStageTwo,
                                            appRoot.useStageThree,
                                            appRoot.useUpscale
                                        )
                                    }
                                }
                            }
                            GoldPanel {
                                Layout.preferredWidth: appRoot.createPreviewWidth
                                Layout.fillHeight: true
                                clip: true
                                Image {
                                    anchors.fill: parent
                                    source: "../assets/panel_backgrounds/panel-01-image-generate.jpg"
                                    fillMode: Image.PreserveAspectCrop
                                    opacity: appRoot.privacyMode ? 0 : 0.16
                                }
                                Rectangle { anchors.fill: parent; color: "#9e000000" }
                                SmallLabel { x: 12; y: 10; text: "Preview" }
                                Rectangle { x: 10; y: 38; width: parent.width - 20; height: parent.height * 0.48; color: "#0b0b08"; border.color: appRoot.line
                                    Image { anchors.fill: parent; anchors.margins: 4; source: genesisBridge.previewUrl; fillMode: Image.PreserveAspectFit }
                                    Text { anchors.centerIn: parent; text: "GENERATED IMAGE PREVIEW"; color: appRoot.textDim; visible: genesisBridge.previewUrl.length === 0 }
                                }
                                Row { x: 10; y: parent.height * 0.52; spacing: 5
                                    GoldButton { width: 106; text: "Open Image"; enabled: genesisBridge.previewUrl.length > 0; onClicked: genesisBridge.openPreview() }
                                    GoldButton { width: 106; text: "Show Folder"; onClicked: genesisBridge.openOutputFolder() }
                                    GoldButton {
                                        width: 106
                                        text: "Send to Edit"
                                        enabled: genesisBridge.previewUrl.length > 0
                                        onClicked: {
                                            appRoot.editSource = genesisBridge.previewUrl
                                            appRoot.pageIndex = 8
                                        }
                                    }
                                }
                                SmallLabel { x: 12; y: parent.height * 0.62; text: "Generation Info" }
                                Text { x: 12; y: parent.height * 0.67; width: parent.width - 24; text: "Engine: " + appRoot.selectedGenerationProfile.label + "\nCreate workflow: " + (appRoot.selectedGenerationProfile.runnable ? "validated" : "not connected") + "\nLoRA routing: one verified adapter\nNegative conditioning: distilled / zeroed\nSize: " + appRoot.generationWidth + " × " + appRoot.generationHeight + "\nPreset: " + appRoot.generationSpeed + "\nStatus: " + genesisBridge.status; color: appRoot.textMain; font.pixelSize: 12; lineHeight: 1.35; elide: Text.ElideRight }
                            }
                        }
                    }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8
                        RowLayout {
                            Layout.fillWidth: true; Layout.preferredHeight: 60
                            Layout.maximumHeight: 60
                            Text { text: "♟"; color: appRoot.gold; font.pixelSize: 36 }
                            Column { Text { text: "POSE LIBRARY"; color: appRoot.brightGold; font.family: genesisDisplayFont.name; font.pixelSize: 29; font.bold: true; font.letterSpacing: 1 }
                                Text { text: "Find the perfect pose for your vision."; color: appRoot.textDim; font.pixelSize: 15 }
                            }
                            Item { Layout.fillWidth: true }
                            GoldButton { text: "Presets"; Layout.preferredWidth: 100; onClicked: presetPopup.open() }
                            GoldButton { text: "▦  Grid"; Layout.preferredWidth: 90; enabled: false }
                        }
                        RowLayout {
                            Layout.fillWidth: true; Layout.preferredHeight: 46
                            Layout.maximumHeight: 46
                            Repeater { model: ["⌕  Search poses…", "Category  All ⌄", "Resolution  All ⌄", "Prompt  Mapped/All ⌄", "Model  AUTO ⌄", "Sort  Name ⌄"]
                                FieldBox { Layout.fillWidth: true; Layout.fillHeight: true; Text { anchors.centerIn: parent; text: modelData; color: appRoot.textMain; font.pixelSize: 13 } }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 8
                            GoldPanel {
                                Layout.preferredWidth: 205; Layout.fillHeight: true
                                SmallLabel { x: 12; y: 12; text: "Categories" }
                                Column { x: 10; y: 42; spacing: 5
                                    Repeater { model: ["All Poses          486", "Standing             172", "Sitting                  76", "Suspended           42", "Lying                    79", "Squatting            36", "Kneeling             33", "Split Leg              30", "All Fours             13", "Metal Stocks          5"]
                                        GoldButton { width: 185; height: 36; text: modelData; font.pixelSize: 13; enabled: false }
                                    }
                                }
                            }
                            GridLayout {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                columns: 4; rowSpacing: 8; columnSpacing: 8
                                Repeater {
                                    model: appRoot.poseModel
                                    GoldPanel {
                                        Layout.fillWidth: true; Layout.fillHeight: true
                                        Rectangle { anchors.fill: parent; anchors.margins: 5; color: index % 2 ? "#0b0b08" : "#100d07"
                                            Image { anchors.fill: parent; source: modelData.source; fillMode: Image.PreserveAspectFit; asynchronous: true; cache: true }
                                        }
                                        Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 24; color: "#b0000000"
                                            Text { anchors.centerIn: parent; text: modelData.name; color: "white"; font.pixelSize: 13 }
                                        }
                                        Text { anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 9; text: "♡"; color: appRoot.brightGold; font.pixelSize: 20 }
                                        MouseArea {
                                            anchors.fill: parent
                                            onClicked: {
                                                appRoot.selectedPoseSource = modelData.source
                                                appRoot.selectedPoseName = modelData.name
                                                appRoot.selectedPoseCategory = modelData.category
                                                appRoot.selectedPoseId = modelData.poseId
                                                appRoot.selectedPosePrompt = modelData.prompt
                                                if (appRoot.selectedCharacterId.length > 0) {
                                                    var identitySource = genesisBridge.characterIdentitySource(appRoot.selectedCharacterId)
                                                    if (identitySource.length > 0) appRoot.generationSource = identitySource
                                                }
                                                appRoot.selectedPoseNegativePrompt = modelData.negativePrompt
                                                appRoot.selectedPosePromptSource = modelData.promptSource
                                                appRoot.selectedPoseTemplateId = modelData.promptTemplateId
                                            }
                                        }
                                    }
                                }
                            }
                            GoldPanel {
                                Layout.preferredWidth: 355; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 6
                                    SmallLabel { text: appRoot.selectedPoseName }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: Math.min(180, parent.height * 0.36)
                                        color: "#0b0b08"; border.color: appRoot.line
                                        Image { anchors.fill: parent; anchors.margins: 4; source: appRoot.selectedPoseSource; fillMode: Image.PreserveAspectFit; asynchronous: true }
                                        Text { anchors.centerIn: parent; text: "SELECTED POSE PREVIEW"; color: appRoot.textDim; visible: appRoot.selectedPoseSource.toString().length === 0 }
                                    }
                                    SmallLabel { text: "Pose Information" }
                                    Text {
                                        Layout.fillWidth: true
                                        text: "Category:  " + appRoot.selectedPoseCategory + "\nPose ID:  " + appRoot.selectedPoseId + "\nPrompt source:  " + appRoot.selectedPosePromptSource + "\n485 mapped poses · model-safe LoRA filtering"
                                        color: appRoot.textMain
                                        font.pixelSize: 12
                                        lineHeight: 1.2
                                        wrapMode: Text.Wrap
                                    }
                                    SmallLabel { text: "Camera / geometry preset" }
                                PremiumCombo {
                                    id: grokPresetPicker
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 40
                                    model: appRoot.grokGeometryPresets
                                    textRole: "label"
                                    onActivated: {
                                        if (currentIndex > 0) {
                                            appRoot.selectedPosePrompt = appRoot.grokGeometryPresets[currentIndex].prompt
                                            appRoot.selectedPosePromptSource = "GROK_GEOMETRY_PRESET"
                                        }
                                    }
                                }
                                    Item { Layout.fillHeight: true }
                                    GoldButton { Layout.preferredWidth: 150; text: "♟  Use Pose"; onClicked: appRoot.pageIndex = 0 }
                                }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true; Layout.preferredHeight: 42
                            Layout.maximumHeight: 42
                            Item { Layout.fillWidth: true }
                            GoldButton { text: "‹"; Layout.preferredWidth: 42; enabled: false }
                            GoldButton { text: "1"; Layout.preferredWidth: 42; active: true }
                            GoldButton { text: "2"; Layout.preferredWidth: 42; enabled: false }
                            GoldButton { text: "3"; Layout.preferredWidth: 42; enabled: false }
                            GoldButton { text: "›"; Layout.preferredWidth: 42; enabled: false }
                            Item { Layout.fillWidth: true }
                            Text { text: "486 indexed poses · 485 Grok Klein mappings · 1 AUTO fallback"; color: appRoot.textDim; font.pixelSize: 12 }
                        }
                    }
                }

                ModulePage {
                    pageTitle: "Workflow Editor"
                    pageSubtitle: "Build, inspect, and test ComfyUI generation pipelines."
                    pageIcon: "◇"
                    sectionTitle: "Workflow Library"
                    quickActions: ["New Workflow", "Import JSON", "Validate"]
                    cards: [
                        {icon:"①", title:"Stage 1 — Phr00t", detail:"Qwen Rapid base generation and prompt controls.", action:"Open Workflow"},
                        {icon:"②", title:"Stage 2 — Lustify", detail:"Refinement, denoise, sampler, and upscale routing.", action:"Open Workflow"},
                        {icon:"③", title:"Stage 3 — ReActor", detail:"ROCm face replacement and output finishing.", action:"Open Workflow"},
                        {icon:"⌘", title:"Node Inspector", detail:"Review loaders, samplers, LoRAs, and image paths.", action:"Inspect Nodes"},
                        {icon:"A/B", title:"Compare / Test", detail:"Run controlled workflow and model comparisons.", action:"Start Comparison"},
                        {icon:"✓", title:"Compatibility", detail:"Check model, LoRA, and stage compatibility rules.", action:"View Report"}
                    ]
                }

                ModulePage {
                    pageTitle: "Media Tools"
                    pageSubtitle: "Create, convert, enhance, and deliver image and video assets."
                    pageIcon: "✂"
                    sectionTitle: "Media Workspace"
                    quickActions: ["Import Media", "New Project", "Open Output"]
                    cards: [
                        {icon:"▶", title:"Video Generation", detail:"Create and manage generated video sequences.", action:"Open Video Gen"},
                        {icon:"✦", title:"Enhance / Upscale", detail:"Improve detail, resolution, and presentation quality.", action:"Open Enhancer"},
                        {icon:"◐", title:"Background Tools", detail:"Remove, replace, blur, or extend backgrounds.", action:"Open Backgrounds"},
                        {icon:"⇄", title:"Format Converter", detail:"Convert image and video formats in batches.", action:"Open Converter"},
                        {icon:"Ps", title:"Photoshop Bridge", detail:"Send current media to the configured editor.", action:"Send to Photoshop"},
                        {icon:"▤", title:"Batch Processor", detail:"Queue repeatable media operations and exports.", action:"Build Batch"}
                    ]
                }

                ModulePage {
                    pageTitle: "Photo Library"
                    pageSubtitle: "Browse, organise, search, and curate your local collection."
                    pageIcon: "▧"
                    sectionTitle: "Library & Collections"
                    quickActions: ["Add Folder", "Scan Library", "New Collection"]
                    cards: [
                        {icon:"▦", title:"All Photos", detail:"Browse the indexed GENESIS photo collection.", action:"Browse Photos"},
                        {icon:"★", title:"Favorites", detail:"Review starred images and selected results.", action:"Open Favorites"},
                        {icon:"☺", title:"People & Faces", detail:"Group and search recognized faces locally.", action:"Open People"},
                        {icon:"⌕", title:"Smart Search", detail:"Filter by metadata, date, rating, tags, and source.", action:"Search Library"},
                        {icon:"≋", title:"Duplicates", detail:"Find visually similar files and safe duplicates.", action:"Open Duplicate Lab"},
                        {icon:"↗", title:"Export & Share", detail:"Prepare selected images for delivery or editing.", action:"Export Selection"}
                    ]
                }

                ModulePage {
                    pageTitle: "Cam Hub"
                    pageSubtitle: "Monitor local cameras and manage recording destinations."
                    pageIcon: "●"
                    sectionTitle: "Camera Sources"
                    quickActions: ["Add Camera", "Grid View", "Recordings"]
                    cards: [
                        {icon:"CAM 1", title:"Front Camera", detail:"Local stream placeholder — connection ready.", action:"Open Camera"},
                        {icon:"CAM 2", title:"Side Camera", detail:"Local stream placeholder — connection ready.", action:"Open Camera"},
                        {icon:"CAM 3", title:"Studio Camera", detail:"Local stream placeholder — connection ready.", action:"Open Camera"},
                        {icon:"CAM 4", title:"Outdoor Camera", detail:"Local stream placeholder — connection ready.", action:"Open Camera"},
                        {icon:"◉", title:"Recordings", detail:"Browse locally stored clips and snapshots.", action:"Browse Recordings"},
                        {icon:"⚙", title:"Camera Settings", detail:"Configure go2rtc sources and privacy controls.", action:"Configure Hub"}
                    ]
                }

                ModulePage {
                    pageTitle: "Entertainment"
                    pageSubtitle: "Launch and organise your local entertainment services."
                    pageIcon: "▷"
                    sectionTitle: "Entertainment Hub"
                    quickActions: ["Favorites", "Recently Used", "Manage Apps"]
                    cards: [
                        {icon:"♫", title:"Music", detail:"Open local music and connected playback services.", action:"Open Music"},
                        {icon:"▶", title:"Movies & TV", detail:"Browse configured video libraries and players.", action:"Open Video Library"},
                        {icon:"▣", title:"Games", detail:"Launch configured games and local frontends.", action:"Open Games"},
                        {icon:"◫", title:"Web Apps", detail:"Access approved entertainment web services.", action:"Browse Apps"},
                        {icon:"☆", title:"Favorites", detail:"Pin frequently used media and destinations.", action:"View Favorites"},
                        {icon:"⚙", title:"Connections", detail:"Manage local players and optional integrations.", action:"Configure"}
                    ]
                }

                ModulePage {
                    pageTitle: "System"
                    pageSubtitle: "Control GENESIS services, resources, settings, and recovery."
                    pageIcon: "⚙"
                    sectionTitle: "System Control"
                    quickActions: ["Health Check", "View Logs", "Backup"]
                    cards: [
                        {icon:"GPU", title:"GPU & VRAM", detail:"Monitor graphics workload and memory use.", action:"Open Monitor"},
                        {icon:"UI", title:"ComfyUI Service", detail:"Check status, start, stop, and open ComfyUI.", action:"Manage Service"},
                        {icon:"AI", title:"GENESIS AI", detail:"Configure the local assistant and model route.", action:"AI Settings"},
                        {icon:"↻", title:"Backup & Restore", detail:"Create recoverable settings and database snapshots.", action:"Open Recovery"},
                        {icon:"☷", title:"Models & Storage", detail:"Review model inventory, paths, and disk use.", action:"Manage Storage"},
                        {icon:"⚙", title:"Application Settings", detail:"Appearance, privacy, startup, and integrations.", action:"Open Settings"}
                    ]
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 58
                            Text { text: "◐"; color: appRoot.gold; font.pixelSize: 34 }
                            Column {
                                Text { text: "Inpaint / Edit"; color: appRoot.brightGold; font.family: genesisDisplayFont.name; font.pixelSize: 27; font.bold: true; font.letterSpacing: 0.4 }
                                Text { text: "Change part of an image while preserving everything else."; color: appRoot.textDim; font.pixelSize: 14 }
                            }
                            Item { Layout.fillWidth: true }
                            GoldButton { text: "Back to Create"; Layout.preferredWidth: 130; onClicked: appRoot.pageIndex = 0 }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 8
                            GoldPanel {
                                Layout.preferredWidth: 330
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 12; spacing: 8
                                    SmallLabel { text: "1. Source Image" }
                                    Rectangle {
                                        Layout.fillWidth: true; Layout.fillHeight: true
                                        color: "#0b0b08"; border.color: appRoot.line; radius: 5
                                        Image { anchors.fill: parent; anchors.margins: 5; source: appRoot.editSource; fillMode: Image.PreserveAspectFit }
                                        Text { anchors.centerIn: parent; text: "DROP SOURCE IMAGE"; color: appRoot.textDim; visible: appRoot.editSource.toString().length === 0 }
                                        DropArea { anchors.fill: parent; onDropped: function(drop) { if (drop.urls.length) appRoot.editSource = drop.urls[0] } }
                                    }
                                    GoldButton {
                                        Layout.fillWidth: true
                                        text: "Use Current Preview"
                                        enabled: genesisBridge.previewUrl.length > 0
                                        onClicked: appRoot.editSource = genesisBridge.previewUrl
                                    }
                                }
                            }
                            GoldPanel {
                                Layout.preferredWidth: 330
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 12; spacing: 8
                                    SmallLabel { text: "2. Mask / Reference" }
                                    Rectangle {
                                        Layout.fillWidth: true; Layout.fillHeight: true
                                        color: "#0b0b08"; border.color: appRoot.line; radius: 5
                                        Image { anchors.fill: parent; anchors.margins: 5; source: appRoot.editMask; fillMode: Image.PreserveAspectFit }
                                        Text { anchors.centerIn: parent; text: "DROP MASK IMAGE"; color: appRoot.textDim; visible: appRoot.editMask.toString().length === 0 }
                                        DropArea { anchors.fill: parent; onDropped: function(drop) { if (drop.urls.length) appRoot.editMask = drop.urls[0] } }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        GoldButton { Layout.fillWidth: true; text: "Choose Mask"; onClicked: appRoot.editMask = genesisBridge.chooseSourceImage() }
                                        GoldButton { Layout.fillWidth: true; text: "Clear"; onClicked: appRoot.editMask = "" }
                                    }
                                }
                            }
                            GoldPanel {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 12; spacing: 9
                                    SmallLabel { text: "3. Edit Instructions" }
                                    TextArea {
                                        Layout.fillWidth: true; Layout.preferredHeight: 150
                                        text: appRoot.editPrompt
                                        placeholderText: "Describe only the change you want. Include lighting and camera continuity."
                                        wrapMode: TextEdit.Wrap
                                        color: appRoot.textMain
                                        onTextChanged: if (activeFocus) appRoot.editPrompt = text
                                        background: Rectangle { color: "#0b0b08"; border.color: appRoot.line; radius: 4 }
                                    }
                                    SmallLabel { text: "Edit engines" }
                                    FieldBox {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 42
                                        Text { anchors.centerIn: parent; text: "FluxUp Q4 image edit · JuggernautXL masked inpaint"; color: appRoot.textMain; font.pixelSize: 13 }
                                    }
                                    SmallLabel { text: "Edit strength  " + appRoot.editStrength.toFixed(2) }
                                    Slider { Layout.fillWidth: true; from: 0.05; to: 0.95; stepSize: 0.05; value: appRoot.editStrength; onMoved: appRoot.editStrength = value }
                                    Text { Layout.fillWidth: true; text: "Lower values preserve identity and composition. Higher values allow broader changes."; color: appRoot.textDim; font.pixelSize: 12; wrapMode: Text.Wrap }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 105
                                        color: "#0b0b08"
                                        border.color: appRoot.line
                                        radius: 4
                                        Image { anchors.fill: parent; anchors.margins: 4; source: genesisBridge.previewUrl; fillMode: Image.PreserveAspectFit }
                                        Text { anchors.centerIn: parent; text: "EDIT PREVIEW"; color: appRoot.textDim; visible: genesisBridge.previewUrl.length === 0 }
                                    }
                                    Text { Layout.fillWidth: true; text: genesisBridge.status; color: genesisBridge.busy ? appRoot.gold : appRoot.textDim; font.pixelSize: 12; wrapMode: Text.Wrap }
                                    Item { Layout.fillHeight: true }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        GoldButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 54
                                            text: genesisBridge.busy ? "Working…" : "▶  Image Edit"
                                            enabled: !genesisBridge.busy && genesisBridge.editAvailable && appRoot.editSource.toString().length > 0 && appRoot.editPrompt.trim().length > 0
                                            onClicked: genesisBridge.queueEdit(appRoot.editSource.toString(), appRoot.editPrompt, appRoot.editStrength)
                                        }
                                        GoldButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 54
                                            text: genesisBridge.busy ? "Working…" : "◉  Masked Inpaint"
                                            enabled: !genesisBridge.busy && genesisBridge.inpaintAvailable && appRoot.editSource.toString().length > 0 && appRoot.editMask.toString().length > 0 && appRoot.editPrompt.trim().length > 0
                                            onClicked: genesisBridge.queueInpaint(appRoot.editSource.toString(), appRoot.editMask.toString(), appRoot.editPrompt, appRoot.editStrength)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 7
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 50
                            Text { text: "♟"; color: appRoot.gold; font.pixelSize: 32 }
                            Column {
                                Text { text: "POSE MAKER"; color: appRoot.brightGold; font.family: genesisDisplayFont.name; font.pixelSize: 27; font.bold: true; font.letterSpacing: 1 }
                                Text { text: "Phr00t  →  Lustify  →  ReActor ROCm"; color: appRoot.textDim; font.pixelSize: 13 }
                            }
                            Item { Layout.fillWidth: true }
                            GoldButton { text: "Browse Pose Library"; Layout.preferredWidth: 170; onClicked: appRoot.pageIndex = 1 }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 205
                            spacing: 8
                            GoldPanel {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 10; spacing: 6
                                    SmallLabel { text: "PERSON / SOURCE IMAGE" }
                                    Rectangle {
                                        Layout.fillWidth: true; Layout.fillHeight: true
                                        color: appRoot.panelRaised; border.color: appRoot.line; radius: 5
                                        Image { anchors.fill: parent; anchors.margins: 5; source: appRoot.generationSource; fillMode: Image.PreserveAspectFit }
                                        Column { anchors.centerIn: parent; visible: appRoot.generationSource.toString().length === 0; spacing: 4
                                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "IMAGE PREVIEW"; color: appRoot.textDim; font.pixelSize: 18; font.bold: true }
                                            Text { text: "drop source image"; color: appRoot.textDim; font.pixelSize: 12 }
                                        }
                                        DropArea { anchors.fill: parent; onDropped: function(drop) { if (drop.urls.length) appRoot.generationSource = drop.urls[0] } }
                                    }
                                }
                            }
                            GoldPanel {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 10; spacing: 6
                                    SmallLabel { text: "POSE REFERENCE (OPTIONAL)" }
                                    Rectangle {
                                        Layout.fillWidth: true; Layout.fillHeight: true
                                        color: appRoot.panelRaised; border.color: appRoot.line; radius: 5
                                        Image { anchors.fill: parent; anchors.margins: 5; source: appRoot.selectedPoseSource; fillMode: Image.PreserveAspectFit }
                                        Text { anchors.centerIn: parent; text: "SELECT FROM POSE LIBRARY"; color: appRoot.textDim; visible: appRoot.selectedPoseSource.toString().length === 0 }
                                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: appRoot.pageIndex = 1 }
                                    }
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true; Layout.preferredHeight: 42
                            Repeater {
                                model: appRoot.poseMakerPresets.slice(0, 5)
                                GoldButton {
                                    Layout.fillWidth: true; text: modelData.label
                                    onClicked: {
                                        appRoot.selectedPosePrompt = modelData.prompt
                                        appRoot.selectedPosePromptSource = "POSE_MAKER_PRESET"
                                    }
                                }
                            }
                            PremiumCombo {
                                id: poseMakerPresetPicker
                                Layout.preferredWidth: 230
                                model: appRoot.poseMakerPresets
                                textRole: "label"
                                onActivated: {
                                    appRoot.selectedPosePrompt = appRoot.poseMakerPresets[currentIndex].prompt
                                    appRoot.selectedPosePromptSource = "CURATED_DATABASE"
                                }
                            }
                        }

                        GoldPanel {
                            Layout.fillWidth: true; Layout.preferredHeight: 88
                            SmallLabel { x: 10; y: 8; text: "POSE INSTRUCTION" }
                            TextArea {
                                x: 8; y: 30; width: parent.width - 16; height: parent.height - 36
                                text: appRoot.selectedPosePrompt
                                placeholderText: "Keep the same person and facial identity. Change only the pose and position."
                                wrapMode: TextEdit.Wrap; color: appRoot.textMain
                                background: Rectangle { color: "transparent" }
                                onTextChanged: if (activeFocus) appRoot.selectedPosePrompt = text
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true; Layout.preferredHeight: 44
                            CheckBox { text: "Stage 2 — Lustify refine"; checked: appRoot.useStageTwo; onToggled: appRoot.useStageTwo = checked }
                            CheckBox { text: "Stage 3 — ReActor face lock"; checked: appRoot.useStageThree; onToggled: appRoot.useStageThree = checked }
                            CheckBox { text: "Face restore after ReActor"; checked: appRoot.useUpscale; onToggled: appRoot.useUpscale = checked }
                            Item { Layout.fillWidth: true }
                            GoldButton {
                                Layout.preferredWidth: 280; Layout.preferredHeight: 50; active: enabled
                                text: genesisBridge.busy ? "GENERATING POSE…" : "GENERATE POSE"
                                enabled: !genesisBridge.busy && appRoot.selectedGenerationProfile.runnable
                                    && appRoot.generationSource.toString().length > 0
                                    && appRoot.selectedPosePrompt.trim().length > 0
                                onClicked: genesisBridge.queueGenerate(
                                    appRoot.selectedPosePrompt, appRoot.selectedPoseNegativePrompt,
                                    appRoot.generationWidth, appRoot.generationHeight,
                                    appRoot.selectedGenerationProfile.model, appRoot.selectedLoraOne,
                                    appRoot.selectedLoraTwo, appRoot.generationSource.toString(),
                                    appRoot.selectedPoseSource.toString(), appRoot.useStageTwo,
                                    appRoot.useStageThree, appRoot.useUpscale
                                )
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 8
                            Repeater {
                                model: ["STAGE 1 — Phr00t", "STAGE 2 — Lustify", "STAGE 3 — Final ReActor"]
                                GoldPanel {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    SmallLabel { x: 10; y: 9; text: modelData }
                                    Rectangle {
                                        anchors.fill: parent; anchors.margins: 10; anchors.topMargin: 36
                                        color: appRoot.panelRaised; border.color: index === 2 ? appRoot.gold : appRoot.line; radius: 5
                                        Image { anchors.fill: parent; anchors.margins: 5; source: index === 2 ? genesisBridge.previewUrl : ""; fillMode: Image.PreserveAspectFit }
                                        Text { anchors.centerIn: parent; text: index === 2 && genesisBridge.previewUrl.length > 0 ? "" : "OUTPUT PREVIEW"; color: appRoot.textDim; font.pixelSize: 15 }
                                    }
                                }
                            }
                        }
                        FieldBox {
                            Layout.fillWidth: true; Layout.preferredHeight: 42
                            Text { anchors.left: parent.left; anchors.leftMargin: 12; anchors.verticalCenter: parent.verticalCenter; text: "RUN LOG  ·  " + genesisBridge.status; color: appRoot.textDim; font.pixelSize: 12 }
                        }
                    }
                }
            }
        }

        GoldPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 46
            Layout.maximumHeight: 46
            RowLayout {
                anchors.fill: parent; anchors.margins: 10; spacing: 18
                Text { text: Qt.formatDateTime(new Date(), "ddd, d MMM yyyy   hh:mm"); color: appRoot.textMain; font.pixelSize: 12 }
                Text { text: runtimeStatus.comfyOnline ? "ComfyUI:  ● Online" : "ComfyUI:  ○ Offline"; color: runtimeStatus.comfyOnline ? "#66dd78" : appRoot.gold; font.pixelSize: 12 }
                Text { text: "GPU: " + runtimeStatus.gpuName; color: appRoot.textMain; font.pixelSize: 12 }
                Text { text: "VRAM: " + runtimeStatus.vramUsedGiB + " / " + runtimeStatus.vramTotalGiB + " GB"; color: appRoot.textMain; font.pixelSize: 12 }
                Item { Layout.fillWidth: true }
                Text { text: "GENESIS v1.0.0"; color: appRoot.gold; font.pixelSize: 12 }
                Text { text: "Keep walking Allan…"; color: appRoot.brightGold; font.pixelSize: 16; font.italic: true }
                Text { text: "⚙"; color: appRoot.textMain; font.pixelSize: 23 }
            }
        }
    }
}
