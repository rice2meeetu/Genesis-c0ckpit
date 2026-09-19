import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: appRoot
    visible: true
    width: 1536
    height: 960
    minimumWidth: 1120
    minimumHeight: 720
    title: "GENESIS c0ckpit · Linux"
    color: "#141619"
    font.family: "Noto Sans"

    readonly property color gold: "#d2a34e"
    readonly property color brightGold: "#f3d28b"
    readonly property color blue: "#3aa7ff"
    readonly property color blueBright: "#75c5ff"
    readonly property color blueDeep: "#123a5a"
    readonly property color bg: "#141619"
    readonly property color panel: "#202328"
    readonly property color raised: "#282c31"
    readonly property color raised2: "#30353b"
    readonly property color line: "#454b53"
    readonly property color textMain: "#eef3f6"
    readonly property color textDim: "#91a2b2"
    readonly property color success: "#62d27a"

    property int pageIndex: 0
    property bool privacyMode: false
    readonly property bool compactNavigation: height < 850
    property var navItems: [
        {icon:"▣", label:"Image Generation", page:0},
        {icon:"♟", label:"Pose Library", page:1},
        {icon:"◇", label:"Workflow Studio", page:2},
        {icon:"✦", label:"Media Tools", page:3},
        {icon:"▧", label:"Photo Library", page:4},
        {icon:"●", label:"Camera Hub", page:5},
        {icon:"▷", label:"Entertainment", page:6},
        {icon:"⚙", label:"System Tools", page:7},
        {icon:"Ps", label:"Canvas / Edit", page:8},
        {icon:"♜", label:"Pose Maker", page:9},
        {icon:"☷", label:"Settings", page:10}
    ]

    Shortcut { sequence: "Alt+1"; onActivated: appRoot.pageIndex = 0 }
    Shortcut { sequence: "Alt+2"; onActivated: appRoot.pageIndex = 1 }
    Shortcut { sequence: "Alt+3"; onActivated: appRoot.pageIndex = 2 }
    Shortcut { sequence: "Alt+4"; onActivated: appRoot.pageIndex = 3 }
    Shortcut { sequence: "Alt+5"; onActivated: appRoot.pageIndex = 4 }
    Shortcut { sequence: "Alt+6"; onActivated: appRoot.pageIndex = 5 }
    Shortcut { sequence: "Alt+7"; onActivated: appRoot.pageIndex = 6 }
    Shortcut { sequence: "Alt+8"; onActivated: appRoot.pageIndex = 7 }
    Shortcut { sequence: "Alt+9"; onActivated: appRoot.pageIndex = 8 }
    Shortcut { sequence: "Alt+0"; onActivated: appRoot.pageIndex = 9 }
    Shortcut { sequence: "Alt+,"; onActivated: appRoot.pageIndex = 10 }
    Shortcut { sequence: "Alt+A"; onActivated: if (appRoot.navItems.length > 11) appRoot.pageIndex = 11 }

    property var generationModel: typeof generationProfiles !== "undefined" ? generationProfiles : []
    property int selectedGenerationIndex: 0
    readonly property var selectedGenerationProfile: generationModel.length
        ? generationModel[selectedGenerationIndex]
        : ({label:"No local model", model:"", note:"No validated local model", loras:["None"], runnable:false, sourceRequired:false})
    property string selectedLora: "None"
    property url generationSource: ""
    property string generationPrompt: ""
    property string generationNegativePrompt: ""
    property int generationWidth: 768
    property int generationHeight: 1152
    property bool useStageTwo: false
    property bool useStageThree: false
    property bool useUpscale: false

    property var poseModel: typeof poseItems !== "undefined" ? poseItems : []
    property var easyPresetModel: typeof curatedPosePresets !== "undefined" ? curatedPosePresets : []
    property url selectedPoseSource: poseModel.length ? poseModel[0].source : ""
    property string selectedPoseName: poseModel.length ? poseModel[0].name : "No pose selected"
    property string selectedPoseCategory: poseModel.length ? poseModel[0].category : ""
    property string selectedPosePrompt: poseModel.length ? poseModel[0].prompt : ""
    property string selectedPresetName: "No preset selected"
    property string presetSearch: ""
    property string presetCategory: "All"
    property string poseSearch: ""
    property string poseCategory: "All"

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

    function applyPreset(row) {
        if (!row) return
        selectedPresetName = row.label || row.name || "Preset"
        if (row.prompt && row.prompt.length)
            generationPrompt = row.prompt
    }

    function applyPose(row) {
        if (!row) return
        selectedPoseSource = row.source || ""
        selectedPoseName = row.name || "Pose"
        selectedPoseCategory = row.category || ""
        selectedPosePrompt = row.prompt || ""
        if (row.prompt && row.prompt.length)
            generationPrompt = row.prompt
    }

    function filteredPresets() {
        var out = []
        var needle = presetSearch.toLowerCase().trim()
        for (var i = 0; i < easyPresetModel.length; ++i) {
            var row = easyPresetModel[i]
            var category = String(row.category || "")
            var collection = String(row.collection || "")
            var label = String(row.label || row.name || "")
            if (presetCategory !== "All" && collection !== presetCategory && category !== presetCategory)
                continue
            if (needle.length && (label + " " + category + " " + collection).toLowerCase().indexOf(needle) < 0)
                continue
            out.push(row)
        }
        return out
    }

    function filteredPoses() {
        var out = []
        var needle = poseSearch.toLowerCase().trim()
        for (var i = 0; i < poseModel.length; ++i) {
            var row = poseModel[i]
            var category = String(row.category || "")
            var name = String(row.name || "")
            if (poseCategory !== "All" && category.toLowerCase().indexOf(poseCategory.toLowerCase()) < 0)
                continue
            if (needle.length && (name + " " + category).toLowerCase().indexOf(needle) < 0)
                continue
            out.push(row)
        }
        return out
    }

    function generateCurrent() {
        var prompt = generationPrompt.trim().length ? generationPrompt : selectedPosePrompt
        genesisBridge.queueGenerate(
            prompt,
            generationNegativePrompt,
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
            GradientStop { position: 0.0; color: "#2b2f34" }
            GradientStop { position: 0.11; color: "#25292e" }
            GradientStop { position: 1.0; color: "#1b1e22" }
        }
        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 16
            anchors.rightMargin: 16
            height: 1
            color: "#55f3d28b"
        }
    }

    component GButton: Button {
        id: button
        property bool active: false
        property bool premium: false
        implicitHeight: 46
        activeFocusOnTab: true
        Accessible.name: text
        Accessible.role: Accessible.Button
        font.pixelSize: 14
        font.weight: active || premium ? Font.DemiBold : Font.Medium
        contentItem: Text {
            text: button.text
            color: !button.enabled ? "#64717c" : (button.premium ? appRoot.brightGold : (button.active ? "#ffffff" : (button.hovered ? appRoot.blueBright : appRoot.textMain)))
            font: button.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            transform: Translate { y: button.down ? 2 : 0 }
        }
        background: Item {
            Rectangle {
                anchors.left: parent.left; anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: parent.height - 3
                radius: 10
                color: button.premium ? "#5b431c" : (button.active ? "#0b2940" : "#10151a")
                border.color: "#080a0d"
            }
            Rectangle {
                anchors.left: parent.left; anchors.right: parent.right
                y: button.down ? 3 : 0
                height: parent.height - 4
                radius: 10
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    GradientStop { position: 0.0; color: !button.enabled ? "#282b2f" : (button.premium ? "#3b3120" : (button.active ? "#1a5278" : (button.hovered ? "#343b42" : "#2b3036"))) }
                    GradientStop { position: 1.0; color: !button.enabled ? "#202226" : (button.premium ? "#1f1b13" : (button.active ? "#12364f" : "#20252a")) }
                }
                border.color: button.premium ? appRoot.gold : (button.active ? appRoot.blueBright : (button.hovered ? appRoot.blue : appRoot.line))
                border.width: button.active || button.hovered || button.premium ? 1.5 : 1
                Rectangle {
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    anchors.leftMargin: 9; anchors.rightMargin: 9
                    height: 1
                    color: button.premium ? "#99f3d28b" : (button.active || button.hovered ? "#aa75c5ff" : "#35ffffff")
                }
            }
        }
    }

    component NavButton: Button {
        id: nav
        property bool active: false
        implicitHeight: 44
        activeFocusOnTab: true
        Accessible.name: text
        Accessible.role: Accessible.Button
        leftPadding: 12
        contentItem: Text {
            text: nav.text
            color: nav.active ? appRoot.brightGold : (nav.hovered ? appRoot.textMain : appRoot.textDim)
            font.pixelSize: 14
            font.weight: nav.active ? Font.DemiBold : Font.Normal
            horizontalAlignment: Text.AlignLeft
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 8
            color: nav.active ? "#17324a" : (nav.hovered ? "#242a30" : "transparent")
            border.color: nav.active ? appRoot.blue : "transparent"
            border.width: 1
            Rectangle {
                visible: nav.active
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: 3
                color: appRoot.blue
                radius: 2
            }
        }
    }

    component SectionLabel: Text {
        color: appRoot.brightGold
        font.pixelSize: 12
        font.bold: true
        font.letterSpacing: 1.1
    }

    component MediaCard: Panel {
        id: mediaCard
        property string titleText: "Tool"
        property string bodyText: ""
        property string iconText: "◆"
        property string actionKey: ""
        property string statusText: "LOCAL TOOL"
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 250
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 14
            spacing: 9
            RowLayout {
                Layout.fillWidth: true
                Text { text: mediaCard.iconText; color: appRoot.blueBright; font.pixelSize: 22; font.bold: true }
                Text { Layout.fillWidth: true; text: mediaCard.titleText; color: appRoot.brightGold; font.family: "Noto Sans Display"; font.pixelSize: 18; font.bold: true; elide: Text.ElideRight }
                Rectangle {
                    radius: 10; height: 22; width: statusLabel.implicitWidth + 18
                    color: "#152b3b"; border.color: appRoot.blue
                    Text { id: statusLabel; anchors.centerIn: parent; text: mediaCard.statusText; color: appRoot.blueBright; font.pixelSize: 9; font.bold: true; font.letterSpacing: 0.7 }
                }
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 118
                radius: 10
                color: "#111418"
                border.color: "#39424b"
                border.width: 1
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    GradientStop { position: 0.0; color: "#24292f" }
                    GradientStop { position: 1.0; color: "#111418" }
                }
                Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; height: 2; color: appRoot.blue; opacity: 0.7 }
                Text { anchors.centerIn: parent; text: mediaCard.iconText; color: "#5575c5ff"; font.pixelSize: 58; font.bold: true }
                Text { anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 10; text: "GENESIS · " + mediaCard.titleText.toUpperCase(); color: appRoot.textDim; font.pixelSize: 9; font.bold: true; font.letterSpacing: 0.8 }
            }
            Text { Layout.fillWidth: true; text: mediaCard.bodyText; color: appRoot.textDim; font.pixelSize: 12; wrapMode: Text.Wrap; maximumLineCount: 3; elide: Text.ElideRight }
            GButton {
                Layout.fillWidth: true
                text: mediaBridge.busy ? "WORKING…" : "OPEN  " + mediaCard.titleText.toUpperCase()
                active: !mediaBridge.busy
                enabled: !mediaBridge.busy
                onClicked: {
                    if (mediaCard.actionKey === "background remover")
                        mediaBridge.chooseAndRemoveBackground()
                    else if (mediaCard.actionKey === "upscale")
                        mediaBridge.chooseAndUpscale(2.0)
                    else if (mediaCard.actionKey === "extract audio")
                        mediaBridge.chooseAndExtractAudio()
                    else if (mediaCard.actionKey === "extract video")
                        mediaBridge.chooseAndExtractVideo()
                    else
                        moduleBridge.triggerAction(mediaCard.actionKey)
                }
            }
        }
    }

    component PageHeader: RowLayout {
        id: pageHeader
        property string titleText: ""
        property string subtitleText: ""
        property string iconText: "◆"
        Layout.fillWidth: true
        Layout.preferredHeight: 62
        spacing: 12
        Text { text: pageHeader.iconText; color: appRoot.gold; font.pixelSize: 30 }
        ColumnLayout {
            spacing: 0
            Text { text: pageHeader.titleText; color: appRoot.brightGold; font.pixelSize: 29; font.bold: true }
            Text { text: pageHeader.subtitleText; color: appRoot.textDim; font.pixelSize: 14 }
        }
        Item { Layout.fillWidth: true }
    }

    Rectangle {
        anchors.fill: parent
        z: -10
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0; color: "#272b30" }
            GradientStop { position: 0.40; color: appRoot.bg }
            GradientStop { position: 1; color: "#111315" }
        }
        Image {
            anchors.fill: parent
            source: "../assets/lunacy_banner/cockpit_background_soft.jpg"
            fillMode: Image.PreserveAspectCrop
            opacity: 0.10
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        Panel {
            Layout.fillWidth: true
            Layout.preferredHeight: appRoot.compactNavigation ? 112 : 150
            clip: true

            Item {
                anchors.fill: parent
                anchors.margins: 10

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 2
                    color: appRoot.gold
                }

                Text {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    text: "LOCAL  /  PRIVATE  /  LINUX"
                    color: appRoot.gold
                    font.pixelSize: 10
                    font.bold: true
                    font.letterSpacing: 1.2
                }

                Text {
                    anchors.left: parent.left
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 10
                    text: "Keep walking Allan.  ·  CREATIVE SYSTEM"
                    color: appRoot.textDim
                    font.pixelSize: 10
                    font.letterSpacing: 1.4
                }

                Image {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.min(parent.width * 0.56, appRoot.compactNavigation ? 500 : 650)
                    height: parent.height - 8
                    source: "../assets/lunacy_banner/genesis_cockpit_wordmark_full.png"
                    sourceClipRect: Qt.rect(0, 28, 945, 317)
                    fillMode: Image.PreserveAspectFit
                    mipmap: true
                    smooth: true
                    visible: !privacyMode
                }

                Text {
                    anchors.centerIn: parent
                    visible: privacyMode
                    text: "GENESIS  COCKPIT"
                    color: appRoot.brightGold
                    font.pixelSize: appRoot.compactNavigation ? 28 : 38
                    font.bold: true
                    font.letterSpacing: 4
                }

                Column {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    width: appRoot.compactNavigation ? 170 : 190
                    spacing: 8

                    Rectangle {
                        width: parent.width
                        height: 34
                        radius: 17
                        color: "#171b20"
                        border.color: runtimeStatus.comfyOnline ? appRoot.success : appRoot.gold
                        Text {
                            anchors.centerIn: parent
                            text: runtimeStatus.comfyOnline ? "●  COMFYUI ONLINE" : "○  COMFYUI OFFLINE"
                            color: runtimeStatus.comfyOnline ? appRoot.success : appRoot.gold
                            font.pixelSize: 11
                            font.bold: true
                        }
                    }

                    GButton {
                        width: parent.width
                        text: privacyMode ? "Privacy On" : "Privacy Mode"
                        active: privacyMode
                        onClicked: privacyMode = !privacyMode
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 10

            Panel {
                Layout.preferredWidth: 250
                Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 5
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: appRoot.compactNavigation ? 96 : 220
                        radius: 14
                        color: "#202328"
                        border.color: appRoot.line
                        Image {
                            anchors.fill: parent
                            anchors.margins: 4
                            source: "../assets/genesis-cockpit-icon-balanced-final.png"
                            fillMode: Image.PreserveAspectFit
                            visible: !privacyMode
                        }
                        Text { anchors.centerIn: parent; text: "PRIVATE"; color: appRoot.gold; font.letterSpacing: 2; visible: privacyMode }
                    }
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: availableWidth
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        ScrollBar.vertical.policy: ScrollBar.AsNeeded

                        Column {
                            width: parent.width
                            spacing: 5
                            Repeater {
                                model: appRoot.navItems
                                NavButton {
                                    width: parent.width
                                    text: modelData.icon + "   " + modelData.label
                                    active: appRoot.pageIndex === modelData.page
                                    onClicked: appRoot.pageIndex = modelData.page
                                }
                            }
                        }
                    }
                    Text { Layout.fillWidth: true; text: "LOCAL · PRIVATE · LINUX"; color: appRoot.textDim; font.pixelSize: 9; horizontalAlignment: Text.AlignHCenter; font.letterSpacing: 0.8 }
                }
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: appRoot.pageIndex

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 9
                        PageHeader { titleText: "Image Generation"; subtitleText: "Load your source image, pick a visual preset or pose, then generate."; iconText: "▣" }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 10

                            Panel {
                                Layout.preferredWidth: 350
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 8
                                    RowLayout {
                                        Layout.fillWidth: true
                                        SectionLabel { text: "1 · SOURCE IMAGE" }
                                        Item { Layout.fillWidth: true }
                                        Text { text: appRoot.generationSource.toString().length ? "LOADED" : "REQUIRED FOR SOURCE WORKFLOWS"; color: appRoot.generationSource.toString().length ? appRoot.success : appRoot.textDim; font.pixelSize: 9; font.bold: true }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 245
                                        radius: 10
                                        color: "#1f2227"
                                        border.color: appRoot.gold
                                        border.width: 2
                                        Image { anchors.fill: parent; anchors.margins: 7; source: appRoot.generationSource; fillMode: Image.PreserveAspectFit; visible: !privacyMode }
                                        Column {
                                            anchors.centerIn: parent
                                            visible: appRoot.generationSource.toString().length === 0
                                            spacing: 6
                                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "+"; color: appRoot.gold; font.pixelSize: 46 }
                                            Text { text: "DROP OR LOAD SOURCE IMAGE"; color: appRoot.textMain; font.pixelSize: 12; font.bold: true }
                                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "PNG · JPG · WEBP"; color: appRoot.textDim; font.pixelSize: 10 }
                                        }
                                        Text { anchors.centerIn: parent; text: "PRIVATE"; color: appRoot.gold; font.pixelSize: 18; visible: privacyMode && appRoot.generationSource.toString().length > 0 }
                                        DropArea { anchors.fill: parent; onDropped: function(drop) { if (drop.urls.length) appRoot.generationSource = drop.urls[0] } }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        GButton { Layout.fillWidth: true; text: "Load Source Image"; active: appRoot.generationSource.toString().length === 0; onClicked: appRoot.chooseSource() }
                                        GButton { Layout.preferredWidth: 82; text: "Clear"; enabled: appRoot.generationSource.toString().length > 0; onClicked: appRoot.generationSource = "" }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        SectionLabel { text: "2 · EASY PRESETS" }
                                        Item { Layout.fillWidth: true }
                                        Text { text: appRoot.filteredPresets().length + " shown"; color: appRoot.textDim; font.pixelSize: 10 }
                                    }
                                    TextField {
                                        Layout.fillWidth: true
                                        placeholderText: "Search 70 Grok + curated presets…"
                                        color: appRoot.textMain
                                        onTextChanged: appRoot.presetSearch = text
                                        background: Rectangle { color: "#1f2227"; border.color: appRoot.line; radius: 8 }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 5
                                        Repeater {
                                            model: ["All", "Full 70", "Curated 18"]
                                            GButton { Layout.fillWidth: true; text: modelData; active: appRoot.presetCategory === modelData; onClicked: appRoot.presetCategory = modelData }
                                        }
                                    }
                                    GridView {
                                        id: quickPresetGrid
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        Layout.minimumHeight: 190
                                        clip: true
                                        cellWidth: Math.max(145, width / 2)
                                        cellHeight: 86
                                        model: appRoot.filteredPresets()
                                        delegate: Rectangle {
                                            width: quickPresetGrid.cellWidth - 7
                                            height: quickPresetGrid.cellHeight - 7
                                            radius: 9
                                            color: appRoot.selectedPresetName === String(modelData.label || modelData.name || "") ? "#26384a" : "#0a1118"
                                            border.color: appRoot.selectedPresetName === String(modelData.label || modelData.name || "") ? appRoot.gold : appRoot.line
                                            Column {
                                                anchors.fill: parent
                                                anchors.margins: 9
                                                spacing: 4
                                                Text { width: parent.width; text: modelData.label || modelData.name || "Preset"; color: appRoot.textMain; font.pixelSize: 11; font.bold: true; elide: Text.ElideRight }
                                                Text { width: parent.width; text: (modelData.collection || "Preset") + " · " + (modelData.category || "General"); color: appRoot.gold; font.pixelSize: 9; elide: Text.ElideRight }
                                                Text { width: parent.width; text: modelData.prompt || ""; color: appRoot.textDim; font.pixelSize: 9; maximumLineCount: 2; elide: Text.ElideRight; wrapMode: Text.Wrap }
                                            }
                                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: appRoot.applyPreset(modelData) }
                                        }
                                        ScrollBar.vertical: ScrollBar { }
                                    }
                                    GButton { Layout.fillWidth: true; text: "Browse Full Visual Pose Library"; onClicked: appRoot.pageIndex = 1 }
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
                                        Layout.preferredHeight: 300
                                        Layout.minimumHeight: 240
                                        color: "#171a1e"
                                        radius: 10
                                        border.color: "#8fd2a34e"
                                        border.width: 1.5
                                        Image { anchors.fill: parent; anchors.margins: 8; source: genesisBridge.previewUrl; fillMode: Image.PreserveAspectFit; visible: !privacyMode }
                                        Text { anchors.centerIn: parent; text: privacyMode ? "PRIVATE" : "GENERATED RESULT"; color: appRoot.textDim; font.pixelSize: 18; visible: privacyMode || genesisBridge.previewUrl.length === 0 }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 92
                                        spacing: 8
                                        Repeater {
                                            model: [
                                                {title:"STAGE 1", name:"Phr00t / Qwen", enabled:true},
                                                {title:"STAGE 2", name:"Lustify SDXL", enabled:appRoot.useStageTwo},
                                                {title:"STAGE 3", name:"ReActor", enabled:appRoot.useStageThree}
                                            ]
                                            Rectangle {
                                                Layout.fillWidth: true
                                                Layout.fillHeight: true
                                                radius: 9
                                                color: modelData.enabled ? "#2b2922" : "#202328"
                                                border.color: modelData.enabled ? appRoot.gold : appRoot.line
                                                border.width: modelData.enabled ? 2 : 1
                                                Column {
                                                    anchors.centerIn: parent
                                                    spacing: 3
                                                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.title; color: modelData.enabled ? appRoot.brightGold : appRoot.textDim; font.pixelSize: 12; font.bold: true }
                                                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.name; color: appRoot.textMain; font.pixelSize: 11; font.bold: true }
                                                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.enabled ? "ACTIVE" : "OPTIONAL"; color: modelData.enabled ? appRoot.gold : appRoot.textDim; font.pixelSize: 9 }
                                                }
                                            }
                                        }
                                    }
                                    SectionLabel { text: "PROMPT" }
                                    TextArea {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 105
                                        text: appRoot.generationPrompt
                                        placeholderText: "Preset or pose fills this automatically — edit anything you want."
                                        color: appRoot.textMain
                                        wrapMode: TextEdit.Wrap
                                        onTextChanged: if (activeFocus) appRoot.generationPrompt = text
                                        background: Rectangle { color: "#1f2227"; border.color: appRoot.line; radius: 8 }
                                    }
                                    TextField {
                                        Layout.fillWidth: true
                                        text: appRoot.generationNegativePrompt
                                        placeholderText: "Negative prompt (optional)"
                                        color: appRoot.textMain
                                        onTextChanged: if (activeFocus) appRoot.generationNegativePrompt = text
                                        background: Rectangle { color: "#1f2227"; border.color: appRoot.line; radius: 8 }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text { text: "Preset: " + appRoot.selectedPresetName; color: appRoot.gold; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                        Text { text: "Pose: " + appRoot.selectedPoseName; color: appRoot.textDim; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight; horizontalAlignment: Text.AlignRight }
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
                                    SectionLabel { text: "3 · MODEL / WORKFLOW" }
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
                                    Rectangle { Layout.fillWidth: true; height: 1; color: appRoot.line }
                                    Text { Layout.fillWidth: true; text: appRoot.generationSource.toString().length ? "Source image stays loaded when you change presets, poses, models or LoRAs." : "Load a source image first for identity/source workflows."; color: appRoot.generationSource.toString().length ? appRoot.success : appRoot.gold; font.pixelSize: 11; wrapMode: Text.Wrap }
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
                                    Text { Layout.fillWidth: true; text: genesisBridge.status; color: genesisBridge.busy ? appRoot.gold : appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap }
                                    GButton { Layout.fillWidth: true; text: "Send Result to Canvas"; enabled: genesisBridge.previewUrl.length > 0; onClicked: { appRoot.editSource = genesisBridge.previewUrl; appRoot.pageIndex = 8 } }
                                }
                            }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 9
                        PageHeader { titleText: "Pose Library"; subtitleText: "Visual pose browser — source image stays loaded while you pick geometry."; iconText: "♟" }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            TextField { Layout.preferredWidth: 280; placeholderText: "Search poses…"; color: appRoot.textMain; onTextChanged: appRoot.poseSearch = text; background: Rectangle { color: "#1f2227"; border.color: appRoot.line; radius: 8 } }
                            Repeater {
                                model: ["All", "Standing", "Sitting", "Lying", "Kneeling", "All Fours"]
                                GButton { text: modelData; active: appRoot.poseCategory === modelData; onClicked: appRoot.poseCategory = modelData }
                            }
                            Item { Layout.fillWidth: true }
                            GButton { text: appRoot.generationSource.toString().length ? "Change Source" : "Load Source Image"; active: appRoot.generationSource.toString().length === 0; Layout.preferredWidth: 150; onClicked: appRoot.chooseSource() }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 10
                            Panel {
                                Layout.preferredWidth: 230
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 8
                                    SectionLabel { text: "SOURCE" }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 170
                                        radius: 8
                                        color: "#1f2227"
                                        border.color: appRoot.generationSource.toString().length ? appRoot.gold : appRoot.line
                                        Image { anchors.fill: parent; anchors.margins: 6; source: appRoot.generationSource; fillMode: Image.PreserveAspectFit; visible: appRoot.generationSource.toString().length > 0 && !privacyMode }
                                        Text { anchors.centerIn: parent; text: appRoot.generationSource.toString().length ? (privacyMode ? "PRIVATE" : "") : "NO SOURCE LOADED"; color: appRoot.textDim; font.pixelSize: 11 }
                                    }
                                    SectionLabel { text: "SELECTED POSE" }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 210
                                        radius: 8
                                        color: "#1f2227"
                                        border.color: appRoot.gold
                                        Image { anchors.fill: parent; anchors.margins: 6; source: appRoot.selectedPoseSource; fillMode: Image.PreserveAspectFit; asynchronous: true }
                                    }
                                    Text { Layout.fillWidth: true; text: appRoot.selectedPoseName; color: appRoot.brightGold; font.pixelSize: 13; font.bold: true; wrapMode: Text.Wrap }
                                    Text { Layout.fillWidth: true; text: appRoot.selectedPoseCategory; color: appRoot.textDim; font.pixelSize: 11 }
                                    Item { Layout.fillHeight: true }
                                    GButton { Layout.fillWidth: true; text: "Use Pose in Create"; active: true; onClicked: { if (appRoot.selectedPosePrompt.length) appRoot.generationPrompt = appRoot.selectedPosePrompt; appRoot.pageIndex = 0 } }
                                }
                            }
                            GridView {
                                id: poseGrid
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                cellWidth: Math.max(175, width / 4)
                                cellHeight: 220
                                model: appRoot.filteredPoses()
                                delegate: Rectangle {
                                    width: poseGrid.cellWidth - 9
                                    height: poseGrid.cellHeight - 9
                                    radius: 10
                                    color: "#0a1118"
                                    border.color: appRoot.selectedPoseName === String(modelData.name || "") ? appRoot.gold : appRoot.line
                                    border.width: appRoot.selectedPoseName === String(modelData.name || "") ? 2 : 1
                                    Image { anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: caption.top; anchors.margins: 6; source: modelData.source; fillMode: Image.PreserveAspectFit; asynchronous: true }
                                    Rectangle {
                                        id: caption
                                        anchors.left: parent.left
                                        anchors.right: parent.right
                                        anchors.bottom: parent.bottom
                                        height: 48
                                        color: "#e6101821"
                                        Column {
                                            anchors.fill: parent
                                            anchors.margins: 6
                                            Text { width: parent.width; text: modelData.name || "Pose"; color: appRoot.textMain; font.pixelSize: 11; font.bold: true; elide: Text.ElideRight }
                                            Text { width: parent.width; text: modelData.category || ""; color: appRoot.gold; font.pixelSize: 9; elide: Text.ElideRight }
                                        }
                                    }
                                    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: appRoot.applyPose(modelData) }
                                }
                                ScrollBar.vertical: ScrollBar { }
                            }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 10
                        PageHeader { titleText: "Workflow Studio"; subtitleText: "Validated generation workflows without manual node wiring."; iconText: "◇" }
                        GridLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            columns: 2
                            rowSpacing: 10
                            columnSpacing: 10
                            Repeater {
                                model: [
                                    {title:"Stage 1 · Phr00t / Qwen", body:"Source-aware pose and identity generation. Best choice when you load a source image."},
                                    {title:"Stage 2 · Lustify SDXL", body:"Optional refinement pass using the preserved Stage 1 output."},
                                    {title:"Stage 3 · ReActor", body:"Optional identity/face restoration from the original source image."},
                                    {title:"Final Upscale", body:"Optional finishing pass when the required local assets are available."}
                                ]
                                Panel {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    ColumnLayout { anchors.fill: parent; anchors.margins: 18; Text { text: modelData.title; color: appRoot.brightGold; font.pixelSize: 20; font.bold: true } Text { Layout.fillWidth: true; text: modelData.body; color: appRoot.textDim; font.pixelSize: 13; wrapMode: Text.Wrap } Item { Layout.fillHeight: true } GButton { text: "Open workflow folder"; onClicked: moduleBridge.triggerAction("workflow") } }
                                }
                            }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 10
                        PageHeader { titleText: "Media Tools"; subtitleText: mediaBridge.status; iconText: "✦" }
                        RowLayout {
                            Layout.fillWidth: true
                            GButton { text: "Open saved result"; enabled: !mediaBridge.busy && mediaBridge.resultUrl.length > 0; onClicked: Qt.openUrlExternally(mediaBridge.resultUrl) }
                            Text { Layout.fillWidth: true; text: mediaBridge.resultUrl; color: appRoot.textDim; elide: Text.ElideMiddle }
                            BusyIndicator { running: mediaBridge.busy; visible: running; Layout.preferredWidth: 32; Layout.preferredHeight: 32 }
                        }
                        ScrollView {
                            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                            id: mediaScroll
                            contentWidth: availableWidth
                        GridLayout {
                            width: mediaScroll.availableWidth; columns: 3; rowSpacing: 10; columnSpacing: 10
                            Repeater {
                                model: [
                                    {title:"Background Remover", body:"Create transparent cut-outs and reusable assets.", action:"background remover", icon:"✂", status:"GPU / LOCAL"},
                                    {title:"Enhance", body:"Restore detail and prepare images for finishing.", action:"enhance", icon:"✦", status:"AI TOOL"},
                                    {title:"Upscale", body:"Increase resolution with the local image stack.", action:"upscale", icon:"⇧", status:"GPU / LOCAL"},
                                    {title:"Extract MP3", body:"Extract an MP3 audio track from a video or audio file.", action:"extract audio", icon:"♫", status:"FFMPEG"},
                                    {title:"Silent Video", body:"Create a video-only copy with its audio track removed.", action:"extract video", icon:"▷", status:"FFMPEG"},
                                    {title:"Media Viewer", body:"Browse, preview and inspect your local images and metadata.", action:"media viewer", icon:"▧", status:"LIBRARY"},
                                    {title:"Canvas", body:"Prompt-based image editing. Layer and cutout tools are not yet implemented.", action:"canvas", icon:"Ps", status:"IN DEVELOPMENT"}
                                ]
                                MediaCard { titleText:modelData.title; bodyText:modelData.body; actionKey:modelData.action; iconText:modelData.icon; statusText:modelData.status }
                            }
                        }
                        }
                    }
                }

                Item {
                    ColumnLayout {
                        anchors.fill: parent; spacing: 10
                        PageHeader { titleText: "Photo Library"; subtitleText: "View, organise, find duplicates and group faces."; iconText: "▧" }
                        GridLayout { Layout.fillWidth: true; Layout.fillHeight: true; columns: 3; rowSpacing: 10; columnSpacing: 10
                            Repeater { model: [
                                {title:"Media Viewer", body:"Thumbnail library, large preview and image metadata.", action:"media viewer", icon:"▧", status:"BROWSE"},
                                {title:"Duplicate Finder", body:"Review exact and near duplicates side-by-side before moving copies to Trash.", action:"duplicate finder", icon:"◫", status:"SAFE REVIEW"},
                                {title:"Face Organiser", body:"People workspace for face grouping and photo organisation.", action:"face organiser", icon:"◎", status:"PEOPLE"}
                            ]
                            MediaCard { titleText:modelData.title; bodyText:modelData.body; actionKey:modelData.action; iconText:modelData.icon; statusText:modelData.status } }
                        }
                    }
                }

                Item {
                    ColumnLayout { anchors.fill: parent; spacing: 10
                        PageHeader { titleText: "Camera Hub"; subtitleText: "Local cameras and recordings in their own workspace."; iconText: "●" }
                        Panel { Layout.fillWidth: true; Layout.fillHeight: true; ColumnLayout { anchors.centerIn: parent; spacing: 12; Text { text:"CAMERA HUB"; color: appRoot.brightGold; font.pixelSize: 38; font.bold: true } Text { text:"Open the local camera service and live grid."; color: appRoot.textDim; font.pixelSize: 14 } GButton { text:"Open Camera Hub"; active:true; Layout.preferredWidth:220; onClicked: moduleBridge.triggerAction("camera hub") } } }
                    }
                }

                Item {
                    ColumnLayout { anchors.fill: parent; spacing: 10
                        PageHeader { titleText: "Entertainment"; subtitleText: "Jellyfin and SillyTavern together, separate from creative tools."; iconText: "▷" }
                        RowLayout { Layout.fillWidth: true; Layout.fillHeight: true; spacing:10
                            Panel { Layout.fillWidth:true; Layout.fillHeight:true; ColumnLayout { anchors.centerIn: parent; spacing:12; Text { text:"JELLYFIN"; color:appRoot.brightGold; font.pixelSize:24; font.bold:true } GButton { text:"Open Jellyfin"; Layout.preferredWidth:200; onClicked:moduleBridge.triggerAction("movie library") } } }
                            Panel { Layout.fillWidth:true; Layout.fillHeight:true; ColumnLayout { anchors.centerIn: parent; spacing:12; Text { text:"SILLYTAVERN"; color:appRoot.brightGold; font.pixelSize:24; font.bold:true } GButton { text:"Open SillyTavern"; Layout.preferredWidth:200; onClicked:moduleBridge.triggerAction("web app") } } }
                        }
                    }
                }

                Item {
                    ColumnLayout { anchors.fill: parent; spacing:10
                        PageHeader { titleText:"System Tools"; subtitleText:"GPU, ComfyUI, storage and recovery."; iconText:"⚙" }
                        GridLayout { Layout.fillWidth:true; Layout.fillHeight:true; columns:2; rowSpacing:10; columnSpacing:10
                            Repeater { model:[
                                {title:"ComfyUI", body:runtimeStatus.comfyOnline ? "Online and ready" : "Offline — start or inspect service", action:"comfyui"},
                                {title:"System Monitor", body:"Inspect GPU, memory and running processes.", action:"monitor"},
                                {title:"Models & Storage", body:"Open your AI model/storage location.", action:"models and storage"},
                                {title:"Backups & Recovery", body:"Open GENESIS recovery resources.", action:"backup recovery"}
                            ]
                            Panel { Layout.fillWidth:true; Layout.fillHeight:true; ColumnLayout { anchors.fill:parent; anchors.margins:18; Text { text:modelData.title; color:appRoot.brightGold; font.pixelSize:19; font.bold:true } Text { Layout.fillWidth:true; text:modelData.body; color:appRoot.textDim; wrapMode:Text.Wrap } Item { Layout.fillHeight:true } GButton { Layout.fillWidth:true; text:"Open"; onClicked:moduleBridge.triggerAction(modelData.action) } } } }
                        }
                    }
                }

                Item {
                    ColumnLayout { anchors.fill: parent; spacing:10
                        PageHeader { titleText:"Canvas / Edit"; subtitleText:"Send generated images here for local editing and finishing."; iconText:"Ps" }
                        RowLayout { Layout.fillWidth:true; Layout.fillHeight:true; spacing:10
                            Panel { Layout.preferredWidth:340; Layout.fillHeight:true; ColumnLayout { anchors.fill:parent; anchors.margins:12; spacing:8; SectionLabel { text:"SOURCE" } Rectangle { Layout.fillWidth:true; Layout.preferredHeight:260; color:"#080d12"; radius:8; border.color:appRoot.line; Image { anchors.fill:parent; anchors.margins:6; source:appRoot.editSource; fillMode:Image.PreserveAspectFit } } GButton { Layout.fillWidth:true; text:"Load Image"; onClicked:appRoot.chooseEditSource() } SectionLabel { text:"EDIT INSTRUCTIONS" } TextArea { Layout.fillWidth:true; Layout.fillHeight:true; text:appRoot.editPrompt; color:appRoot.textMain; placeholderText:"Describe the edit…"; onTextChanged:if(activeFocus) appRoot.editPrompt=text; background:Rectangle{color:"#080d12"; border.color:appRoot.line; radius:8} } GButton { Layout.fillWidth:true; text:"Run Image Edit"; active:true; enabled:appRoot.editSource.toString().length>0 && appRoot.editPrompt.trim().length>0 && !genesisBridge.busy; onClicked:genesisBridge.queueEdit(appRoot.editSource.toString(), appRoot.editPrompt, appRoot.editStrength) } } }
                            Panel { Layout.fillWidth:true; Layout.fillHeight:true; Rectangle { anchors.fill:parent; anchors.margins:12; color:"#05080b"; radius:10; border.color:appRoot.line; Image { anchors.fill:parent; anchors.margins:8; source:genesisBridge.previewUrl; fillMode:Image.PreserveAspectFit } Text { anchors.centerIn:parent; visible:genesisBridge.previewUrl.length===0; text:"EDIT RESULT"; color:appRoot.textDim; font.pixelSize:18 } } }
                        }
                    }
                }

                Item {
                    ColumnLayout { anchors.fill:parent; spacing:10
                        PageHeader { titleText:"Pose Maker"; subtitleText:"Build a prompt from the preset packs, then send it to Create."; iconText:"♜" }
                        RowLayout { Layout.fillWidth:true; Layout.fillHeight:true; spacing:10
                            Panel { Layout.preferredWidth:360; Layout.fillHeight:true; ColumnLayout { anchors.fill:parent; anchors.margins:12; spacing:8; SectionLabel { text:"PRESETS" } TextField { Layout.fillWidth:true; placeholderText:"Search presets…"; color:appRoot.textMain; onTextChanged:appRoot.presetSearch=text; background:Rectangle{color:"#080d12"; border.color:appRoot.line; radius:8} } ListView { Layout.fillWidth:true; Layout.fillHeight:true; clip:true; spacing:5; model:appRoot.filteredPresets(); delegate:GButton { width:ListView.view.width; text:modelData.label || modelData.name || "Preset"; active:appRoot.selectedPresetName===text; onClicked:appRoot.applyPreset(modelData) } } } }
                            Panel { Layout.fillWidth:true; Layout.fillHeight:true; ColumnLayout { anchors.fill:parent; anchors.margins:16; spacing:10; SectionLabel { text:"ACTIVE PRESET" } Text { Layout.fillWidth:true; text:appRoot.selectedPresetName; color:appRoot.brightGold; font.pixelSize:22; font.bold:true; wrapMode:Text.Wrap } TextArea { Layout.fillWidth:true; Layout.fillHeight:true; text:appRoot.generationPrompt; color:appRoot.textMain; wrapMode:TextEdit.Wrap; onTextChanged:if(activeFocus) appRoot.generationPrompt=text; background:Rectangle{color:"#080d12"; border.color:appRoot.line; radius:8} } GButton { Layout.fillWidth:true; text:"Use in Image Generation"; active:true; onClicked:appRoot.pageIndex=0 } } }
                        }
                    }
                }

                Item {
                    ColumnLayout { anchors.fill:parent; spacing:10
                        PageHeader { titleText:"Settings"; subtitleText:"Local services and GENESIS workspace settings."; iconText:"☷" }
                        Panel { Layout.fillWidth:true; Layout.fillHeight:true; ColumnLayout { anchors.fill:parent; anchors.margins:20; spacing:12; Text { text:"GENESIS LINUX"; color:appRoot.brightGold; font.pixelSize:24; font.bold:true } Text { text:"Backend status: " + moduleBridge.status; color:appRoot.textDim; font.pixelSize:13; wrapMode:Text.Wrap; Layout.fillWidth:true } RowLayout { GButton { text:"Refresh Health"; onClicked:moduleBridge.triggerAction("refresh") } GButton { text:"Open Settings Folder"; onClicked:moduleBridge.triggerAction("settings") } } Item { Layout.fillHeight:true } Text { text:"The source image, selected preset/pose and prompt are preserved while you move between Create and Pose Library."; color:appRoot.textDim; font.pixelSize:12; wrapMode:Text.Wrap; Layout.fillWidth:true } } }
                    }
                }
            }
        }
    }
}
