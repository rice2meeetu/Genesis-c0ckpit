"""Offline actual-click and route coverage for image finishing controls."""
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image
from PyQt6.QtCore import QUrl
import qt_cockpit as cockpit
from genesis.backend_routing import Route, remote_url
from genesis.canvas_bridge import CanvasBridge
from genesis.media_bridge import MediaBridge
from genesis.media_functions import OperationResult


def test_actual_finishing_engine_clicks_and_facefusion_local_gate(tmp_path):
    """Load real QML; queue slots record arguments without starting inference."""
    image = tmp_path / "neutral.png"
    Image.new("RGB", (16, 16), "gray").save(image)
    script = r'''
import os, sys
from pathlib import Path
from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtProperty, pyqtSlot
from PyQt6.QtQml import QQmlExpression
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
import qt_cockpit as c
import qt_cockpit_linux_premium as launch
import genesis.pose_workbench as handoff
handoff.POSE_WORKBENCH_HANDOFF_FILE = Path(os.environ['XDG_CONFIG_HOME']) / 'isolated-handoff.json'
launch.load_pose_items = lambda **kwargs: []
launch.load_grok_preset_items = lambda: []
launch.load_curated_pose_presets = lambda **kwargs: []
launch.load_runtime_status = lambda **kwargs: {'identityEngines': ['reactor_inswapper', 'reactor_hyperswap']}
launch.BackendBridge.start = lambda self: None
finish_calls, facefusion_calls = [], []
class CaptureBridge(c.GenerationBridge):
    @pyqtProperty(bool, constant=True)
    def faceFusionAvailable(self):
        return True
    @pyqtSlot(bool, bool, int, str, str, str, float)
    def queueFinish(self, *args):
        finish_calls.append(tuple(args))
    @pyqtSlot(str, str)
    def queueFaceFusion(self, *args):
        facefusion_calls.append(tuple(args))
launch.GenerationBridge = CaptureBridge
engines = []
factory = launch.QQmlApplicationEngine
launch.QQmlApplicationEngine = lambda: (engines.append(factory()) or engines[-1])

def verify():
    try:
        engine = engines[0]
        context = engine.rootContext()
        window = engine.rootObjects()[0]
        bridge = context.contextProperty('genesisBridge')
        backend = context.contextProperty('backendBridge')
        image = Path(os.environ['IMAGE_AUDIT_SOURCE'])
        uri = QUrl.fromLocalFile(str(image))
        bridge._original_master = image
        bridge._finish_info = {
            'ReActorFaceSwapOpt': {'input': {'required': {'swap_model': [['inswapper_128.onnx']]}}},
            'ReActorOptions': {'input': {'required': {}}},
            'LoadImage': {'input': {'required': {}}},
        }
        bridge._set_preview(uri.toString())
        def evaluate(code, scope=None):
            expression = QQmlExpression(context, scope or window, code)
            value, _ = expression.evaluate()
            assert not expression.hasError(), expression.error().toString()
            QApplication.processEvents()
            return value
        def button_named(name, text):
            button = window.findChild(QObject, name)
            if button is None:
                button = next((item for item in window.findChildren(QObject)
                    if item.property('text') == text), None)
            assert button is not None, name
            return button
        def open_stage_three():
            card = evaluate('itemAt(2)', window.findChild(QObject, 'generationStageRepeater'))
            if hasattr(card, 'toQObject'):
                card = card.toQObject()
            mouse = card.findChild(QObject, 'stageModelBoxClick2')
            assert mouse is not None
            evaluate('clicked(null)', mouse)
            QTest.qWait(100)
        def stage_choice(index):
            item = evaluate(f'itemAtIndex({index})', window.findChild(QObject, 'stageModelChoiceList'))
            return item.toQObject() if hasattr(item, 'toQObject') else item
        identity = button_named('finishIdentityButton', 'Identity / Face Lock')
        assert identity.property('enabled'), bridge.status
        # Switch using the real Stage 3 popup and its real button delegate.
        open_stage_three()
        choose = stage_choice(1)
        assert choose is not None and choose.property('enabled')
        evaluate('clicked()', choose)
        assert bridge._stage_three_engine == 'reactor_hyperswap'
        assert not identity.property('enabled'), 'Face Lock retained readiness for the previous swap model'
        open_stage_three()
        evaluate('clicked()', stage_choice(0))
        assert bridge._stage_three_engine == 'reactor_inswapper'
        assert identity.property('enabled')
        evaluate('clicked()', identity)
        assert len(finish_calls) == 1
        assert finish_calls[0][:3] == (False, True, 0)
        assert finish_calls[0][5:] == ('None', 0.0)
        # FaceFusion's UI must honor its explicit LOCAL-only route contract.
        window.setProperty('pageIndex', 12)
        window.setProperty('faceSwapTarget', uri)
        window.setProperty('faceSwapSource', uri)
        facefusion = button_named('faceFusionButton', 'FACEFUSION · LOCAL IMAGE')
        for mode in ('RUNPOD', 'AUTO'):
            backend._mode = mode
            backend.changed.emit()
            QApplication.processEvents()
            assert not facefusion.property('enabled'), 'FaceFusion enabled in ' + mode
        backend._mode = 'LOCAL'
        backend.changed.emit()
        QApplication.processEvents()
        assert facefusion.property('enabled')
        evaluate('clicked()', facefusion)
        assert facefusion_calls == [(uri.toString(), uri.toString())]
        bridge._set_busy(True)
        assert not identity.property('enabled')
        assert not facefusion.property('enabled')
        print('IMAGE_FINISHING_BUTTON_AUDIT_OK')
        QApplication.instance().exit(0)
    except Exception:
        import traceback
        traceback.print_exc()
        QApplication.instance().exit(1)
class CheckedApp(QApplication):
    def exec(self):
        QTimer.singleShot(300, verify)
        QTimer.singleShot(12000, lambda: self.exit(2))
        return super().exec()
launch.QApplication = CheckedApp
sys.argv = ['finishing-button-audit', '--page', 'create']
sys.exit(launch.main())
'''
    runtime = tmp_path / "runtime"
    runtime.mkdir(mode=0o700)
    config = tmp_path / "config"
    config.mkdir()
    data = tmp_path / "data"
    data.mkdir()
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software",
               QTWEBENGINE_DISABLE_SANDBOX="1", QSG_RHI_BACKEND="software",
               LIBGL_ALWAYS_SOFTWARE="1", GENESIS_RUNPOD_AUTOCONNECT="0",
               XDG_RUNTIME_DIR=str(runtime), XDG_CONFIG_HOME=str(config),
               XDG_DATA_HOME=str(data), IMAGE_AUDIT_SOURCE=str(image),
               PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run([sys.executable, "-c", script],
                            cwd=Path(__file__).resolve().parents[1], env=env,
                            capture_output=True, text=True, timeout=25)
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert "IMAGE_FINISHING_BUTTON_AUDIT_OK" in result.stdout


