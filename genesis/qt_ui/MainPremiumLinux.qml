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
    color: "#080808"
    font.family: "Noto Sans"

    readonly property color gold: "#d2a34e"
    readonly property color brightGold: "#f3d28b"
    readonly property color blue: "#bc9458"
    readonly property color blueBright: "#e0bc7c"
    readonly property color blueDeep: "#302719"
    readonly property color bg: "#080808"
    readonly property color panel: "#101010"
    readonly property color raised: "#171717"
    readonly property color raised2: "#202020"
    readonly property color line: "#343434"
    readonly property color textMain: "#eef3f6"
    readonly property color textDim: "#aaa7a1"
    readonly property color success: "#62d27a"

    onClosing: function(close) { close.accepted = canvasBridge.confirmClose() }

    property int pageIndex: 0
    property bool feefeeOpen: false
    property int lastWorkspacePage: 0
    onPageIndexChanged: if (pageIndex !== 11) lastWorkspacePage = pageIndex
    palette.window: "#101010"
    palette.base: "#161616"
    palette.button: "#202020"
    palette.text: "#e9e6df"
    palette.buttonText: "#e9e6df"
    palette.windowText: "#e9e6df"
    palette.highlight: "#79603b"
    palette.highlightedText: "#fff3d8"
    palette.placeholderText: "#969087"
    property bool privacyMode: false
    readonly property bool compactNavigation: height < 850
    property var navItems: [
        {icon:"▣", label:"Image Generation", page:0},
        {icon:"✦", label:"Media Tools", page:3},
        {icon:"●", label:"Camera Hub", page:5},
        {icon:"⚙", label:"System Tools", page:7},
        {icon:"☷", label:"Settings", page:10}
    ]

    // Primary navigation shortcuts mirror the visible sidebar. Internal generation tabs
    // intentionally have no global number shortcuts.
    Shortcut { sequence: "Alt+1"; onActivated: appRoot.pageIndex = 0 }
    Shortcut { sequence: "Alt+2"; onActivated: appRoot.pageIndex = 3 }
    Shortcut { sequence: "Alt+3"; onActivated: appRoot.pageIndex = 5 }
    Shortcut { sequence: "Alt+4"; onActivated: appRoot.pageIndex = 7 }
    Shortcut { sequence: "Alt+,"; onActivated: appRoot.pageIndex = 10 }

    property var generationModel: typeof generationProfiles !== "undefined" ? generationProfiles : []
    property int selectedGenerationIndex: 0
    property bool modelDefaultsApplied: false
    property string selectedModelName: ""
    onGenerationModelChanged: {
        if (generationModel.length) {
            var index = 0
            for (var i = 0; i < generationModel.length; ++i)
                if (generationModel[i].model === selectedModelName) { index = i; break }
            selectedGenerationIndex = index
            if (!modelDefaultsApplied || generationModel[index].model !== selectedModelName) {
                selectGeneration(index)
                modelDefaultsApplied = true
            }
        }
    }
    Component.onCompleted: if (generationModel.length) { selectGeneration(0); modelDefaultsApplied = true }
    readonly property var selectedGenerationProfile: generationModel.length
        ? generationModel[Math.min(selectedGenerationIndex, generationModel.length - 1)]
        : ({label:"No model available", model:"", note:"Waiting for the backend model catalog", loras:["None"], runnable:false, sourceRequired:false})
    property string selectedLora: "None"
    property string selectedLoraTwo: "None"
    property string selectedLoraThree: "None"
    property real selectedLoraStrength: 0.65
    property real selectedLoraTwoStrength: 0.65
    property real selectedLoraThreeStrength: 0.65
    property url generationSource: ""
    property url faceSwapTarget: ""
    property url faceSwapSource: ""
    property string generationPrompt: ""
    property string generationNegativePrompt: ""
    property int generationWidth: 768
    property int generationHeight: 1152
    property int generationSteps: 6
    property real generationCfg: 1.0
    property int generationSeed: -1
    property real generationDenoise: 1.0
    property string generationSampler: "er_sde"
    property string generationScheduler: "beta"
    property bool useStageTwo: false
    property bool useStageThree: false
    property bool useUpscale: false

    property var poseModel: typeof poseItems !== "undefined" ? poseItems : []
    property var easyPresetModel: typeof curatedPosePresets !== "undefined" ? curatedPosePresets : []
    property url selectedPoseSource: poseModel.length ? poseModel[0].source : ""
    property url selectedPoseThumbnail: poseModel.length ? (poseModel[0].thumbnail || poseModel[0].source) : ""
    property string selectedPoseName: poseModel.length ? poseModel[0].name : "No pose selected"
    property string selectedPoseCategory: poseModel.length ? poseModel[0].category : ""
    property string selectedPosePrompt: poseModel.length ? poseModel[0].prompt : ""
    property string selectedPresetName: "No preset selected"
    property string presetSearch: ""
    property string presetCategory: "All"
    property string poseSearch: ""
    property string poseCategory: "All"

    property url viewerSource: ""
    property url editSource: ""
    property url editMask: ""
    property string editPrompt: ""
    property real editStrength: 0.40

    property bool mediaToolOpen: false
    property string mediaToolKey: ""
    property string mediaToolTitle: "Media Tool"
    property string mediaToolDescription: ""
    property string mediaToolStatus: ""

    function openMediaTool(key, title, description, status) {
        mediaToolKey = key
        mediaToolTitle = title
        mediaToolDescription = description
        mediaToolStatus = status
        mediaBridge.clearInput()
        mediaToolOpen = true
    }

    function closeMediaTool() {
        mediaToolOpen = false
    }

    function mediaToolRunLabel() {
        if (mediaToolKey === "batch background") return "RUN BATCH"
        if (mediaToolKey === "batch upscale") return "RUN BATCH"
        if (mediaToolKey === "duplicate finder") return "SCAN LIBRARY"
        if (mediaToolKey === "face organiser") return "GROUP FACES"
        if (mediaToolKey === "extract audio") return "EXTRACT MP3"
        if (mediaToolKey === "extract video") return "EXTRACT VIDEO"
        if (mediaToolKey === "standard resize") return "RESIZE 2×"
        if (mediaToolKey === "upscale") return "UPSCALE 2×"
        return "REMOVE BACKGROUND"
    }

    function mediaToolInputHint() {
        if (mediaToolKey === "batch background" || mediaToolKey === "batch upscale")
            return "Select multiple images, then choose the destination folder."
        if (mediaToolKey === "duplicate finder")
            return "Select an image library folder. GENESIS will prepare safe review pairs before anything can be moved to Trash."
        if (mediaToolKey === "face organiser")
            return "Select a photo library folder. GENESIS will group detected faces for review."
        if (mediaToolKey === "extract audio")
            return "Select a video or audio file. GENESIS will create a separate MP3 and keep the source unchanged."
        if (mediaToolKey === "extract video")
            return "Select a video file. GENESIS will create a separate MP4 while preserving the source."
        if (mediaToolKey === "standard resize")
            return "Select one image for a local CPU 2× resize. Transparency is preserved."
        if (mediaToolKey === "upscale")
            return "Select one image for AI 2× upscale through the currently selected backend."
        return "Select one image. The source file is preserved."
    }

    function mediaToolHasVisualResult() {
        return mediaToolKey === "background remover"
            || mediaToolKey === "upscale"
            || mediaToolKey === "standard resize"
    }

    function mediaToolIsReview() {
        return mediaToolKey === "duplicate finder" || mediaToolKey === "face organiser"
    }

    function chooseMediaToolInput() {
        mediaBridge.chooseToolInput(mediaToolKey)
    }

    function runMediaTool() {
        mediaBridge.runSelectedTool(mediaToolKey)
    }

    function selectedLoraTriggerText() {
        var profile = selectedGenerationProfile
        var triggerMap = profile && profile.triggers ? profile.triggers : ({})
        var selected = [selectedLora, selectedLoraTwo, selectedLoraThree]
        var output = []
        for (var i = 0; i < selected.length; ++i) {
            var name = selected[i]
            if (!name || name === "None") continue
            var words = triggerMap[name]
            if (words && words.length)
                output.push(name + ": " + words.join(", "))
        }
        return output.join("  ·  ")
    }

    function chooseSource() {
        var chosen = genesisBridge.chooseSourceImage()
        if (chosen.length) generationSource = chosen
    }

    function chooseFaceSwapTarget() {
        var chosen = genesisBridge.chooseSourceImage()
        if (chosen.length) faceSwapTarget = chosen
    }

    function chooseFaceSwapSource() {
        var chosen = genesisBridge.chooseSourceImage()
        if (chosen.length) faceSwapSource = chosen
    }

    function runFaceSwap() {
        genesisBridge.queueFaceSwap(faceSwapTarget.toString(), faceSwapSource.toString())
    }

    function chooseEditSource() {
        var chosen = genesisBridge.chooseSourceImage()
        if (chosen.length) editSource = chosen
    }

    function selectGeneration(index) {
        if (generationModel[index]) selectedModelName = generationModel[index].model
        selectedGenerationIndex = index
        selectedLora = "None"
        selectedLoraTwo = "None"
        selectedLoraThree = "None"
        selectedLoraStrength = 0.65
        selectedLoraTwoStrength = 0.65
        selectedLoraThreeStrength = 0.65

        var profile = selectedGenerationProfile
        if (!profile) return
        if (profile.defaultWidth !== undefined) generationWidth = profile.defaultWidth
        if (profile.defaultHeight !== undefined) generationHeight = profile.defaultHeight
        if (profile.defaultSteps !== undefined) generationSteps = profile.defaultSteps
        if (profile.defaultCfg !== undefined) generationCfg = profile.defaultCfg
        if (profile.defaultDenoise !== undefined) generationDenoise = profile.defaultDenoise
        if (profile.defaultSampler !== undefined) generationSampler = profile.defaultSampler
        if (profile.defaultScheduler !== undefined) generationScheduler = profile.defaultScheduler
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
        selectedPoseThumbnail = row.thumbnail || row.source || ""
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
        genesisBridge.queueGenerateAdvanced(
            prompt,
            generationNegativePrompt,
            generationWidth,
            generationHeight,
            selectedGenerationProfile.model,
            selectedLora,
            selectedLoraTwo,
            generationSource.toString(),
            selectedPoseSource.toString(),
            useStageTwo,
            useStageThree,
            useUpscale,
            generationSteps,
            generationCfg,
            generationSeed,
            generationDenoise,
            generationSampler,
            generationScheduler,
            selectedLoraThree,
            selectedLoraStrength,
            selectedLoraTwoStrength,
            selectedLoraThreeStrength
        )
    }

    component Panel: Rectangle {
        color: appRoot.panel
        radius: 12
        border.color: appRoot.line
        border.width: 1
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: "#191919" }
            GradientStop { position: 0.11; color: "#151515" }
            GradientStop { position: 1.0; color: "#101010" }
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
        implicitHeight: 36
        implicitWidth: Math.max(58, contentItem.implicitWidth + 22)
        Layout.maximumWidth: 16777215
        activeFocusOnTab: true
        Accessible.name: text
        Accessible.role: Accessible.Button
        ToolTip.visible: hovered && text.length > 16
        ToolTip.text: text
        ToolTip.delay: 700
        font.pixelSize: 13
        font.weight: active || premium ? Font.Bold : Font.DemiBold
        contentItem: Text {
            text: button.text
            color: !button.enabled ? "#6f6758" : (button.premium || button.active ? "#fff7d0" : (button.hovered ? "#fff1b0" : appRoot.textMain))
            font: button.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            transform: Translate { y: button.down ? 2 : 0 }
        }
        background: Item {
            // Deep lower lip gives the control its chunky machined 3D profile.
            Rectangle {
                anchors.left: parent.left; anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: parent.height - 3
                radius: 13
                color: !button.enabled ? "#29251f" : "#6f4510"
                border.color: "#171009"
                border.width: 1
            }
            Rectangle {
                anchors.left: parent.left; anchors.right: parent.right
                y: button.down ? 3 : 0
                height: parent.height - 5
                radius: 13
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    GradientStop { position: 0.00; color: !button.enabled ? "#4a463f" : (button.hovered ? "#fff09a" : "#e8c65c") }
                    GradientStop { position: 0.16; color: !button.enabled ? "#3a3732" : "#b57a18" }
                    GradientStop { position: 0.50; color: !button.enabled ? "#292825" : (button.premium || button.active ? "#6c4615" : "#49371f") }
                    GradientStop { position: 0.84; color: !button.enabled ? "#242321" : "#8d5b12" }
                    GradientStop { position: 1.00; color: !button.enabled ? "#35322d" : "#d7a932" }
                }
                border.color: !button.enabled ? "#59534a" : (button.hovered ? "#fff1a0" : appRoot.gold)
                border.width: button.activeFocus || button.hovered || button.active || button.premium ? 2 : 1
                // Recessed centre panel, inspired by the rounded metallic reference.
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 5
                    radius: 9
                    gradient: Gradient {
                        orientation: Gradient.Vertical
                        GradientStop { position: 0.0; color: !button.enabled ? "#32302c" : (button.premium || button.active ? "#8b5a16" : "#4a3a25") }
                        GradientStop { position: 0.55; color: !button.enabled ? "#292825" : (button.premium || button.active ? "#5b3b13" : "#292823") }
                        GradientStop { position: 1.0; color: !button.enabled ? "#262522" : "#201b13" }
                    }
                    border.color: !button.enabled ? "#45413b" : "#f2c84b"
                    border.width: 1
                }
                // Fine top highlight sells the polished metal edge without neon/glass styling.
                Rectangle {
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    anchors.leftMargin: 12; anchors.rightMargin: 12; anchors.topMargin: 2
                    height: 1
                    radius: 1
                    color: button.enabled ? "#fff3ad" : "#625d54"
                    opacity: button.down ? 0.35 : 0.9
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
            font.pixelSize: appRoot.width < 1300 ? 12 : 14
            font.weight: nav.active ? Font.DemiBold : Font.Normal
            horizontalAlignment: Text.AlignLeft
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle {
            radius: 8
            color: nav.active ? "#302719" : (nav.hovered ? "#1c1a17" : "transparent")
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
        Layout.minimumHeight: 190
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 11
            spacing: 7
            RowLayout {
                Layout.fillWidth: true
                Text { text: mediaCard.iconText; color: appRoot.gold; font.pixelSize: 18; font.bold: true }
                Text { Layout.fillWidth: true; text: mediaCard.titleText; color: appRoot.brightGold; font.family: "Noto Sans Display"; font.pixelSize: 16; font.bold: true; elide: Text.ElideRight }
                Rectangle {
                    radius: 10; height: 22; width: statusLabel.implicitWidth + 18
                    color: "#241c11"; border.color: appRoot.gold
                    Text { id: statusLabel; anchors.centerIn: parent; text: mediaCard.statusText; color: appRoot.brightGold; font.pixelSize: 9; font.bold: true; font.letterSpacing: 0.7 }
                }
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 72
                radius: 10
                color: "#11100e"
                border.color: "#40372a"
                border.width: 1
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    GradientStop { position: 0.0; color: "#211d17" }
                    GradientStop { position: 1.0; color: "#11100e" }
                }
                Rectangle { anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; height: 2; color: appRoot.gold; opacity: 0.7 }
                Text { anchors.centerIn: parent; text: mediaCard.iconText; color: "#55f3d28b"; font.pixelSize: 58; font.bold: true }
                Text { anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 10; text: "GENESIS · " + mediaCard.titleText.toUpperCase(); color: appRoot.textDim; font.pixelSize: 9; font.bold: true; font.letterSpacing: 0.8 }
            }
            Text { Layout.fillWidth: true; text: mediaCard.bodyText; color: appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight }
            GButton {
                Layout.fillWidth: true
                text: mediaBridge.busy ? "WORKING…" : "OPEN  " + mediaCard.titleText.toUpperCase()
                active: !mediaBridge.busy
                enabled: !mediaBridge.busy
                onClicked: {
                    if (mediaCard.actionKey === "face swap")
                        appRoot.pageIndex = 12
                    else if (mediaCard.actionKey === "media viewer")
                        appRoot.pageIndex = 4
                    else if (mediaCard.actionKey === "canvas")
                        appRoot.pageIndex = 8
                    else
                        appRoot.openMediaTool(mediaCard.actionKey, mediaCard.titleText, mediaCard.bodyText, mediaCard.statusText)
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

    Item {
        id: genesisScene
        objectName: "genesisScene"
        anchors.fill: parent
    Rectangle {
        anchors.fill: parent
        z: -10
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0; color: "#101010" }
            GradientStop { position: 0.40; color: appRoot.bg }
            GradientStop { position: 1; color: "#080808" }
        }
        Image {
            anchors.fill: parent
            source: "../assets/lunacy_banner/cockpit_background_soft.jpg"
            fillMode: Image.PreserveAspectCrop
            opacity: 0.10
        }
    }

    ColumnLayout {
        objectName: "genesisMainWorkspace"
        anchors.fill: parent
        anchors.margins: 10
        spacing: 8

        Panel {
            Layout.fillWidth: true
            Layout.preferredHeight: appRoot.compactNavigation ? 112 : 146
            clip: true

            Image {
                anchors.fill: parent
                source: "../assets/lunacy_banner/genesis-cockpit-banner-lunacy-final.png"
                fillMode: Image.PreserveAspectCrop
                verticalAlignment: Image.AlignTop
                opacity: 0.42
                visible: !privacyMode
            }
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
                    width: Math.min(parent.width - 420, appRoot.compactNavigation ? 820 : 1080)
                    height: parent.height - 8
                    source: "../assets/lunacy_banner/genesis_cockpit_wordmark_full.png"
                    sourceClipRect: Qt.rect(0, 28, 945, 317)
                    fillMode: Image.Stretch
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
                        color: "#161616"
                        border.color: runtimeStatus.comfyOnline ? appRoot.success : appRoot.gold
                        Text {
                            anchors.centerIn: parent
                            text: runtimeStatus.routingSummary || (runtimeStatus.remote
                                ? (runtimeStatus.comfyOnline ? "●  RUNPOD ONLINE" : "○  RUNPOD OFFLINE")
                                : (runtimeStatus.comfyOnline ? "●  COMFYUI ONLINE" : "○  COMFYUI OFFLINE"))
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
            spacing: 8

            Panel {
                Layout.preferredWidth: appRoot.width < 1300 ? 165 : 205
                Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 5
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: appRoot.compactNavigation ? 82 : 160
                        radius: 14
                        color: appRoot.panel
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
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            GButton { Layout.preferredWidth: implicitWidth; text: "⌂  Create"; active: true; onClicked: appRoot.pageIndex = 0 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Pose Library"; onClicked: appRoot.pageIndex = 1 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Workflow"; onClicked: appRoot.pageIndex = 2 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Pose Maker"; onClicked: appRoot.pageIndex = 9 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Canvas"; onClicked: appRoot.pageIndex = 8 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Results"; onClicked: { appRoot.viewerSource = genesisBridge.previewUrl; appRoot.pageIndex = 4 } }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 8

                            Panel {
                                Layout.preferredWidth: appRoot.width < 1300 ? 210 : 260
                                Layout.minimumWidth: appRoot.width < 1300 ? 210 : 240
                                Layout.maximumWidth: 280
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8
                                    RowLayout {
                                        Layout.fillWidth: true
                                        SectionLabel { text: "1 · SOURCE IMAGE" }
                                        Item { Layout.fillWidth: true }
                                        Text { text: appRoot.generationSource.toString().length ? "LOADED" : "SOURCE"; color: appRoot.generationSource.toString().length ? appRoot.success : appRoot.textDim; font.pixelSize: 9; font.bold: true }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 150
                                        Layout.minimumHeight: 132
                                        radius: 10
                                        color: "#0d0d0d"
                                        border.color: appRoot.generationSource.toString().length > 0 ? appRoot.gold : appRoot.line
                                        border.width: appRoot.generationSource.toString().length > 0 ? 1.5 : 1
                                        Image { anchors.fill: parent; anchors.margins: 7; source: appRoot.generationSource; fillMode: Image.PreserveAspectFit; visible: !privacyMode }
                                        Column {
                                            anchors.centerIn: parent
                                            visible: appRoot.generationSource.toString().length === 0
                                            spacing: 6
                                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "+"; color: appRoot.gold; font.pixelSize: 34 }
                                            Text { text: "LOAD SOURCE IMAGE"; color: appRoot.textMain; font.pixelSize: 12; font.bold: true }
                                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "PNG · JPG · WEBP"; color: appRoot.textDim; font.pixelSize: 10 }
                                        }
                                        Text { anchors.centerIn: parent; text: "PRIVATE"; color: appRoot.gold; font.pixelSize: 18; visible: privacyMode && appRoot.generationSource.toString().length > 0 }
                                        DropArea { anchors.fill: parent; onDropped: function(drop) { if (drop.urls.length) appRoot.generationSource = drop.urls[0] } }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        GButton { Layout.preferredWidth: implicitWidth; text: appRoot.width < 1300 ? "Load image" : "Load Source Image"; active: appRoot.generationSource.toString().length === 0; onClicked: appRoot.chooseSource() }
                                        GButton { Layout.preferredWidth: 60; text: "Clear"; enabled: appRoot.generationSource.toString().length > 0; onClicked: appRoot.generationSource = "" }
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
                                        background: Rectangle { color: "#191919"; border.color: appRoot.line; radius: 8 }
                                    }
                                    GridView {
                                        id: quickPresetGrid
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        Layout.minimumHeight: 190
                                        clip: true
                                        // Keep names legible on compact displays.
                                        cellWidth: Math.floor(width / (appRoot.width < 1300 ? 2 : 3))
                                        cellHeight: 68
                                        model: appRoot.filteredPresets()
                                        delegate: Rectangle {
                                            width: quickPresetGrid.cellWidth - 7
                                            height: quickPresetGrid.cellHeight - 7
                                            radius: 9
                                            color: appRoot.selectedPresetName === String(modelData.label || modelData.name || "") ? "#30291c" : "#121212"
                                            border.color: appRoot.selectedPresetName === String(modelData.label || modelData.name || "") ? appRoot.gold : appRoot.line
                                            Column {
                                                anchors.fill: parent
                                                anchors.margins: 7
                                                spacing: 2
                                                Text { width: parent.width; text: modelData.label || modelData.name || "Preset"; color: appRoot.textMain; font.pixelSize: 10; font.bold: true; elide: Text.ElideRight }
                                                Text { width: parent.width; text: (modelData.collection || "Preset") + " · " + (modelData.category || "General"); color: appRoot.gold; font.pixelSize: 8; elide: Text.ElideRight }
                                                Text { width: parent.width; text: modelData.prompt || ""; color: appRoot.textDim; font.pixelSize: 8; maximumLineCount: 1; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                                            }
                                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: appRoot.applyPreset(modelData) }
                                        }
                                        ScrollBar.vertical: ScrollBar { }
                                    }
                                }
                            }

                            Panel {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 60
                                        Layout.minimumHeight: 60
                                        Layout.maximumHeight: 60
                                        objectName: "generationStageStrip"
                                        spacing: 6
                                        Repeater {
                                            model: [
                                                {title:"STAGE 1", name:"Phr00t / Qwen", enabled:true},
                                                {title:"STAGE 2", name:"Lustify SDXL", enabled:appRoot.useStageTwo},
                                                {title:"STAGE 3", name:"ReActor", enabled:appRoot.useStageThree}
                                            ]
                                            Rectangle {
                                                Layout.fillWidth: true
                                                Layout.fillHeight: true
                                                radius: 8
                                                color: modelData.enabled ? "#2b2922" : appRoot.raised
                                                border.color: modelData.enabled ? appRoot.gold : appRoot.line
                                                border.width: modelData.enabled ? 2 : 1
                                                Column {
                                                    anchors.centerIn: parent
                                                    spacing: 1
                                                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.title; color: modelData.enabled ? appRoot.brightGold : appRoot.textDim; font.pixelSize: 10; font.bold: true }
                                                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.name; color: appRoot.textMain; font.pixelSize: 10; font.bold: true }
                                                    Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.enabled ? "ACTIVE" : "OPTIONAL"; color: modelData.enabled ? appRoot.gold : appRoot.textDim; font.pixelSize: 8 }
                                                }
                                            }
                                        }
                                    }
                                    SectionLabel { text: "PROMPT" }
                                    TextArea {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        Layout.minimumHeight: 72
                                        text: appRoot.generationPrompt
                                        placeholderText: "Preset or pose fills this automatically — edit anything you want."
                                        color: appRoot.textMain
                                        wrapMode: TextEdit.Wrap
                                        onTextChanged: if (activeFocus) appRoot.generationPrompt = text
                                        background: Rectangle { color: "#191919"; border.color: appRoot.line; radius: 8 }
                                    }
                                    TextField {
                                        Layout.fillWidth: true
                                        text: appRoot.generationNegativePrompt
                                        placeholderText: "Negative prompt (optional)"
                                        color: appRoot.textMain
                                        onTextChanged: if (activeFocus) appRoot.generationNegativePrompt = text
                                        background: Rectangle { color: "#191919"; border.color: appRoot.line; radius: 8 }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text { text: "Preset: " + appRoot.selectedPresetName; color: appRoot.gold; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                        Text { text: "Pose: " + appRoot.selectedPoseName; color: appRoot.textDim; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight; horizontalAlignment: Text.AlignRight }
                                    }
                                    GButton {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 44
                                        active: enabled
                                        text: genesisBridge.busy ? "GENERATING…" : "GENERATE"
                                        enabled: !genesisBridge.busy
                                            && appRoot.selectedGenerationProfile.runnable
                                            && (appRoot.generationPrompt.trim().length > 0 || appRoot.selectedPosePrompt.trim().length > 0)
                                            && (!appRoot.selectedGenerationProfile.sourceRequired || appRoot.generationSource.toString().length > 0)
                                        onClicked: appRoot.generateCurrent()
                                    }
                                    ProgressBar {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 12
                                        from: 0
                                        to: 1
                                        value: genesisBridge.progress < 0 ? 0 : genesisBridge.progress
                                        indeterminate: genesisBridge.busy && genesisBridge.progress < 0
                                        visible: genesisBridge.busy || genesisBridge.progress >= 0 || genesisBridge.previewUrl.length > 0
                                    }
                                    Text { Layout.fillWidth: true; text: genesisBridge.status; color: genesisBridge.busy ? appRoot.gold : appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap }
                                    SectionLabel { text: "RESULT" }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: appRoot.height < 800 ? 110 : 168
                                        objectName: "generationResultPreview"
                                        Layout.minimumHeight: 100
                                        Layout.maximumHeight: 190
                                        radius: 10
                                        color: "#0d0d0d"
                                        border.color: genesisBridge.previewUrl.length > 0 ? appRoot.gold : appRoot.line
                                        border.width: genesisBridge.previewUrl.length > 0 ? 1.5 : 1
                                        Image {
                                            anchors.fill: parent
                                            anchors.margins: 7
                                            source: genesisBridge.previewUrl
                                            fillMode: Image.PreserveAspectFit
                                            smooth: true
                                            mipmap: true
                                            visible: !privacyMode && genesisBridge.previewUrl.length > 0
                                        }
                                        Text {
                                            anchors.centerIn: parent
                                            text: privacyMode ? "PRIVATE" : "GENERATED RESULT"
                                            color: appRoot.textDim
                                            font.pixelSize: 13
                                            visible: privacyMode || genesisBridge.previewUrl.length === 0
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            enabled: genesisBridge.previewUrl.length > 0 && !privacyMode
                                            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                            onClicked: genesisBridge.openPreview()
                                        }
                                        Row {
                                            anchors.right: parent.right
                                            anchors.bottom: parent.bottom
                                            anchors.margins: 7
                                            spacing: 6
                                            GButton { text: "Open Result"; enabled: genesisBridge.previewUrl.length > 0; onClicked: genesisBridge.openPreview() }
                                            GButton { text: "Output Folder"; onClicked: genesisBridge.openOutputFolder() }
                                        }
                                    }
                                    Text { Layout.fillWidth: true; text: "Output: " + genesisBridge.outputFolder; color: appRoot.textDim; font.pixelSize: 9; elide: Text.ElideMiddle }
                                    RowLayout {
                                    Layout.fillWidth: true
                                    GButton { Layout.preferredWidth: implicitWidth; text: "Output location"; onClicked: genesisBridge.chooseOutputFolder() }
                                    GButton { Layout.preferredWidth: implicitWidth; text: "Edit in Canvas"; enabled: genesisBridge.previewUrl.length > 0; onClicked: { appRoot.editSource = genesisBridge.previewUrl; appRoot.pageIndex = 8 } }
                                    }
                                }
                            }

                            Panel {
                                Layout.preferredWidth: appRoot.width < 1300 ? 280 : 360
                                Layout.minimumWidth: appRoot.width < 1300 ? 280 : 340
                                Layout.maximumWidth: 400
                                Layout.fillHeight: true
                                ScrollView {
                                    id: generationSettings
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    contentWidth: availableWidth
                                    clip: true
                                    rightPadding: 14
                                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                                    ScrollBar.vertical.policy: ScrollBar.AsNeeded
                                ColumnLayout {
                                    width: generationSettings.availableWidth
                                    spacing: 8
                                    SectionLabel { text: "3 · MODEL / WORKFLOW" }
                                    ComboBox {
                                        Layout.fillWidth: true
                                        model: ["AUTO", "LOCAL", "RUNPOD"]
                                        currentIndex: model.indexOf(backendBridge.mode)
                                        enabled: !genesisBridge.busy
                                        onActivated: backendBridge.setMode(currentText)
                                    }
                                    Text { Layout.fillWidth: true; text: backendBridge.message; color: appRoot.textDim; wrapMode: Text.Wrap; font.pixelSize: 11 }
                                    TextField {
                                        id: runpodEndpoint
                                        Layout.fillWidth: true
                                        text: backendBridge.endpoint
                                        placeholderText: "RunPod ComfyUI URL or pod ID"
                                        enabled: !genesisBridge.busy
                                        selectByMouse: true
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        GButton { text: "Save endpoint"; enabled: !genesisBridge.busy; onClicked: backendBridge.setEndpoint(runpodEndpoint.text) }
                                        GButton { text: backendBridge.checking ? "Checking…" : "Refresh"; enabled: !backendBridge.checking; onClicked: backendBridge.refresh() }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: "Destination: " + (appRoot.selectedGenerationProfile.destination || "UNAVAILABLE")
                                        color: appRoot.gold; font.pixelSize: 12; font.bold: true
                                    }
                                    ComboBox {
                                        Layout.fillWidth: true
                                        model: appRoot.generationModel
                                        textRole: "label"
                                        currentIndex: appRoot.selectedGenerationIndex
                                        onActivated: appRoot.selectGeneration(currentIndex)
                                    }
                                    Text { Layout.fillWidth: true; text: appRoot.selectedGenerationProfile.note || ""; color: appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap }
                                    SectionLabel { text: "COMPATIBLE LORA" }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        ComboBox {
                                            Layout.fillWidth: true
                                            model: appRoot.selectedGenerationProfile.loras || ["None"]
                                            currentIndex: Math.max(0, model.indexOf(appRoot.selectedLora))
                                            onActivated: appRoot.selectedLora = currentText
                                        }
                                        SpinBox {
                                            from: 0; to: 100; value: Math.round(appRoot.selectedLoraStrength * 100)
                                            editable: true
                                            enabled: appRoot.selectedLora !== "None"
                                            onValueModified: appRoot.selectedLoraStrength = value / 100.0
                                            textFromValue: function(value) { return (value / 100.0).toFixed(2) }
                                            valueFromText: function(text) { return Math.round(Number(text) * 100) }
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        visible: (appRoot.selectedGenerationProfile.maxLoras || 0) > 1
                                        ComboBox {
                                            Layout.fillWidth: true
                                            model: appRoot.selectedGenerationProfile.loras || ["None"]
                                            onActivated: appRoot.selectedLoraTwo = currentText
                                        }
                                        SpinBox {
                                            from: 0; to: 100; value: Math.round(appRoot.selectedLoraTwoStrength * 100)
                                            editable: true
                                            enabled: appRoot.selectedLoraTwo !== "None"
                                            onValueModified: appRoot.selectedLoraTwoStrength = value / 100.0
                                            textFromValue: function(value) { return (value / 100.0).toFixed(2) }
                                            valueFromText: function(text) { return Math.round(Number(text) * 100) }
                                        }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        visible: (appRoot.selectedGenerationProfile.maxLoras || 0) > 2
                                        ComboBox {
                                            Layout.fillWidth: true
                                            model: appRoot.selectedGenerationProfile.loras || ["None"]
                                            onActivated: appRoot.selectedLoraThree = currentText
                                        }
                                        SpinBox {
                                            from: 0; to: 100; value: Math.round(appRoot.selectedLoraThreeStrength * 100)
                                            editable: true
                                            enabled: appRoot.selectedLoraThree !== "None"
                                            onValueModified: appRoot.selectedLoraThreeStrength = value / 100.0
                                            textFromValue: function(value) { return (value / 100.0).toFixed(2) }
                                            valueFromText: function(text) { return Math.round(Number(text) * 100) }
                                        }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        visible: appRoot.selectedLora !== "None" || appRoot.selectedLoraTwo !== "None" || appRoot.selectedLoraThree !== "None"
                                        text: (appRoot.selectedGenerationProfile.experimentalLoras ? "EXPERIMENTAL · " : "")
                                            + "LoRAs run in picker order with independent strengths."
                                        color: appRoot.selectedGenerationProfile.experimentalLoras ? appRoot.gold : appRoot.textDim
                                        font.pixelSize: 10
                                        wrapMode: Text.Wrap
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        visible: appRoot.selectedLoraTriggerText().length > 0
                                        text: "LORA TRIGGER · " + appRoot.selectedLoraTriggerText()
                                        color: appRoot.brightGold
                                        font.pixelSize: 10
                                        wrapMode: Text.Wrap
                                    }
                                    SectionLabel { text: "QUALITY" }
                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: 3
                                        GButton { Layout.preferredWidth: implicitWidth; text: "Fast"; active: appRoot.generationWidth === 512; onClicked: { generationWidth = 512; generationHeight = 512 } }
                                        GButton { Layout.preferredWidth: implicitWidth; text: "Balanced"; active: appRoot.generationWidth === 768; onClicked: { generationWidth = 768; generationHeight = 1152 } }
                                        GButton { Layout.preferredWidth: implicitWidth; text: "Quality"; active: appRoot.generationWidth === 1024; onClicked: { generationWidth = 1024; generationHeight = 1024 } }
                                        GButton { Layout.preferredWidth: implicitWidth; text: "2K"; visible: !!appRoot.selectedGenerationProfile.remote; active: appRoot.generationWidth === 2048; onClicked: { generationWidth = 2048; generationHeight = 2048 } }
                                        GButton { Layout.preferredWidth: implicitWidth; text: "4K"; visible: !!appRoot.selectedGenerationProfile.remote; active: appRoot.generationWidth === 4096; onClicked: { generationWidth = 4096; generationHeight = 4096 } }
                                    }
                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: 2
                                        columnSpacing: 8
                                        rowSpacing: 5
                                        Text { text: "Width"; color: appRoot.textDim; font.pixelSize: 10 }
                                        SpinBox { Layout.fillWidth: true; from: 256; to: (!!appRoot.selectedGenerationProfile.remote ? 4096 : 1536); stepSize: 64; value: appRoot.generationWidth; editable: true; onValueModified: appRoot.generationWidth = value }
                                        Text { text: "Height"; color: appRoot.textDim; font.pixelSize: 10 }
                                        SpinBox { Layout.fillWidth: true; from: 256; to: (!!appRoot.selectedGenerationProfile.remote ? 4096 : 1536); stepSize: 64; value: appRoot.generationHeight; editable: true; onValueModified: appRoot.generationHeight = value }
                                        Text { text: "Steps"; color: appRoot.textDim; font.pixelSize: 10 }
                                        SpinBox { Layout.fillWidth: true; from: 1; to: 100; value: appRoot.generationSteps; editable: true; onValueModified: appRoot.generationSteps = value }
                                        Text { text: "CFG"; color: appRoot.textDim; font.pixelSize: 10 }
                                        SpinBox { Layout.fillWidth: true; from: 0; to: 3000; value: Math.round(appRoot.generationCfg * 100); editable: true; onValueModified: appRoot.generationCfg = value / 100.0; textFromValue: function(v) { return (v / 100.0).toFixed(2) }; valueFromText: function(t) { return Math.round(Number(t) * 100) } }
                                        Text { text: "Seed"; color: appRoot.textDim; font.pixelSize: 10 }
                                        SpinBox { Layout.fillWidth: true; from: -1; to: 2147483647; value: appRoot.generationSeed; editable: true; onValueModified: appRoot.generationSeed = value }
                                        Text { text: "Denoise"; color: appRoot.textDim; font.pixelSize: 10 }
                                        SpinBox { Layout.fillWidth: true; from: 0; to: 100; value: Math.round(appRoot.generationDenoise * 100); editable: true; onValueModified: appRoot.generationDenoise = value / 100.0; textFromValue: function(v) { return (v / 100.0).toFixed(2) }; valueFromText: function(t) { return Math.round(Number(t) * 100) } }
                                        Text { text: "Sampler"; color: appRoot.textDim; font.pixelSize: 10 }
                                        ComboBox { Layout.fillWidth: true; model: ["er_sde", "euler", "euler_ancestral", "dpmpp_2m", "dpmpp_2m_sde"]; currentIndex: Math.max(0, model.indexOf(appRoot.generationSampler)); onActivated: appRoot.generationSampler = currentText }
                                        Text { text: "Scheduler"; color: appRoot.textDim; font.pixelSize: 10 }
                                        ComboBox { Layout.fillWidth: true; model: ["beta", "normal", "karras", "sgm_uniform"]; currentIndex: Math.max(0, model.indexOf(appRoot.generationScheduler)); onActivated: appRoot.generationScheduler = currentText }
                                    }
                                    SectionLabel { text: "PIPELINE" }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        CheckBox { text: "Stage 2 · refine"; checked: appRoot.useStageTwo; onToggled: appRoot.useStageTwo = checked }
                                        ComboBox {
                                            Layout.fillWidth: true
                                            visible: appRoot.selectedGenerationProfile.remote === true
                                            enabled: !genesisBridge.busy
                                            model: ["Aisha 9B v9.7", "Klein 9B"]
                                            onActivated: genesisBridge.setStageTwoModel(currentIndex === 0
                                                ? "aisha_nsfw_beta_v9_7_distilled_bf16.safetensors"
                                                : "flux-2-klein-9b.safetensors")
                                        }
                                    }
                                    CheckBox { text: "Stage 3 · identity lock"; checked: appRoot.useStageThree; onToggled: appRoot.useStageThree = checked }
                                    CheckBox { text: "Final upscale"; checked: appRoot.useUpscale; enabled: genesisBridge.upscaleAvailable; onToggled: appRoot.useUpscale = checked }
                                    Rectangle { Layout.fillWidth: true; height: 1; color: appRoot.line }
                                    Text { Layout.fillWidth: true; text: appRoot.generationSource.toString().length ? "Source image stays loaded when you change presets, poses, models or LoRAs." : "Load a source image first for identity/source workflows."; color: appRoot.generationSource.toString().length ? appRoot.success : appRoot.gold; font.pixelSize: 11; wrapMode: Text.Wrap }


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
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            GButton { Layout.preferredWidth: implicitWidth; text: "‹  Create"; active: false; onClicked: appRoot.pageIndex = 0 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Pose Library"; active: true; onClicked: appRoot.pageIndex = 1 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Workflow"; active: false; onClicked: appRoot.pageIndex = 2 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Pose Maker"; onClicked: appRoot.pageIndex = 9 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Canvas"; onClicked: appRoot.pageIndex = 8 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Results"; onClicked: { appRoot.viewerSource = genesisBridge.previewUrl; appRoot.pageIndex = 4 } }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            TextField { Layout.preferredWidth: 280; placeholderText: "Search poses…"; color: appRoot.textMain; onTextChanged: appRoot.poseSearch = text; background: Rectangle { color: "#191919"; border.color: appRoot.line; radius: 8 } }
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
                            spacing: 8
                            Panel {
                                Layout.preferredWidth: 230
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8
                                    SectionLabel { text: "SOURCE" }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 130
                                        Layout.minimumHeight: 115
                                        radius: 8
                                        color: "#0d0d0d"
                                        border.color: appRoot.generationSource.toString().length ? appRoot.gold : appRoot.line
                                        Image { anchors.fill: parent; anchors.margins: 6; source: appRoot.generationSource; fillMode: Image.PreserveAspectFit; visible: appRoot.generationSource.toString().length > 0 && !privacyMode }
                                        Text { anchors.centerIn: parent; text: appRoot.generationSource.toString().length ? (privacyMode ? "PRIVATE" : "") : "NO SOURCE LOADED"; color: appRoot.textDim; font.pixelSize: 11 }
                                    }
                                    SectionLabel { text: "SELECTED POSE" }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 160
                                        Layout.minimumHeight: 140
                                        spacing: 6
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.fillHeight: true
                                            radius: 8; color: "#0d0d0d"; border.color: appRoot.gold
                                            Image { anchors.fill: parent; anchors.margins: 6; source: appRoot.selectedPoseThumbnail; fillMode: Image.PreserveAspectFit; asynchronous: true }
                                            Text { anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 6; text: "PREVIEW"; color: appRoot.brightGold; font.pixelSize: 8; font.bold: true }
                                        }
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.fillHeight: true
                                            radius: 8; color: "#0d0d0d"; border.color: appRoot.line
                                            Image { anchors.fill: parent; anchors.margins: 6; source: appRoot.selectedPoseSource; fillMode: Image.PreserveAspectFit; asynchronous: true }
                                            Text { anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 6; text: "SKELETON"; color: appRoot.textDim; font.pixelSize: 8; font.bold: true }
                                        }
                                    }
                                    Text { Layout.fillWidth: true; text: appRoot.selectedPoseName; color: appRoot.brightGold; font.pixelSize: 13; font.bold: true; wrapMode: Text.Wrap }
                                    Text { Layout.fillWidth: true; text: appRoot.selectedPoseCategory; color: appRoot.textDim; font.pixelSize: 11 }
                                    Item { Layout.fillHeight: true }
                                    GButton { Layout.preferredWidth: implicitWidth; text: "Use Pose in Create"; active: true; onClicked: { if (appRoot.selectedPosePrompt.length) appRoot.generationPrompt = appRoot.selectedPosePrompt; appRoot.pageIndex = 0 } }
                                }
                            }
                            GridView {
                                id: poseGrid
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                clip: true
                                cellWidth: Math.max(155, width / 4)
                                cellHeight: 190
                                model: appRoot.filteredPoses()
                                delegate: Rectangle {
                                    width: poseGrid.cellWidth - 9
                                    height: poseGrid.cellHeight - 9
                                    radius: 10
                                    color: appRoot.panel
                                    border.color: appRoot.selectedPoseName === String(modelData.name || "") ? appRoot.gold : appRoot.line
                                    border.width: appRoot.selectedPoseName === String(modelData.name || "") ? 2 : 1
                                    Image { anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: caption.top; anchors.margins: 6; source: modelData.thumbnail || modelData.source; fillMode: Image.PreserveAspectFit; asynchronous: true }
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
                        spacing: 8
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            GButton { Layout.preferredWidth: implicitWidth; text: "‹  Create"; active: false; onClicked: appRoot.pageIndex = 0 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Pose Library"; active: false; onClicked: appRoot.pageIndex = 1 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Workflow"; active: true; onClicked: appRoot.pageIndex = 2 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Pose Maker"; onClicked: appRoot.pageIndex = 9 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Canvas"; onClicked: appRoot.pageIndex = 8 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Results"; onClicked: { appRoot.viewerSource = genesisBridge.previewUrl; appRoot.pageIndex = 4 } }
                        }
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
                        spacing: 8
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            Text { Layout.fillWidth:true; text:"MEDIA TOOLS"; color:appRoot.brightGold; font.pixelSize:18; font.bold:true }
                            Text { Layout.preferredWidth:260; text:mediaBridge.status; color:appRoot.textDim; elide:Text.ElideRight }
                        }
                        ScrollView {
                            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                            id: mediaScroll
                            contentWidth: availableWidth
                        GridLayout {
                            width: mediaScroll.availableWidth; columns: width < 1050 ? 2 : 3; rowSpacing: 10; columnSpacing: 10
                            Repeater {
                                model: [
                                    {title:"Background Remover", body:"Create one transparent cut-out while preserving the source.", action:"background remover", icon:"✂", status:"GPU / LOCAL"},
                                    {title:"Batch Cut-outs", body:"Remove backgrounds from multiple selected images into an output folder.", action:"batch background", icon:"✂", status:"GPU / BATCH"},
                                    {title:"Upscale 2×", body:"AI upscale through the selected backend. Use Standard Resize for CPU resizing.", action:"upscale", icon:"⇧", status:backendBridge.mode},
                                    {title:"Standard Resize 2×", body:"Resize locally without starting an AI model. Keeps transparency.", action:"standard resize", icon:"⇧", status:"CPU"},
                                    {title:"Batch Upscale 4×", body:"Quality-upscale multiple selected images into an output folder.", action:"batch upscale", icon:"⇧", status:backendBridge.mode + " / BATCH"},
                                    {title:"Extract MP3", body:"Extract an MP3 audio track from a video or audio file.", action:"extract audio", icon:"♫", status:"FFMPEG"},
                                    {title:"Extract Video", body:"Save a video copy while keeping its original audio track.", action:"extract video", icon:"▷", status:"FFMPEG"},
                                    {title:"Media Viewer", body:"Browse, preview and inspect your local images and metadata.", action:"media viewer", icon:"▧", status:"LIBRARY"},
                                    {title:"Duplicate Finder", body:"Review exact and near duplicates before moving copies to Trash.", action:"duplicate finder", icon:"◫", status:"SAFE REVIEW"},
                                    {title:"Face Organiser", body:"Group and organise photos by people.", action:"face organiser", icon:"◎", status:"PEOPLE"},
                                    {title:"Face Swap", body:"ReActor uses the selected backend. FaceFusion runs local images only.", action:"face swap", icon:"◎", status:backendBridge.mode},
                                    {title:"Canvas", body:"Layer images and cutouts, arrange your scene and export a PNG.", action:"canvas", icon:"Ps", status:"LOCAL EDITOR"}
                                ]
                                MediaCard { titleText:modelData.title; bodyText:modelData.body; actionKey:modelData.action; iconText:modelData.icon; statusText:modelData.status }
                            }
                        }
                        }
                    }
                    Rectangle {
                        anchors.fill: parent
                        objectName: "mediaToolWorkspace"
                        visible: appRoot.mediaToolOpen
                        z: 30
                        color: appRoot.bg
                        border.color: appRoot.line
                        radius: 2

                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 10

                            RowLayout {
                                Layout.fillWidth: true
                                GButton { text: "‹  MEDIA TOOLS"; active: true; onClicked: appRoot.closeMediaTool() }
                                Text { Layout.fillWidth: true; text: appRoot.mediaToolTitle.toUpperCase(); color: appRoot.brightGold; font.pixelSize: 22; font.bold: true }
                                Rectangle {
                                    radius: 2
                                    height: 24
                                    width: toolStatus.implicitWidth + 18
                                    color: "#241c11"
                                    border.color: appRoot.gold
                                    Text { id: toolStatus; anchors.centerIn: parent; text: appRoot.mediaToolStatus; color: appRoot.brightGold; font.pixelSize: 9; font.bold: true }
                                }
                            }

                            Text {
                                Layout.fillWidth: true
                                text: appRoot.mediaToolDescription
                                color: appRoot.textDim
                                font.pixelSize: 12
                                wrapMode: Text.Wrap
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                spacing: 10

                                Panel {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 14
                                        spacing: 10
                                        SectionLabel { text: "SOURCE / INPUT" }
                                        Rectangle {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            Layout.minimumHeight: 240
                                            color: "#070707"
                                            border.color: appRoot.line
                                            radius: 2
                                            Image {
                                                anchors.fill: parent
                                                anchors.margins: 8
                                                source: mediaBridge.inputUrl
                                                fillMode: Image.PreserveAspectFit
                                                visible: mediaBridge.inputUrl.length > 0
                                                    && appRoot.mediaToolHasVisualResult()
                                                    && !appRoot.privacyMode
                                            }
                                            Column {
                                                anchors.centerIn: parent
                                                spacing: 8
                                                visible: mediaBridge.inputUrl.length === 0
                                                    || !appRoot.mediaToolHasVisualResult()
                                                    || appRoot.privacyMode
                                                Text {
                                                    anchors.horizontalCenter: parent.horizontalCenter
                                                    text: mediaBridge.inputCount > 0 ? "✓" : "＋"
                                                    color: appRoot.gold
                                                    font.pixelSize: 42
                                                }
                                                Text {
                                                    width: 380
                                                    anchors.horizontalCenter: parent.horizontalCenter
                                                    horizontalAlignment: Text.AlignHCenter
                                                    wrapMode: Text.Wrap
                                                    text: mediaBridge.inputCount > 0
                                                        ? mediaBridge.inputSummary
                                                        : appRoot.mediaToolInputHint()
                                                    color: mediaBridge.inputCount > 0 ? appRoot.textMain : appRoot.textDim
                                                    font.pixelSize: 12
                                                }
                                            }
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            GButton {
                                                Layout.fillWidth: true
                                                text: mediaBridge.inputCount > 0 ? "CHANGE INPUT" : "CHOOSE INPUT"
                                                enabled: !mediaBridge.busy
                                                onClicked: appRoot.chooseMediaToolInput()
                                            }
                                            GButton {
                                                Layout.fillWidth: true
                                                text: mediaBridge.busy ? "WORKING…" : appRoot.mediaToolRunLabel()
                                                active: mediaBridge.inputCount > 0 && !mediaBridge.busy
                                                enabled: mediaBridge.inputCount > 0 && !mediaBridge.busy
                                                onClicked: appRoot.runMediaTool()
                                            }
                                        }
                                    }
                                }

                                Panel {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 14
                                        spacing: 10
                                        SectionLabel { text: "OUTPUT / RESULT" }
                                        Rectangle {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true
                                            Layout.minimumHeight: 240
                                            color: "#070707"
                                            border.color: mediaBridge.resultUrl.length ? appRoot.gold : appRoot.line
                                            radius: 2
                                            Image {
                                                anchors.fill: parent
                                                anchors.margins: 8
                                                source: mediaBridge.resultUrl
                                                fillMode: Image.PreserveAspectFit
                                                visible: appRoot.mediaToolHasVisualResult()
                                                    && mediaBridge.resultUrl.length > 0
                                                    && !appRoot.privacyMode
                                            }
                                            ListView {
                                                anchors.fill: parent
                                                anchors.margins: 8
                                                spacing: 8
                                                clip: true
                                                visible: appRoot.mediaToolIsReview()
                                                model: appRoot.mediaToolKey === "duplicate finder"
                                                    ? mediaBridge.duplicatePairs
                                                    : mediaBridge.faceGroups
                                                delegate: Rectangle {
                                                    required property var modelData
                                                    width: ListView.view.width
                                                    height: 112
                                                    radius: 2
                                                    color: appRoot.raised
                                                    border.color: appRoot.line
                                                    RowLayout {
                                                        anchors.fill: parent
                                                        anchors.margins: 7
                                                        spacing: 8
                                                        Image {
                                                            Layout.preferredWidth: 105
                                                            Layout.fillHeight: true
                                                            source: "file://" + (modelData.left || (modelData.members && modelData.members.length ? modelData.members[0].path : ""))
                                                            fillMode: Image.PreserveAspectFit
                                                            asynchronous: true
                                                        }
                                                        Image {
                                                            Layout.preferredWidth: 105
                                                            Layout.fillHeight: true
                                                            visible: modelData.right !== undefined
                                                            source: "file://" + (modelData.right || "")
                                                            fillMode: Image.PreserveAspectFit
                                                            asynchronous: true
                                                        }
                                                        ColumnLayout {
                                                            Layout.fillWidth: true
                                                            Text { text: modelData.kind || ("GROUP " + modelData.group_id); color: appRoot.brightGold; font.pixelSize: 10; font.bold: true }
                                                            Text { text: modelData.right !== undefined ? "distance " + modelData.distance : modelData.count + " faces"; color: appRoot.textDim; font.pixelSize: 9 }
                                                            Item { Layout.fillHeight: true }
                                                            RowLayout {
                                                                visible: modelData.right !== undefined
                                                                GButton { text: "KEEP LEFT"; onClicked: mediaBridge.trashDuplicate(modelData.right) }
                                                                GButton { text: "KEEP RIGHT"; onClicked: mediaBridge.trashDuplicate(modelData.left) }
                                                            }
                                                            GButton {
                                                                visible: modelData.right === undefined && modelData.members && modelData.members.length
                                                                text: "OPEN GROUP"
                                                                onClicked: mediaBridge.openPath(modelData.members[0].path)
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                            Text {
                                                anchors.centerIn: parent
                                                width: parent.width - 40
                                                horizontalAlignment: Text.AlignHCenter
                                                wrapMode: Text.Wrap
                                                visible: !appRoot.mediaToolIsReview()
                                                    && (!appRoot.mediaToolHasVisualResult() || mediaBridge.resultUrl.length === 0 || appRoot.privacyMode)
                                                text: appRoot.privacyMode && mediaBridge.resultUrl.length
                                                    ? "PRIVATE"
                                                    : (mediaBridge.resultUrl.length
                                                        ? "RESULT SAVED · use Open Result or Open Folder below"
                                                        : "NO RESULT YET")
                                                color: appRoot.textDim
                                                font.pixelSize: 15
                                            }
                                            Text {
                                                anchors.centerIn: parent
                                                width: parent.width - 40
                                                horizontalAlignment: Text.AlignHCenter
                                                visible: appRoot.mediaToolIsReview()
                                                    && ((appRoot.mediaToolKey === "duplicate finder" && mediaBridge.duplicatePairs.length === 0)
                                                        || (appRoot.mediaToolKey === "face organiser" && mediaBridge.faceGroups.length === 0))
                                                text: mediaBridge.busy ? "SCANNING…" : "NO REVIEW RESULTS YET"
                                                color: appRoot.textDim
                                                font.pixelSize: 14
                                            }
                                        }
                                        RowLayout {
                                            Layout.fillWidth: true
                                            GButton { text: "OPEN RESULT"; enabled: !mediaBridge.busy && mediaBridge.resultUrl.length > 0; onClicked: Qt.openUrlExternally(mediaBridge.resultUrl) }
                                            GButton { text: "OPEN FOLDER"; enabled: !mediaBridge.busy && mediaBridge.resultUrl.length > 0; onClicked: mediaBridge.openResultFolder() }
                                            GButton { text: "SEND TO CANVAS"; enabled: !mediaBridge.busy && appRoot.mediaToolHasVisualResult() && mediaBridge.resultUrl.length > 0; onClicked: { appRoot.editSource = mediaBridge.resultUrl; appRoot.pageIndex = 8; appRoot.closeMediaTool() } }
                                        }
                                    }
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                BusyIndicator { running: mediaBridge.busy; visible: running; Layout.preferredWidth: 28; Layout.preferredHeight: 28 }
                                Text { Layout.fillWidth: true; text: mediaBridge.status; color: mediaBridge.busy ? appRoot.gold : appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap }
                                GButton { text: "CLEAR RESULT"; enabled: !mediaBridge.busy && mediaBridge.resultUrl.length > 0; onClicked: mediaBridge.clearResult() }
                            }
                        }
                    }
                }

                MediaWorkspace {
                    sourceUrl: appRoot.viewerSource
                    resultUrl: genesisBridge.previewUrl
                    statusText: "Local image review · no generation service required."
                    onBrowseRequested: {
                        var chosen = genesisBridge.chooseSourceImage()
                        if (chosen.length) appRoot.viewerSource = chosen
                    }
                    onResultsRequested: {
                        var chosen = genesisBridge.chooseResultImage()
                        if (chosen.length) appRoot.viewerSource = chosen
                    }
                    onCanvasRequested: function(imageUrl) { appRoot.editSource = imageUrl; appRoot.pageIndex = 8 }
                }

                Item {
                    ColumnLayout { anchors.fill: parent; spacing: 10
                        Panel { Layout.fillWidth:true; Layout.fillHeight:true; ColumnLayout { anchors.fill:parent; anchors.margins:16; spacing:10
                            RowLayout { Layout.fillWidth:true; Text { Layout.fillWidth:true; text:"CAMERA HUB"; color:appRoot.brightGold; font.pixelSize:18; font.bold:true } Text { text:"LOCAL CAMERAS"; color:appRoot.textDim; font.pixelSize:10; font.letterSpacing:1.2 } }
                            Rectangle { Layout.fillWidth:true; Layout.fillHeight:true; Layout.minimumHeight:180; color:"#0d0d0d"; radius:10; border.color:appRoot.line
                                Column { anchors.centerIn:parent; spacing:8; Text { anchors.horizontalCenter:parent.horizontalCenter; text:"●"; color:appRoot.gold; font.pixelSize:28 } Text { anchors.horizontalCenter:parent.horizontalCenter; text:"Camera service and live grid"; color:appRoot.textDim; font.pixelSize:12 } }
                            }
                            GButton { Layout.preferredWidth: implicitWidth; text:"Open Camera Hub"; active:true; onClicked:moduleBridge.triggerAction("camera hub") }
                        } }
                    }
                }

                // Page 6 intentionally retired; retained as an empty slot to preserve stable page indices.
                Item { }

                Item {
                    ColumnLayout { anchors.fill: parent; spacing:10
                        GridLayout { Layout.fillWidth:true; Layout.fillHeight:true; columns:2; rowSpacing:10; columnSpacing:10
                            Repeater { model:[
                                {title:"ComfyUI", body:runtimeStatus.comfyOnline ? "Online and ready" : "Offline — start or inspect service", action:"comfyui"},
                                {title:"System Monitor", body:"Inspect GPU, memory and running processes.", action:"monitor"},
                                {title:"Models & Storage", body:"Open your AI model/storage location.", action:"models and storage"},
                                {title:"Backups & Recovery", body:"Open GENESIS recovery resources.", action:"backup recovery"}
                            ]
                            Panel { Layout.fillWidth:true; Layout.fillHeight:true; Layout.minimumHeight:150; ColumnLayout { anchors.fill:parent; anchors.margins:14; spacing:6; Text { text:modelData.title; color:appRoot.brightGold; font.pixelSize:16; font.bold:true } Text { Layout.fillWidth:true; text:modelData.body; color:appRoot.textDim; font.pixelSize:11; wrapMode:Text.Wrap; maximumLineCount:2; elide:Text.ElideRight } Item { Layout.fillHeight:true } GButton { Layout.preferredWidth: implicitWidth; text:"Open"; onClicked:moduleBridge.triggerAction(modelData.action) } } } }
                        }
                    }
                }

                CanvasWorkspace {
                    sourceUrl: appRoot.editSource
                }

                Item {
                    ColumnLayout { anchors.fill:parent; spacing:10
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            GButton { Layout.preferredWidth: implicitWidth; text: "‹  Create"; onClicked: appRoot.pageIndex = 0 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Pose Library"; onClicked: appRoot.pageIndex = 1 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Workflow"; onClicked: appRoot.pageIndex = 2 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Pose Maker"; active: true; onClicked: appRoot.pageIndex = 9 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Canvas"; onClicked: appRoot.pageIndex = 8 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Results"; onClicked: { appRoot.viewerSource = genesisBridge.previewUrl; appRoot.pageIndex = 4 } }
                        }
                        RowLayout { Layout.fillWidth:true; Layout.fillHeight:true; spacing:10
                            Panel {
                                Layout.preferredWidth: 380; Layout.fillHeight: true
                                ColumnLayout { anchors.fill: parent; anchors.margins: 16; spacing: 10
                                    SectionLabel { text: "POSE MAKER WORKBENCH" }
                                    Text { Layout.fillWidth:true; text:"Custom pose/photo workflow"; color:appRoot.brightGold; font.pixelSize:20; font.bold:true; wrapMode:Text.Wrap }
                                    Text { Layout.fillWidth:true; text:"Use Pose Maker when you want to upload a custom pose photo, extract pose geometry with DWPose, use prompt-only pose control, or run the dedicated Stage 1 → Stage 2 → Stage 3 pose pipeline."; color:appRoot.textMain; font.pixelSize:12; wrapMode:Text.Wrap }
                                    Rectangle { Layout.fillWidth:true; Layout.preferredHeight:150; radius:10; color:"#0d0d0d"; border.color:appRoot.gold
                                        Column { anchors.centerIn:parent; spacing:7
                                            Text { anchors.horizontalCenter:parent.horizontalCenter; text:"CUSTOM POSE"; color:appRoot.brightGold; font.pixelSize:16; font.bold:true }
                                            Text { anchors.horizontalCenter:parent.horizontalCenter; text:"PHOTO → GEOMETRY → 3-STAGE PIPELINE"; color:appRoot.textDim; font.pixelSize:9; font.letterSpacing:0.8 }
                                        }
                                    }
                                    GButton { Layout.preferredWidth: implicitWidth; text:"Open Pose Maker Workbench"; active:true; onClicked:moduleBridge.triggerAction("pose maker") }
                                    Text { Layout.fillWidth:true; text:moduleBridge.status; color:appRoot.textDim; font.pixelSize:10; wrapMode:Text.Wrap }
                                    Item { Layout.fillHeight:true }
                                }
                            }
                            Panel {
                                Layout.fillWidth:true; Layout.fillHeight:true
                                ColumnLayout { anchors.fill:parent; anchors.margins:16; spacing:10
                                    SectionLabel { text:"WHAT GOES WHERE" }
                                    Text { Layout.fillWidth:true; text:"POSE LIBRARY"; color:appRoot.brightGold; font.pixelSize:16; font.bold:true }
                                    Text { Layout.fillWidth:true; text:"Browse the curated pose thumbnail grid. Selecting a card keeps its visual preview separate from the OpenPose skeleton used by generation."; color:appRoot.textMain; font.pixelSize:12; wrapMode:Text.Wrap }
                                    GButton { Layout.preferredWidth: implicitWidth; text:"Browse Pose Library"; onClicked:appRoot.pageIndex=1 }
                                    Rectangle { Layout.fillWidth:true; height:1; color:appRoot.line }
                                    Text { Layout.fillWidth:true; text:"POSE MAKER"; color:appRoot.brightGold; font.pixelSize:16; font.bold:true }
                                    Text { Layout.fillWidth:true; text:"Create or extract a pose from your own reference image, tune pose strength/identity lock, then run the dedicated pose pipeline. It is no longer a duplicate preset browser."; color:appRoot.textMain; font.pixelSize:12; wrapMode:Text.Wrap }
                                    Item { Layout.fillHeight:true }
                                    Text { Layout.fillWidth:true; text:"Heavy image generation remains off until you explicitly run it; opening the workbench itself does not start a generation."; color:appRoot.textDim; font.pixelSize:10; wrapMode:Text.Wrap }
                                }
                            }
                        }
                    }
                }

                Item {
                    ColumnLayout { anchors.fill:parent; spacing:10
                        Panel { Layout.fillWidth:true; Layout.fillHeight:true; ColumnLayout { anchors.fill:parent; anchors.margins:16; spacing:10; RowLayout { Layout.fillWidth:true; Text { Layout.fillWidth:true; text:"GENESIS LINUX"; color:appRoot.brightGold; font.pixelSize:18; font.bold:true } Text { text:moduleBridge.status; color:appRoot.textDim; font.pixelSize:11; elide:Text.ElideRight; Layout.maximumWidth:360 } } RowLayout { GButton { text:"Refresh Health"; onClicked:moduleBridge.triggerAction("refresh") } GButton { text:"Open Settings Folder"; onClicked:moduleBridge.triggerAction("settings") } } Item { Layout.fillHeight:true } Text { text:"Workspace state is preserved while moving between Create, Pose Library and the generation tools."; color:appRoot.textDim; font.pixelSize:11; wrapMode:Text.Wrap; Layout.fillWidth:true } } }
                    }
                }

                // GENESIS_FACE_SWAP_PAGE
                Item {
                    objectName: "faceSwapWorkspace"
                    ColumnLayout { anchors.fill:parent; spacing:10
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            GButton { Layout.preferredWidth: implicitWidth; text: "‹  Create"; onClicked: appRoot.pageIndex = 0 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Pose Library"; onClicked: appRoot.pageIndex = 1 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Workflow"; onClicked: appRoot.pageIndex = 2 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Pose Maker"; onClicked: appRoot.pageIndex = 9 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Canvas"; onClicked: appRoot.pageIndex = 8 }
                            GButton { Layout.preferredWidth: implicitWidth; text: "Results"; onClicked: { appRoot.viewerSource = genesisBridge.previewUrl; appRoot.pageIndex = 4 } }
                        }
                        RowLayout { Layout.fillWidth:true; Layout.fillHeight:true; spacing:10
                            Panel { Layout.fillWidth:true; Layout.fillHeight:true; ColumnLayout { anchors.fill:parent; anchors.margins:14; spacing:10
                                SectionLabel { text:"TARGET IMAGE · WHERE THE FACE GOES" }
                                Rectangle { Layout.fillWidth:true; Layout.fillHeight:true; Layout.minimumHeight:180; color:"#0c0c0c"; radius:10; border.color:appRoot.faceSwapTarget.toString().length ? appRoot.gold : appRoot.line
                                    Image { anchors.fill:parent; anchors.margins:8; source:appRoot.faceSwapTarget; fillMode:Image.PreserveAspectFit; visible:appRoot.faceSwapTarget.toString().length > 0 && !privacyMode }
                                    Text { anchors.centerIn:parent; text:appRoot.faceSwapTarget.toString().length ? (privacyMode ? "PRIVATE" : "") : "NO TARGET IMAGE"; color:appRoot.textDim; font.pixelSize:16 }
                                }
                                RowLayout { Layout.fillWidth:true; GButton { Layout.preferredWidth: implicitWidth; text:"Load Target Image"; onClicked:appRoot.chooseFaceSwapTarget() } GButton { Layout.preferredWidth:80; text:"Clear"; enabled:appRoot.faceSwapTarget.toString().length>0; onClicked:appRoot.faceSwapTarget="" } }
                            } }
                            Panel { Layout.fillWidth:true; Layout.fillHeight:true; ColumnLayout { anchors.fill:parent; anchors.margins:14; spacing:10
                                SectionLabel { text:"SOURCE IDENTITY · FACE TO USE" }
                                Rectangle { Layout.fillWidth:true; Layout.fillHeight:true; Layout.minimumHeight:180; color:"#0c0c0c"; radius:10; border.color:appRoot.faceSwapSource.toString().length ? appRoot.gold : appRoot.line
                                    Image { anchors.fill:parent; anchors.margins:8; source:appRoot.faceSwapSource; fillMode:Image.PreserveAspectFit; visible:appRoot.faceSwapSource.toString().length > 0 && !privacyMode }
                                    Text { anchors.centerIn:parent; text:appRoot.faceSwapSource.toString().length ? (privacyMode ? "PRIVATE" : "") : "NO SOURCE IMAGE"; color:appRoot.textDim; font.pixelSize:16 }
                                }
                                RowLayout { Layout.fillWidth:true; GButton { Layout.preferredWidth: implicitWidth; text:"Load Source Image"; onClicked:appRoot.chooseFaceSwapSource() } GButton { Layout.preferredWidth:80; text:"Clear"; enabled:appRoot.faceSwapSource.toString().length>0; onClicked:appRoot.faceSwapSource="" } }
                            } }
                            Panel { Layout.preferredWidth:360; Layout.fillHeight:true; ColumnLayout { anchors.fill:parent; anchors.margins:14; spacing:10
                                SectionLabel { text:"RESULT" }
                                Rectangle { Layout.fillWidth:true; Layout.fillHeight:true; Layout.minimumHeight:180; color:"#0c0c0c"; radius:10; border.color:appRoot.line
                                    Image { anchors.fill:parent; anchors.margins:8; source:genesisBridge.previewUrl; fillMode:Image.PreserveAspectFit; visible:!privacyMode }
                                    Text { anchors.centerIn:parent; text:privacyMode ? "PRIVATE" : "FACE SWAP RESULT"; color:appRoot.textDim; font.pixelSize:16; visible:privacyMode || genesisBridge.previewUrl.length===0 }
                                }
                                GButton { Layout.preferredWidth: implicitWidth; text:genesisBridge.busy ? "RUNNING…" : "RUN REACTOR"; active:true; enabled:!genesisBridge.busy && appRoot.faceSwapTarget.toString().length>0 && appRoot.faceSwapSource.toString().length>0; onClicked:appRoot.runFaceSwap() }
                                GButton { Layout.preferredWidth: implicitWidth; text:genesisBridge.busy ? "RUNNING…" : "FACEFUSION · LOCAL IMAGE"; enabled:!genesisBridge.busy && appRoot.faceSwapTarget.toString().length>0 && appRoot.faceSwapSource.toString().length>0; onClicked:genesisBridge.queueFaceFusion(appRoot.faceSwapTarget.toString(), appRoot.faceSwapSource.toString()) }
                                GButton { Layout.preferredWidth: implicitWidth; text:"Open Full Size"; enabled:genesisBridge.previewUrl.length>0; onClicked:genesisBridge.openPreview() }
                            } }
                        }
                        Text { Layout.fillWidth:true; text:"Use images you own or have permission to use. Neutral portraits work best; extreme angles, occlusion, hands, hair, and mismatched lighting can still cause distortion. This isolated tool is for ordinary, non-explicit images."; color:appRoot.gold; font.pixelSize:11; wrapMode:Text.Wrap }
                        Text { Layout.fillWidth:true; text:genesisBridge.status; color:genesisBridge.busy ? appRoot.gold : appRoot.textDim; font.pixelSize:11; wrapMode:Text.Wrap }
                    }
                }
            }
        }
    }
    }
}
