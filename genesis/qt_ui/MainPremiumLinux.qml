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
    color: "#040404"
    font.family: "Noto Sans"

    readonly property color gold: "#e8b654"
    readonly property color brightGold: "#ffda87"
    readonly property color blue: "#d6ac63"
    readonly property color blueBright: "#ffe0a0"
    readonly property color blueDeep: "#49371f"
    readonly property color bg: "#101215"
    readonly property color panel: "#191c21"
    readonly property color raised: "#23272d"
    readonly property color raised2: "#20242a"
    readonly property color line: "#41454c"
    readonly property color textMain: "#fff4e3"
    readonly property color textDim: "#b9b4aa"
    readonly property color success: "#62d27a"
    readonly property url glassButtonSource: "../assets/ui/glass-button-pill.png"

    onClosing: function(close) { close.accepted = canvasBridge.confirmClose() && skeletonBridge.confirmClose() }

    property int pageIndex: 14
    property bool feefeeOpen: false
    property int lastWorkspacePage: 0
    onPageIndexChanged: if (pageIndex !== 11) lastWorkspacePage = pageIndex
    palette.window: "#191c21"
    palette.base: "#070707"
    palette.button: "#111111"
    palette.text: "#e9e6df"
    palette.buttonText: "#e9e6df"
    palette.windowText: "#e9e6df"
    palette.highlight: "#8a642b"
    palette.highlightedText: "#fff3d8"
    palette.placeholderText: "#b9b4aa"
    property bool privacyMode: false
    readonly property bool compactNavigation: height < 850
    property var navItems: [
        {icon:"⌂", label:"Home", page:14},
        {icon:"▣", label:"Image Generation", page:0},
        {icon:"✧", label:"Grok Imagine", page:13},
        {icon:"✦", label:"Media Tools", page:3},
        {icon:"●", label:"Camera Hub", page:5},
        {icon:"⚙", label:"System Tools", page:7},
        {icon:"☷", label:"Settings", page:10}
    ]

    // Primary navigation shortcuts mirror the visible sidebar. Internal generation tabs
    // intentionally have no global number shortcuts.
    Shortcut { sequence: "Alt+Home"; onActivated: appRoot.pageIndex = 14 }
    Shortcut { sequence: "Alt+1"; onActivated: appRoot.pageIndex = 0 }
    Shortcut { sequence: "Alt+2"; onActivated: appRoot.pageIndex = 3 }
    Shortcut { sequence: "Alt+3"; onActivated: appRoot.pageIndex = 5 }
    Shortcut { sequence: "Alt+4"; onActivated: appRoot.pageIndex = 7 }
    Shortcut { sequence: "Alt+,"; onActivated: appRoot.pageIndex = 10 }

    // Show configured models even when the current backend is offline. Route
    // readiness gates GENERATE, not visibility or choosing a model profile.
    property var generationModel: typeof generationProfiles !== "undefined"
        ? generationProfiles.filter(function(row) {
            return (row.runnable === true || (row.stageOneConfigured === true && row.profileSelectable === true))
                && (!generationSource.toString().length || row.sourceSupported !== false)
        }) : []
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
                selectGeneration(index, false)
                modelDefaultsApplied = true
            }
        }
    }
    Component.onCompleted: if (generationModel.length) { selectGeneration(0, false); modelDefaultsApplied = true }
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
    onGenerationSourceChanged: applyGenerationDefaults(selectedGenerationProfile)
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
    onStageTwoModelChanged: finishLora = "None"
    property string finishLora: "None"
    property real finishLoraStrength: 0.65
    property int finishScale: 2
    readonly property var finishAvailability: {
        var refresh = genesisBridge.previewUrl + genesisBridge.status + genesisBridge.busy + backendBridge.connected + backendBridge.endpoint
        return genesisBridge.finishingAvailability(stageTwoModel, generationSource.toString(), finishScale)
    }
    property bool useStageTwo: false
    property bool useStageThree: false
    property string stageTwoModel: "aisha_nsfw_beta_v9_7_distilled_fp8.safetensors"
    readonly property var stageTwoChoices: generationModel.filter(function(row) { return row.stageTwoEligible === true && row.selectable !== false })
    readonly property var stageTwoSelectableChoices: stageTwoChoices.filter(function(row) { return row.selectable !== false })
    readonly property string stageTwoLabel: {
        for (var i = 0; i < stageTwoChoices.length; ++i)
            if (stageTwoChoices[i].model === stageTwoModel) return stageTwoChoices[i].label
        return "Choose a refinement model"
    }
    readonly property var selectedStageTwoProfile: {
        for (var i = 0; i < stageTwoChoices.length; ++i)
            if (stageTwoChoices[i].model === stageTwoModel) return stageTwoChoices[i]
        return ({})
    }
    readonly property var liveIdentityEngines: (runtimeStatus && runtimeStatus.identityEngines) ? runtimeStatus.identityEngines : []
    readonly property var stageThreeChoices: [
        {label:"ReActor · Inswapper", engine:"reactor_inswapper", available:liveIdentityEngines.indexOf("reactor_inswapper") >= 0},
        {label:"ReActor · ReSwapper", engine:"reactor_reswapper", available:liveIdentityEngines.indexOf("reactor_reswapper") >= 0},
        {label:"ReActor · HyperSwap", engine:"reactor_hyperswap", available:liveIdentityEngines.indexOf("reactor_hyperswap") >= 0}
    ].filter(function(row) { return row.available === true })
    readonly property bool stageThreeReady: liveIdentityEngines.length > 0
    readonly property string stageThreeLabel: {
        for (var i = 0; i < stageThreeChoices.length; ++i)
            if (stageThreeChoices[i].engine === stageThreeEngine) return stageThreeChoices[i].label
        return "Choose an identity engine"
    }
    readonly property var stageOneChoices: generationModel.filter(function(row) { return row.stageOneEligible !== false || row.stageOneConfigured === true })
    readonly property var stageOneSelectableChoices: stageOneChoices
    readonly property int stageOneChoiceIndex: {
        for (var i = 0; i < stageOneSelectableChoices.length; ++i)
            if (stageOneSelectableChoices[i].model === selectedGenerationProfile.model) return i
        return -1
    }
    property int editingStage: 0
    readonly property var stageChoices: editingStage === 0 ? stageOneChoices
        : (editingStage === 1 ? stageTwoChoices : stageThreeChoices)
    property string stageThreeEngine: "reactor_inswapper"
    property bool useUpscale: false

    property var poseModel: typeof poseItems !== "undefined" ? poseItems : []
    property var easyPresetModel: typeof curatedPosePresets !== "undefined" ? curatedPosePresets : []
    property url selectedPoseSource: ""
    property url selectedPoseThumbnail: ""
    property string selectedPoseName: "No pose selected"
    property string selectedPoseCategory: ""
    property string selectedPosePrompt: ""
    property var selectedPresetPayload: null
    property string presetAttribution: ""
    property string presetSettingsNote: ""
    readonly property string comparisonSource: {
        var rows = genesisBridge.finishingResults
        for (var i = 0; i < rows.length; ++i)
            if (rows[i].source === genesisBridge.previewUrl) return rows[i].inputSource || ""
        return ""
    }
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

    function openStageModels(stage) {
        if (genesisBridge.busy) return
        editingStage = stage
        stageModelPopup.open()
    }

    function selectStageChoice(index) {
        var row = stageChoices[index]
        if (!row || genesisBridge.busy || row.available === false || (editingStage !== 0 && row.selectable === false)) return
        if (editingStage === 0) {
            selectStageOneChoice(index)
        } else if (editingStage === 1) {
            stageTwoModel = row.model
            if (row.remote === true || String(row.destination || "").indexOf("RUNPOD") >= 0)
                backendBridge.prepareModelRoute(row.model)
            genesisBridge.setStageTwoModel(row.model)
            useStageTwo = true
        } else {
            stageThreeEngine = row.engine
            genesisBridge.setStageThreeEngine(row.engine)
            useStageThree = true
        }
        stageModelPopup.close()
    }

    function selectStageOneChoice(index) {
        var row = stageOneChoices[index]
        if (!row || genesisBridge.busy) return
        for (var i = 0; i < generationModel.length; ++i)
            if (generationModel[i].model === row.model) { selectGeneration(i); return }
    }

    function selectStageOneAvailableChoice(index) {
        var row = stageOneSelectableChoices[index]
        if (!row || genesisBridge.busy) return
        for (var i = 0; i < generationModel.length; ++i)
            if (generationModel[i].model === row.model) { selectGeneration(i); return }
    }

    function selectGeneration(index, userChoseModel) {
        if (generationModel[index]) {
            selectedModelName = generationModel[index].model
            if (userChoseModel !== false && (generationModel[index].remote === true || String(generationModel[index].destination || "").indexOf("RUNPOD") >= 0))
                backendBridge.prepareModelRoute(generationModel[index].model)
        }
        selectedGenerationIndex = index
        selectedLora = "None"
        selectedLoraTwo = "None"
        selectedLoraThree = "None"
        selectedLoraStrength = 0.65
        selectedLoraTwoStrength = 0.65
        selectedLoraThreeStrength = 0.65

        // Use the row selected by the user directly. Reading the bound
        // selectedGenerationProfile here can briefly expose the previous row
        // while selectedGenerationIndex is changing, which leaks old model
        // defaults into the newly selected model.
        var profile = generationModel[index]
        if (!profile) return
        applyGenerationDefaults(profile)
    }

    function applyGenerationDefaults(profile) {
        if (!profile) return
        var defaults = generationSource.toString().length
            ? (profile.sourceDefaults || profile) : (profile.createDefaults || profile)
        generationWidth = defaults.defaultWidth !== undefined ? defaults.defaultWidth : 1024
        generationHeight = defaults.defaultHeight !== undefined ? defaults.defaultHeight : 1024
        generationSteps = defaults.defaultSteps !== undefined ? defaults.defaultSteps : 4
        generationCfg = defaults.defaultCfg !== undefined ? defaults.defaultCfg : 1.0
        generationDenoise = defaults.defaultDenoise !== undefined ? defaults.defaultDenoise : 1.0
        generationSampler = defaults.defaultSampler !== undefined ? defaults.defaultSampler : "euler"
        generationScheduler = defaults.defaultScheduler !== undefined ? defaults.defaultScheduler : "simple"
        if (typeof selectedPresetPayload !== "undefined" && selectedPresetPayload) applyPresetPayload(selectedPresetPayload, profile)
    }

    readonly property var activeGenerationDefaults: generationSource.toString().length
        ? (selectedGenerationProfile.sourceDefaults || selectedGenerationProfile)
        : (selectedGenerationProfile.createDefaults || selectedGenerationProfile)

    function qualityPresetActive(name, width, height) {
        var presets = selectedGenerationProfile.qualityPresets
        var size = presets && presets[name] ? presets[name] : ({width: width, height: height})
        return generationWidth === size.width && generationHeight === size.height
    }

    function applyQualityPreset(name, width, height) {
        var presets = selectedGenerationProfile.qualityPresets
        if (presets && presets[name]) {
            applyGenerationDefaults(selectedGenerationProfile)
            generationWidth = presets[name].width
            generationHeight = presets[name].height
        } else {
            generationWidth = width
            generationHeight = height
        }
    }

    onSelectedLoraChanged: selectedLoraStrength = defaultLoraStrength(selectedLora)

    onSelectedLoraTwoChanged: selectedLoraTwoStrength = defaultLoraStrength(selectedLoraTwo)

    onSelectedLoraThreeChanged: selectedLoraThreeStrength = defaultLoraStrength(selectedLoraThree)

    function defaultLoraStrength(name) {
        return String(name).split("/").pop() === "refcontrol_v2_poses.safetensors" ? 0.9 : 0.65
    }

    function clearPose() {
        selectedPoseSource = ""
        selectedPoseThumbnail = ""
        selectedPoseName = "No pose selected"
        selectedPoseCategory = ""
        selectedPosePrompt = ""
        selectedPresetPayload = null
        presetAttribution = ""
        presetSettingsNote = ""
    }

    function applyPresetPayload(row, profile) {
        if (!row || !profile) return
        var payload = moduleBridge.posePresetPayload(row, profile.model)
        generationPrompt = payload.prompt || ""
        selectedPosePrompt = generationPrompt
        generationNegativePrompt = payload.negativePrompt || ""
        presetAttribution = String(payload.attribution || "") + " · prompt: " + String(payload.promptSource || "")
        presetSettingsNote = payload.settingsNote || ""
        var settings = payload.settings || ({})
        if (settings.steps !== undefined) generationSteps = settings.steps
        if (settings.cfg !== undefined) generationCfg = settings.cfg
        if (settings.width !== undefined) generationWidth = settings.width
        if (settings.height !== undefined) generationHeight = settings.height
        if (settings.seed !== undefined) generationSeed = settings.seed
        if (settings.denoise !== undefined) generationDenoise = settings.denoise
        if (settings.sampler !== undefined) generationSampler = settings.sampler
        // FLUX scheduler node has its own fixed schedule.
        if (settings.scheduler !== undefined && !activeGenerationDefaults.schedulerFixed)
            generationScheduler = settings.scheduler
    }

    function applyPreset(row) {
        if (!row) return
        if (row.source) { applyPose(row); selectedPresetName = row.label || row.name; return }
        clearPose()
        selectedPresetPayload = row
        applyGenerationDefaults(selectedGenerationProfile)
        selectedPresetName = row.label || row.name || "Preset"

    }

    function applyPose(row) {
        if (!row) return
        selectedPresetName = ""
        selectedPoseSource = row.source || ""
        selectedPoseThumbnail = row.thumbnail || row.source || ""
        selectedPoseName = row.name || "Pose"
        selectedPoseCategory = row.category || ""
        selectedPresetPayload = row
        applyGenerationDefaults(selectedGenerationProfile)
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

    Popup {
        id: finishCompare
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(parent.width - 40, 1200)
        height: Math.min(parent.height - 40, 800)
        modal: true
        ColumnLayout {
            anchors.fill: parent
            RowLayout {
                Text { text: "Previous result · Selected finishing result"; color: appRoot.textMain; Layout.fillWidth: true }
                GButton { text: "Close"; onClicked: finishCompare.close() }
            }
            RowLayout {
                Layout.fillWidth: true; Layout.fillHeight: true
                Image { Layout.fillWidth: true; Layout.fillHeight: true; fillMode: Image.PreserveAspectFit; source: appRoot.privacyMode ? "" : appRoot.comparisonSource }
                Image { Layout.fillWidth: true; Layout.fillHeight: true; fillMode: Image.PreserveAspectFit; source: appRoot.privacyMode ? "" : genesisBridge.previewUrl }
            }
            Text { visible: appRoot.privacyMode; text: "Turn off private preview to view the saved results."; color: appRoot.textDim }
        }
    }

    component Panel: Rectangle {
        color: appRoot.panel
        radius: 2
        border.color: appRoot.line
        border.width: 1
        gradient: Gradient {
            orientation: Gradient.Vertical
            GradientStop { position: 0.0; color: "#2c3037" }
            GradientStop { position: 0.11; color: "#202329" }
            GradientStop { position: 1.0; color: "#191c21" }
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

    Popup {
        id: stageModelPopup
        objectName: "stageModelPopup"
        parent: Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(760, appRoot.width - 48)
        height: Math.min(760, appRoot.height - 48)
        modal: true
        focus: true
        padding: 20
        background: Rectangle { color: appRoot.panel; radius: 8; border.color: appRoot.gold; border.width: 2 }
        contentItem: ColumnLayout {
            spacing: 14
            Text { text: "STAGE " + (appRoot.editingStage + 1) + " · CHOOSE " + (appRoot.editingStage === 2 ? "IDENTITY ENGINE" : "MODEL"); color: appRoot.brightGold; font.pixelSize: 20; font.bold: true; Layout.fillWidth: true; wrapMode: Text.Wrap }
            Text { Layout.fillWidth: true; text: appRoot.editingStage === 2 ? "Choose the configured identity engine. Its required weights are checked before generation." : "Choose a configured model · " + appRoot.stageChoices.length + " available/configured entries. Scroll to see the full list."; color: appRoot.textDim; font.pixelSize: 15; wrapMode: Text.Wrap }
            ListView {
                objectName: "stageModelChoiceList"
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 8
                model: appRoot.stageChoices
                delegate: Button {
                    objectName: "stageModelChoice" + index
                    width: ListView.view.width
                    implicitHeight: 64
                    enabled: !genesisBridge.busy && (modelData.engine ? modelData.available !== false : (appRoot.editingStage === 0 || modelData.selectable !== false))
                    Accessible.name: modelData.label
                    readonly property bool currentStageOneChoice: appRoot.editingStage === 0 && modelData.model === appRoot.selectedGenerationProfile.model
                    contentItem: Column {
                        spacing: 5
                        Text { width: parent.width; text: modelData.label; color: parent.parent.currentStageOneChoice ? appRoot.brightGold : appRoot.textMain; font.pixelSize: 17; font.bold: true; elide: Text.ElideRight }
                        Text {
                            width: parent.width
                            text: modelData.engine
                                ? (modelData.available !== false ? "Identity pass · available" : "Unavailable · ReActor engine missing on current RunPod")
                                : (modelData.routeReady === true && modelData.runnable === true
                                    ? (parent.parent.currentStageOneChoice ? "Selected · ready to generate" : "Ready to generate")
                                    : "Selectable · generation unavailable on current backend")
                            color: (modelData.engine ? modelData.available !== false : (modelData.routeReady === true && modelData.runnable === true)) ? appRoot.success : appRoot.textDim
                            font.pixelSize: 14
                            elide: Text.ElideRight
                        }
                    }
                    background: Rectangle {
                        radius: 5
                        color: parent.hovered ? appRoot.raised2 : appRoot.raised
                        border.color: parent.currentStageOneChoice ? appRoot.brightGold : (parent.hovered ? appRoot.brightGold : appRoot.line)
                        border.width: parent.currentStageOneChoice ? 2 : 1
                    }
                    onClicked: appRoot.selectStageChoice(index)
                }
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }
            }
            Text { visible: appRoot.stageChoices.length === 0; text: "No compatible models found for this stage on the selected backend. Refresh to check again."; color: appRoot.gold; font.pixelSize: 16; Layout.fillWidth: true; wrapMode: Text.Wrap }
            RowLayout {
                Layout.fillWidth: true
                CheckBox { visible: appRoot.editingStage > 0; text: "Use this stage"; checked: appRoot.editingStage === 1 ? appRoot.useStageTwo : appRoot.useStageThree; enabled: !genesisBridge.busy && (appRoot.editingStage === 1 ? appRoot.selectedStageTwoProfile.selectable !== false : appRoot.stageThreeReady); onToggled: { if (appRoot.editingStage === 1) appRoot.useStageTwo = checked; else appRoot.useStageThree = checked } }
                Item { Layout.fillWidth: true }
                GButton { text: "Close"; onClicked: stageModelPopup.close() }
            }
        }
    }

    component GButton: Button {
        id: button
        property bool active: false
        property bool premium: false
        implicitHeight: appRoot.pageIndex === 0 ? 44 : 36
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
            // Supplied glass-button artwork provides the luminous rounded silhouette;
            // the overlays below keep the existing GENESIS state colors and focus cues.
            BorderImage {
                anchors.fill: parent
                source: appRoot.glassButtonSource
                border.left: 28; border.right: 28; border.top: 20; border.bottom: 20
                horizontalTileMode: BorderImage.Stretch
                verticalTileMode: BorderImage.Stretch
                opacity: button.enabled ? (button.down ? 0.62 : (button.hovered || button.active || button.premium ? 0.94 : 0.78)) : 0.22
            }
            // Deep lower lip gives the control its chunky machined 3D profile.
            Rectangle {
                anchors.left: parent.left; anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: parent.height - 3
                radius: 2
                color: !button.enabled ? "#20242a" : "#0a0805"
                border.color: "#171009"
                border.width: 1
            }
            Rectangle {
                anchors.left: parent.left; anchors.right: parent.right
                y: button.down ? 3 : 0
                height: parent.height - 5
                radius: 2
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    GradientStop { position: 0.00; color: !button.enabled ? "#151515" : (button.hovered ? "#241b0d" : "#17130c") }
                    GradientStop { position: 0.16; color: !button.enabled ? "#111111" : "#151108" }
                    GradientStop { position: 0.50; color: !button.enabled ? "#0f0f0f" : (button.premium || button.active ? "#21180b" : "#11100d") }
                    GradientStop { position: 0.84; color: !button.enabled ? "#080808" : "#0d0c0a" }
                    GradientStop { position: 1.00; color: !button.enabled ? "#20242a" : "#080808" }
                }
                border.color: !button.enabled ? "#303030" : (button.hovered ? appRoot.brightGold : (button.premium || button.active ? appRoot.gold : "#a17b3b"))
                border.width: button.activeFocus || button.hovered || button.active || button.premium ? 2 : 1
                // Recessed centre panel, inspired by the rounded metallic reference.
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 5
                    radius: 2
                    gradient: Gradient {
                        orientation: Gradient.Vertical
                        GradientStop { position: 0.0; color: !button.enabled ? "#111111" : (button.premium || button.active ? "#1d160b" : "#12110e") }
                        GradientStop { position: 0.55; color: !button.enabled ? "#0e0e0e" : (button.premium || button.active ? "#151006" : "#0d0d0c") }
                        GradientStop { position: 1.0; color: !button.enabled ? "#20242a" : "#191c21" }
                    }
                    border.color: !button.enabled ? "#41454c" : (button.premium || button.active ? "#be924b" : "#6e6047")
                    border.width: 1
                }
                // Fine top highlight sells the polished metal edge without neon/glass styling.
                Rectangle {
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    anchors.leftMargin: 12; anchors.rightMargin: 12; anchors.topMargin: 2
                    height: 1
                    radius: 1
                    color: button.enabled ? "#d7ae61" : "#303030"
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
            radius: 10
            color: "transparent"
            border.color: nav.active ? appRoot.gold : (nav.hovered ? appRoot.brightGold : "transparent")
            border.width: nav.active || nav.hovered ? 1 : 0
            BorderImage {
                anchors.fill: parent
                anchors.margins: 1
                source: appRoot.glassButtonSource
                border.left: 28; border.right: 28; border.top: 20; border.bottom: 20
                horizontalTileMode: BorderImage.Stretch
                verticalTileMode: BorderImage.Stretch
                opacity: nav.active ? 0.9 : (nav.hovered ? 0.72 : 0.42)
            }
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

    component PageArtwork: Image {
        property int pageNumber: -1
        property url artwork: ""
        anchors.fill: parent
        source: appRoot.pageIndex === pageNumber && !appRoot.privacyMode && !genesisLayout.backgroundUrl.length ? artwork : ""
        sourceSize.width: 1600
        sourceSize.height: 1000
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        opacity: 0.24
    }

    component MediaCard: Panel {
        id: mediaCard
        objectName: "mediaCard_" + actionKey
        property string titleText: "Tool"
        property string bodyText: ""
        property string iconText: "◆"
        property string actionKey: ""
        property string statusText: "LOCAL TOOL"
        property var tools: []
        gradient: null
        color: "#b3101215"
        Layout.fillWidth: true
        Layout.minimumWidth: 0
        Layout.preferredWidth: 1
        Layout.minimumHeight: 250
        Layout.preferredHeight: 270

        function launchTool(key, title) {
            if (key === "face swap") appRoot.pageIndex = 12
            else if (key === "media viewer") appRoot.pageIndex = 4
            else if (key === "canvas") appRoot.pageIndex = 8
            else appRoot.openMediaTool(key, title, mediaCard.bodyText, mediaCard.statusText)
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 12
            RowLayout {
                Layout.fillWidth: true
                Text { text: mediaCard.iconText; color: appRoot.gold; font.pixelSize: 24; font.bold: true }
                Text { Layout.fillWidth: true; text: mediaCard.titleText; color: appRoot.brightGold; font.pixelSize: 20; font.bold: true; wrapMode: Text.Wrap }
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 68
                clip: true
                radius: 4
                color: "#101215"
                Text { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; anchors.rightMargin: 20; text: mediaCard.iconText; color: appRoot.gold; opacity: 0.35; font.pixelSize: 48 }
                Text { anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 12; text: mediaCard.statusText; color: appRoot.textMain; font.pixelSize: 10; font.bold: true; font.letterSpacing: 1 }
            }
            Text { Layout.fillWidth: true; Layout.minimumHeight: 36; text: mediaCard.bodyText; color: appRoot.textDim; font.pixelSize: 12; wrapMode: Text.Wrap }
            GButton {
                id: mediaOpenButton
                objectName: "mediaOpen_" + mediaCard.actionKey
                Layout.fillWidth: true
                Layout.preferredHeight: 44
                text: mediaCard.tools.length ? "CHOOSE TOOL  ▾" : "OPEN  " + mediaCard.titleText.toUpperCase()
                enabled: !mediaBridge.busy
                onClicked: {
                    if (mediaCard.tools.length) toolMenu.popup()
                    else mediaCard.launchTool(mediaCard.actionKey, mediaCard.titleText)
                }
                Menu {
                    id: toolMenu
                    objectName: "mediaMenu_" + mediaCard.actionKey
                    width: mediaOpenButton.width
                    Repeater {
                        model: mediaCard.tools
                        MenuItem {
                            required property var modelData
                            text: modelData.title
                            enabled: !mediaBridge.busy
                            onTriggered: mediaCard.launchTool(modelData.action, modelData.title)
                        }
                    }
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
            objectName: "workspaceBackground"
            source: appRoot.privacyMode ? "" : (genesisLayout.backgroundUrl.length ? genesisLayout.backgroundUrl : "../assets/lunacy_banner/cockpit_background_soft.jpg")
            fillMode: Image.PreserveAspectCrop
            sourceSize.width: 2048
            sourceSize.height: 1440
            asynchronous: true
            opacity: genesisLayout.backgroundUrl.length ? genesisLayout.backgroundOpacity : 0.10
        }
    }

    ColumnLayout {
        objectName: "genesisMainWorkspace"
        anchors.fill: parent
        anchors.margins: 10
        spacing: 8

        Panel {
            Layout.fillWidth: true
            objectName: "mainPageBanner"
            Layout.preferredHeight: 180
            visible: appRoot.pageIndex !== 8
            clip: true

            Image {
                anchors.fill: parent
                source: "../assets/lunacy_banner/genesis-cockpit-banner-lunacy-latest.png"
                fillMode: Image.PreserveAspectFit
                verticalAlignment: Image.AlignVCenter
                opacity: 1.0
                visible: !privacyMode
            }
            Rectangle {
                anchors.fill: parent
                gradient: Gradient {
                    orientation: Gradient.Vertical
                    GradientStop { position: 0.0; color: "#12000000" }
                    GradientStop { position: 0.58; color: "#32000000" }
                    GradientStop { position: 1.0; color: "#b8080808" }
                }
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
                    spacing: 4

                    Rectangle {
                        width: parent.width
                        height: 24
                        radius: 2
                        color: "#080808"
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
                        height: 28
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
                Layout.preferredWidth: appRoot.width < 1300 ? 190 : 245
                visible: appRoot.pageIndex !== 8
                Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 5
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: appRoot.compactNavigation ? 104 : 200
                        radius: 2
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
                    clip: true
                    PageArtwork { objectName: "generationPageArtwork"; pageNumber: 0; artwork: "../assets/media_cards/reference-5.jpg" }
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
                                gradient: null
                                color: "#b3101215"
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
                                        radius: 2
                                        color: "#080808"
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
                                        background: Rectangle { color: "#14171c"; border.color: appRoot.line; radius: 2 }
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
                                            radius: 2
                                            color: appRoot.selectedPresetName === String(modelData.label || modelData.name || "") ? "#18130a" : "#20242a"
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
                                gradient: null
                                color: "#b3101215"
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 10
                                    spacing: 8
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 164
                                        Layout.minimumHeight: Layout.preferredHeight
                                        Layout.maximumHeight: Layout.preferredHeight
                                        objectName: "generationStageStrip"
                                        spacing: 10
                                        Repeater {
                                            objectName: "generationStageRepeater"
                                            model: [
                                                {title:"STAGE 1", name:appRoot.selectedGenerationProfile.label || "Choose a model", detail:"Create the base image with your selected model", enabled:true},
                                                {title:"STAGE 2", name:appRoot.stageTwoLabel, detail:"Refine the previous output", enabled:appRoot.useStageTwo},
                                                {title:"STAGE 3", name:appRoot.stageThreeLabel, detail:"Apply the identity pass", enabled:appRoot.useStageThree}
                                            ]
                                            Rectangle {
                                                objectName: "generationStageCard" + index
                                                Layout.fillWidth: true
                                                Layout.preferredWidth: 1
                                                Layout.minimumWidth: 0
                                                Layout.fillHeight: true
                                                radius: 4
                                                color: modelData.enabled ? "#17140d" : appRoot.raised
                                                border.color: modelData.enabled ? appRoot.gold : appRoot.line
                                                border.width: modelData.enabled ? 2 : 1
                                                ColumnLayout {
                                                    anchors.fill: parent
                                                    anchors.margins: appRoot.compactNavigation ? 10 : 14
                                                    spacing: 5
                                                    Text { Layout.fillWidth: true; text: modelData.title; color: modelData.enabled ? appRoot.brightGold : appRoot.textDim; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1 }
                                                    Text { objectName: "generationStageModel" + index; Layout.fillWidth: true; text: modelData.name; color: appRoot.textMain; font.pixelSize: 18; font.bold: true; maximumLineCount: 2; elide: Text.ElideRight; wrapMode: Text.Wrap }
                                                    Text { Layout.fillWidth: true; visible: !appRoot.compactNavigation; text: modelData.detail; color: appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap }
                                                    Item { Layout.fillHeight: true }
                                                    Text { text: modelData.enabled ? "CLICK TO CHANGE" : "CLICK TO ENABLE"; color: modelData.enabled ? appRoot.gold : appRoot.textDim; font.pixelSize: 9; font.bold: true }
                                                }
                                                MouseArea {
                                                    objectName: "stageModelBoxClick" + index
                                                    anchors.fill: parent
                                                    enabled: !genesisBridge.busy
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: appRoot.openStageModels(index)
                                                }
                                            }
                                        }
                                    }
                                    SectionLabel { text: "PROMPT" }
                                    Text {
                                        Layout.fillWidth: true
                                        visible: appRoot.presetAttribution.length > 0
                                        textFormat: Text.PlainText
                                        text: "Preset source: " + appRoot.presetAttribution + "\n" + appRoot.presetSettingsNote
                                        color: appRoot.textDim; wrapMode: Text.WordWrap; font.pixelSize: 12
                                    }
                                    TextArea {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        Layout.minimumHeight: 72
                                        Layout.preferredHeight: 180
                                        objectName: "generationPromptEditor"
                                        text: appRoot.generationPrompt
                                        placeholderText: "Preset or pose fills this automatically — edit anything you want."
                                        color: appRoot.textMain
                                        wrapMode: TextEdit.Wrap
                                        onTextChanged: if (activeFocus) appRoot.generationPrompt = text
                                        background: Rectangle { color: "#14171c"; border.color: appRoot.line; radius: 2 }
                                    }
                                    TextField {
                                        Layout.fillWidth: true
                                        text: appRoot.generationNegativePrompt
                                        placeholderText: "Negative prompt (optional)"
                                        color: appRoot.textMain
                                        onTextChanged: if (activeFocus) appRoot.generationNegativePrompt = text
                                        background: Rectangle { color: "#14171c"; border.color: appRoot.line; radius: 2 }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Text { text: "Preset: " + appRoot.selectedPresetName; color: appRoot.gold; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight }
                                        Text { text: "Pose reference: " + appRoot.selectedPoseName; color: appRoot.textDim; font.pixelSize: 10; Layout.fillWidth: true; elide: Text.ElideRight; horizontalAlignment: Text.AlignRight }
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        GButton {
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 44
                                            active: enabled
                                            objectName: "generateButton"
                                            text: genesisBridge.busy ? "GENERATING…" : "GENERATE"
                                            enabled: !genesisBridge.busy
                                                && appRoot.selectedGenerationProfile.routeReady === true && appRoot.selectedGenerationProfile.runnable === true
                                                && (appRoot.generationPrompt.trim().length > 0 || appRoot.selectedPosePrompt.trim().length > 0)
                                                && (!appRoot.selectedGenerationProfile.sourceRequired || appRoot.generationSource.toString().length > 0)
                                            onClicked: appRoot.generateCurrent()
                                        }
                                        GButton {
                                            visible: genesisBridge.busy
                                            enabled: genesisBridge.busy
                                            Layout.preferredWidth: 110
                                            Layout.preferredHeight: 44
                                            text: "CANCEL"
                                            onClicked: genesisBridge.cancelGeneration()
                                        }
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
                                        Layout.fillHeight: true
                                        Layout.preferredHeight: 180
                                        objectName: "generationResultPreview"
                                        Layout.minimumHeight: 100
                                        radius: 2
                                        color: "#080808"
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
                                    Flow {
                                        Layout.fillWidth: true; spacing: 6
                                        GButton { text: "Keep / Save"; enabled: !genesisBridge.busy && genesisBridge.previewUrl.length > 0; onClicked: genesisBridge.keepResult() }
                                        GButton { text: "Refine / More Realism"; enabled: !genesisBridge.busy && appRoot.finishAvailability.refine; onClicked: genesisBridge.queueFinish(true, false, 0, appRoot.generationSource.toString(), appRoot.stageTwoModel, appRoot.finishLora, appRoot.finishLoraStrength) }
                                        GButton { text: "Identity / Face Lock"; enabled: !genesisBridge.busy && appRoot.finishAvailability.identity; onClicked: genesisBridge.queueFinish(false, true, 0, appRoot.generationSource.toString(), appRoot.stageTwoModel, "None", 0) }
                                        GButton { text: "Upscale " + appRoot.finishScale + "×"; enabled: !genesisBridge.busy && appRoot.finishAvailability.upscale; onClicked: genesisBridge.queueFinish(false, false, appRoot.finishScale, appRoot.generationSource.toString(), appRoot.stageTwoModel, "None", 0) }
                                        GButton { text: "Full Finish"; enabled: !genesisBridge.busy && appRoot.finishAvailability.refine && appRoot.finishAvailability.identity && appRoot.finishAvailability.upscale; onClicked: genesisBridge.queueFinish(true, true, appRoot.finishScale, appRoot.generationSource.toString(), appRoot.stageTwoModel, appRoot.finishLora, appRoot.finishLoraStrength) }
                                    }
                                    GButton { text: "Compare with previous result"; enabled: appRoot.comparisonSource.length > 0; onClicked: finishCompare.open() }
                                    GButton { text: "Reject finishing result / return to previous"; enabled: !genesisBridge.busy && genesisBridge.finishingResults.length > 1; onClicked: genesisBridge.rejectFinishingResult() }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        ComboBox { model: ["2×", "4×"]; onActivated: appRoot.finishScale = currentIndex === 0 ? 2 : 4 }
                                        ComboBox { Layout.fillWidth: true; model: (appRoot.selectedStageTwoProfile.loras || ["None"]).filter(function(name) { return name !== "refcontrol_v2_poses.safetensors" }); currentIndex: Math.max(0, model.indexOf(appRoot.finishLora)); onActivated: appRoot.finishLora = currentText }
                                        SpinBox { from: 0; to: 100; value: 65; editable: true; onValueModified: appRoot.finishLoraStrength = value / 100.0 }
                                    }
                                    Text { Layout.fillWidth: true; text: appRoot.finishAvailability.reason || ""; color: appRoot.textDim; wrapMode: Text.Wrap }
                                    ComboBox { Layout.fillWidth: true; model: genesisBridge.finishingResults; textRole: "label"; onActivated: genesisBridge.selectFinishingResult(model[currentIndex].source) }
                                    CharacterReferences { Layout.fillWidth: true; bridge: genesisBridge; privatePreview: appRoot.privacyMode; inputSource: appRoot.generationSource.toString(); onUseMaster: function(source) { appRoot.generationSource = source } }
                                    Text { Layout.fillWidth: true; text: "Output: " + genesisBridge.outputFolder; color: appRoot.textDim; font.pixelSize: 9; elide: Text.ElideMiddle }
                                    RowLayout {
                                    Layout.fillWidth: true
                                    GButton { Layout.preferredWidth: implicitWidth; text: "Output location"; onClicked: genesisBridge.chooseOutputFolder() }
                                    GButton { Layout.preferredWidth: implicitWidth; text: "Edit in Canvas"; enabled: genesisBridge.previewUrl.length > 0; onClicked: { appRoot.editSource = genesisBridge.previewUrl; appRoot.pageIndex = 8 } }
                                    }
                                }
                            }

                            Panel {
                                gradient: null
                                color: "#b3101215"
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
                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: generationSettings.availableWidth < 290 ? 1 : 2
                                        columnSpacing: 6
                                        rowSpacing: 6
                                        GButton { text: "Save endpoint"; enabled: !genesisBridge.busy; onClicked: backendBridge.setEndpoint(runpodEndpoint.text) }
                                        GButton {
                                            text: backendBridge.connected ? "Connected" : "Connect RunPod"
                                            enabled: !genesisBridge.busy && !backendBridge.checking && !backendBridge.connected
                                            onClicked: backendBridge.connectRemote()
                                        }
                                        GButton {
                                            text: "Disconnect"
                                            enabled: !genesisBridge.busy && backendBridge.connected
                                            onClicked: backendBridge.disconnectRemote()
                                        }
                                        GButton {
                                            text: backendBridge.checking ? "Checking…" : "Refresh"
                                            enabled: backendBridge.connected && !backendBridge.checking
                                            onClicked: backendBridge.refresh()
                                        }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: backendBridge.connected
                                            ? "RunPod connection active. Disconnect stops GENESIS remote polling."
                                            : "RunPod disconnected by default. GENESIS will not contact the saved endpoint until Connect RunPod is pressed."
                                        color: backendBridge.connected ? appRoot.gold : appRoot.textDim
                                        font.pixelSize: 10
                                        wrapMode: Text.Wrap
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: "Destination: " + (appRoot.selectedGenerationProfile.destination || "UNAVAILABLE")
                                        color: appRoot.gold; font.pixelSize: 12; font.bold: true
                                    }
                                    SectionLabel { text: "STAGE 1 · MODEL" }
                                    ComboBox {
                                        objectName: "stageOneModelPicker"
                                        Layout.fillWidth: true
                                        enabled: !genesisBridge.busy && appRoot.stageOneSelectableChoices.length > 0
                                        model: appRoot.stageOneSelectableChoices
                                        textRole: "label"
                                        currentIndex: appRoot.stageOneChoiceIndex
                                        onActivated: appRoot.selectStageOneAvailableChoice(currentIndex)
                                    }
                                    Text { Layout.fillWidth: true; text: appRoot.selectedGenerationProfile.note || ""; color: appRoot.textDim; font.pixelSize: 11; wrapMode: Text.Wrap }
                                    Text { Layout.fillWidth: true; text: "MODEL PATH: " + (appRoot.selectedGenerationProfile.modelPath || appRoot.selectedGenerationProfile.model || "Unknown"); color: appRoot.textDim; font.pixelSize: 11; wrapMode: Text.WrapAnywhere }
                                    Text { Layout.fillWidth: true; text: "WORKFLOW: " + (appRoot.selectedGenerationProfile.workflowPath || "Not mapped"); color: appRoot.textDim; font.pixelSize: 11; wrapMode: Text.WrapAnywhere }
                                    SectionLabel { text: "COMPATIBLE LORA" }
                                    Text {
                                        Layout.fillWidth: true
                                        text: (appRoot.selectedGenerationProfile.maxLoras || 0) > 0
                                            ? "Choose up to 3 compatible LoRAs below, each with its own strength."
                                            : "No compatible LoRAs available for this model."
                                        color: appRoot.textDim; font.pixelSize: 14; wrapMode: Text.Wrap
                                    }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        visible: (appRoot.selectedGenerationProfile.maxLoras || 0) > 0
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
                                            currentIndex: Math.max(0, model.indexOf(appRoot.selectedLoraTwo))
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
                                            currentIndex: Math.max(0, model.indexOf(appRoot.selectedLoraThree))
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
                                    Text { Layout.fillWidth: true; visible: text.length > 0; text: appRoot.selectedGenerationProfile.qualityNote || ""; color: appRoot.textDim; wrapMode: Text.Wrap; font.pixelSize: 14 }
                                    GridLayout {
                                        Layout.fillWidth: true
                                        columns: 3
                                        GButton { Layout.preferredWidth: implicitWidth; text: "Fast"; active: appRoot.qualityPresetActive("Fast", 512, 512); onClicked: appRoot.applyQualityPreset("Fast", 512, 512) }
                                        GButton { Layout.preferredWidth: implicitWidth; text: "Balanced"; active: appRoot.qualityPresetActive("Balanced", 768, 1152); onClicked: appRoot.applyQualityPreset("Balanced", 768, 1152) }
                                        GButton { Layout.preferredWidth: implicitWidth; text: "Quality"; active: appRoot.qualityPresetActive("Quality", 1024, 1024); onClicked: appRoot.applyQualityPreset("Quality", 1024, 1024) }
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
                                        Text { Layout.columnSpan: 2; Layout.fillWidth: true; text: appRoot.selectedGenerationProfile.identityGuidance || "Keep model defaults initially."; color: appRoot.textDim; font.pixelSize: 14; wrapMode: Text.Wrap }
                                        Text { text: "Denoise"; color: appRoot.textDim; font.pixelSize: 10 }
                                        SpinBox { Layout.fillWidth: true; from: 0; to: 100; value: Math.round(appRoot.generationDenoise * 100); enabled: !appRoot.activeGenerationDefaults.denoiseFixed; editable: true; onValueModified: appRoot.generationDenoise = value / 100.0; textFromValue: function(v) { return (v / 100.0).toFixed(2) }; valueFromText: function(t) { return Math.round(Number(t) * 100) } }
                                        Text { text: "Sampler"; color: appRoot.textDim; font.pixelSize: 10 }
                                        ComboBox { Layout.fillWidth: true; model: ["er_sde", "euler", "euler_ancestral", "res_multistep", "dpmpp_2m", "dpmpp_2m_sde", "dpmpp_sde", "dpmpp_3m_sde"]; currentIndex: Math.max(0, model.indexOf(appRoot.generationSampler)); onActivated: appRoot.generationSampler = currentText }
                                        Text { text: "Scheduler"; color: appRoot.textDim; font.pixelSize: 10 }
                                        ComboBox { Layout.fillWidth: true; enabled: !appRoot.activeGenerationDefaults.schedulerFixed; model: appRoot.activeGenerationDefaults.schedulerFixed ? ["Flux2Scheduler"] : ["beta", "simple", "normal", "karras", "sgm_uniform"]; currentIndex: Math.max(0, model.indexOf(appRoot.generationScheduler)); onActivated: appRoot.generationScheduler = currentText }
                                    }
                                    SectionLabel { text: "PIPELINE" }
                                    ComboBox {
                                        Layout.fillWidth: true
                                        model: ["Single model", "3-stage · Selected model → Refine → Identity"]
                                        currentIndex: (appRoot.useStageTwo && appRoot.useStageThree) ? 1 : 0
                                        onActivated: {
                                            var fullPipeline = currentIndex === 1
                                            appRoot.useStageTwo = fullPipeline
                                            appRoot.useStageThree = fullPipeline
                                        }
                                    }
                                    Text {
                                        Layout.fillWidth: true
                                        text: appRoot.useStageTwo && appRoot.useStageThree
                                            ? "Stage 1 " + (appRoot.selectedGenerationProfile.label || "selected model") + " → Stage 2 refinement → Stage 3 identity lock"
                                            : "Single-model generation; stages can also be enabled individually below."
                                        color: appRoot.textDim
                                        font.pixelSize: 10
                                        wrapMode: Text.Wrap
                                    }
                                    CheckBox { text: "Stage 2 · refine"; checked: appRoot.useStageTwo; enabled: !genesisBridge.busy; onToggled: appRoot.useStageTwo = checked }
                                    GButton { Layout.fillWidth: true; text: appRoot.stageTwoLabel; enabled: !genesisBridge.busy; onClicked: appRoot.openStageModels(1) }
                                    Text { Layout.fillWidth: true; visible: appRoot.useStageTwo; text: "MODEL PATH: " + (appRoot.selectedStageTwoProfile.modelPath || appRoot.stageTwoModel || "Unknown"); color: appRoot.textDim; font.pixelSize: 12; wrapMode: Text.WrapAnywhere }
                                    Text { Layout.fillWidth: true; visible: appRoot.useStageTwo; text: "WORKFLOW: " + (appRoot.selectedStageTwoProfile.workflowPath || "Not mapped"); color: appRoot.textDim; font.pixelSize: 12; wrapMode: Text.WrapAnywhere }
                                    CheckBox { text: "Stage 3 · identity lock"; checked: appRoot.useStageThree; enabled: !genesisBridge.busy && appRoot.stageThreeReady; onToggled: appRoot.useStageThree = checked }
                                    GButton { Layout.fillWidth: true; text: appRoot.stageThreeLabel; enabled: !genesisBridge.busy; onClicked: appRoot.openStageModels(2) }
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
                            TextField { Layout.preferredWidth: 280; placeholderText: "Search poses…"; color: appRoot.textMain; onTextChanged: appRoot.poseSearch = text; background: Rectangle { color: "#14171c"; border.color: appRoot.line; radius: 2 } }
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
                                        radius: 2
                                        color: "#080808"
                                        border.color: appRoot.generationSource.toString().length ? appRoot.gold : appRoot.line
                                        Image { anchors.fill: parent; anchors.margins: 6; source: appRoot.generationSource; fillMode: Image.PreserveAspectFit; visible: appRoot.generationSource.toString().length > 0 && !privacyMode }
                                        Text { anchors.centerIn: parent; text: appRoot.generationSource.toString().length ? (privacyMode ? "PRIVATE" : "") : "NO SOURCE LOADED"; color: appRoot.textDim; font.pixelSize: 11 }
                                    }
                                    SectionLabel { text: "SELECTED POSE" }
                                    GButton { objectName: "openSkeletonEditor"; Layout.fillWidth: true; text: "Edit Skeleton"; onClicked: skeletonBridge.openEditor(String(appRoot.selectedPoseSource)) }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 160
                                        Layout.minimumHeight: 140
                                        spacing: 6
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.fillHeight: true
                                            radius: 2; color: "#080808"; border.color: appRoot.gold
                                            Image { anchors.fill: parent; anchors.margins: 6; source: appRoot.selectedPoseThumbnail; fillMode: Image.PreserveAspectFit; asynchronous: true }
                                            Text { anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 6; text: "PREVIEW"; color: appRoot.brightGold; font.pixelSize: 8; font.bold: true }
                                        }
                                        Rectangle {
                                            Layout.fillWidth: true; Layout.fillHeight: true
                                            radius: 2; color: "#080808"; border.color: appRoot.line
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
                                    radius: 2
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
                        ColumnLayout {
                            objectName: "workflowGraphWorkspace"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            spacing: 10
                            Text { Layout.fillWidth: true; text: "COMFYUI NODE GRAPH IN GENESIS"; color: appRoot.brightGold; font.pixelSize: 20; font.bold: true }
                            Text { Layout.fillWidth: true; text: workflowGraphBridge.status; color: appRoot.textDim; font.pixelSize: 12; wrapMode: Text.Wrap }
                            RowLayout {
                                Layout.fillWidth: true
                                GButton { text: "New graph"; onClicked: { workflowGraphBridge.openGraph(""); workflowGraphBridge.newGraph() } }
                                GButton { text: "Load JSON graph"; onClicked: { workflowGraphBridge.openGraph(""); workflowGraphBridge.chooseGraph() } }
                            }
                            ScrollView {
                                id: workflowScroll
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                contentWidth: availableWidth
                                clip: true
                                GridLayout {
                                    id: workflowGrid
                                    width: workflowScroll.availableWidth
                                    columns: width >= 850 ? 2 : 1
                                    rowSpacing: 10
                                    columnSpacing: 10
                                    Repeater {
                                        model: workflowGraphBridge.workflows
                                        Panel {
                                            Layout.fillWidth: true
                                            Layout.preferredWidth: (workflowGrid.width - (workflowGrid.columns - 1) * workflowGrid.columnSpacing) / workflowGrid.columns
                                            Layout.preferredHeight: 146
                                            ColumnLayout {
                                                anchors.fill: parent
                                                anchors.margins: 14
                                                Text { text: modelData.name; color: appRoot.brightGold; font.pixelSize: 17; font.bold: true }
                                                Text { Layout.fillWidth: true; text: modelData.file; color: appRoot.textDim; font.pixelSize: 10; elide: Text.ElideMiddle }
                                                Item { Layout.fillHeight: true }
                                                GButton { text: "Edit node graph"; active: true; onClicked: workflowGraphBridge.openGraph(modelData.file) }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Item {
                    clip: true
                    PageArtwork { objectName: "mediaPageArtwork"; pageNumber: 3; artwork: "../assets/media_cards/reference-3.jpg" }
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
                            id: mediaGrid
                            objectName: "mediaToolsGrid"
                            width: mediaScroll.availableWidth
                            columns: width >= 1050 ? 6 : (width >= 650 ? 2 : 1)
                            rowSpacing: 16
                            columnSpacing: 16
                            Repeater {
                                id: mediaCardRepeater
                                objectName: "mediaCardRepeater"
                                model: [
                                    {title:"Canvas & Cut-outs", body:"Build a layered scene or prepare transparent images, one at a time or in a batch.", action:"canvas", icon:"✂", status:"CREATE / EDIT", tools:[{title:"Open Canvas", action:"canvas"}, {title:"Background Remover", action:"background remover"}, {title:"Batch Cut-outs", action:"batch background"}]},
                                    {title:"Audio & Video", body:"Extract an MP3 audio track or save a video copy with its original audio.", action:"audio video", icon:"♫", status:"FFMPEG", tools:[{title:"Extract MP3", action:"extract audio"}, {title:"Extract Video", action:"extract video"}]},
                                    {title:"Media Library", body:"Browse local images, inspect metadata and revisit your results.", action:"media viewer", icon:"▧", status:"BROWSE / INSPECT", tools:[]},
                                    {title:"Photo Organisation", body:"Review duplicate images or organise your photo library by people.", action:"organisation", icon:"◫", status:"REVIEW / ORGANISE", tools:[{title:"Duplicate Finder", action:"duplicate finder"}, {title:"Face Organiser", action:"face organiser"}]},
                                    {title:"Face Swap", body:"Open the identity workspace with ReActor and local FaceFusion options.", action:"face swap", icon:"◎", status:backendBridge.mode, tools:[]}
                                ]
                                MediaCard {
                                    Layout.columnSpan: mediaGrid.columns === 6 ? (index < 3 ? 2 : 3) : (mediaGrid.columns === 2 && index === 4 ? 2 : 1)
                                    Layout.preferredWidth: (mediaGrid.width - (mediaGrid.columns - 1) * mediaGrid.columnSpacing) / mediaGrid.columns * Layout.columnSpan + (Layout.columnSpan - 1) * mediaGrid.columnSpacing
                                    Layout.maximumWidth: Layout.preferredWidth
                                    titleText:modelData.title; bodyText:modelData.body; actionKey:modelData.action
                                    iconText:modelData.icon; statusText:modelData.status; tools:modelData.tools
                                }
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
                            Rectangle { Layout.fillWidth:true; Layout.fillHeight:true; Layout.minimumHeight:180; color:"#080808"; radius: 2; border.color:appRoot.line
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
                    onHomeRequested: appRoot.pageIndex = 14
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
                                    Rectangle { Layout.fillWidth:true; Layout.preferredHeight:150; radius: 2; color:"#080808"; border.color:appRoot.gold
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
                        Panel {
                            Layout.fillWidth: true; Layout.preferredHeight: 180
                            ColumnLayout {
                                anchors.fill: parent; anchors.margins: 18; spacing: 12
                                Text { text: "WORKSPACE BACKGROUND"; color: appRoot.brightGold; font.pixelSize: 18; font.bold: true }
                                Text { Layout.fillWidth: true; text: "Choose your own image for the workspace. Your choice is remembered; Privacy Mode hides it."; color: appRoot.textDim; wrapMode: Text.Wrap; font.pixelSize: 12 }
                                RowLayout {
                                    Layout.fillWidth: true
                                    GButton { objectName: "chooseBackgroundButton"; text: "Choose image…"; onClicked: genesisLayout.chooseBackground() }
                                    GButton { text: "Reset"; onClicked: genesisLayout.resetBackground() }
                                    Text { text: "Opacity"; color: appRoot.textDim }
                                    Slider { Layout.fillWidth: true; from: 0; to: 1; value: genesisLayout.backgroundOpacity; onMoved: genesisLayout.setBackgroundOpacity(value) }
                                    Text { text: Math.round(genesisLayout.backgroundOpacity * 100) + "%"; color: appRoot.textDim }
                                }
                            }
                        }
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
                                Rectangle { Layout.fillWidth:true; Layout.fillHeight:true; Layout.minimumHeight:180; color:"#070707"; radius: 2; border.color:appRoot.faceSwapTarget.toString().length ? appRoot.gold : appRoot.line
                                    Image { anchors.fill:parent; anchors.margins:8; source:appRoot.faceSwapTarget; fillMode:Image.PreserveAspectFit; visible:appRoot.faceSwapTarget.toString().length > 0 && !privacyMode }
                                    Text { anchors.centerIn:parent; text:appRoot.faceSwapTarget.toString().length ? (privacyMode ? "PRIVATE" : "") : "NO TARGET IMAGE"; color:appRoot.textDim; font.pixelSize:16 }
                                }
                                RowLayout { Layout.fillWidth:true; GButton { Layout.preferredWidth: implicitWidth; text:"Load Target Image"; onClicked:appRoot.chooseFaceSwapTarget() } GButton { Layout.preferredWidth:80; text:"Clear"; enabled:appRoot.faceSwapTarget.toString().length>0; onClicked:appRoot.faceSwapTarget="" } }
                            } }
                            Panel { Layout.fillWidth:true; Layout.fillHeight:true; ColumnLayout { anchors.fill:parent; anchors.margins:14; spacing:10
                                SectionLabel { text:"SOURCE IDENTITY · FACE TO USE" }
                                Rectangle { Layout.fillWidth:true; Layout.fillHeight:true; Layout.minimumHeight:180; color:"#070707"; radius: 2; border.color:appRoot.faceSwapSource.toString().length ? appRoot.gold : appRoot.line
                                    Image { anchors.fill:parent; anchors.margins:8; source:appRoot.faceSwapSource; fillMode:Image.PreserveAspectFit; visible:appRoot.faceSwapSource.toString().length > 0 && !privacyMode }
                                    Text { anchors.centerIn:parent; text:appRoot.faceSwapSource.toString().length ? (privacyMode ? "PRIVATE" : "") : "NO SOURCE IMAGE"; color:appRoot.textDim; font.pixelSize:16 }
                                }
                                RowLayout { Layout.fillWidth:true; GButton { Layout.preferredWidth: implicitWidth; text:"Load Source Image"; onClicked:appRoot.chooseFaceSwapSource() } GButton { Layout.preferredWidth:80; text:"Clear"; enabled:appRoot.faceSwapSource.toString().length>0; onClicked:appRoot.faceSwapSource="" } }
                            } }
                            Panel { Layout.preferredWidth:360; Layout.fillHeight:true; ColumnLayout { anchors.fill:parent; anchors.margins:14; spacing:10
                                SectionLabel { text:"RESULT" }
                                Rectangle { Layout.fillWidth:true; Layout.fillHeight:true; Layout.minimumHeight:180; color:"#070707"; radius: 2; border.color:appRoot.line
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
                // GENESIS_GROK_PAGE_INSERT

                Item {
                    objectName: "homeWorkspace"
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 18
                        RowLayout {
                            Layout.fillWidth: true
                            ColumnLayout {
                                Layout.fillWidth: true
                                Text { text: "HOME"; color: appRoot.brightGold; font.pixelSize: 30; font.bold: true; font.letterSpacing: 3 }
                                Text { text: "Your creative workspace"; color: appRoot.textDim; font.pixelSize: 14 }
                            }
                            GButton { text: "Settings"; onClicked: appRoot.pageIndex = 10 }
                        }
                        GridLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            columns: width < 1000 ? 2 : 3
                            rowSpacing: 14; columnSpacing: 14
                            Repeater {
                                objectName: "homeCardRepeater"
                                model: [
                                    {title: "Image Generation", artwork: "../assets/home_buttons/image-swap_2026-08-22_22-36-37.jpg", icon: "▣", detail: "Create with your models, references and workflows", page: 0},
                                    {title: "GENESIS Mungbean", artwork: "../assets/home_buttons/t.png", icon: "✧", detail: "Open the Grok-style image and video studio", page: 13},
                                    {title: "Canvas", artwork: "../assets/home_buttons/e7a0662e0c0a4c7e878c6d28827e813f.jpg", icon: "⤢", detail: "Arrange layers, resize images and prepare cutouts", page: 8},
                                    {title: "Media Tools", artwork: "../assets/home_buttons/r.png", icon: "✦", detail: "Browse, organise and work with your media", page: 3},
                                    {title: "Camera Hub", artwork: "../assets/home_buttons/Untitled-1.png", icon: "●", detail: "Open your cameras and live views", page: 5},
                                    {title: "System Tools", artwork: "../assets/home_buttons/1248519.small.jpg", icon: "⚙", detail: "Check services, models and storage", page: 7}
                                ]
                                Button {
                                    required property var modelData
                                    objectName: "homeCard_" + modelData.page
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    Layout.minimumWidth: 220; Layout.minimumHeight: 120
                                    Layout.preferredWidth: 300; Layout.preferredHeight: 210
                                    padding: 22
                                    Accessible.name: modelData.title
                                    onClicked: appRoot.pageIndex = modelData.page
                                    background: Rectangle {
                                        radius: 2
                                        color: parent.down ? "#342818" : parent.hovered ? "#231f18" : "#111111"
                                        border.color: parent.hovered || parent.activeFocus ? appRoot.gold : "#4b3e29"
                                        border.width: parent.activeFocus ? 2 : 1
                                        clip: true
                                        Image {
                                            anchors.fill: parent
                                            anchors.margins: 2
                                            source: modelData.artwork
                                            fillMode: Image.PreserveAspectCrop
                                            asynchronous: true
                                            sourceSize.width: 640
                                            sourceSize.height: 420
                                            smooth: true
                                        }
                                        Rectangle {
                                            anchors.fill: parent
                                            anchors.margins: 1
                                            gradient: Gradient {
                                                orientation: Gradient.Vertical
                                                GradientStop { position: 0.0; color: parent.parent.down ? "#55150f08" : "#66080808" }
                                                GradientStop { position: 0.58; color: parent.parent.down ? "#99150f08" : "#aa080808" }
                                                GradientStop { position: 1.0; color: parent.parent.down ? "#dd150f08" : "#e0080808" }
                                            }
                                        }
                                    }
                                    contentItem: ColumnLayout {
                                        spacing: 10
                                        Text { text: modelData.icon; color: appRoot.gold; font.pixelSize: 30 }
                                        Text { Layout.fillWidth: true; text: modelData.title; color: appRoot.brightGold; font.pixelSize: 21; font.bold: true; wrapMode: Text.Wrap }
                                        Text { Layout.fillWidth: true; text: modelData.detail; color: appRoot.textDim; font.pixelSize: 12; wrapMode: Text.Wrap }
                                        Item { Layout.fillHeight: true }
                                    }
                                }
                            }
                        }
                    }
                }

            }
        }
    }
    }
}