def test_facefusion_selected_cpu_provider_does_not_require_gpu(tmp_path, monkeypatch):
    """The selected CPU override, rather than saved GPU config, governs launch."""
    root = tmp_path / "facefusion"
    (root / ".venv/bin").mkdir(parents=True)
    (root / ".venv/bin/python").write_text("isolated fake runtime")
    (root / "facefusion.py").write_text("isolated fake entry")
    (root / "facefusion.ini").write_text("[execution]\nexecution_providers = migraphx\n")
    monkeypatch.setattr(cockpit.integrations, "FACEFUSION_ROOT", root)
    guard = Mock(side_effect=AssertionError("CPU selection must not probe the GPU"))
    monkeypatch.setattr(cockpit.integrations, "gpu_kernel_preflight", guard)
    source = tmp_path / "neutral.png"
    Image.new("RGB", (16, 16), "gray").save(source)
    uri = QUrl.fromLocalFile(str(source)).toString()
    bridge = cockpit.GenerationBridge()
    bridge.backend_router = SimpleNamespace(mode="LOCAL")
    bridge.setFaceFusionProvider("cpu")
    thread = Mock()
    monkeypatch.setattr(cockpit.threading, "Thread", thread)
    bridge.queueFaceFusion(uri, uri)
    assert bridge.busy, bridge.status
    guard.assert_not_called()
    thread.return_value.start.assert_called_once()
    assert thread.call_args.kwargs["target"] == bridge._run_facefusion
    assert thread.call_args.kwargs["args"][:2] == (source, source)


@pytest.mark.parametrize("kind,scale", [("upscale", 2), ("upscale", 4),
                                        ("upscale", 8), ("standard resize", 2),
                                        ("background remover", 2)])
