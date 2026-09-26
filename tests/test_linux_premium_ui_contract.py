from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QML = ROOT / "genesis" / "qt_ui" / "MainPremiumLinux.qml"
LAUNCHER = ROOT / "qt_cockpit_linux_premium.py"
ASSISTANT = ROOT / "genesis" / "assistant_bridge.py"
MEDIA_BRIDGE = ROOT / "genesis" / "media_bridge.py"
SHELL_LAUNCHER = ROOT / "launch-qt-cockpit.sh"
LLAMA_SERVICE = ROOT / "systemd" / "genesis-llama.service"
ASSISTANT_SERVICE = ROOT / "systemd" / "genesis-assistant.service"
QWEN_SERVICE = ROOT / "systemd" / "genesis-qwen.service"


def source() -> str:
    return QML.read_text(encoding="utf-8")


def test_premium_linux_qml_exists():
    assert QML.is_file()
    assert "GENESIS c0ckpit · Linux" in source()
    assert "Keep walking Allan." in source()


def test_source_image_is_a_real_preview_not_filename_only():
    qml = source()
    assert '"Load image" : "Load Source Image"' in qml
    assert "genesisBridge.chooseSourceImage()" in qml
    assert "source: appRoot.generationSource" in qml
    assert "fillMode: Image.PreserveAspectFit" in qml
    assert "DropArea" in qml
    assert "Source image stays loaded when you change presets" in qml


def test_easy_presets_are_first_class_visual_controls():
    qml = source()
    assert 'text: "2 · EASY PRESETS"' in qml
    assert "model: appRoot.filteredPresets()" in qml
    assert "appRoot.applyPreset(modelData)" in qml
    assert 'text: "Pose Library"; onClicked: appRoot.pageIndex = 1' in qml


def test_full_pose_browser_and_source_controls_are_available_together():
    qml = source()
    assert "model: appRoot.filteredPoses()" in qml
    assert "appRoot.applyPose(modelData)" in qml
    assert 'text: "Pose Library"; active: true' in qml
    assert '"Load Source Image"' in qml
    assert 'text: "Use Pose in Create"' in qml


def test_generation_keeps_model_lora_and_stage_controls():
    qml = source()
    assert 'text: "3 · MODEL / WORKFLOW"' in qml
    assert 'text: "COMPATIBLE LORA"' in qml
    assert 'text: "LORA TRIGGER · " + appRoot.selectedLoraTriggerText()' in qml
    assert 'text: "Stage 2 · refine"' in qml
    assert 'text: "Stage 3 · identity lock"' in qml
    assert 'model: ["Single model", "3-stage · Phr00t → Refine → Identity"]' in qml
    assert "appRoot.useStageTwo = fullPipeline" in qml
    assert "appRoot.useStageThree = fullPipeline" in qml
    assert '"ReActor · Inswapper ✓"' in qml
    assert '"ReActor · ReSwapper ✓"' in qml
    assert '"ReActor · HyperSwap ✓"' in qml
    assert '"PuLID FLUX.2 · pending"' in qml
    assert "genesisBridge.setStageThreeEngine" in qml
    assert 'text: "Final upscale"' in qml
    assert "genesisBridge.queueGenerateAdvanced(" in qml


def test_linux_launcher_loads_full_pose_index_premium_qml_and_ai():
    launcher = LAUNCHER.read_text(encoding="utf-8")
    assert "load_pose_items(limit=600)" in launcher
    assert 'UI_ROOT / "MainPremiumLinux.qml"' in launcher
    assert '"settings": 10' in launcher
    assert '"ai": 11' in launcher
    assert 'label:"AI Assistant", page:11' in launcher
    assert '"grok": 13' in launcher
    assert 'label:"Grok Imagine", page:13' in source()
    assert "GROK_PAGE_QML" in launcher
    assert 'moduleBridge.triggerAction("grok imagine")' in launcher
    assert "AssistantBridge" in launcher
    feefee = Path("genesis/qt_ui/FeeFeeChat.qml").read_text(encoding="utf-8")
    assert "FeeFeeChat" in launcher
    assert 'model: ["CHAT", "BUILD", "STUDIO"]' in feefee
    assert 'model: ["AUTO", "LOCAL", "CLOUD"]' in feefee


