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
    color: "#030504"

    readonly property color gold: "#e5b94f"
    readonly property color brightGold: "#ffd978"
    readonly property color panel: "#090c0b"
    readonly property color panelSoft: "#101412"
    readonly property color line: "#020201"
    readonly property color textMain: "#f4e8c8"
    readonly property color textDim: "#aaa99f"
    FontLoader { id: genesisDisplayFont; source: "../assets/fonts/Exo2-Black.ttf" }
    property bool privacyMode: false
    property int pageIndex: 0
    readonly property var pageNames: ["IMAGE GENERATION", "POSE LIBRARY", "WORKFLOW EDITOR", "MEDIA TOOLS", "PHOTO LIBRARY", "CAM HUB", "ENTERTAINMENT", "SYSTEM"]
    // Editable in Qt Design Studio. Leave blank to show a framed placeholder.
    property url photoOneSource: ""
    property url photoTwoSource: ""
    property url photoThreeSource: ""
    property url photoFourSource: ""
    property url sideColumnImageSource: ""
    readonly property var photoBannerSources: [photoOneSource, photoTwoSource, photoThreeSource, photoFourSource]
    property int bannerMode: 0 // 0 = two live MP4s, 1 = four editable photos
    property var poseModel: typeof poseItems !== "undefined" ? poseItems : []
    property url selectedPoseSource: poseModel.length ? poseModel[0].source : ""
    property string selectedPoseName: poseModel.length ? poseModel[0].name : "Standing 001"
    property string selectedPoseCategory: poseModel.length ? poseModel[0].category : "Standing"
    property string selectedPoseId: poseModel.length ? poseModel[0].poseId : ""
    property string selectedPosePrompt: poseModel.length ? poseModel[0].prompt : ""
    property string selectedPoseNegativePrompt: poseModel.length ? poseModel[0].negativePrompt : ""
    property string selectedPosePromptSource: poseModel.length ? poseModel[0].promptSource : "AUTO_FALLBACK"
    property string selectedPoseTemplateId: poseModel.length ? poseModel[0].promptTemplateId : ""

    component GoldPanel: Rectangle {
        color: appRoot.panel
        border.color: "transparent"
        border.width: 1
        radius: 6
    }

    component GoldButton: Button {
        id: control
        implicitHeight: 40
        font.pixelSize: 14
        contentItem: Text {
            text: control.text
            color: control.down ? "#171006" : appRoot.textMain
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 5
            border.color: control.hovered ? appRoot.brightGold : appRoot.line
            gradient: Gradient {
                GradientStop { position: 0; color: control.down ? "#efc45b" : "#221b0d" }
                GradientStop { position: 1; color: control.down ? "#a97b22" : "#0b0d0c" }
            }
        }
    }

    component FieldBox: Rectangle {
        color: "#111513"
        border.color: "#30332d"
        radius: 4
    }

    component SmallLabel: Text {
        color: appRoot.gold
        font.pixelSize: 13
        font.bold: true
    }

    component ModulePage: Item {
        property string pageTitle
        property string pageSubtitle
        property string pageIcon: "◆"
        property string sectionTitle: "Workspace"
        property var cards: []
        property var quickActions: []

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
                    GoldButton { text: modelData; Layout.preferredWidth: 128 }
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
                        Text { anchors.left: parent.left; anchors.leftMargin: 14; anchors.verticalCenter: parent.verticalCenter; text: "⌕  Search and filter…"; color: appRoot.textDim; font.pixelSize: 13 }
                    }
                    GoldButton { text: "Refresh"; Layout.preferredWidth: 100 }
                    GoldButton { text: "View Options"; Layout.preferredWidth: 120 }
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
                                GoldButton { Layout.fillWidth: true; text: modelData.action }
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
                            Text { anchors.centerIn: parent; text: "SYSTEM READY"; color: "#59d66f"; font.pixelSize: 18; font.bold: true }
                        }
                        SmallLabel { text: "Recent Activity" }
                        Repeater {
                            model: ["No active operation", "Queue is ready", "Local processing enabled", "Privacy controls available"]
                            Text { Layout.fillWidth: true; text: "●  " + modelData; color: appRoot.textMain; font.pixelSize: 12; wrapMode: Text.Wrap }
                        }
                        Rectangle { Layout.fillWidth: true; height: 1; color: appRoot.line }
                        SmallLabel { text: "Quick Access" }
                        GoldButton { Layout.fillWidth: true; text: "Open Output Folder" }
                        GoldButton { Layout.fillWidth: true; text: "GENESIS AI Assistant" }
                        Item { Layout.fillHeight: true }
                        Text { Layout.fillWidth: true; text: "Backend actions will connect to the preserved GENESIS services."; color: appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap }
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
        anchors.margins: 8
        spacing: 6

        GoldPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(170, appRoot.height * 0.19)
            Layout.maximumHeight: Math.max(170, appRoot.height * 0.19)
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

            Image {
                z: 0
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.leftMargin: parent.width * 0.25
                anchors.rightMargin: parent.width * 0.25
                source: "../assets/panel_backgrounds/pose-library-banner-reference.png"
                sourceClipRect: Qt.rect(274, 0, 990, 185)
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
                visible: appRoot.bannerMode === 0 && !appRoot.privacyMode
            }

            Row {
                z: 0
                anchors.fill: parent
                visible: appRoot.bannerMode === 1 && !appRoot.privacyMode
                Repeater {
                    model: 4
                    Rectangle {
                        width: parent.width / 4
                        height: parent.height
                        color: index % 2 ? "#0d100f" : "#080a09"
                        border.color: appRoot.line
                        clip: true
                        Image {
                            anchors.fill: parent
                            anchors.margins: 3
                            source: appRoot.photoBannerSources[index]
                            fillMode: Image.PreserveAspectCrop
                            asynchronous: true
                            visible: source.toString().length > 0
                        }
                        Column {
                            anchors.centerIn: parent
                            spacing: 4
                            visible: appRoot.photoBannerSources[index].toString().length === 0
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "+"; color: appRoot.gold; font.pixelSize: 28 }
                            Text { text: "PHOTO SLOT " + (index + 1); color: appRoot.textDim; font.pixelSize: 12; font.letterSpacing: 1 }
                        }
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
                visible: appRoot.bannerMode === 0 && !appRoot.privacyMode
            }
            VideoOutput {
                id: rightVideo
                z: 0
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: parent.width * 0.25
                fillMode: VideoOutput.PreserveAspectCrop
                visible: appRoot.bannerMode === 0 && !appRoot.privacyMode
            }
            Rectangle {
                anchors.fill: leftVideo
                color: "#050706"
                border.color: appRoot.gold
                radius: 6
                visible: appRoot.bannerMode === 0 && appRoot.privacyMode
                Text { anchors.centerIn: parent; text: "PRIVATE"; color: appRoot.gold; font.pixelSize: 18 }
            }
            Rectangle {
                anchors.fill: rightVideo
                color: "#050706"
                border.color: appRoot.gold
                radius: 6
                visible: appRoot.bannerMode === 0 && appRoot.privacyMode
                Text { anchors.centerIn: parent; text: "PRIVATE"; color: appRoot.gold; font.pixelSize: 18 }
            }

            Rectangle {
                z: 2
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.top: parent.top
                anchors.topMargin: 8
                width: 455
                height: 145
                radius: 0
                color: "transparent"
                border.color: appRoot.line
                Item {
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: 5
                    width: 390
                    height: 76
                    Image {
                        id: bannerGenesisSource
                        anchors.fill: parent
                        source: "../assets/panel_backgrounds/genesis-cockpit-logo.jpg"
                        sourceClipRect: Qt.rect(170, 850, 920, 155)
                        fillMode: Image.PreserveAspectFit
                        visible: false
                    }
                    MultiEffect {
                        anchors.fill: parent
                        source: bannerGenesisSource
                        colorization: 0.82
                        colorizationColor: appRoot.brightGold
                    }
                }
                Image {
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: 76
                    width: 205
                    height: 30
                    source: "../assets/panel_backgrounds/genesis-cockpit-logo.jpg"
                    sourceClipRect: Qt.rect(320, 1000, 620, 85)
                    fillMode: Image.PreserveAspectFit
                }
                Rectangle { anchors.horizontalCenter: parent.horizontalCenter; y: 104; width: 300; height: 1; color: appRoot.line }
                Text { anchors.horizontalCenter: parent.horizontalCenter; y: 112; text: appRoot.pageNames[appRoot.pageIndex]; color: appRoot.gold; font.family: genesisDisplayFont.name; font.pixelSize: 13; font.letterSpacing: 3 }
            }
            Rectangle {
                z: 4
                anchors.fill: parent
                color: "#050706"
                border.color: appRoot.gold
                visible: appRoot.privacyMode
                Text { anchors.centerIn: parent; text: "PRIVATE"; color: appRoot.gold; font.pixelSize: 18; font.letterSpacing: 4 }
            }
            GoldButton {
                z: 5
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.rightMargin: 10
                anchors.bottomMargin: 8
                width: 154
                height: 30
                text: appRoot.bannerMode === 0 ? "4-PHOTO BANNER" : "VIDEO BANNER"
                font.pixelSize: 10
                onClicked: appRoot.bannerMode = appRoot.bannerMode === 0 ? 1 : 0
            }
        }

        GoldPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 54
            Layout.maximumHeight: 54
            RowLayout {
                anchors.fill: parent
                anchors.margins: 6
                spacing: 6
                Repeater {
                    model: [
                        {label:"Image Gen", page:0},
                        {label:"Media Tools", page:3}, {label:"Photo Library", page:4},
                        {label:"Cam Hub", page:5}, {label:"Entertainment", page:6},
                        {label:"System", page:7}
                    ]
                    GoldButton {
                        text: modelData.label
                        Layout.preferredWidth: index === 1 ? 145 : 130
                        onClicked: appRoot.pageIndex = modelData.page
                    }
                }
                Item { Layout.fillWidth: true }
                GoldButton { text: "✥  GENESIS AI  ›"; Layout.preferredWidth: 160 }
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
            spacing: 6

            GoldPanel {
                Layout.preferredWidth: 132
                Layout.fillHeight: true
                Column {
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 8
                    Item {
                        width: 108; height: 108
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
                            {label:"▣  Image Gen", page:0}, {label:"▣  Video Gen", page:3},
                            {label:"Ps  Photoshop", page:3}, {label:"✂  Media Tools", page:3},
                            {label:"▧  Photo Library", page:4}, {label:"●  Cam Hub", page:5},
                            {label:"▷  Entertainment", page:6}, {label:"⚙  System", page:7}
                        ]
                        GoldButton { width: 116; height: 44; text: modelData.label; onClicked: appRoot.pageIndex = modelData.page }
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
                            Text { text: "♟"; color: appRoot.gold; font.pixelSize: 34 }
                            Column {
                                Text { text: "Image Generation"; color: appRoot.brightGold; font.pixelSize: 25; font.bold: true }
                                Text { text: "Turn your ideas into reality."; color: appRoot.textDim; font.pixelSize: 14 }
                            }
                            Item { Layout.fillWidth: true }
                            GoldButton { text: "Load Preset"; Layout.preferredWidth: 120 }
                            GoldButton { text: "Save Preset"; Layout.preferredWidth: 120 }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 40
                            Layout.maximumHeight: 40
                            Repeater {
                                model: ["Create", "Pose Library", "Workflow", "Advanced", "ControlNet", "Inpaint / Edit", "Batch", "Settings"]
                                GoldButton {
                                    text: modelData
                                    Layout.fillWidth: true
                                    onClicked: { if (index === 1) appRoot.pageIndex = 1; else if (index === 2) appRoot.pageIndex = 2 }
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
                                        TextArea { x: 8; y: 28; width: parent.width - 16; height: parent.height - 34; wrapMode: TextEdit.Wrap; color: appRoot.textMain; font.pixelSize: 13; background: Rectangle { color: "transparent" } text: appRoot.selectedPosePrompt; placeholderText: "Select a pose or enter a prompt"; onTextChanged: if (activeFocus) appRoot.selectedPosePrompt = text }
                                    }
                                    GoldPanel {
                                        Layout.fillWidth: true; Layout.fillHeight: true
                                        SmallLabel { x: 10; y: 8; text: "Negative Prompt" }
                                        TextArea { x: 8; y: 28; width: parent.width - 16; height: parent.height - 34; wrapMode: TextEdit.Wrap; color: appRoot.textDim; font.pixelSize: 13; background: Rectangle { color: "transparent" } text: appRoot.selectedPoseNegativePrompt; placeholderText: "Model-aware negative prompt"; onTextChanged: if (activeFocus) appRoot.selectedPoseNegativePrompt = text }
                                    }
                                }
                                GoldPanel {
                                    Layout.fillWidth: true; Layout.preferredHeight: 112
                                    Layout.maximumHeight: 112
                                    SmallLabel { x: 12; y: 10; text: "Reference / Pose" }
                                    GoldButton { x: 12; y: 38; width: 185; text: "Select from Pose Library"; onClicked: appRoot.pageIndex = 1 }
                                    SmallLabel { x: 220; y: 10; text: "Model & LoRA Selection (Auto-filtered)" }
                                    Row { x: 220; y: 40; spacing: 10
                                        Repeater { model: ["AUTO / Recommended", "LoRA 1: Compatible only", "LoRA 2: Compatible only"]
                                            FieldBox { width: 185; height: 42; Text { anchors.centerIn: parent; text: modelData + " ⌄"; color: appRoot.textMain; font.pixelSize: 12 } }
                                        }
                                    }
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
                                            Text { x: 126; y: 42; width: parent.width - 138; text: modelData.model + "\n\n" + modelData.detail; color: appRoot.textMain; font.pixelSize: 12; lineHeight: 1.45 }
                                            Text { x: 12; anchors.bottom: parent.bottom; anchors.bottomMargin: 10; text: "☑  Use previous stage output"; color: appRoot.textMain; font.pixelSize: 12 }
                                        }
                                    }
                                }
                                GoldPanel {
                                    Layout.fillWidth: true; Layout.preferredHeight: 88
                                    Layout.maximumHeight: 88
                                    SmallLabel { x: 12; y: 8; text: "Output Settings" }
                                    Row { x: 12; y: 36; spacing: 8
                                        Repeater { model: ["Width  768", "Height  1152", "Batch  1", "Format  PNG", "Save to  GENESIS/Output"]
                                            FieldBox { width: index === 4 ? 210 : 112; height: 38; Text { anchors.centerIn: parent; text: modelData; color: appRoot.textMain; font.pixelSize: 12 } }
                                        }
                                    }
                                    GoldButton { anchors.right: parent.right; anchors.rightMargin: 10; y: 28; width: 190; height: 50; text: "▶  Generate" }
                                }
                            }
                            GoldPanel {
                                Layout.preferredWidth: 355
                                Layout.fillHeight: true
                                SmallLabel { x: 12; y: 10; text: "Preview" }
                                Rectangle { x: 10; y: 38; width: parent.width - 20; height: parent.height * 0.48; color: "#171a18"; border.color: appRoot.line
                                    Text { anchors.centerIn: parent; text: "GENERATED IMAGE PREVIEW"; color: appRoot.textDim }
                                }
                                Row { x: 10; y: parent.height * 0.52; spacing: 5
                                    Repeater { model: ["Open", "Save", "Send To"]
                                        GoldButton { width: 106; text: modelData }
                                    }
                                }
                                SmallLabel { x: 12; y: parent.height * 0.62; text: "Generation Info" }
                                Text { x: 12; y: parent.height * 0.67; text: "Model: Dynamic inventory\nSize: 768 × 1152\nStages: 1 / 2 / 3\nStatus: Ready"; color: appRoot.textMain; font.pixelSize: 13; lineHeight: 1.5 }
                            }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 8
                        RowLayout {
                            Layout.fillWidth: true; Layout.preferredHeight: 55
                            Layout.maximumHeight: 55
                            Text { text: "♟"; color: appRoot.gold; font.pixelSize: 36 }
                            Column { Text { text: "POSE LIBRARY"; color: appRoot.brightGold; font.family: genesisDisplayFont.name; font.pixelSize: 29; font.bold: true; font.letterSpacing: 1 }
                                Text { text: "Find the perfect pose for your vision."; color: appRoot.textDim; font.pixelSize: 14 }
                            }
                            Item { Layout.fillWidth: true }
                            GoldButton { text: "▦  Grid"; Layout.preferredWidth: 90 }
                        }
                        RowLayout {
                            Layout.fillWidth: true; Layout.preferredHeight: 42
                            Layout.maximumHeight: 42
                            Repeater { model: ["⌕  Search poses…", "Category  All ⌄", "Resolution  All ⌄", "Prompt  Mapped/All ⌄", "Model  AUTO ⌄", "Sort  Name ⌄"]
                                FieldBox { Layout.fillWidth: true; Layout.fillHeight: true; Text { anchors.centerIn: parent; text: modelData; color: appRoot.textMain; font.pixelSize: 12 } }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 8
                            GoldPanel {
                                Layout.preferredWidth: 195; Layout.fillHeight: true
                                SmallLabel { x: 12; y: 12; text: "Categories" }
                                Column { x: 10; y: 42; spacing: 5
                                    Repeater { model: ["All Poses          486", "Standing             172", "Sitting                  76", "Suspended           42", "Lying                    79", "Squatting            36", "Kneeling             33", "Split Leg              30", "All Fours             13", "Metal Stocks          5"]
                                        GoldButton { width: 175; height: 34; text: modelData }
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
                                            Text { anchors.centerIn: parent; text: modelData.name; color: "white"; font.pixelSize: 12 }
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
                                Layout.preferredWidth: 340; Layout.fillHeight: true
                                SmallLabel { x: 12; y: 10; text: appRoot.selectedPoseName }
                                Rectangle { x: 10; y: 38; width: parent.width - 20; height: parent.height * 0.38; color: "#191c19"; border.color: appRoot.line
                                    Image { anchors.fill: parent; anchors.margins: 4; source: appRoot.selectedPoseSource; fillMode: Image.PreserveAspectFit; asynchronous: true }
                                    Text { anchors.centerIn: parent; text: "SELECTED POSE PREVIEW"; color: appRoot.textDim; visible: appRoot.selectedPoseSource.toString().length === 0 }
                                }
                                SmallLabel { x: 12; y: parent.height * 0.43; text: "Pose Information" }
                                Text { x: 12; y: parent.height * 0.48; width: parent.width - 24; text: "Category:        " + appRoot.selectedPoseCategory + "\nPose ID:            " + appRoot.selectedPoseId + "\nPrompt source:  " + appRoot.selectedPosePromptSource + "\n\nModel routing\n● AUTO / Recommended\n● Phr00t / Qwen reference baseline\n● Klein 9B quality profile\n● Klein 4B quick profile\n\nLoRAs are filtered by model family."; color: appRoot.textMain; font.pixelSize: 11; lineHeight: 1.2; wrapMode: Text.Wrap }
                                Row { anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.margins: 10; spacing: 8
                                    GoldButton { width: 150; text: "♟  Use Pose"; onClicked: appRoot.pageIndex = 0 }
                                }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true; Layout.preferredHeight: 42
                            Layout.maximumHeight: 42
                            Item { Layout.fillWidth: true }
                            GoldButton { text: "‹"; Layout.preferredWidth: 42 }
                            GoldButton { text: "1"; Layout.preferredWidth: 42 }
                            GoldButton { text: "2"; Layout.preferredWidth: 42 }
                            GoldButton { text: "3"; Layout.preferredWidth: 42 }
                            GoldButton { text: "›"; Layout.preferredWidth: 42 }
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
            }
        }

        GoldPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 46
            Layout.maximumHeight: 46
            RowLayout {
                anchors.fill: parent; anchors.margins: 10; spacing: 18
                Text { text: Qt.formatDateTime(new Date(), "ddd, d MMM yyyy   hh:mm"); color: appRoot.textMain; font.pixelSize: 12 }
                Text { text: "ComfyUI:  ● Online"; color: "#66dd78"; font.pixelSize: 12 }
                Text { text: "GPU: RX 9060 XT (16 GB)"; color: appRoot.textMain; font.pixelSize: 12 }
                Text { text: "VRAM: 3.2 / 16 GB"; color: appRoot.textMain; font.pixelSize: 12 }
                Item { Layout.fillWidth: true }
                Text { text: "GENESIS v1.0.0"; color: appRoot.gold; font.pixelSize: 12 }
                Text { text: "Keep walking Allan…"; color: appRoot.brightGold; font.pixelSize: 16; font.italic: true }
                Text { text: "⚙"; color: appRoot.textMain; font.pixelSize: 23 }
            }
        }
    }
}