def test_canvas_processing_routes_and_preserves_source(tmp_path, monkeypatch, kind, scale):
    """Each Canvas image action reaches the worker and replaces only its layer."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    source = tmp_path / "source.png"
    Image.new("RGBA", (16, 8), (40, 80, 120, 100)).save(source)
    before = source.read_bytes()
    canvas = CanvasBridge()
    media = MediaBridge()
    route = Route("LOCAL", "")
    media.backend_router = Mock()
    media.backend_router.resolve_operation.return_value = route
    canvas.attach_media_tools(media)
    canvas.addImage(str(source))
    calls = []
    def fake_upscale(original, output, **kwargs):
        calls.append((original, output, kwargs, remote_url()))
        Image.new("RGBA", (16 * scale, 8 * scale), (40, 80, 120, 100)).save(output)
        return OperationResult(output, "mock-image-processor", {})
    def fake_background(original, output):
        calls.append((original, output, {}, remote_url()))
        Image.new("RGBA", (16, 8), (40, 80, 120, 0)).save(output)
        return OperationResult(output, "mock-image-processor", {})
    monkeypatch.setattr("genesis.media_bridge.upscale_enhance", fake_upscale)
    monkeypatch.setattr("genesis.media_bridge.remove_background", fake_background)
    def execute(label, operation):
        media._set_busy(True)
        media._finish(operation())
    monkeypatch.setattr(media, "_start", execute)
    canvas.processSelected(kind, scale)
    assert len(calls) == 1
    assert calls[0][0] == source
    assert calls[0][1] != source
    assert calls[0][1].parent == tmp_path / "data/genesis/canvas-assets"
    if kind == "upscale":
        media.backend_router.resolve_operation.assert_called_once_with("upscale")
        assert calls[0][2] == dict(scale=scale, prefer_ai=True, require_ai=True)
        assert calls[0][3] == ""
    else:
        media.backend_router.resolve_operation.assert_not_called()
    assert len(canvas.layers) == 2
    assert not canvas.layers[0]["visible"]
    assert canvas.layers[1]["visible"]
    assert source.read_bytes() == before
    assert not canvas.busy


def test_facefusion_output_invalidates_prior_comfy_finishing_context(tmp_path, monkeypatch):
    bridge = cockpit.GenerationBridge()
    bridge._output_dir = tmp_path
    bridge._facefusion_provider = "cpu"
    bridge._finish_route = Route("RUNPOD", "https://previous.example")
    bridge._finish_info = {"old-generation-catalog": {}}
    source = tmp_path / "portrait.png"
    Image.new("RGB", (16, 8), "gray").save(source)
    def execute(command, **kwargs):
        output = Path(command[command.index("--output-path") + 1])
        Image.new("RGB", (16, 8), "gray").save(output)
        return SimpleNamespace(returncode=0, stdout="mock-completed")
    monkeypatch.setattr(cockpit.subprocess, "run", execute)
    bridge._run_facefusion(source, source, Path("/fake/python"),
                           Path("/fake/facefusion.py"), Path("/fake/facefusion.ini"))
    assert bridge.status.startswith("FaceFusion complete"), bridge.status
    assert bridge._finish_route is None
    assert bridge._finish_info == {}
    assert not bridge.finishingAvailability(cockpit.REMOTE_DONUTS_MODEL, "", 2)["upscale"]


@pytest.mark.parametrize("kind", ["edit", "inpaint", "face_swap"])
@pytest.mark.parametrize("route", [Route("LOCAL", ""), Route("RUNPOD", "https://current.example")])
def test_standalone_comfy_result_uses_its_captured_finishing_context(tmp_path, monkeypatch, kind, route):
    bridge = cockpit.GenerationBridge()
    bridge._output_dir = tmp_path
    bridge._finish_route = Route("RUNPOD", "https://previous.example")
    bridge._finish_info = {"old-generation-catalog": {}}
    bridge._finish_width, bridge._finish_height = 1024, 1536
    source = tmp_path / "source.png"
    output = tmp_path / "result.png"
    Image.new("RGB", (24, 16), "gray").save(source)
    Image.new("RGB", (48, 32), "gray").save(output)
    info = {
        "CheckpointLoaderSimple": {"input": {"required": {"ckpt_name": [[cockpit.INPAINT_CHECKPOINT]]}}},
        "ReActorFaceSwapOpt": {"input": {"required": {"swap_model": [["inswapper_128.onnx"]]}}},
        "ReActorOptions": {"input": {"required": {}}},
    }
    client = Mock()
    client.object_info.return_value = info
    client.upload_image.return_value = {"name": "source.png", "subfolder": "isolated"}
    monkeypatch.setattr(bridge, "_connect_comfyui", lambda: (client, {}))
    monkeypatch.setattr(bridge, "_submit_and_save", lambda *args, **kwargs: output)
    monkeypatch.setattr(cockpit, "validate_operation_prompt", lambda *args: None)
    monkeypatch.setattr(cockpit.workflow_lab, "validate_prompt", lambda *args: {"valid": True})
    if kind == "edit":
        monkeypatch.setattr(cockpit.workflow_lab, "workflow_to_prompt", lambda *args, **kwargs: {
            "image": {"class_type": "LoadImage", "inputs": {"image": "placeholder.png"}}})
        monkeypatch.setattr(cockpit.workflow_lab, "discover_workflow_controls", lambda *args: {})
        operation = bridge._run_edit
        args = (source, "A neutral ceramic mug", 0.4)
    elif kind == "inpaint":
        operation = bridge._run_inpaint
        args = (source, source, "A neutral ceramic mug", 0.4)
    else:
        monkeypatch.setattr("genesis.person_a_targeting.prepare_crops", lambda *args: (source, source))
        monkeypatch.setattr("genesis.person_a_targeting.composite_crop", lambda *args: output)
        operation = bridge._run_face_swap
        args = (source, source, (Mock(), Mock()))
    bridge._run_routed_operation(route, operation, *args)
    assert bridge.status.startswith("Complete"), bridge.status
    assert bridge.previewUrl == QUrl.fromLocalFile(str(output)).toString()
    assert bridge._finish_route == route
    assert bridge._finish_info == info
    assert (bridge._finish_width, bridge._finish_height) == (48, 32)


def test_finishing_history_select_and_reject_restore_each_results_backend(tmp_path):
    bridge = cockpit.GenerationBridge()
    local = tmp_path / "local.png"
    remote = tmp_path / "remote.png"
    original_local = tmp_path / "local-source.png"
    original_remote = tmp_path / "remote-source.png"
    for path, size in ((local, (48, 32)), (remote, (96, 64)),
                       (original_local, (16, 16)), (original_remote, (32, 32))):
        Image.new("RGB", size, "gray").save(path)
    local_route = Route("LOCAL", "")
    remote_route = Route("RUNPOD", "https://later.example")
    local_info = {"local-catalog": {}}
    remote_info = {"remote-catalog": {}}
    bridge._finish_route = local_route
    bridge._finish_info = local_info
    bridge._finish_width, bridge._finish_height = (48, 32)
    bridge._original_master = original_local
    bridge._record_finish("Local generated", local)
    bridge._finish_route = remote_route
    bridge._finish_info = remote_info
    bridge._finish_width, bridge._finish_height = (96, 64)
    bridge._original_master = original_remote
    bridge._record_finish("Remote generated", remote)
    bridge.selectFinishingResult(QUrl.fromLocalFile(str(local)).toString())
    assert bridge._finish_route == local_route
    assert bridge._finish_info == local_info
    assert (bridge._finish_width, bridge._finish_height) == (48, 32)
    assert bridge._identity_master() == original_local
    bridge.selectFinishingResult(QUrl.fromLocalFile(str(remote)).toString())
    assert bridge._finish_route == remote_route
    assert bridge._finish_info == remote_info
    assert (bridge._finish_width, bridge._finish_height) == (96, 64)
    assert bridge._identity_master() == original_remote
    bridge.rejectFinishingResult()
    assert bridge.previewUrl == QUrl.fromLocalFile(str(local)).toString()
    assert bridge._finish_route == local_route
    assert bridge._finish_info == local_info
    assert (bridge._finish_width, bridge._finish_height) == (48, 32)
    assert local.is_file() and remote.is_file()


@pytest.mark.parametrize("model_spec", [
    [["4x-UltraSharp.pth"]],
    ["COMBO", {"options": ["4x-UltraSharp.pth"]}],
])
def test_media_ai_upscale_accepts_classic_and_modern_model_combo(tmp_path, monkeypatch, model_spec):
    """Canvas and media upscale share this parser; mock every backend call."""
    import io
    from genesis import media_functions as media
    from genesis.backend_routing import use_route
    source = tmp_path / "source.png"
    target = tmp_path / "result.png"
    Image.new("RGB", (16, 8), "gray").save(source)
    native = io.BytesIO()
    Image.new("RGB", (64, 32), "gray").save(native, format="PNG")
    client = Mock()
    client.object_info.return_value = {
        "UpscaleModelLoader": {"input": {"required": {"model_name": model_spec}}}}
    client.upload_image.return_value = {"name": "source.png", "subfolder": "isolated"}
    client.wait.return_value = SimpleNamespace(status="completed", outputs=[{"filename": "mock.png"}])
    client.view.return_value = native.getvalue()
    monkeypatch.setattr(media, "ComfyClient", Mock(return_value=client))
    with use_route(Route("RUNPOD", "https://mock-upscale.example")):
        result = media.upscale_enhance(source, target, scale=2, prefer_ai=True, require_ai=True)
    client.submit.assert_called_once()
    graph = client.submit.call_args.args[0]
    assert graph["2"]["inputs"]["model_name"] == "4x-UltraSharp.pth"
    assert result.output == target
    with Image.open(target) as image:
        assert image.size == (32, 16)