def test_local_assistant_preserves_chosen_model_split():
    assistant = ASSISTANT.read_text(encoding="utf-8")
    llama = LLAMA_SERVICE.read_text(encoding="utf-8")
    local = ASSISTANT_SERVICE.read_text(encoding="utf-8")
    qwen = QWEN_SERVICE.read_text(encoding="utf-8")
    assert "Rocinante is intentionally excluded" in assistant
    assert "Qwen3-Coder-30B-A3B" in assistant
    assert "integrations.ASSISTANT_URL" in assistant
    assert "integrations.QWEN_URL" in assistant
    assert "Rocinante-X-12B-v1-Heretic-Uncensored.Q5_K_M.gguf" in llama
    assert "--port 8081" in llama
    assert "qwen2.5-coder-14b-instruct-q4_k_m.gguf" in local
    assert "--port 8083" in local
    assert "Qwen3-Coder-30B-A3B-Instruct-UD-Q3_K_XL.gguf" in qwen
    assert "--port 8082" in qwen


def test_media_tools_are_wired_to_real_backend_operations():
    qml = source()
    launcher = LAUNCHER.read_text(encoding="utf-8")
    bridge = MEDIA_BRIDGE.read_text(encoding="utf-8")
    assert 'context.setContextProperty("mediaBridge", media_bridge)' in launcher
    assert "mediaBridge.chooseToolInput(mediaToolKey)" in qml
    assert "mediaBridge.runSelectedTool(mediaToolKey)" in qml
    assert "def chooseToolInput(self, kind: str)" in bridge
    assert "def runSelectedTool(self, kind: str)" in bridge
    assert "remove_background" in bridge
    assert "upscale_enhance" in bridge
    assert "extract_media" in bridge


def test_media_cards_open_dedicated_workspace_before_running_tools():
    qml = source()
    assert "property bool mediaToolOpen: false" in qml
    assert "function openMediaTool(key, title, description, status)" in qml
    assert 'text: "‹  MEDIA TOOLS"' in qml
    assert 'text: mediaBridge.busy ? "WORKING…" : appRoot.mediaToolRunLabel()' in qml
    assert "function mediaToolInputHint()" in qml
    assert "function mediaToolIsReview()" in qml
    assert "onClicked: appRoot.runMediaTool()" in qml
    assert "visible: appRoot.mediaToolOpen" in qml
    assert "appRoot.openMediaTool(key, title, mediaCard.bodyText, mediaCard.statusText)" in qml


def test_page_header_binds_to_component_properties():
    qml = source()
    assert "id: pageHeader" in qml
    assert "text: pageHeader.titleText" in qml
    assert "text: pageHeader.subtitleText" in qml
    assert "text: parent.titleText" not in qml
    assert "text: parent.subtitleText" not in qml


def test_shell_launcher_uses_premium_entrypoint():
    shell = SHELL_LAUNCHER.read_text(encoding="utf-8")
    assert "qt_cockpit_linux_premium.py" in shell


def test_image_studio_launcher_keeps_gpu_backend_off_until_work_is_requested():
    launcher = (ROOT / "launch-image-studio.sh").read_text(encoding="utf-8")
    backend = (ROOT / "qt_cockpit.py").read_text(encoding="utf-8")
    assert "integrations.start_user_service" not in launcher
    assert "systemctl --user start genesis-comfyui.service" not in launcher
    assert "_connect_comfyui" in backend
    assert "integrations.start_user_service" in backend
    assert "integrations.gpu_kernel_abort_reason" in backend
    assert "GENESIS_COMFY_URL" in backend


def test_premium_launcher_is_single_instance_guarded():
    launcher = LAUNCHER.read_text(encoding="utf-8")
    assert "QLockFile" in launcher
    assert "genesis-cockpit-premium.lock" in launcher
    assert "tryLock(0)" in launcher


def test_premium_linux_visual_polish_stays_charcoal_gold_and_compact():
    qml = source()
    for legacy_blue in ("#17324a", "#242a30", "#152b3b", "#39424b", "#24292f", "#5575c5ff"):
        assert legacy_blue not in qml
    assert 'appRoot.width < 1300 ? 210 : 260' in qml
    assert 'appRoot.width < 1300 ? 280 : 360' in qml
    assert 'objectName: "generationResultPreview"' in qml
    assert 'Layout.preferredHeight: 180' in qml
    assert 'appRoot.compactNavigation ? 96 : 148' in qml
