import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: appRoot
    visible: true
    width: 1536
    height: 960
    minimumWidth: 1100
    minimumHeight: 700
    title: "GENESIS c0ckpit"
    color: "#070b10"
    font.family: "Noto Sans"

    readonly property color gold: "#d2a34e"
    readonly property color brightGold: "#f3d28b"
    readonly property color ice: "#7fc4d8"
    readonly property color bg: "#070b10"
    readonly property color panel: "#0d141d"
    readonly property color raised: "#121c27"
    readonly property color raised2: "#172432"
    readonly property color line: "#2d4354"
    readonly property color textMain: "#eef3f6"
    readonly property color textDim: "#91a2b2"
    readonly property color success: "#62d27a"

    property int pageIndex: 0
    property bool privacyMode: false
    property var navItems: [
        {icon:"⌂", label:"Home", page:0},
        {icon:"▣", label:"Image Generation", page:1},
        {icon:"♟", label:"Pose Library", page:2},
        {icon:"◇", label:"Workflow Studio", page:3},
        {icon:"✦", label:"Media Tools", page:4},
        {icon:"▧", label:"Photo Library", page:5},
        {icon:"●", label:"Camera Hub", page:6},
        {icon:"▷", label:"Entertainment", page:7},
        {icon:"⚙", label:"System Tools", page:8},
        {icon:"Ps", label:"Canvas / Edit", page:9},
        {icon:"♜", label:"Pose Maker", page:10},
        {icon:"☷", label:"Settings", page:11}
    ]

    property var generationModel: typeof generationProfiles !== "undefined" ? generationProfiles : []
    property int selectedGenerationIndex: 0
    readonly property var selectedGenerationProfile: generationModel.length
        ? generationModel[selectedGenerationIndex]
        : ({label:"No local model", model:"", note:"No validated local model", loras:["None"], runnable:false, sourceRequired:false})
    property string selectedLora: "None"
    property url generationSource: ""
    property string generationPrompt: ""
    property int generationWidth: 768
    property int generationHeight: 1152
    property bool useStageTwo: false
    property bool useStageThree: false
    property bool useUpscale: false

    property var poseModel: typeof poseItems !== "undefined" ? poseItems : []
    property url selectedPoseSource: poseModel.length ? poseModel[0].source : ""
    property string selectedPoseName: poseModel.length ? poseModel[0].name : "No pose selected"
    property string selectedPoseCategory: poseModel.length ? poseModel[0].category : ""
    property string selectedPosePrompt: poseModel.length ? poseModel[0].prompt : ""

    property string activeMediaTool: "Enhance"
    property string activeLibraryMode: "Media Viewer"
    property url editSource: ""
    property url editMask: ""
    property string editPrompt: ""
    property real editStrength: 0.40

    function chooseSource() {
        var chosen = genesisBridge.chooseSourceImage()
        if (chosen.length) generationSource = chosen
    }

    function chooseEditSource() {
        var chosen = genesisBridge.chooseSourceImage()
        if (chosen.length) editSource = chosen
    }

    function selectGeneration(index) {
        selectedGenerationIndex = index
        selectedLora = "None"
    }

    function generateCurrent() {
        var prompt = generationPrompt.trim().length ? generationPrompt : selectedPosePrompt
        genesisBridge.queueGenerate(
            prompt,
            "",
            generationWidth,
            generationHeight,
            selectedGenerationProfile.model,
            selectedLora,
            "None",
            generationSource.toString(),
            selectedPoseSource.toString(),
            useStageTwo,
            useStageThree,
            useUpscale
        )
    }

    component Panel: Rectangle {
        color: appRoot.panel
        radius: 12
        border.color: appRoot.line
        border.width: 1
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: "#152230" }
            GradientStop { position: 0.11; color: "#101923" }
            GradientStop { position: 1.0; color: "#0a1017" }
        }
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            height: 1
            color: "#55f3d28b"
        }
    }

    component GButton: Button {
        id: button
        property bool active: false
        implicitHeight: 42
        font.pixelSize: 13
        font.weight: active ? Font.DemiBold : Font.Medium
        contentItem: Text {
            text: button.text
            color: !button.enabled ? "#64717c" : (button.active ? "#081017" : (button.hovered ? appRoot.brightGold : appRoot.textMain))
            font: button.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 9
            color: !button.enabled ? "#10161d" : (button.active ? appRoot.gold : (button.down ? "#182735" : (button.hovered ? "#162432" : "#101923")))
            border.color: button.active ? appRoot.brightGold : (button.hovered ? appRoot.ice : appRoot.line)
            border.width: button.active || button.hovered ? 1.5 : 1
        }
    }

    component NavButton: Button {
        id: nav
        property bool active: false
        implicitHeight: 44
        leftPadding: 12
        contentItem: Text {
            text: nav.text
            color: nav.active ? appRoot.brightGold : (nav.hovered ? appRoot.textMain : appRoot.textDim)
            font.pixelSize: 13
            font.weight: nav.active ? Font.DemiBold : Font.Normal
            horizontalAlignment: Text.AlignLeft
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 8
            color: nav.active ? "#182635" : (nav.hovered ? "#111d28" : "transparent")
            border.color: nav.active ? appRoot.gold : "transparent"
            border.width: 1
            Rectangle {
                visible: nav.active
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: 3
                color: appRoot.gold
                radius: 2
            }
        }
    }

    component SectionLabel: Text {
        color: appRoot.brightGold
        font.pixelSize: 11
        font.bold: true
        font.letterSpacing: 1.1
    }

    component PageHeader: RowLayout {
        property string titleText: ""
        property string subtitleText: ""
        property string iconText: "◆"
        Layout.fillWidth: true
        Layout.preferredHeight: 62
        spacing: 12
        Text { text: parent.iconText; color: appRoot.gold; font.pixelSize: 30 }
        ColumnLayout {
            spacing: 0
            Text { text: parent.titleText; color: appRoot.brightGold; font.pixelSize: 27; font.bold: true; font.letterSpacing: 0.3 }
            Text { text: parent.subtitleText; color: appRoot.textDim; font.pixelSize: 13 }
        }
        Item { Layout.fillWidth: true }
    }

    Rectangle {
        anchors.fill: parent
        z: -10
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0; color: "#0f1a25" }
            GradientStop { position: 0.40; color: appRoot.bg }
            GradientStop { position: 1; color: "#04070b" }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        Panel {
            Layout.fillWidth: true
            Layout.preferredHeight: 74
            RowLayout {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12
                Rectangle {
                    Layout.preferredWidth: 46
                    Layout.preferredHeight: 46
                    radius: 12
                    color: appRoot.gold
                    Text { anchors.centerIn: parent; text: "G"; color: "#071018"; font.pixelSize: 28; font.bold: true }
                }
                ColumnLayout {
                    spacing: 0
                    Text { text: "GENESIS c0ckpit"; color: appRoot.brightGold; font.pixelSize: 22; font.bold: true; font.letterSpacing: 0.5 }
                    Text { text: "Keep walking Allan.  ·  Local creative workspace"; color: appRoot.textDim; font.pixelSize: 11 }
                }
                Item { Layout.fillWidth: true }
                Rectangle {
                    Layout.preferredWidth: 190
                    Layout.preferredHeight: 34
                    radius: 17
                    color: "#111c25"
                    border.color: runtimeStatus.comfyOnline ? appRoot.success : appRoot.gold
                    Text {
                        anchors.centerIn: parent
                        text: runtimeStatus.comfyOnline ? "●  COMFYUI ONLINE" : "○  COMFYUI OFFLINE"
                        color: runtimeStatus.comfyOnline ? appRoot.success : appRoot.gold
                        font.pixelSize: 11
                        font.bold: true
                    }
                }
                GButton { text: privacyMode ? "Privacy On" : "Privacy Mode"; active: privacyMode; Layout.preferredWidth: 130; onClicked: privacyMode = !privacyMode }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10

            Panel {
                Layout.preferredWidth: 202
                Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 5
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 86
                        radius: 9
                        color: "#0a0f15"
                        border.color: appRoot.line
                        Image {
                            anchors.fill: parent
                            anchors.margins: 8
                            source: "../assets/genesis-cockpit-icon-balanced-final.png"
                            fillMode: Image.PreserveAspectFit
                            visible: !privacyMode
                        }
                        Text { anchors.centerIn: parent; text: "PRIVATE"; color: appRoot.gold; font.letterSpacing: 2; visible: privacyMode }
                    }
                    Repeater {
                        model: appRoot.navItems
                        NavButton {
                            Layout.fillWidth: true
                            text: modelData.icon + "   " + modelData.label
                            active: appRoot.pageIndex === modelData.page
                            onClicked: appRoot.pageIndex = modelData.page
                        }
                    }
                    Item { Layout.fillHeight: true }
                    Text { Layout.fillWidth: true; text: "LOCAL · PRIVATE · WINDOWS"; color: appRoot.textDim; font.pixelSize: 9; horizontalAlignment: Text.AlignHCenter; font.letterSpacing: 0.8 }
                }
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: appRoot.pageIndex

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 10
                        PageHeader { titleText: "Home"; subtitleText: "Your local creative suite — task first, technical depth when you need it."; iconText: "⌂" }
                        Panel {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 180
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 18
                                spacing: 18
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Text { text: "CREATE. ORGANISE. FINISH."; color: appRoot.brightGold; font.pixelSize: 30; font.bold: true; font.letterSpacing: 1.2 }
                                    Text { Layout.fillWidth: true; text: "Images, poses, media, cameras and local AI in one private desktop workspace. Your content stays central; advanced model and workflow controls stay available without getting in the way."; color: appRoot.textMain; font.pixelSize: 14; wrapMode: Text.Wrap }
                                    RowLayout {
                                        GButton { text: "Start Creating"; active: true; Layout.preferredWidth: 150; onClicked: appRoot.pageIndex = 1 }
                                        GButton { text: "Browse Poses"; Layout.preferredWidth: 140; onClicked: appRoot.pageIndex = 2 }
                                        GButton { text: "Media Tools"; Layout.preferredWidth: 130; onClicked: appRoot.pageIndex = 4 }
                                    }
                                }
                                Rectangle {
                                    Layout.preferredWidth: 330
                                    Layout.fillHeight: true
                                    radius: 10
                                    color: "#091019"
                                    border.color: appRoot.line
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 14
                                        SectionLabel { text: "SYSTEM STATUS" }
                                        Text { text: runtimeStatus.comfyOnline ? "Ready to generate" : "ComfyUI needs attention"; color: runtimeStatus.comfyOnline ? appRoot.success : appRoot.gold; font.pixelSize: 18; font.bold: true }
                                        Text { text: "GPU  " + runtimeStatus.gpuName; color: appRoot.textMain; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true }
                                        Text { text: "VRAM  " + runtimeStatus.vramUsedGiB + " / " + runtimeStatus.vramTotalGiB + " GB"; color: appRoot.textDim; font.pixelSize: 12 }
                                        Text { text: moduleBridge.status; color: appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                    }
                                }
                            }
                        }
                        GridLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            columns: 3
                            rowSpacing: 10
                            columnSpacing: 10
                            Repeater {
                                model: [
                                    {title:"Image Generation", sub:"Load source · choose pose · generate", page:1, icon:"▣"},
                                    {title:"Pose Library", sub:"Visual preset browser and camera guides", page:2, icon:"♟"},
                                    {title:"Media Tools", sub:"Enhance · upscale · remove background · batch", page:4, icon:"✦"},
                                    {title:"Photo Library", sub:"Viewer · people · duplicates", page:5, icon:"▧"},
                                    {title:"Camera Hub", sub:"Live local cameras and recordings", page:6, icon:"●"},
                                    {title:"Entertainment", sub:"Jellyfin · local media · SillyTavern", page:7, icon:"▷"}
                                ]
                                Panel {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: appRoot.pageIndex = modelData.page }
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 16
                                        Text { text: modelData.icon; color: appRoot.gold; font.pixelSize: 34 }
                                        Item { Layout.fillHeight: true }
                                        Text { text: modelData.title; color: appRoot.brightGold; font.pixelSize: 18; font.bold: true }
                                        Text { Layout.fillWidth: true; text: modelData.sub; color: appRoot.textDim; font.pixelSize: 12; wrapMode: Text.Wrap }
                                    }
                                }
                            }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 9
                        PageHeader { titleText: "Image Generation"; subtitleText: "Load image → choose look or pose → generate. Advanced controls stay on the right."; iconText: "▣" }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 10
                            Panel {
                                Layout.preferredWidth: 330
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 8
                                    SectionLabel { text: "SOURCE IMAGE" }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 210
                                        radius: 8
                                        color: "#080d12"
                                        border.color: appRoot.generationSource.toString().length ? appRoot.gold : appRoot.line
                                        Image { anchors.fill: parent; anchors.margins: 6; source: appRoot.generationSource; fillMode: Image.PreserveAspectFit }
                                        Column {
                                            anchors.centerIn: parent
                                            visible: appRoot.generationSource.toString().length === 0
                                            spacing: 5
                                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "+"; color: appRoot.gold; font.pixelSize: 38 }
                                            Text { text: "DROP OR LOAD IMAGE"; color: appRoot.textDim; font.pixelSize: 12; font.bold: true }
                                        }
                                        DropArea { anchors.fill: parent; onDropped: function(drop) { if (drop.urls.length) appRoot.generationSource = drop.urls[0] } }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        GButton { Layout.fillWidth: true; text: "Load Image"; onClicked: appRoot.chooseSource() }
                                        GButton { Layout.preferredWidth: 88; text: "Clear"; enabled: appRoot.generationSource.toString().length > 0; onClicked: appRoot.generationSource = "" }
                                    }
                                    SectionLabel { text: "PROMPT" }
                                    TextArea {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        Layout.minimumHeight: 150
                                        text: appRoot.generationPrompt
                                        placeholderText: "Describe the image. Pose presets can fill this automatically."
                                        color: appRoot.textMain
                                        wrapMode: TextEdit.Wrap
                                        onTextChanged: if (activeFocus) appRoot.generationPrompt = text
                                        background: Rectangle { color: "#080d12"; border.color: appRoot.line; radius: 8 }
                                    }
                                    GButton { Layout.fillWidth: true; text: "Choose from Pose Library"; onClicked: appRoot.pageIndex = 2 }
                                }
                            }

                            Panel {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 8
                                    RowLayout {
                                        Layout.fillWidth: true
                                        SectionLabel { text: "RESULT" }
                                        Item { Layout.fillWidth: true }
                                        GButton { text: "Open"; enabled: genesisBridge.previewUrl.length > 0; onClicked: genesisBridge.openPreview() }
                                        GButton { text: "Folder"; onClicked: genesisBridge.openOutputFolder() }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        color: "#05080b"
                                        radius: 10
                                        border.color: appRoot.line
                                        Image { anchors.fill: parent; anchors.margins: 8; source: genesisBridge.previewUrl; fillMode: Image.PreserveAspectFit; visible: !privacyMode }
                                        Text { anchors.centerIn: parent; text: privacyMode ? "PRIVATE" : "GENERATED RESULT"; color: appRoot.textDim; font.pixelSize: 17; visible: privacyMode || genesisBridge.previewUrl.length === 0 }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text { text: genesisBridge.status; color: genesisBridge.busy ? appRoot.gold : appRoot.textDim; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                                        GButton { text: "Send to Canvas"; enabled: genesisBridge.previewUrl.length > 0; onClicked: { appRoot.editSource = genesisBridge.previewUrl; appRoot.pageIndex = 9 } }
                                    }
                                }
                            }

                            Panel {
                                Layout.preferredWidth: 330
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 8
                                    SectionLabel { text: "MODEL / WORKFLOW" }
                                    ComboBox {
                                        Layout.fillWidth: true
                                        model: appRoot.generationModel
                                        textRole: "label"
                                        currentIndex: appRoot.selectedGenerationIndex
                                        onActivated: appRoot.selectGeneration(currentIndex)
                                    }
                                    Text { Layout.fillWidth: true; text: appRoot.selectedGenerationProfile.note || ""; color: appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap }
                                    SectionLabel { text: "COMPATIBLE LORA" }
                                    ComboBox {
                                        Layout.fillWidth: true
                                        model: appRoot.selectedGenerationProfile.loras || ["None"]
                                        onActivated: appRoot.selectedLora = currentText
                                    }
                                    SectionLabel { text: "QUALITY" }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        GButton { Layout.fillWidth: true; text: "Fast"; active: appRoot.generationWidth === 512; onClicked: { generationWidth = 512; generationHeight = 512 } }
                                        GButton { Layout.fillWidth: true; text: "Balanced"; active: appRoot.generationWidth === 768; onClicked: { generationWidth = 768; generationHeight = 1152 } }
                                        GButton { Layout.fillWidth: true; text: "Quality"; active: appRoot.generationWidth === 1024; onClicked: { generationWidth = 1024; generationHeight = 1024 } }
                                    }
                                    SectionLabel { text: "PIPELINE" }
                                    CheckBox { text: "Stage 2 · refine"; checked: appRoot.useStageTwo; onToggled: appRoot.useStageTwo = checked }
                                    CheckBox { text: "Stage 3 · identity lock"; checked: appRoot.useStageThree; onToggled: appRoot.useStageThree = checked }
                                    CheckBox { text: "Final upscale"; checked: appRoot.useUpscale; enabled: genesisBridge.upscaleAvailable; onToggled: appRoot.useUpscale = checked }
                                    Item { Layout.fillHeight: true }
                                    GButton {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 58
                                        active: enabled
                                        text: genesisBridge.busy ? "GENERATING…" : "GENERATE"
                                        enabled: !genesisBridge.busy
                                            && appRoot.selectedGenerationProfile.runnable
                                            && (appRoot.generationPrompt.trim().length > 0 || appRoot.selectedPosePrompt.trim().length > 0)
                                            && (!appRoot.selectedGenerationProfile.sourceRequired || appRoot.generationSource.toString().length > 0)
                                        onClicked: appRoot.generateCurrent()
                                    }
                                }
                            }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 9
                        PageHeader { titleText: "Pose Library"; subtitleText: "Visual preset browser — choose geometry first, then send it straight to Create."; iconText: "♟" }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 44
                            Repeater {
                                model: ["All", "Standing", "Sitting", "Lying", "Kneeling", "All Fours", "Grok Presets"]
                                GButton { text: modelData; active: index === 0; Layout.preferredWidth: index === 6 ? 130 : 100 }
                            }
                            Item { Layout.fillWidth: true }
                            GButton { text: "Load Source Image"; Layout.preferredWidth: 150; onClicked: appRoot.chooseSource() }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 10
                            Panel {
                                Layout.preferredWidth: 190
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 12; spacing: 7
                                    SectionLabel { text: "FILTERS" }
                                    TextField { Layout.fillWidth: true; placeholderText: "Search poses…" }
                                    ComboBox { Layout.fillWidth: true; model: ["All collections", "Full 70", "Curated 18", "OpenPose library"] }
                                    ComboBox { Layout.fillWidth: true; model: ["All models", appRoot.selectedGenerationProfile.label] }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: appRoot.line }
                                    Text { Layout.fillWidth: true; text: "Preset cards stay visual. Model/workflow compatibility is handled underneath rather than making you wire nodes manually."; color: appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap }
                                    Item { Layout.fillHeight: true }
                                    GButton { Layout.fillWidth: true; text: "Grok Camera Presets" }
                                }
                            }
                            GridLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                columns: 4
                                rowSpacing: 9
                                columnSpacing: 9
                                Repeater {
                                    model: appRoot.poseModel
                                    Panel {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        Rectangle {
                                            anchors.fill: parent
                                            anchors.margins: 6
                                            radius: 7
                                            color: "#080d12"
                                            Image { anchors.fill: parent; anchors.margins: 4; source: modelData.source; fillMode: Image.PreserveAspectFit; asynchronous: true }
                                            Rectangle {
                                                anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                                                height: 34; color: "#cc081017"
                                                Text { anchors.centerIn: parent; width: parent.width - 8; text: modelData.name; color: appRoot.textMain; font.pixelSize: 11; elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter }
                                            }
                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: {
                                                    appRoot.selectedPoseSource = modelData.source
                                                    appRoot.selectedPoseName = modelData.name
                                                    appRoot.selectedPoseCategory = modelData.category
                                                    appRoot.selectedPosePrompt = modelData.prompt
                                                    if (modelData.prompt && modelData.prompt.length) appRoot.generationPrompt = modelData.prompt
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                            Panel {
                                Layout.preferredWidth: 290
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 12; spacing: 8
                                    SectionLabel { text: "SELECTED POSE" }
                                    Text { text: appRoot.selectedPoseName; color: appRoot.brightGold; font.pixelSize: 17; font.bold: true }
                                    Rectangle {
                                        Layout.fillWidth: true; Layout.preferredHeight: 220
                                        radius: 8; color: "#080d12"; border.color: appRoot.gold
                                        Image { anchors.fill: parent; anchors.margins: 6; source: appRoot.selectedPoseSource; fillMode: Image.PreserveAspectFit }
                                    }
                                    Text { text: "Category  " + appRoot.selectedPoseCategory; color: appRoot.textDim; font.pixelSize: 11 }
                                    Text { Layout.fillWidth: true; text: appRoot.selectedPosePrompt.length ? appRoot.selectedPosePrompt : "This pose has no mapped prompt yet."; color: appRoot.textMain; font.pixelSize: 11; wrapMode: Text.Wrap; maximumLineCount: 7; elide: Text.ElideRight }
                                    Item { Layout.fillHeight: true }
                                    GButton { Layout.fillWidth: true; text: "USE POSE IN CREATE"; active: true; onClicked: { if (appRoot.selectedPosePrompt.length) appRoot.generationPrompt = appRoot.selectedPosePrompt; appRoot.pageIndex = 1 } }
                                }
                            }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 9
                        PageHeader { titleText: "Workflow Studio"; subtitleText: "Inspect, validate and launch the generation pipelines behind GENESIS."; iconText: "◇" }
                        RowLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 10
                            Panel {
                                Layout.preferredWidth: 240; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 12; spacing: 7
                                    SectionLabel { text: "WORKFLOW LIBRARY" }
                                    Repeater {
                                        model: ["Stage 1 · Phr00t", "Stage 2 · Lustify", "Stage 3 · ReActor", "Klein 4B Create", "Klein 9B Create", "Image Edit / Inpaint"]
                                        GButton { Layout.fillWidth: true; text: modelData; active: index === 0; onClicked: moduleBridge.triggerAction("Open Workflow") }
                                    }
                                    Item { Layout.fillHeight: true }
                                    GButton { Layout.fillWidth: true; text: "Import JSON"; onClicked: moduleBridge.triggerAction("Import JSON") }
                                }
                            }
                            Panel {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                Item {
                                    anchors.fill: parent; anchors.margins: 14
                                    Rectangle { x: 20; y: 80; width: 190; height: 86; radius: 10; color: "#152536"; border.color: appRoot.ice; Text { anchors.centerIn: parent; text: "MODEL LOADER"; color: appRoot.textMain; font.bold: true } }
                                    Rectangle { x: 270; y: 80; width: 190; height: 86; radius: 10; color: "#192434"; border.color: appRoot.gold; Text { anchors.centerIn: parent; text: "PROMPT / CONDITION"; color: appRoot.textMain; font.bold: true } }
                                    Rectangle { x: 520; y: 80; width: 190; height: 86; radius: 10; color: "#152536"; border.color: appRoot.ice; Text { anchors.centerIn: parent; text: "SAMPLER"; color: appRoot.textMain; font.bold: true } }
                                    Rectangle { x: 390; y: 240; width: 210; height: 86; radius: 10; color: "#1d2831"; border.color: appRoot.gold; Text { anchors.centerIn: parent; text: "SAVE / OUTPUT"; color: appRoot.textMain; font.bold: true } }
                                    Rectangle { x: 210; y: 121; width: 60; height: 2; color: appRoot.gold }
                                    Rectangle { x: 460; y: 121; width: 60; height: 2; color: appRoot.gold }
                                    Rectangle { x: 600; y: 281; width: 120; height: 2; color: appRoot.gold }
                                    Text { x: 20; y: 20; text: "NODE CANVAS"; color: appRoot.textDim; font.pixelSize: 12; font.letterSpacing: 1 }
                                }
                            }
                            Panel {
                                Layout.preferredWidth: 300; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 12; spacing: 8
                                    SectionLabel { text: "VALIDATION" }
                                    Text { text: appRoot.selectedGenerationProfile.runnable ? "✓ ACTIVE CREATE ROUTE VALIDATED" : "! SELECTED ROUTE NOT READY"; color: appRoot.selectedGenerationProfile.runnable ? appRoot.success : appRoot.gold; font.bold: true; font.pixelSize: 12 }
                                    Text { Layout.fillWidth: true; text: appRoot.selectedGenerationProfile.note || ""; color: appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: appRoot.line }
                                    SectionLabel { text: "TOOLS" }
                                    GButton { Layout.fillWidth: true; text: "Validate Workflow"; onClicked: moduleBridge.triggerAction("Validate") }
                                    GButton { Layout.fillWidth: true; text: "Inspect Nodes"; onClicked: moduleBridge.triggerAction("Inspect Nodes") }
                                    GButton { Layout.fillWidth: true; text: "Open Workflow Folder"; onClicked: moduleBridge.triggerAction("Open Workflow") }
                                    Item { Layout.fillHeight: true }
                                    Text { Layout.fillWidth: true; text: moduleBridge.status; color: appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap }
                                }
                            }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 9
                        PageHeader { titleText: "Media Tools"; subtitleText: "One production workspace for cutout, enhance, upscale and batch processing."; iconText: "✦" }
                        RowLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 10
                            Panel {
                                Layout.preferredWidth: 150; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 10; spacing: 6
                                    SectionLabel { text: "TOOLS" }
                                    Repeater {
                                        model: ["Background Remove", "Enhance", "Upscale", "Media Viewer", "Duplicate Finder", "Face Organiser", "Canvas Editor"]
                                        GButton {
                                            Layout.fillWidth: true
                                            text: modelData
                                            active: appRoot.activeMediaTool === modelData
                                            onClicked: appRoot.activeMediaTool = modelData
                                        }
                                    }
                                    Item { Layout.fillHeight: true }
                                    GButton { Layout.fillWidth: true; text: "Open Full Tool"; onClicked: moduleBridge.triggerAction("Open " + appRoot.activeMediaTool) }
                                }
                            }
                            Panel {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 12; spacing: 8
                                    RowLayout {
                                        Layout.fillWidth: true
                                        SectionLabel { text: appRoot.activeMediaTool.toUpperCase() }
                                        Item { Layout.fillWidth: true }
                                        GButton { text: "Original"; active: true; Layout.preferredWidth: 90 }
                                        GButton { text: "Result"; Layout.preferredWidth: 90 }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true; Layout.fillHeight: true
                                        radius: 9; color: "#05080b"; border.color: appRoot.line
                                        Text { anchors.centerIn: parent; text: "LARGE MEDIA PREVIEW"; color: appRoot.textDim; font.pixelSize: 18 }
                                    }
                                    SectionLabel { text: "BATCH QUEUE" }
                                    RowLayout {
                                        Layout.fillWidth: true; Layout.preferredHeight: 92
                                        Repeater {
                                            model: ["01 · Ready", "02 · Pending", "03 · Pending", "04 · Pending", "+ Add"]
                                            Rectangle {
                                                Layout.fillWidth: true; Layout.fillHeight: true
                                                radius: 7; color: index === 0 ? "#172433" : "#0b1118"; border.color: index === 0 ? appRoot.gold : appRoot.line
                                                Text { anchors.centerIn: parent; text: modelData; color: index === 0 ? appRoot.brightGold : appRoot.textDim; font.pixelSize: 11 }
                                            }
                                        }
                                    }
                                }
                            }
                            Panel {
                                Layout.preferredWidth: 300; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 12; spacing: 8
                                    SectionLabel { text: "SETTINGS" }
                                    Text { text: "Mode"; color: appRoot.textDim; font.pixelSize: 11 }
                                    ComboBox { Layout.fillWidth: true; model: appRoot.activeMediaTool === "Background Remove" ? ["Transparent", "Solid", "Custom background"] : ["Auto", "Balanced", "Maximum quality"] }
                                    Text { text: "Detail / strength"; color: appRoot.textDim; font.pixelSize: 11 }
                                    Slider { Layout.fillWidth: true; from: 0; to: 100; value: 70 }
                                    CheckBox { text: "Apply settings to all"; checked: true }
                                    CheckBox { text: "Keep originals"; checked: true }
                                    Item { Layout.fillHeight: true }
                                    GButton { Layout.fillWidth: true; text: "PROCESS CURRENT"; active: true; onClicked: moduleBridge.triggerAction("Open " + appRoot.activeMediaTool) }
                                    GButton { Layout.fillWidth: true; text: "PROCESS ALL"; onClicked: moduleBridge.triggerAction("Build Batch") }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        GButton { Layout.fillWidth: true; text: "Save Current"; onClicked: moduleBridge.triggerAction("Open Output") }
                                        GButton { Layout.fillWidth: true; text: "Save All"; onClicked: moduleBridge.triggerAction("Open Output") }
                                    }
                                }
                            }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent; spacing: 9
                        PageHeader { titleText: "Photo Library"; subtitleText: "Your media is the interface — viewer, people and duplicate management in one place."; iconText: "▧" }
                        RowLayout {
                            Layout.fillWidth: true; Layout.preferredHeight: 44
                            Repeater {
                                model: ["Media Viewer", "People", "Duplicates"]
                                GButton { text: modelData; active: appRoot.activeLibraryMode === modelData; Layout.preferredWidth: 120; onClicked: appRoot.activeLibraryMode = modelData }
                            }
                            Item { Layout.fillWidth: true }
                            TextField { Layout.preferredWidth: 250; placeholderText: "Search folders, people or files…" }
                            GButton { text: "Scan Folder"; onClicked: moduleBridge.triggerAction("Scan Library") }
                        }
                        RowLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 10
                            Panel {
                                Layout.preferredWidth: 210; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 12; spacing: 6
                                    SectionLabel { text: "LIBRARY" }
                                    Repeater {
                                        model: ["Pictures", "GENESIS Exports", "Generated Images", "Video", "Cutouts", "Wallpapers"]
                                        GButton { Layout.fillWidth: true; text: modelData; active: index === 0 }
                                    }
                                    Item { Layout.fillHeight: true }
                                    GButton { Layout.fillWidth: true; text: "Add Folder"; onClicked: moduleBridge.triggerAction("Add Folder") }
                                }
                            }
                            Panel {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 12; spacing: 8
                                    RowLayout {
                                        Layout.fillWidth: true
                                        SectionLabel { text: appRoot.activeLibraryMode.toUpperCase() }
                                        Item { Layout.fillWidth: true }
                                        Text { text: "Local files · originals stay in place"; color: appRoot.textDim; font.pixelSize: 11 }
                                    }
                                    GridLayout {
                                        visible: appRoot.activeLibraryMode !== "Duplicates"
                                        Layout.fillWidth: true; Layout.fillHeight: true
                                        columns: 4; rowSpacing: 8; columnSpacing: 8
                                        Repeater {
                                            model: appRoot.activeLibraryMode === "People"
                                                ? ["Person 01", "Person 02", "Person 03", "Unnamed", "Unnamed", "Suggested", "Suggested", "Suggested"]
                                                : ["Media 01", "Media 02", "Media 03", "Media 04", "Media 05", "Media 06", "Media 07", "Media 08"]
                                            Rectangle {
                                                Layout.fillWidth: true; Layout.fillHeight: true
                                                radius: 8; color: "#091017"; border.color: appRoot.line
                                                Rectangle { anchors.fill: parent; anchors.margins: 7; radius: 6; color: index % 2 ? "#121b24" : "#0f171f" }
                                                Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; height: 30; color: "#cc070b10"; Text { anchors.centerIn: parent; text: modelData; color: appRoot.textMain; font.pixelSize: 11 } }
                                            }
                                        }
                                    }
                                    ColumnLayout {
                                        visible: appRoot.activeLibraryMode === "Duplicates"
                                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 7
                                        Repeater {
                                            model: ["Group 01 · 3 files · 98% similar", "Group 02 · 2 files · exact hash", "Group 03 · 4 files · resized copies", "Group 04 · 2 files · 95% similar"]
                                            Rectangle {
                                                Layout.fillWidth: true; Layout.preferredHeight: 58
                                                radius: 7; color: index === 0 ? "#172433" : "#0b1118"; border.color: index === 0 ? appRoot.gold : appRoot.line
                                                RowLayout { anchors.fill: parent; anchors.margins: 10; CheckBox { checked: false }; Text { text: modelData; color: appRoot.textMain; font.pixelSize: 12; Layout.fillWidth: true }; Text { text: index === 0 ? "Previewing" : ""; color: appRoot.gold; font.pixelSize: 11 } }
                                            }
                                        }
                                        Item { Layout.fillHeight: true }
                                    }
                                }
                            }
                            Panel {
                                Layout.preferredWidth: 300; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 12; spacing: 8
                                    SectionLabel { text: appRoot.activeLibraryMode === "People" ? "PERSON DETAIL" : (appRoot.activeLibraryMode === "Duplicates" ? "VERIFY / COMPARE" : "SELECTED MEDIA") }
                                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 230; radius: 8; color: "#060a0e"; border.color: appRoot.line; Text { anchors.centerIn: parent; text: "PREVIEW"; color: appRoot.textDim; font.pixelSize: 17 } }
                                    Text { Layout.fillWidth: true; text: appRoot.activeLibraryMode === "People" ? "Confirmed faces + suggested matches. Approve or reject without moving originals." : (appRoot.activeLibraryMode === "Duplicates" ? "Compare candidates, keep the best file, and confirm before moving or deleting anything." : "Open selected media or send it directly into another GENESIS tool."); color: appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap }
                                    Item { Layout.fillHeight: true }
                                    GButton { Layout.fillWidth: true; text: appRoot.activeLibraryMode === "People" ? "Open Face Organiser" : (appRoot.activeLibraryMode === "Duplicates" ? "Open Duplicate Finder" : "Open Media Viewer"); active: true; onClicked: moduleBridge.triggerAction(text) }
                                    GButton { Layout.fillWidth: true; text: "Send to Media Tools"; onClicked: appRoot.pageIndex = 4 }
                                }
                            }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent; spacing: 9
                        PageHeader { titleText: "Camera Hub"; subtitleText: "Live local cameras, recordings and device settings in one dedicated workspace."; iconText: "●" }
                        RowLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 10
                            GridLayout {
                                Layout.fillWidth: true; Layout.fillHeight: true; columns: 2; rowSpacing: 9; columnSpacing: 9
                                Repeater {
                                    model: ["Front Camera", "Side Camera", "Studio Camera", "Outdoor Camera"]
                                    Panel {
                                        Layout.fillWidth: true; Layout.fillHeight: true
                                        Rectangle { anchors.fill: parent; anchors.margins: 8; radius: 8; color: "#05080b"; border.color: appRoot.line; Text { anchors.centerIn: parent; text: modelData + "\n\nLIVE PREVIEW"; color: appRoot.textDim; font.pixelSize: 15; horizontalAlignment: Text.AlignHCenter } }
                                        Rectangle { anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 15; width: 72; height: 24; radius: 12; color: "#18261f"; Text { anchors.centerIn: parent; text: "● READY"; color: appRoot.success; font.pixelSize: 9; font.bold: true } }
                                    }
                                }
                            }
                            Panel {
                                Layout.preferredWidth: 310; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 12; spacing: 8
                                    SectionLabel { text: "CAMERA SETTINGS" }
                                    ComboBox { Layout.fillWidth: true; model: ["Front Camera", "Side Camera", "Studio Camera", "Outdoor Camera"] }
                                    Text { text: "Quality"; color: appRoot.textDim; font.pixelSize: 11 }
                                    ComboBox { Layout.fillWidth: true; model: ["Original", "1080p", "720p"] }
                                    CheckBox { text: "Audio enabled"; checked: false }
                                    CheckBox { text: "Record locally"; checked: false }
                                    Item { Layout.fillHeight: true }
                                    GButton { Layout.fillWidth: true; text: "OPEN CAMERA HUB"; active: true; onClicked: moduleBridge.triggerAction("Camera Hub") }
                                    GButton { Layout.fillWidth: true; text: "Browse Recordings"; onClicked: moduleBridge.triggerAction("Recordings") }
                                    Text { Layout.fillWidth: true; text: moduleBridge.status; color: appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap }
                                }
                            }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent; spacing: 9
                        PageHeader { titleText: "Entertainment"; subtitleText: "Jellyfin, local playback and SillyTavern grouped into one media-first section."; iconText: "▷" }
                        RowLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 10
                            Panel {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 18; spacing: 10
                                    Text { text: "JELLYFIN"; color: appRoot.brightGold; font.pixelSize: 28; font.bold: true }
                                    Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; radius: 10; color: "#05080b"; border.color: appRoot.line; Text { anchors.centerIn: parent; text: "MOVIES · TV · LOCAL MEDIA"; color: appRoot.textDim; font.pixelSize: 20 } }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        GButton { Layout.fillWidth: true; text: "Open Jellyfin"; active: true; onClicked: moduleBridge.triggerAction("Movies & TV") }
                                        GButton { Layout.fillWidth: true; text: "Open Video Library"; onClicked: moduleBridge.triggerAction("Open Video Library") }
                                    }
                                }
                            }
                            Panel {
                                Layout.preferredWidth: 390; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 18; spacing: 10
                                    Text { text: "SILLYTAVERN"; color: appRoot.brightGold; font.pixelSize: 24; font.bold: true }
                                    Text { Layout.fillWidth: true; text: "Launch the configured local web app without leaving the GENESIS entertainment area."; color: appRoot.textDim; font.pixelSize: 12; wrapMode: Text.Wrap }
                                    Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; radius: 10; color: "#0a1118"; border.color: appRoot.line; Text { anchors.centerIn: parent; text: "LOCAL WEB APP"; color: appRoot.textDim; font.pixelSize: 18 } }
                                    GButton { Layout.fillWidth: true; text: "Open SillyTavern"; active: true; onClicked: moduleBridge.triggerAction("Web Apps") }
                                }
                            }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent; spacing: 9
                        PageHeader { titleText: "System Tools"; subtitleText: "Services, GPU, models, recovery and application health."; iconText: "⚙" }
                        GridLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; columns: 3; rowSpacing: 10; columnSpacing: 10
                            Repeater {
                                model: [
                                    {title:"GPU & VRAM", detail:runtimeStatus.gpuName + "\n" + runtimeStatus.vramUsedGiB + " / " + runtimeStatus.vramTotalGiB + " GB", action:"Open Monitor", icon:"GPU"},
                                    {title:"ComfyUI", detail:runtimeStatus.comfyOnline ? "Online · generation service ready" : "Offline · health check required", action:"Manage Service", icon:"UI"},
                                    {title:"GENESIS AI", detail:"Local assistant and model route", action:"AI Settings", icon:"AI"},
                                    {title:"Models & Storage", detail:"Model inventory, paths and disk use", action:"Manage Storage", icon:"☷"},
                                    {title:"Backup & Restore", detail:"Recovery snapshots and checkpoints", action:"Open Recovery", icon:"↻"},
                                    {title:"Health Check", detail:moduleBridge.status, action:"Health Check", icon:"✓"}
                                ]
                                Panel {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent; anchors.margins: 16; spacing: 8
                                        Text { text: modelData.icon; color: appRoot.gold; font.pixelSize: 30; font.bold: true }
                                        Text { text: modelData.title; color: appRoot.brightGold; font.pixelSize: 17; font.bold: true }
                                        Text { Layout.fillWidth: true; Layout.fillHeight: true; text: modelData.detail; color: appRoot.textDim; font.pixelSize: 12; wrapMode: Text.Wrap }
                                        GButton { Layout.fillWidth: true; text: modelData.action; onClicked: moduleBridge.triggerAction(modelData.action) }
                                    }
                                }
                            }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent; spacing: 8
                        PageHeader { titleText: "Canvas / Edit"; subtitleText: "Photoshop-style spatial workspace for cutouts, layers and targeted image edits."; iconText: "Ps" }
                        RowLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 8
                            Panel {
                                Layout.preferredWidth: 76; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 8; spacing: 6
                                    Repeater { model: ["↖", "✥", "▣", "T", "○", "✎", "⌫", "↻"]; GButton { Layout.fillWidth: true; text: modelData; Layout.preferredHeight: 48 } }
                                    Item { Layout.fillHeight: true }
                                }
                            }
                            ColumnLayout {
                                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 8
                                Panel {
                                    Layout.fillWidth: true; Layout.preferredHeight: 52
                                    RowLayout { anchors.fill: parent; anchors.margins: 7; spacing: 6; Text { text: "W 1920   H 1080   ⛓ 100%   Rotate 0°"; color: appRoot.textDim; font.pixelSize: 12 }; Item { Layout.fillWidth: true }; GButton { text: "Select Subject" }; GButton { text: "Remove Background"; onClicked: { activeMediaTool = "Background Remove"; pageIndex = 4 } }; GButton { text: "Enhance"; onClicked: { activeMediaTool = "Enhance"; pageIndex = 4 } } }
                                }
                                Panel {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    Rectangle {
                                        anchors.fill: parent; anchors.margins: 16
                                        color: "#15191c"; border.color: appRoot.line
                                        Image { anchors.fill: parent; anchors.margins: 12; source: appRoot.editSource; fillMode: Image.PreserveAspectFit; visible: !privacyMode }
                                        Text { anchors.centerIn: parent; text: appRoot.editSource.toString().length ? "" : "CANVAS\n\nLoad an image or generated result"; color: appRoot.textDim; font.pixelSize: 17; horizontalAlignment: Text.AlignHCenter }
                                        DropArea { anchors.fill: parent; onDropped: function(drop) { if (drop.urls.length) appRoot.editSource = drop.urls[0] } }
                                    }
                                }
                                Panel {
                                    Layout.fillWidth: true; Layout.preferredHeight: 60
                                    RowLayout { anchors.fill: parent; anchors.margins: 8; GButton { text: "Load Image"; onClicked: appRoot.chooseEditSource() }; GButton { text: "Use Generated Result"; enabled: genesisBridge.previewUrl.length > 0; onClicked: appRoot.editSource = genesisBridge.previewUrl }; Item { Layout.fillWidth: true }; GButton { text: "Export"; onClicked: genesisBridge.openOutputFolder() } }
                                }
                            }
                            Panel {
                                Layout.preferredWidth: 310; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 12; spacing: 7
                                    RowLayout { Layout.fillWidth: true; Repeater { model: ["Properties", "Adjust", "Layers"]; GButton { Layout.fillWidth: true; text: modelData; active: index === 2 } } }
                                    SectionLabel { text: "EDIT INSTRUCTIONS" }
                                    TextArea { Layout.fillWidth: true; Layout.preferredHeight: 130; text: appRoot.editPrompt; placeholderText: "Describe only the change you want…"; color: appRoot.textMain; wrapMode: TextEdit.Wrap; onTextChanged: if (activeFocus) appRoot.editPrompt = text; background: Rectangle { color: "#080d12"; border.color: appRoot.line; radius: 8 } }
                                    Text { text: "Strength  " + appRoot.editStrength.toFixed(2); color: appRoot.textDim; font.pixelSize: 11 }
                                    Slider { Layout.fillWidth: true; from: 0.05; to: 0.95; stepSize: 0.05; value: appRoot.editStrength; onMoved: appRoot.editStrength = value }
                                    SectionLabel { text: "LAYERS" }
                                    Repeater { model: ["Subject / Image", "Adjustment", "Background"]; Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 42; radius: 6; color: index === 0 ? "#172433" : "#0b1118"; border.color: index === 0 ? appRoot.gold : appRoot.line; RowLayout { anchors.fill: parent; anchors.margins: 8; CheckBox { checked: true }; Text { text: modelData; color: appRoot.textMain; font.pixelSize: 11; Layout.fillWidth: true } } } }
                                    Item { Layout.fillHeight: true }
                                    GButton { Layout.fillWidth: true; text: genesisBridge.busy ? "WORKING…" : "APPLY IMAGE EDIT"; active: enabled; enabled: !genesisBridge.busy && genesisBridge.editAvailable && appRoot.editSource.toString().length > 0 && appRoot.editPrompt.trim().length > 0; onClicked: genesisBridge.queueEdit(appRoot.editSource.toString(), appRoot.editPrompt, appRoot.editStrength) }
                                }
                            }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent; spacing: 9
                        PageHeader { titleText: "Pose Maker"; subtitleText: "Source image + pose reference + staged refinement in one production view."; iconText: "♜" }
                        RowLayout {
                            Layout.fillWidth: true; Layout.preferredHeight: 190; spacing: 9
                            Repeater {
                                model: [
                                    {title:"SOURCE IMAGE", source:appRoot.generationSource},
                                    {title:"POSE REFERENCE", source:appRoot.selectedPoseSource}
                                ]
                                Panel {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout { anchors.fill: parent; anchors.margins: 10; SectionLabel { text: modelData.title }; Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; color: "#05080b"; border.color: appRoot.line; Image { anchors.fill: parent; anchors.margins: 5; source: modelData.source; fillMode: Image.PreserveAspectFit }; Text { anchors.centerIn: parent; text: modelData.source.toString().length ? "" : "LOAD / SELECT"; color: appRoot.textDim } } }
                                }
                            }
                            Panel {
                                Layout.preferredWidth: 320; Layout.fillHeight: true
                                ColumnLayout { anchors.fill: parent; anchors.margins: 10; SectionLabel { text: "POSE INSTRUCTION" }; TextArea { Layout.fillWidth: true; Layout.fillHeight: true; text: appRoot.generationPrompt; color: appRoot.textMain; wrapMode: TextEdit.Wrap; onTextChanged: if (activeFocus) appRoot.generationPrompt = text; background: Rectangle { color: "#080d12"; border.color: appRoot.line; radius: 7 } } }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 9
                            Repeater {
                                model: ["STAGE 1 · Phr00t / Create", "STAGE 2 · Lustify refine", "STAGE 3 · ReActor identity lock"]
                                Panel {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout { anchors.fill: parent; anchors.margins: 12; SectionLabel { text: modelData }; Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; color: "#05080b"; border.color: index === 2 ? appRoot.gold : appRoot.line; Image { anchors.fill: parent; anchors.margins: 6; source: index === 2 ? genesisBridge.previewUrl : ""; fillMode: Image.PreserveAspectFit }; Text { anchors.centerIn: parent; text: index === 2 && genesisBridge.previewUrl.length ? "" : "OUTPUT PREVIEW"; color: appRoot.textDim } }; CheckBox { text: index === 0 ? "Pipeline input" : "Use this stage"; enabled: index > 0; checked: index === 0 || (index === 1 ? appRoot.useStageTwo : appRoot.useStageThree); onToggled: { if (index === 1) appRoot.useStageTwo = checked; if (index === 2) appRoot.useStageThree = checked } } } }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true; Layout.preferredHeight: 56
                            GButton { text: "Load Source"; onClicked: appRoot.chooseSource() }
                            GButton { text: "Choose Pose"; onClicked: appRoot.pageIndex = 2 }
                            CheckBox { text: "Final upscale"; checked: appRoot.useUpscale; enabled: genesisBridge.upscaleAvailable; onToggled: appRoot.useUpscale = checked }
                            Item { Layout.fillWidth: true }
                            GButton { Layout.preferredWidth: 220; Layout.preferredHeight: 52; text: genesisBridge.busy ? "GENERATING…" : "GENERATE POSE"; active: enabled; enabled: !genesisBridge.busy && appRoot.selectedGenerationProfile.runnable && appRoot.generationSource.toString().length > 0 && (appRoot.generationPrompt.trim().length > 0 || appRoot.selectedPosePrompt.trim().length > 0); onClicked: appRoot.generateCurrent() }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent; spacing: 9
                        PageHeader { titleText: "Settings"; subtitleText: "Appearance, privacy, local integrations and application behaviour."; iconText: "☷" }
                        RowLayout {
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 10
                            Panel {
                                Layout.preferredWidth: 250; Layout.fillHeight: true
                                ColumnLayout { anchors.fill: parent; anchors.margins: 12; SectionLabel { text: "CATEGORIES" }; Repeater { model: ["Appearance", "Privacy", "Generation", "Integrations", "Storage", "Advanced"]; GButton { Layout.fillWidth: true; text: modelData; active: index === 0 } }; Item { Layout.fillHeight: true } }
                            }
                            Panel {
                                Layout.fillWidth: true; Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 18; spacing: 12
                                    Text { text: "Appearance"; color: appRoot.brightGold; font.pixelSize: 22; font.bold: true }
                                    Text { Layout.fillWidth: true; text: "GENESIS uses a restrained graphite, antique-gold and cool-status-blue system. Gold marks selected or important states rather than decorating every surface."; color: appRoot.textDim; font.pixelSize: 12; wrapMode: Text.Wrap }
                                    RowLayout { Layout.fillWidth: true; Text { text: "Privacy mode"; color: appRoot.textMain; Layout.fillWidth: true }; Switch { checked: appRoot.privacyMode; onToggled: appRoot.privacyMode = checked } }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: appRoot.line }
                                    Text { text: "Local integrations"; color: appRoot.brightGold; font.pixelSize: 18; font.bold: true }
                                    Repeater { model: ["ComfyUI", "GENESIS AI", "Camera Hub", "Jellyfin", "SillyTavern"]; RowLayout { Layout.fillWidth: true; Text { text: modelData; color: appRoot.textMain; Layout.fillWidth: true }; GButton { text: "Open / Check"; onClicked: moduleBridge.triggerAction(modelData) } } }
                                    Item { Layout.fillHeight: true }
                                    GButton { Layout.preferredWidth: 180; text: "Open App Settings"; onClicked: moduleBridge.triggerAction("Application Settings") }
                                }
                            }
                        }
                    }
                }
            }
        }

        Panel {
            Layout.fillWidth: true
            Layout.preferredHeight: 42
            RowLayout {
                anchors.fill: parent; anchors.margins: 8; spacing: 16
                Text { text: Qt.formatDateTime(new Date(), "ddd, d MMM yyyy  hh:mm"); color: appRoot.textDim; font.pixelSize: 10 }
                Text { text: runtimeStatus.comfyOnline ? "ComfyUI ● Online" : "ComfyUI ○ Offline"; color: runtimeStatus.comfyOnline ? appRoot.success : appRoot.gold; font.pixelSize: 10 }
                Text { text: "GPU  " + runtimeStatus.gpuName; color: appRoot.textDim; font.pixelSize: 10; elide: Text.ElideRight; Layout.maximumWidth: 280 }
                Item { Layout.fillWidth: true }
                Text { text: moduleBridge.status; color: appRoot.textDim; font.pixelSize: 10; elide: Text.ElideRight; Layout.maximumWidth: 420 }
                Text { text: "GENESIS PREMIUM UI"; color: appRoot.gold; font.pixelSize: 10; font.bold: true; font.letterSpacing: 0.8 }
            }
        }
    }
}
