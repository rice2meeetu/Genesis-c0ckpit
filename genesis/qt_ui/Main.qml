import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import QtMultimedia

ApplicationWindow {
    id: appRoot
    visible: true
    width: 1536
    height: 960
    minimumWidth: 1280
    minimumHeight: 760
    title: "GENESIS COCKPIT"
    color: "#02040a"
    font.family: "Noto Sans"
    font.pixelSize: 14

    readonly property color gold: "#e5b94f"
    readonly property color brightGold: "#ffd978"
    readonly property color panel: "#060b14"
    readonly property color panelSoft: "#0b1320"
    readonly property color panelRaised: "#101b2a"
    readonly property color line: "#4a3a1a"
    readonly property color lineSoft: "#29251b"
    readonly property color textMain: "#f4e8c8"
    readonly property color textDim: "#aaa99f"
    FontLoader { id: genesisDisplayFont; source: "../assets/fonts/Exo2-Black.ttf" }
    property bool privacyMode: false
    property int pageIndex: 0
    readonly property var pageNames: ["IMAGE GENERATION", "POSE LIBRARY", "WORKFLOW EDITOR", "MEDIA TOOLS", "PHOTO LIBRARY", "CAM HUB", "ENTERTAINMENT", "SYSTEM", "INPAINT / EDIT"]
    readonly property var pageBannerSources: [
        "../assets/panel_backgrounds/panel-01-image-generate.jpg",
        "../assets/panel_backgrounds/panel-02-pose-lab.jpg",
        "../assets/panel_backgrounds/panel-04-prompt-manager.jpg",
        "../assets/panel_backgrounds/panel-06-duplicate-lab.jpg",
        "../assets/panel_backgrounds/panel-05-photo-organiser.jpg",
        "../assets/panel_backgrounds/panel-08-camera-hub.png",
        "../assets/panel_backgrounds/panel-07-photo-viewer.png",
        "../assets/panel_backgrounds/panel-03-face-studio.jpg",
        "../assets/panel_backgrounds/panel-01-image-generate.jpg"
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
        "../assets/panel_backgrounds/genesis-cockpit-banner-user-right.mp4"
    ]
    readonly property var grokGeometryPresets: [
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
    readonly property var strengthProfiles: ["NATURAL", "BALANCED", "STRONG", "STRICT", "MAX POSE", "MAX IDENTITY", "HYBRID STRONG", "CUSTOM"]
    readonly property var posePromptModes: ["AUTO — prompt from selected pose", "MANUAL — keep my written prompt", "POSE ONLY — no written prompt"]
    readonly property var vramPresets: ["QUALITY · 832×1216", "BALANCED · 768×1152", "FAST SAFE · 704×1024"]
    // Editable in Qt Design Studio. Leave blank to show a framed placeholder.
    property url photoOneSource: ""
    property url photoTwoSource: ""
    property url photoThreeSource: ""
    property url photoFourSource: ""
    property url sideColumnImageSource: ""
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
        width: 780
        height: 650
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
            GridLayout {
                Layout.fillWidth: true
                columns: 2
                rowSpacing: 8
                columnSpacing: 8
                Repeater {
                    model: appRoot.grokGeometryPresets.slice(1)
                    GoldButton {
                        Layout.fillWidth: true
                        height: 42
                        text: modelData.label
                        active: appRoot.activeGrokPreset === modelData.label
                        onClicked: {
                            appRoot.selectedPosePrompt = modelData.prompt
                            appRoot.selectedPosePromptSource = "GROK_GEOMETRY_PRESET"
                            appRoot.activeGrokPreset = modelData.label
                            appRoot.activePresetStatus = "Grok guide loaded: " + modelData.label
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
        border.color: appRoot.lineSoft
        border.width: 1
        radius: 8
    }

    component GoldButton: Button {
        id: control
        property bool active: false
        implicitHeight: 44
        leftPadding: 12
        rightPadding: 12
        font.pixelSize: 14
        font.weight: active ? Font.DemiBold : Font.Medium
        contentItem: Text {
            text: control.text
            color: !control.enabled ? "#68675f" : (control.down || control.active ? "#171006" : (control.hovered ? appRoot.brightGold : appRoot.textMain))
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Item {
            Rectangle {
                anchors.fill: parent
                anchors.margins: -3
                radius: 8
                color: "transparent"
                border.width: 2
                border.color: appRoot.brightGold
                opacity: control.active ? 0.42 : (control.hovered ? 0.20 : 0)
            }
            Rectangle {
                anchors.fill: parent
                radius: 6
                border.color: !control.enabled ? appRoot.lineSoft : (control.active || control.hovered ? appRoot.brightGold : appRoot.line)
                border.width: control.active ? 2 : 1
                gradient: Gradient {
                    GradientStop { position: 0; color: control.down ? "#efc45b" : (control.active ? "#f2ca64" : (control.hovered ? "#17263a" : "#0c1421")) }
                    GradientStop { position: 1; color: control.down ? "#a97b22" : (control.active ? "#ad7c22" : "#040811") }
                }
                Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 2; height: 1; color: control.active || control.hovered ? "#80ffe8a3" : "#18ffffff" }
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
        background: Rectangle {
            color: picker.pressed ? "#17263a" : "#09111e"
            border.color: picker.hovered || picker.popup.visible ? appRoot.brightGold : appRoot.line
            border.width: picker.popup.visible ? 2 : 1
            radius: 6
        }
        delegate: ItemDelegate {
            width: picker.width
            height: 40
            contentItem: Text {
                text: picker.textRole ? model[picker.textRole] : modelData
                color: highlighted ? "#171006" : appRoot.textMain
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
        color: "#111513"
        border.color: "#30332d"
        radius: 4
    }

    component SmallLabel: Text {
        color: appRoot.gold
        font.family: appRoot.font.family
        font.pixelSize: 14
        font.bold: true
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
        Rectangle { anchors.fill: parent; color: "#c0020710" }

        ColumnLayout {
            anchors.fill: parent
            spacing: 8
            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 58
                Layout.maximumHeight: 58
                Text { text: pageIcon; color: appRoot.gold; font.pixelSize: 34 }
                Column {
                    Text { text: pageTitle; color: appRoot.brightGold; font.pixelSize: 27; font.bold: true }
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
                                    color: index % 2 ? "#111512" : "#161914"
                                    border.color: "#302b1c"
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
                            Text { anchors.centerIn: parent; text: runtimeStatus.ready ? "SYSTEM READY" : "CHECK REQUIRED"; color: runtimeStatus.ready ? "#59d66f" : "#e5b94f"; font.pixelSize: 18; font.bold: true }
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
                        Text { Layout.fillWidth: true; text: "Preview module. Disabled controls are not connected to the Qt cockpit yet."; color: appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap }
                    }
                }
            }
        }
    }

    MediaPlayer {
        id: leftPlayer
        source: "../assets/panel_backgrounds/genesis-cockpit-banner.mp4"
        loops: MediaPlayer.Infinite
        videoOutput: leftVideo
        audioOutput: AudioOutput { muted: true }
        Component.onCompleted: play()
    }
    MediaPlayer {
        id: rightPlayer
        source: "../assets/panel_backgrounds/genesis-cockpit-banner-user-right.mp4"
        loops: MediaPlayer.Infinite
        videoOutput: rightVideo
        audioOutput: AudioOutput { muted: true }
        Component.onCompleted: play()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 8

        GoldPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(154, appRoot.height * 0.17)
            Layout.maximumHeight: Math.max(154, appRoot.height * 0.17)
            clip: true

            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: "#120d04" }
                    GradientStop { position: 0.5; color: "#020303" }
                    GradientStop { position: 1; color: "#120d04" }
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

                Rectangle { anchors.fill: parent; color: "#030403" }
                Image {
                    anchors.fill: parent
                    anchors.margins: 5
                    source: "../assets/panel_backgrounds/genesis-cockpit-logo.jpg"
                    sourceClipRect: Qt.rect(170, 825, 920, 285)
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                }
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 8
                    width: Math.min(parent.width - 40, 410)
                    height: 30
                    radius: 15
                    color: "#e6030403"
                    border.color: appRoot.line
                    Text {
                        anchors.centerIn: parent
                        text: appRoot.pageNames[appRoot.pageIndex]
                        color: appRoot.gold
                        font.pixelSize: 13
                        font.letterSpacing: 2
                    }
                }
            }

            VideoOutput {
                id: leftVideo
                z: 0
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: parent.width * 0.25
                fillMode: VideoOutput.PreserveAspectCrop
                visible: !appRoot.privacyMode
            }
            VideoOutput {
                id: rightVideo
                z: 0
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: parent.width * 0.25
                fillMode: VideoOutput.PreserveAspectCrop
                visible: !appRoot.privacyMode
            }

            Rectangle {
                z: 4
                anchors.fill: parent
                color: "#050706"
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
                        {label:"Create", page:0}, {label:"Poses", page:1},
                        {label:"Workflows", page:2}, {label:"Media", page:3},
                        {label:"Photos", page:4}, {label:"Cameras", page:5},
                        {label:"Entertainment", page:6}, {label:"System", page:7}
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
                    spacing: 9
                    Item {
                        width: 124; height: 108
                        anchors.horizontalCenter: parent.horizontalCenter
                        Image {
                            id: sidebarLogoSource
                            anchors.fill: parent
                            source: "../assets/panel_backgrounds/genesis-cockpit-logo.jpg"
                            fillMode: Image.PreserveAspectCrop
                            visible: false
                        }
                        Rectangle {
                            id: sidebarLogoMask
                            anchors.fill: parent
                            radius: 8
                            color: "white"
                            visible: false
                            layer.enabled: true
                        }
                        MultiEffect {
                            anchors.fill: parent
                            source: sidebarLogoSource
                            maskEnabled: true
                            maskSource: sidebarLogoMask
                            maskThresholdMin: 0.5
                            maskSpreadAtMin: 1.0
                        }
                        Rectangle {
                            z: 2
                            anchors.fill: parent
                            color: "transparent"
                            border.color: appRoot.brightGold
                            border.width: 2
                            radius: 8
                        }
                    }
                    Repeater {
                        model: [
                            {label:"▣  Image Gen", page:0}, {label:"♟  Pose Library", page:1},
                            {label:"◇  Workflows", page:2}, {label:"✂  Media Tools", page:3},
                            {label:"▧  Photo Library", page:4}, {label:"●  Cam Hub", page:5},
                            {label:"▷  Entertainment", page:6}, {label:"⚙  System", page:7}
                        ]
                        GoldButton {
                            width: 140
                            height: 46
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
                    height: Math.min(185, parent.height * 0.22)
                    color: "#090b0a"
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
                        Text { text: "COLUMN PHOTO"; color: appRoot.textDim; font.pixelSize: 11; font.letterSpacing: 1 }
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
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 6
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 52
                            Layout.maximumHeight: 52
                            Text { text: "♟"; color: appRoot.gold; font.pixelSize: 32 }
                            Column {
                                Text { text: "Image Generation"; color: appRoot.brightGold; font.pixelSize: 24; font.bold: true }
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
                            Layout.preferredHeight: 44
                            Layout.maximumHeight: 44
                            Repeater {
                                model: ["Create", "Pose Library", "Workflow", "Advanced", "ControlNet", "Inpaint / Edit", "Batch", "Settings"]
                                GoldButton {
                                    text: modelData
                                    active: index === 0
                                    Layout.fillWidth: true
                                    onClicked: {
                                        if (index === 1)
                                            appRoot.pageIndex = 1
                                        else if (index === 2)
                                            appRoot.pageIndex = 2
                                        else if (index === 5)
                                            appRoot.pageIndex = 8
                                    }
                                }
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
                                    Layout.preferredHeight: 106
                                    Layout.maximumHeight: 106
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
                                    Layout.fillWidth: true; Layout.preferredHeight: 112
                                    Layout.maximumHeight: 112
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
                                                appRoot.selectedGenerationIndex = currentIndex
                                                appRoot.selectedLoraOne = "None"
                                                appRoot.selectedLoraTwo = "None"
                                                loraOnePicker.currentIndex = 0
                                                loraTwoPicker.currentIndex = 0
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
                                    Text { x: 220; y: 84; width: parent.width - 232; text: appRoot.selectedGenerationProfile.note + "  ·  Triggers: " + appRoot.activeLoraTriggers; color: appRoot.textDim; font.pixelSize: 11; elide: Text.ElideRight }
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
                                            Rectangle { x: 10; y: 40; width: 105; height: parent.height - 82; color: "#181b18"; border.color: appRoot.line
                                                Text { anchors.centerIn: parent; text: "PREVIEW"; color: appRoot.textDim }
                                            }
                                            Text { x: 126; y: 42; width: parent.width - 138; text: modelData.model + "\n\n" + modelData.detail; color: appRoot.textMain; font.pixelSize: 13; lineHeight: 1.4 }
                                            Text { x: 12; anchors.bottom: parent.bottom; anchors.bottomMargin: 10; text: "☑  Use previous stage output"; color: appRoot.textMain; font.pixelSize: 13 }
                                        }
                                    }
                                }
                                GoldPanel {
                                    Layout.fillWidth: true; Layout.preferredHeight: 88
                                    Layout.maximumHeight: 88
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
                                        enabled: !genesisBridge.busy && appRoot.selectedPosePrompt.trim().length > 0 && appRoot.selectedGenerationProfile.runnable
                                        onClicked: genesisBridge.queueGenerate(
                                            appRoot.selectedPosePrompt,
                                            appRoot.selectedPoseNegativePrompt,
                                            appRoot.generationWidth,
                                            appRoot.generationHeight,
                                            appRoot.selectedGenerationProfile.model,
                                            appRoot.selectedLoraOne,
                                            appRoot.selectedLoraTwo
                                        )
                                    }
                                }
                            }
                            GoldPanel {
                                Layout.preferredWidth: 370
                                Layout.fillHeight: true
                                SmallLabel { x: 12; y: 10; text: "Preview" }
                                Rectangle { x: 10; y: 38; width: parent.width - 20; height: parent.height * 0.48; color: "#171a18"; border.color: appRoot.line
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
                                        Rectangle { anchors.fill: parent; anchors.margins: 5; color: index % 2 ? "#181b18" : "#20231f"
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
                                        color: "#191c19"; border.color: appRoot.line
                                        Image { anchors.fill: parent; anchors.margins: 4; source: appRoot.selectedPoseSource; fillMode: Image.PreserveAspectFit; asynchronous: true }
                                        Text { anchors.centerIn: parent; text: "SELECTED POSE PREVIEW"; color: appRoot.textDim; visible: appRoot.selectedPoseSource.toString().length === 0 }
                                    }
                                    SmallLabel { text: "Pose Information" }
                                    Text {
                                        Layout.fillWidth: true
                                        text: "Category:  " + appRoot.selectedPoseCategory + "\nPose ID:  " + appRoot.selectedPoseId + "\nPrompt source:  " + appRoot.selectedPosePromptSource + "\n485 mapped poses · model-safe LoRA filtering"
                                        color: appRoot.textMain
                                        font.pixelSize: 11
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
                                Text { text: "Inpaint / Edit"; color: appRoot.brightGold; font.pixelSize: 27; font.bold: true }
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
                                        color: "#151916"; border.color: appRoot.line; radius: 5
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
                                    SmallLabel { text: "2. Mask / Reference (not connected)" }
                                    Rectangle {
                                        Layout.fillWidth: true; Layout.fillHeight: true
                                        color: "#151916"; border.color: appRoot.line; radius: 5
                                        Image { anchors.fill: parent; anchors.margins: 5; source: appRoot.editMask; fillMode: Image.PreserveAspectFit }
                                        Text { anchors.centerIn: parent; text: "DROP MASK OR REFERENCE"; color: appRoot.textDim; visible: appRoot.editMask.toString().length === 0 }
                                        DropArea { anchors.fill: parent; enabled: false }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        GoldButton { Layout.fillWidth: true; text: "Paint Mask"; enabled: false }
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
                                        background: Rectangle { color: "#111513"; border.color: appRoot.line; radius: 4 }
                                    }
                                    SmallLabel { text: "Fast edit engine" }
                                    FieldBox {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 42
                                        Text { anchors.centerIn: parent; text: "FluxUp Q4 · RX 9060 XT · Fast 8-step edit"; color: appRoot.textMain; font.pixelSize: 13 }
                                    }
                                    SmallLabel { text: "Edit strength  " + appRoot.editStrength.toFixed(2) }
                                    Slider { Layout.fillWidth: true; from: 0.05; to: 0.95; stepSize: 0.05; value: appRoot.editStrength; onMoved: appRoot.editStrength = value }
                                    Text { Layout.fillWidth: true; text: "Lower values preserve identity and composition. Higher values allow broader changes."; color: appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 105
                                        color: "#151916"
                                        border.color: appRoot.line
                                        radius: 4
                                        Image { anchors.fill: parent; anchors.margins: 4; source: genesisBridge.previewUrl; fillMode: Image.PreserveAspectFit }
                                        Text { anchors.centerIn: parent; text: "EDIT PREVIEW"; color: appRoot.textDim; visible: genesisBridge.previewUrl.length === 0 }
                                    }
                                    Text { Layout.fillWidth: true; text: genesisBridge.status; color: genesisBridge.busy ? appRoot.gold : appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap }
                                    Item { Layout.fillHeight: true }
                                    GoldButton {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 54
                                        text: genesisBridge.busy ? "Working…" : "▶  Queue Image Edit"
                                        enabled: !genesisBridge.busy && genesisBridge.editAvailable && appRoot.editSource.toString().length > 0 && appRoot.editPrompt.trim().length > 0
                                        onClicked: genesisBridge.queueEdit(
                                            appRoot.editSource.toString(),
                                            appRoot.editPrompt,
                                            appRoot.editStrength
                                        )
                                    }
                                }
                            }
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
                Text { text: runtimeStatus.comfyOnline ? "ComfyUI:  ● Online" : "ComfyUI:  ○ Offline"; color: runtimeStatus.comfyOnline ? "#66dd78" : "#e5b94f"; font.pixelSize: 12 }
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
