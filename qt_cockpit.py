"""Launch the Qt Quick GENESIS Cockpit reconstruction preview.

The existing Tk application remains the production entry point while this
frontend is reviewed and connected to the established backend.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import threading
import time
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDesktopServices, QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine

from genesis.model_compatibility import compatibility_note, compatible_loras
from genesis.model_registry import MODEL_ROOTS, readiness_report
from genesis.pose_prompt_profiles import PosePromptMap
from genesis import workflow_lab


PROJECT_ROOT = Path(__file__).resolve().parent
UI_ROOT = PROJECT_ROOT / "genesis" / "qt_ui"
ASSET_ROOT = PROJECT_ROOT / "genesis" / "assets" / "panel_backgrounds"
POSE_INDEX = PROJECT_ROOT / "genesis" / "reference" / "pose_library_index.json"
WORKFLOW_ROOT = Path.home() / "AI" / "ComfyUI" / "user" / "default" / "workflows"
GENERATION_WORKFLOW = WORKFLOW_ROOT / "GENESIS_FLUX2_KLEIN_9B_KV_OFFICIAL_T2I.json"
REGULAR_9B_WORKFLOWS = (
    Path("/mnt/AI-Storage/ComfyUI/workflows/Flux.2 Klein 9b Text To Image.json"),
    WORKFLOW_ROOT / "Flux.2 Klein 9b Text To Image.json",
)
EDIT_WORKFLOW = WORKFLOW_ROOT / "GENESIS_FLUXUP_IMG2IMG_RX9060.json"
REGULAR_9B_MODEL = "flux-2-klein-base-9b-Q4_K_M.gguf"
KV_9B_MODEL = "flux-2-klein-9b-kv-fp8.safetensors"
TEXT_ENCODER_9B = "qwen_3_8b_fp8mixed.safetensors"
SUPPORTED_CREATE_MODELS = {REGULAR_9B_MODEL, KV_9B_MODEL}
OUTPUT_DIR = Path.home() / "GENESIS-Exports"


def build_generation_profiles(
    report: dict,
    installed_loras: list[str],
    lora_triggers: dict[str, list[str]] | None = None,
) -> list[dict]:
    """Convert filesystem readiness evidence into QML-safe model choices."""
    lora_triggers = lora_triggers or {}
    profiles = []
    for profile in report.get("profiles", []):
        evidence = profile.get("evidence") or {}
        model_path = evidence.get("MODEL")
        if model_path is None:
            continue
        model_name = Path(model_path).name
        compatible = compatible_loras(model_name, installed_loras)
        ready = bool(profile.get("ready"))
        runnable = ready and model_name in SUPPORTED_CREATE_MODELS
        note = compatibility_note(model_name)
        if ready and not runnable:
            note += " · Create workflow not yet validated"
        profiles.append({
            "label": str(profile.get("name") or model_name),
            "model": model_name,
            "note": note,
            "loras": ["None", *compatible],
            "triggers": {name: lora_triggers.get(name, []) for name in compatible},
            "ready": ready,
            "runnable": runnable,
        })
    profiles.sort(key=lambda item: ("Klein 9B Base" not in item["label"], item["label"].casefold()))
    return profiles


def lora_trigger_words(path: Path) -> list[str]:
    """Extract explicit activation terms without loading LoRA tensor data."""
    try:
        with path.open("rb") as handle:
            header_size = struct.unpack("<Q", handle.read(8))[0]
            if header_size > 16 * 1024 * 1024:
                return []
            metadata = json.loads(handle.read(header_size)).get("__metadata__", {})
    except (OSError, ValueError, json.JSONDecodeError, struct.error):
        return []

    words: list[str] = []
    for key in ("modelspec.trigger_phrase", "trigger_words", "activation text"):
        value = metadata.get(key)
        if isinstance(value, str):
            words.extend(part.strip() for part in value.split(",") if part.strip())
    tag_frequency = metadata.get("ss_tag_frequency")
    if isinstance(tag_frequency, str):
        try:
            groups = json.loads(tag_frequency)
            for tags in groups.values():
                if isinstance(tags, dict):
                    words.extend(str(tag).strip() for tag in tags if str(tag).strip())
        except json.JSONDecodeError:
            pass
    return list(dict.fromkeys(words))[:12]


def load_generation_profiles() -> list[dict]:
    """Read installed model/LoRA names without loading any model tensors."""
    loras: set[str] = set()
    triggers: dict[str, list[str]] = {}
    for root in MODEL_ROOTS:
        lora_root = root / "loras"
        if not lora_root.is_dir():
            continue
        try:
            for path in lora_root.rglob("*"):
                if path.is_file() and path.suffix.lower() in {".safetensors", ".pt"}:
                    loras.add(path.name)
                    triggers[path.name] = lora_trigger_words(path)
        except OSError:
            continue
    return build_generation_profiles(
        readiness_report(),
        sorted(loras, key=str.casefold),
        triggers,
    )


def insert_model_only_loras(
    prompt: dict,
    source_node: str,
    consumer_node: str,
    consumer_input: str,
    loras: list[str],
    strength: float = 0.65,
) -> dict:
    """Insert the single live-validated model-only LoRA route."""
    selected = [name for name in loras if name and name != "None"]
    if len(selected) > 1:
        raise workflow_lab.ComfyError(
            "LoRA stacking is blocked because live image checks produced distortion."
        )

    model_link: list = [str(source_node), 0]
    for index, name in enumerate(selected, 1):
        node_id = f"genesis_lora_{index}"
        prompt[node_id] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": model_link,
                "lora_name": name,
                "strength_model": float(strength),
            },
            "_meta": {"title": f"GENESIS LoRA {index}: {name}"},
        }
        model_link = [node_id, 0]
    prompt[str(consumer_node)]["inputs"][consumer_input] = model_link
    return prompt


def build_create_prompt(
    info: dict,
    prompt_text: str,
    width: int,
    height: int,
    model_name: str,
    loras: list[str] | None = None,
) -> dict:
    """Build one of the two live-validated Create graphs selected in QML."""
    width = max(256, min(1536, int(width)))
    height = max(256, min(1536, int(height)))
    loras = loras or []

    if model_name == REGULAR_9B_MODEL:
        workflow = next((path for path in REGULAR_9B_WORKFLOWS if path.is_file()), None)
        if workflow is None:
            raise workflow_lab.ComfyError("The regular Klein 9B workflow is unavailable.")
        prompt = workflow_lab.workflow_to_prompt(workflow, info)
        prompt["126"]["class_type"] = "UnetLoaderGGUF"
        prompt["126"]["inputs"] = {"unet_name": REGULAR_9B_MODEL}
        prompt["136"]["inputs"]["clip_name"] = TEXT_ENCODER_9B
        prompt["107"]["inputs"]["text"] = prompt_text
        prompt["134"]["inputs"].update({"steps": 4, "cfg": 1.0})
        prompt["105"]["inputs"].update({"width": width, "height": height, "batch_size": 1})
        prompt["9"]["inputs"]["filename_prefix"] = "GENESIS-Klein9B-Regular"
        insert_model_only_loras(prompt, "126", "134", "model", loras)
    elif model_name == KV_9B_MODEL:
        selected = [name for name in loras if name and name != "None"]
        if selected:
            raise workflow_lab.ComfyError("Klein 9B-KV has no validated LoRA route.")
        if not GENERATION_WORKFLOW.is_file():
            raise workflow_lab.ComfyError("The validated Klein 9B-KV workflow is unavailable.")
        prompt = workflow_lab.workflow_to_prompt(GENERATION_WORKFLOW, info)
        prompt["1"]["inputs"]["unet_name"] = KV_9B_MODEL
        prompt["2"]["inputs"]["clip_name"] = TEXT_ENCODER_9B
        prompt["3"]["inputs"]["text"] = prompt_text
        prompt["9"]["inputs"].update({"steps": 4, "width": width, "height": height})
        prompt["10"]["inputs"].update({"width": width, "height": height, "batch_size": 1})
        prompt["14"]["inputs"]["filename_prefix"] = "GENESIS-Klein9B-KV"
    else:
        raise workflow_lab.ComfyError(f"No validated Create workflow for {model_name}.")

    validation = workflow_lab.validate_prompt(prompt, info)
    if not validation["valid"]:
        missing = validation["missing_nodes"] + validation["missing_inputs"]
        raise workflow_lab.ComfyError("Workflow is not runnable: " + ", ".join(missing))
    return prompt


def load_pose_items(limit: int = 12) -> list[dict[str, str]]:
    """Return a varied, existing subset of the local Pose Maker library."""
    roots = (
        Path.home() / "AI" / "GENESIS_POSE_MAKER" / "assets" / "pose_library",
        Path.home() / "Downloads" / "GENESIS_POSE_MAKER_V15_USER_IMAGE_SLOTS(1)"
        / "GENESIS_POSE_MAKER" / "assets" / "pose_library",
    )
    library_root = next((root for root in roots if root.is_dir()), None)
    if library_root is None or not POSE_INDEX.is_file():
        return []
    try:
        indexed = json.loads(POSE_INDEX.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    try:
        prompt_map = PosePromptMap.load()
    except (OSError, ValueError, json.JSONDecodeError):
        prompt_map = None

    categories: dict[str, list[dict]] = {}
    for item in indexed if isinstance(indexed, list) else []:
        if not isinstance(item, dict) or not item.get("path"):
            continue
        source = library_root / str(item["path"])
        if source.is_file():
            category = str(item.get("category", "Pose"))
            resolution = str(item.get("resolution", ""))
            raw_name = str(item.get("name", source.stem))
            pose_id = f"{category}/{resolution}/{raw_name}"
            record = prompt_map.records.get(pose_id) if prompt_map is not None else None
            categories.setdefault(category, []).append({
                **item,
                "source": QUrl.fromLocalFile(str(source)).toString(),
                "poseId": pose_id,
                "prompt": record.prompt if record else "",
                "negativePrompt": record.negative_prompt if record else "",
                "promptSource": record.source if record else "AUTO_FALLBACK",
                "promptTemplateId": record.prompt_template_id if record else "",
                "promptMapped": bool(record),
            })

    result: list[dict[str, str]] = []
    while len(result) < limit and any(categories.values()):
        for category in list(categories):
            if categories[category] and len(result) < limit:
                item = categories[category].pop(0)
                result.append({
                    "name": str(item.get("name", "Pose")).replace("_", " ").title(),
                    "category": category.replace("NSFW_", "").replace("_", " ").title(),
                    "resolution": str(item.get("resolution", "")),
                    "source": str(item["source"]),
                    "poseId": str(item.get("poseId", "")),
                    "prompt": str(item.get("prompt", "")),
                    "negativePrompt": str(item.get("negativePrompt", "")),
                    "promptSource": str(item.get("promptSource", "AUTO_FALLBACK")),
                    "promptTemplateId": str(item.get("promptTemplateId", "")),
                    "promptMapped": bool(item.get("promptMapped", False)),
                })
    return result


def load_runtime_status() -> dict:
    """Read live local service/GPU state without starting or stopping anything."""
    try:
        stats = workflow_lab.system_stats()
        metrics = workflow_lab.gpu_metrics(stats)
        gib = 1024 ** 3
        return {
            "comfyOnline": True,
            "gpuName": metrics["name"],
            "vramUsedGiB": round(metrics["vram_used"] / gib, 1),
            "vramTotalGiB": round(metrics["vram_total"] / gib, 1),
            "ready": workflow_lab.gpu_acceleration_available(stats),
        }
    except Exception:
        return {
            "comfyOnline": False,
            "gpuName": "Unavailable",
            "vramUsedGiB": 0,
            "vramTotalGiB": 0,
            "ready": False,
        }


class GenerationBridge(QObject):
    """Asynchronous Qt boundary around the preserved local ComfyUI client."""

    statusChanged = pyqtSignal()
    busyChanged = pyqtSignal()
    previewChanged = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._status = "Ready"
        self._busy = False
        self._preview = ""

    @pyqtProperty(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @pyqtProperty(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @pyqtProperty(str, notify=previewChanged)
    def previewUrl(self) -> str:
        return self._preview

    @pyqtProperty(bool, constant=True)
    def editAvailable(self) -> bool:
        return EDIT_WORKFLOW.is_file()

    def _set_status(self, value: str) -> None:
        self._status = value
        self.statusChanged.emit()

    def _set_busy(self, value: bool) -> None:
        self._busy = value
        self.busyChanged.emit()

    def _set_preview(self, value: str) -> None:
        self._preview = value
        self.previewChanged.emit()

    @pyqtSlot()
    def openOutputFolder(self) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(OUTPUT_DIR))):
            self._set_status("Could not open the GENESIS-Exports folder.")

    @pyqtSlot()
    def openPreview(self) -> None:
        source = Path(QUrl(self._preview).toLocalFile())
        if not self._preview or not source.is_file():
            self._set_status("No generated preview is available yet.")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(source))):
            self._set_status("Could not open the generated image.")

    @pyqtSlot(str, str, int, int, str, str, str)
    def queueGenerate(
        self,
        prompt_text: str,
        negative_prompt: str,
        width: int,
        height: int,
        model_name: str,
        lora_one: str,
        lora_two: str,
    ) -> None:
        if self._busy:
            return
        prompt_text = prompt_text.strip()
        if not prompt_text:
            self._set_status("Enter a prompt before generating.")
            return
        if model_name not in SUPPORTED_CREATE_MODELS:
            self._set_status("That model has no validated Create workflow yet.")
            return
        self._set_busy(True)
        engine = "Klein 9B Base" if model_name == REGULAR_9B_MODEL else "Klein 9B-KV"
        self._set_status(f"Preparing validated {engine} generation…")
        threading.Thread(
            target=self._run_generate,
            args=(prompt_text, negative_prompt, int(width), int(height), model_name, lora_one, lora_two),
            daemon=True,
        ).start()

    @pyqtSlot(str, str, float)
    def queueEdit(self, source_url: str, prompt_text: str, strength: float) -> None:
        if self._busy:
            return
        source = Path(QUrl(source_url).toLocalFile())
        prompt_text = prompt_text.strip()
        if not source.is_file() or not prompt_text:
            self._set_status("Choose a source image and enter edit instructions.")
            return
        if not EDIT_WORKFLOW.is_file():
            self._set_status("The saved Klein image-edit workflow is unavailable.")
            return
        self._set_busy(True)
        self._set_status("Preparing validated image-edit workflow…")
        threading.Thread(
            target=self._run_edit,
            args=(source, prompt_text, float(strength)),
            daemon=True,
        ).start()

    def _run_generate(
        self,
        prompt_text: str,
        negative_prompt: str,
        width: int,
        height: int,
        model_name: str,
        lora_one: str,
        lora_two: str,
    ) -> None:
        try:
            client = workflow_lab.ComfyClient(workflow_lab.COMFY_URL)
            stats = client.system_stats()
            if not workflow_lab.gpu_acceleration_available(stats):
                raise workflow_lab.ComfyError("ComfyUI GPU acceleration is unavailable.")
            info = client.object_info()
            prompt = build_create_prompt(
                info, prompt_text, width, height, model_name, [lora_one, lora_two]
            )
            # These validated distilled graphs intentionally use zeroed negative
            # conditioning; preserve the proven graph until another route is tested.
            _ = negative_prompt

            prompt_id = client.submit(prompt)
            self._set_status(f"Queued {prompt_id[:8]}…")
            result = client.wait(
                prompt_id,
                timeout=1800,
                progress=lambda value: self._set_status(
                    f"Generation {value.get('status', 'working')} · {int(value.get('elapsed', 0))}s"
                ),
            )
            if result.status != "completed":
                raise workflow_lab.ComfyError(result.error or f"Generation ended: {result.status}")

            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            saved: list[Path] = []
            stamp = time.strftime("%Y%m%d-%H%M%S")
            for index, output in enumerate(result.outputs, 1):
                if output.get("kind") != "images":
                    continue
                suffix = Path(output.get("filename", "image.png")).suffix or ".png"
                target = OUTPUT_DIR / f"GENESIS-Klein-{stamp}-{index}{suffix}"
                target.write_bytes(client.view(output))
                saved.append(target)
            if not saved:
                raise workflow_lab.ComfyError("ComfyUI completed without an image output.")
            self._set_preview(QUrl.fromLocalFile(str(saved[-1])).toString())
            self._set_status(f"Complete · {saved[-1].name}")
        except Exception as exc:
            self._set_status(f"Generation failed · {exc}")
        finally:
            self._set_busy(False)

    def _run_edit(self, source: Path, prompt_text: str, strength: float) -> None:
        try:
            client = workflow_lab.ComfyClient(workflow_lab.COMFY_URL)
            stats = client.system_stats()
            if not workflow_lab.gpu_acceleration_available(stats):
                raise workflow_lab.ComfyError("ComfyUI GPU acceleration is unavailable.")
            info = client.object_info()
            base = workflow_lab.workflow_to_prompt(EDIT_WORKFLOW, info)
            controls = workflow_lab.discover_workflow_controls(base)
            overrides: dict[str, dict] = {}

            def override(control: str, value) -> None:
                target = controls.get(control)
                if target:
                    node_id, input_name = target
                    overrides.setdefault(str(node_id), {})[input_name] = value

            override("positive", prompt_text)
            override("denoise", max(0.05, min(0.95, strength)))
            override("steps", 8)
            override("encoder", "qwen_3_4b_fp4_flux2.safetensors")

            uploaded = client.upload_image(source)
            image_name = "/".join(
                value for value in (uploaded.get("subfolder"), uploaded.get("name")) if value
            )
            load_nodes = [
                str(node_id) for node_id, node in base.items()
                if node.get("class_type") == "LoadImage"
            ]
            if not load_nodes:
                raise workflow_lab.ComfyError("Image-edit workflow has no source-image input.")
            overrides.setdefault(load_nodes[0], {})["image"] = image_name

            prompt = workflow_lab.workflow_to_prompt(EDIT_WORKFLOW, info, overrides)
            validation = workflow_lab.validate_prompt(prompt, info)
            if not validation["valid"]:
                missing = validation["missing_nodes"] + validation["missing_inputs"]
                raise workflow_lab.ComfyError("Workflow is not runnable: " + ", ".join(missing))

            prompt_id = client.submit(prompt)
            self._set_status(f"Queued {prompt_id[:8]}…")
            result = client.wait(
                prompt_id,
                timeout=3600,
                progress=lambda value: self._set_status(
                    f"Image edit {value.get('status', 'working')} · {int(value.get('elapsed', 0))}s"
                ),
            )
            if result.status != "completed":
                raise workflow_lab.ComfyError(result.error or f"Edit ended: {result.status}")

            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            saved: list[Path] = []
            stamp = time.strftime("%Y%m%d-%H%M%S")
            for index, output in enumerate(result.outputs, 1):
                if output.get("kind") != "images":
                    continue
                suffix = Path(output.get("filename", "image.png")).suffix or ".png"
                target = OUTPUT_DIR / f"GENESIS-Edit-{stamp}-{index}{suffix}"
                target.write_bytes(client.view(output))
                saved.append(target)
            if not saved:
                raise workflow_lab.ComfyError("ComfyUI completed without an image output.")
            self._set_preview(QUrl.fromLocalFile(str(saved[-1])).toString())
            self._set_status(f"Complete · {saved[-1].name}")
        except Exception as exc:
            self._set_status(f"Edit failed · {exc}")
        finally:
            self._set_busy(False)


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--screenshot")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    page_indexes = {
        "create": 0, "poses": 1, "workflow": 2, "media": 3,
        "photos": 4, "cameras": 5, "entertainment": 6, "system": 7, "edit": 8,
    }
    parser.add_argument("--page", choices=tuple(page_indexes), default="create")
    parser.add_argument("--banner", choices=("video", "photos"), default="video")
    args, qt_args = parser.parse_known_args()
    sys.argv = [sys.argv[0], *qt_args]
    app = QGuiApplication(sys.argv)
    app.setApplicationName("GENESIS Cockpit")
    engine = QQmlApplicationEngine()
    context = engine.rootContext()
    context.setContextProperty("genesisAssetRoot", QUrl.fromLocalFile(str(ASSET_ROOT) + "/"))
    context.setContextProperty("genesisUiRoot", QUrl.fromLocalFile(str(UI_ROOT) + "/"))
    context.setContextProperty("poseItems", load_pose_items())
    context.setContextProperty("generationProfiles", load_generation_profiles())
    context.setContextProperty("runtimeStatus", load_runtime_status())
    generation_bridge = GenerationBridge(app)
    context.setContextProperty("genesisBridge", generation_bridge)
    engine.load(QUrl.fromLocalFile(str(UI_ROOT / "Main.qml")))
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]
    window.setProperty("pageIndex", page_indexes[args.page])
    window.setProperty("bannerMode", 1 if args.banner == "photos" else 0)
    if args.width or args.height:
        window.resize(max(900, args.width or window.width()), max(600, args.height or window.height()))
    if not args.screenshot:
        window.showMaximized()
    if args.screenshot:
        target = Path(args.screenshot).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        def save_screenshot() -> None:
            screen = window.screen() or app.primaryScreen()
            image = screen.grabWindow(int(window.winId())) if screen else None
            if image is None or image.isNull() or not image.save(str(target)):
                app.exit(2)
                return
            app.quit()

        QTimer.singleShot(2500, save_screenshot)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
