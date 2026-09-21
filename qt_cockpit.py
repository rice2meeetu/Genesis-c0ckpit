"""Launch the Qt Quick GENESIS Cockpit reconstruction preview.

The existing Tk application remains the production entry point while this
frontend is reviewed and connected to the established backend.
"""

from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

from PyQt6.QtCore import QObject, QSettings, QSize, QTimer, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDesktopServices, QGuiApplication, QIcon
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWidgets import QApplication, QFileDialog, QListView

from genesis.model_compatibility import compatibility_note, compatible_loras
from genesis.model_registry import MODEL_ROOTS, readiness_report
from genesis.asset_inventory import unavailable_local_assets
from genesis.pose_prompt_profiles import PosePromptMap
from genesis.generation_pipeline import adapt_prompt, compatible_selection
from genesis import integrations, workflow_lab
from genesis.character_library import add_reference, character_items, preferred_reference, save_character


PROJECT_ROOT = Path(__file__).resolve().parent
UI_ROOT = PROJECT_ROOT / "genesis" / "qt_ui"
ASSET_ROOT = PROJECT_ROOT / "genesis" / "assets" / "panel_backgrounds"
POSE_INDEX = PROJECT_ROOT / "genesis" / "reference" / "pose_library_index.json"
POSE_THUMB_CACHE = Path.home() / "GENESIS-Photo-Studio" / "cache" / "thumbnails"
WORKFLOW_ROOT = Path.home() / "AI" / "ComfyUI" / "user" / "default" / "workflows"
GENERATION_WORKFLOW = WORKFLOW_ROOT / "GENESIS_FLUX2_KLEIN_9B_KV_OFFICIAL_T2I.json"
REGULAR_9B_WORKFLOWS = (
    Path("/mnt/AI-Storage/ComfyUI/workflows/Flux.2 Klein 9b Text To Image.json"),
    WORKFLOW_ROOT / "Flux.2 Klein 9b Text To Image.json",
)
EDIT_WORKFLOW = WORKFLOW_ROOT / "GENESIS_FLUXUP_IMG2IMG_RX9060.json"
INPAINT_CHECKPOINT = "juggernautXL_ragnarokBy.safetensors"
REGULAR_9B_MODEL = "flux-2-klein-base-9b-Q4_K_M.gguf"
KV_9B_MODEL = "flux-2-klein-9b-kv-fp8.safetensors"
QWEN_MODEL = "Qwen-Rapid-AIO-NSFW-v19.safetensors"
FOUR_B_MODEL = "flux-2-klein-4b.safetensors"
TEXT_ENCODER_4B = "qwen_3_4b_fp4_flux2.safetensors"
TEXT_ENCODER_9B = "qwen_3_8b_fp8mixed.safetensors"
SUPPORTED_CREATE_MODELS = {FOUR_B_MODEL, REGULAR_9B_MODEL, KV_9B_MODEL, QWEN_MODEL}
OUTPUT_DIR = Path.home() / "GENESIS-Exports"
REFERENCE_WORKFLOW_ROOT = PROJECT_ROOT / "genesis" / "reference" / "pose_workflows"
STAGE_1_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "STAGE_1_PHR00T_POSE.json"
STAGE_2_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "STAGE_2_LUSTIFY_REFINE.json"
STAGE_3_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "STAGE_3_REACTOR_ROCM.json"
FOUR_B_SOURCE_WORKFLOW = WORKFLOW_ROOT / "FLUX2_Klein_Deepthroat_FaceSwap.json"
UPSCALE_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "SD_UPSCALE_REFERENCE.json"
UPSCALE_REQUIRED_ASSETS = {
    "Realistic_Vision_V6.0_NV_B1.safetensors",
    "vae-ft-mse-840000-ema-pruned.safetensors",
    "4x-UltraSharp.safetensors",
}


def load_curated_pose_presets() -> list[dict]:
    """Load the full 70-preset pack plus the separate curated 18-preset pack."""
    presets: list[dict] = []
    full_path = PROJECT_ROOT / "genesis/reference/prompt_maps/pose_presets_full.json"
    try:
        payload = json.loads(full_path.read_text(encoding="utf-8"))
        for category, rows in payload.get("categories", {}).items():
            for position, row in enumerate(rows):
                if not isinstance(row, dict) or not row.get("prompt"):
                    continue
                presets.append({
                    "id": "full70:" + str(row.get("id", "")),
                    "label": str(row.get("name", "Preset")),
                    "prompt": str(row["prompt"]),
                    "priority": len(presets) + 1,
                    "collection": "Full 70",
                    "category": str(category),
                })
    except (OSError, ValueError, TypeError):
        pass

    candidates = (
        Path.home() / "GENESIS_CURATED_PRESETS_DATABASE.json",
        Path.home() / "AI/GENESIS_POSE_MAKER/GENESIS_CURATED_PRESETS_DATABASE.json",
    )
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows = payload.get("sexual_act_presets", [])
            curated = [
                {
                    "id": "curated18:" + str(row.get("id", "")),
                    "label": str(row.get("name", "Preset")) + " · Curated 18",
                    "prompt": str(row.get("prompt", "")),
                    "priority": 70 + int(row.get("priority", 9999)),
                    "collection": "Curated 18",
                    "category": "Curated",
                }
                for row in rows
                if isinstance(row, dict) and row.get("prompt")
            ]
            presets.extend(sorted(curated, key=lambda row: (row["priority"], row["label"])))
            break
        except (OSError, ValueError, TypeError):
            continue
    return presets


def upscale_assets_available() -> bool:
    found: set[str] = set()
    for root in MODEL_ROOTS:
        if not root.is_dir():
            continue
        try:
            found.update(path.name for path in root.rglob("*") if path.is_file())
        except OSError:
            continue
    return UPSCALE_WORKFLOW.is_file() and UPSCALE_REQUIRED_ASSETS <= found


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
            "sourceRequired": model_name == QWEN_MODEL,
            "maxLoras": 3 if model_name == REGULAR_9B_MODEL else (1 if model_name == FOUR_B_MODEL else 0),
            "experimentalLoras": model_name in {REGULAR_9B_MODEL, FOUR_B_MODEL},
        })
    priority = {FOUR_B_MODEL: 0, REGULAR_9B_MODEL: 1, KV_9B_MODEL: 2, QWEN_MODEL: 3}
    profiles.sort(key=lambda item: (priority.get(item["model"], 99), item["label"].casefold()))
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



def load_grok_preset_items() -> list[dict]:
    p = PROJECT_ROOT / "genesis/reference/prompt_maps/pose_presets_full.json"
    if not p.is_file():
        return []
    try:
        d = __import__("json").loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    out = [{"label": "Grok preset…", "prompt": ""}]
    for cat, rows in d.get("categories", {}).items():
        for row in rows or []:
            if row.get("prompt"):
                out.append({
                    "label": f"{cat.replace('_', '/')} · {row.get('name', row.get('id', 'Preset'))}",
                    "prompt": row["prompt"],
                })
    return out

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
    strengths: list[float] | None = None,
    strength: float = 0.65,
) -> dict:
    """Chain model-only LoRAs in selection order with per-slot strengths."""
    pairs = [
        (name, float((strengths or [])[index] if index < len(strengths or []) else strength))
        for index, name in enumerate(loras)
        if name and name != "None"
    ]
    if len(pairs) > 3:
        raise workflow_lab.ComfyError("GENESIS currently allows at most 3 stacked LoRAs.")
    if len({name for name, _ in pairs}) != len(pairs):
        raise workflow_lab.ComfyError("Select each LoRA only once.")
    if any(value < 0.0 or value > 1.0 for _, value in pairs):
        raise workflow_lab.ComfyError("LoRA strengths must be between 0.00 and 1.00.")

    model_link: list = [str(source_node), 0]
    for index, (name, value) in enumerate(pairs, 1):
        node_id = f"genesis_lora_{index}"
        prompt[node_id] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": model_link,
                "lora_name": name,
                "strength_model": value,
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
    lora_strengths: list[float] | None = None,
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
        insert_model_only_loras(prompt, "126", "134", "model", loras, lora_strengths)
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
    elif model_name == FOUR_B_MODEL:
        prompt = workflow_lab.workflow_to_prompt(GENERATION_WORKFLOW, info)
        prompt["1"]["inputs"]["unet_name"] = FOUR_B_MODEL
        prompt["2"]["inputs"]["clip_name"] = TEXT_ENCODER_4B
        prompt["3"]["inputs"]["text"] = prompt_text
        prompt.pop("5", None)
        prompt["6"]["inputs"]["model"] = ["1", 0]
        prompt["9"]["inputs"].update({"steps": 4, "width": width, "height": height})
        prompt["10"]["inputs"].update({"width": width, "height": height, "batch_size": 1})
        prompt["14"]["inputs"]["filename_prefix"] = "GENESIS-Klein4B-Fast"
        insert_model_only_loras(prompt, "1", "6", "model", loras, lora_strengths, strength=0.5)
    else:
        raise workflow_lab.ComfyError(f"No validated Create workflow for {model_name}.")

    validation = workflow_lab.validate_prompt(prompt, info)
    if not validation["valid"]:
        missing = validation["missing_nodes"] + validation["missing_inputs"]
        raise workflow_lab.ComfyError("Workflow is not runnable: " + ", ".join(missing))
    return prompt


def _pose_thumbnail_for(source: Path) -> Path:
    """Prefer the Photo Studio visual preview while preserving skeleton input separately."""
    stem = source.stem
    for suffix in ("_bone_structure", "_bone_strucure"):
        if stem.endswith(suffix):
            stem = stem[:-len(suffix)]
            break
    for variant in ("depth", "lineart", "bone_structure"):
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            candidate = POSE_THUMB_CACHE / f"{stem}_{variant}{ext}"
            if candidate.is_file():
                return candidate
    return source


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
                "thumbnail": QUrl.fromLocalFile(str(_pose_thumbnail_for(source))).toString(),
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
                    "thumbnail": str(item.get("thumbnail", item["source"])),
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


class LayoutSettingsBridge(QObject):
    """Persist user-adjustable QML layout values without touching generation state."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._settings = QSettings("GENESIS", "c0ckpit")

    @pyqtSlot(result="QVariant")
    def loadCreateLayout(self):
        defaults = {
            "previewWidth": 370.0,
            "promptHeight": 106.0,
            "referenceHeight": 112.0,
            "sourceHeight": 92.0,
            "outputHeight": 88.0,
        }
        return {key: float(self._settings.value("layout/create/" + key, value)) for key, value in defaults.items()}

    @pyqtSlot(float, float, float, float, float)
    def saveCreateLayout(self, previewWidth, promptHeight, referenceHeight, sourceHeight, outputHeight) -> None:
        values = {
            "previewWidth": previewWidth,
            "promptHeight": promptHeight,
            "referenceHeight": referenceHeight,
            "sourceHeight": sourceHeight,
            "outputHeight": outputHeight,
        }
        for key, value in values.items():
            self._settings.setValue("layout/create/" + key, float(value))
        self._settings.sync()

    @pyqtSlot()
    def resetCreateLayout(self) -> None:
        self._settings.remove("layout/create")
        self._settings.sync()


class ModuleBridge(QObject):
    """Route Qt module cards to existing GENESIS tools and services."""

    statusChanged = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._status = "Ready · choose a module action"

    @pyqtProperty(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    def _set_status(self, value: str) -> None:
        self._status = value
        self.statusChanged.emit()

    def _open(self, target: str | Path, label: str) -> None:
        url = QUrl(str(target)) if str(target).startswith(("http://", "https://")) else QUrl.fromLocalFile(str(target))
        ok = QDesktopServices.openUrl(url)
        self._set_status(f"{label} opened" if ok else f"Could not open {label}")

    def _legacy(self, action: str) -> None:
        if integrations.process_running(r"Genesis-c0ckpit/main.py"):
            self._set_status(f"{action} · full GENESIS workspace is already running")
            return
        try:
            subprocess.Popen(
                [sys.executable, str(PROJECT_ROOT / "main.py")],
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self._set_status(f"{action} · full GENESIS workspace opened")
        except OSError as exc:
            self._set_status(f"{action} failed · {exc}")

    def _pose_maker(self) -> None:
        root = Path.home() / "AI" / "GENESIS_POSE_MAKER"
        run_script = root / "run.sh"
        url = "http://127.0.0.1:7861"

        def worker() -> None:
            if not integrations.endpoint_online(url, "/", timeout=0.8):
                if not run_script.is_file():
                    self._set_status("Pose Maker is not installed")
                    return
                try:
                    subprocess.Popen(
                        [str(run_script)],
                        cwd=str(root),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                except OSError as exc:
                    self._set_status(f"Pose Maker failed · {exc}")
                    return
                for _ in range(60):
                    if integrations.endpoint_online(url, "/", timeout=0.5):
                        break
                    time.sleep(0.5)
                else:
                    self._set_status("Pose Maker did not come online on port 7861")
                    return
            integrations.open_url(url)
            self._set_status("Pose Maker workbench opened")

        self._set_status("Starting Pose Maker workbench…")
        threading.Thread(target=worker, daemon=True).start()

    def _service(self, url: str, health_path: str, service: str, label: str) -> None:
        def worker() -> None:
            online = integrations.endpoint_online(url, health_path)
            ok, detail = integrations.start_user_service(service, already_online=online)
            if ok:
                for _ in range(40):
                    if integrations.endpoint_online(url, health_path, timeout=0.5):
                        integrations.open_url(url)
                        self._set_status(f"{label} online")
                        return
                    time.sleep(0.75)
            self._set_status(f"{label} · {detail}")
        self._set_status(f"Starting {label}…")
        threading.Thread(target=worker, daemon=True).start()

    @pyqtSlot()
    def refresh(self) -> None:
        def worker() -> None:
            snapshot = integrations.status_snapshot()
            online = [
                name for name, item in snapshot.get("integrations", {}).items()
                if item.get("online")
            ]
            summary = ", ".join(online) if online else "no local services online"
            self._set_status("Health check · " + summary)
        self._set_status("Running health check…")
        threading.Thread(target=worker, daemon=True).start()

    @pyqtSlot(str)
    def triggerAction(self, action: str) -> None:
        key = action.strip().lower()
        if not key:
            return
        if key in {"refresh", "health check"}:
            self.refresh()
        elif any(word in key for word in ("output", "export")):
            self._open(OUTPUT_DIR, "GENESIS exports")
        elif any(word in key for word in ("workflow", "json", "nodes", "preflight", "validate")):
            self._open(WORKFLOW_ROOT, "ComfyUI workflows")
        elif any(word in key for word in ("camera", "grid", "recordings", "hub")):
            self._service(integrations.GO2RTC_URL, "/api/streams", "go2rtc.service", "Camera Hub")
        elif "pose maker" in key or "pose workbench" in key:
            self._pose_maker()
        elif any(word in key for word in ("movie", "video library")):
            ok, detail = integrations.launch_jellyfin_desktop()
            self._set_status(detail if ok else f"Jellyfin failed · {detail}")
        elif "comfyui" in key or key == "manage service":
            self._service(integrations.COMFYUI_URL, "/system_stats", integrations.COMFYUI_SERVICE, "ComfyUI")
        elif "ai settings" in key or "ai assistant" in key:
            self._service(integrations.QWEN_URL, "/health", integrations.QWEN_SERVICE, "GENESIS AI")
        elif "monitor" in key:
            try:
                subprocess.Popen(["gnome-system-monitor"], start_new_session=True)
                self._set_status("System monitor opened")
            except OSError as exc:
                self._set_status(f"System monitor failed · {exc}")
        elif "backup" in key or "recovery" in key:
            self._open(PROJECT_ROOT / "backups", "GENESIS recovery")
        elif "storage" in key or "model" in key:
            self._open(Path("/mnt/AI-Storage"), "Models and storage")
        elif "settings" in key:
            self._open(PROJECT_ROOT, "GENESIS settings")
        else:
            self._legacy(action)


class GenerationBridge(QObject):
    """Asynchronous Qt boundary around the preserved local ComfyUI client."""

    statusChanged = pyqtSignal()
    busyChanged = pyqtSignal()
    previewChanged = pyqtSignal()
    charactersChanged = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._status = "Ready"
        self._busy = False
        self._preview = ""
        self._settings = QSettings("GENESIS", "c0ckpit")
        configured_output = str(self._settings.value("generation/output_dir", str(OUTPUT_DIR)))
        self._output_dir = Path(configured_output).expanduser()

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

    @pyqtProperty(bool, constant=True)
    def inpaintAvailable(self) -> bool:
        return True

    @pyqtProperty(bool, constant=True)
    def upscaleAvailable(self) -> bool:
        return upscale_assets_available()

    def _set_status(self, value: str) -> None:
        self._status = value
        self.statusChanged.emit()

    def _set_busy(self, value: bool) -> None:
        self._busy = value
        self.busyChanged.emit()

    def _set_preview(self, value: str) -> None:
        self._preview = value
        self.previewChanged.emit()

    def _connect_comfyui(self):
        safe, detail = integrations.gpu_kernel_preflight()
        if not safe:
            raise workflow_lab.ComfyError(detail)
        online = integrations.endpoint_online(
            integrations.COMFYUI_URL, "/system_stats", timeout=0.8
        )
        ok, detail = integrations.start_user_service(
            integrations.COMFYUI_SERVICE, already_online=online
        )
        if not ok:
            raise workflow_lab.ComfyError(detail)
        client = workflow_lab.ComfyClient(workflow_lab.COMFY_URL)
        deadline = time.monotonic() + 30
        last_error = "backend not ready"
        while time.monotonic() < deadline:
            try:
                stats = client.system_stats()
                if workflow_lab.gpu_acceleration_available(stats):
                    return client, stats
                last_error = "GPU acceleration unavailable"
            except Exception as exc:
                last_error = str(exc)
            time.sleep(0.5)
        raise workflow_lab.ComfyError(f"ComfyUI did not become GPU-ready: {last_error}")

    @pyqtProperty("QVariantList", notify=charactersChanged)
    def characters(self):
        return character_items()

    @pyqtSlot(str, str, bool, result=str)
    def createCharacterFromImage(self, name: str, source_url: str, adult_confirmed: bool) -> str:
        source = Path(QUrl(source_url).toLocalFile()) if source_url else Path()
        try:
            row = save_character(name, str(source), adult_confirmed=adult_confirmed)
        except ValueError as exc:
            self._set_status(str(exc))
            return ""
        self.charactersChanged.emit()
        self._set_status(f"Character saved · {row['name']}")
        return row["id"]

    @pyqtSlot(str, result=str)
    @pyqtSlot(str, str, result=str)
    def characterIdentitySource(self, character_id: str, role: str = "") -> str:
        source = preferred_reference(character_id, role)
        return QUrl.fromLocalFile(source).toString() if source else ""

    @pyqtSlot(str, str, str, result=bool)
    def addCharacterReference(self, character_id: str, source_url: str, role: str) -> bool:
        source = Path(QUrl(source_url).toLocalFile()) if source_url else Path()
        try:
            row = add_reference(character_id, str(source), role=role)
        except ValueError as exc:
            self._set_status(str(exc))
            return False
        self.charactersChanged.emit()
        self._set_status(f"Character anchor added · {row['name']} · {role or 'anchor'}")
        return True

    @pyqtSlot(result=str)
    def chooseSourceImage(self) -> str:
        dialog = QFileDialog(None, "Choose a source image", str(Path.home()))
        dialog.setNameFilter("Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setViewMode(QFileDialog.ViewMode.List)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        for view in dialog.findChildren(QListView):
            view.setViewMode(QListView.ViewMode.IconMode)
            view.setIconSize(QSize(180, 135))
            view.setGridSize(QSize(210, 175))
            view.setResizeMode(QListView.ResizeMode.Adjust)
            view.setWordWrap(True)
        if dialog.exec() != QFileDialog.DialogCode.Accepted:
            return ""
        selected = dialog.selectedFiles()
        return QUrl.fromLocalFile(selected[0]).toString() if selected else ""

    @pyqtSlot(str, str)
    def queueFaceSwap(self, target_url: str, source_url: str) -> None:
        """Run the isolated two-image ReActor route for ordinary images."""
        if self._busy:
            return
        target = Path(QUrl(target_url).toLocalFile()) if target_url else Path()
        source = Path(QUrl(source_url).toLocalFile()) if source_url else Path()
        if not target.is_file() or not source.is_file():
            self._set_status("Choose both a target image and a source image.")
            return
        self._set_busy(True)
        self._set_status("Preparing two-image face swap…")
        threading.Thread(
            target=self._run_face_swap,
            args=(target, source),
            daemon=True,
        ).start()

    def _run_face_swap(self, target: Path, source: Path) -> None:
        try:
            client, stats = self._connect_comfyui()
            info = client.object_info()
            stamp = time.strftime("%Y%m%d-%H%M%S")
            current = self._run_reference_stage(
                client, info, STAGE_3_WORKFLOW, target, "", stamp,
                "FaceSwap", secondary_image=source,
            )
            self._set_preview(QUrl.fromLocalFile(str(current)).toString())
            self._set_status(f"Complete · {current.name}")
        except Exception as exc:
            self._set_status(f"Face swap failed · {exc}")
        finally:
            self._set_busy(False)

    @pyqtProperty(str, notify=statusChanged)
    def outputFolder(self) -> str:
        return str(self._output_dir)

    @pyqtSlot(result=str)
    def chooseOutputFolder(self) -> str:
        path = QFileDialog.getExistingDirectory(
            None, "Choose GENESIS output folder", str(self._output_dir),
            QFileDialog.Option.ShowDirsOnly,
        )
        if path:
            self._output_dir = Path(path).expanduser()
            self._settings.setValue("generation/output_dir", str(self._output_dir))
            self._settings.sync()
            self._set_status(f"Output folder · {self._output_dir}")
        return str(self._output_dir)

    @pyqtSlot()
    def openOutputFolder(self) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._output_dir))):
            self._set_status("Could not open the selected output folder.")

    @pyqtSlot()
    def showPreviewInFolder(self) -> None:
        source = Path(QUrl(self._preview).toLocalFile())
        if not self._preview or not source.is_file():
            self._set_status("No generated preview is available yet.")
            return
        try:
            subprocess.Popen(["xdg-open", str(source.parent)], start_new_session=True)
        except OSError as exc:
            self._set_status(f"Could not show the generated image folder · {exc}")

    @pyqtSlot()
    def openPreview(self) -> None:
        source = Path(QUrl(self._preview).toLocalFile())
        if not self._preview or not source.is_file():
            self._set_status("No generated preview is available yet.")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(source))):
            self._set_status("Could not open the generated image.")

    @pyqtSlot(str, str, int, int, str, str, str, str, str, bool, bool, bool, name="queueGenerate")
    def queueGenerateLegacy(
        self, prompt_text, negative_prompt, width, height, model_name,
        lora_one, lora_two, source_url, pose_url,
        use_stage_two, use_stage_three, use_upscale,
    ) -> None:
        """Preserve the original QML pose-button contract and model defaults."""
        strength = 0.5 if model_name == FOUR_B_MODEL else 0.65
        self.queueGenerate(
            prompt_text, negative_prompt, width, height, model_name,
            lora_one, lora_two, "None", strength, strength, strength,
            source_url, pose_url, use_stage_two, use_stage_three, use_upscale,
        )

    @pyqtSlot(str, str, int, int, str, str, str, str, float, float, float, str, str, bool, bool, bool)
    def queueGenerate(
        self,
        prompt_text: str,
        negative_prompt: str,
        width: int,
        height: int,
        model_name: str,
        lora_one: str,
        lora_two: str,
        lora_three: str,
        lora_one_strength: float,
        lora_two_strength: float,
        lora_three_strength: float,
        source_url: str,
        pose_url: str,
        use_stage_two: bool,
        use_stage_three: bool,
        use_upscale: bool,
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
        source = Path(QUrl(source_url).toLocalFile()) if source_url else None
        pose = Path(QUrl(pose_url).toLocalFile()) if pose_url else None
        if source_url and (source is None or not source.is_file()):
            self._set_status("The selected source image is unavailable.")
            return
        if model_name == QWEN_MODEL and source is None:
            self._set_status("Phr00t/Qwen requires a source image.")
            return
        if source is not None and model_name not in {QWEN_MODEL, FOUR_B_MODEL}:
            self._set_status(
                "That engine has no validated source-image graph. Choose 4B or Phr00t/Qwen, "
                "or clear the source for text-to-image."
            )
            return
        if use_stage_three and source is None:
            self._set_status("Stage 3 face lock requires an original source image.")
            return
        if use_upscale and not self.upscaleAvailable:
            self._set_status("Upscale is blocked: its checkpoint, VAE, or 4x-UltraSharp asset is missing.")
            return
        try:
            selected_loras = compatible_selection(model_name, [lora_one, lora_two, lora_three])
            max_loras = 1 if model_name in {REGULAR_9B_MODEL, FOUR_B_MODEL} else 0
            if len(selected_loras) > max_loras:
                raise ValueError(f"{model_name} allows {max_loras} LoRA slot(s).")
            if any(value < 0.0 or value > 1.0 for value in (lora_one_strength, lora_two_strength, lora_three_strength)):
                raise ValueError("LoRA strengths must be between 0.00 and 1.00.")
        except ValueError as exc:
            self._set_status(str(exc))
            return
        self._set_busy(True)
        engine = {
            REGULAR_9B_MODEL: "Klein 9B Base",
            KV_9B_MODEL: "Klein 9B-KV",
            QWEN_MODEL: "Phr00t/Qwen",
            FOUR_B_MODEL: "Klein 4B Fast",
        }[model_name]
        self._set_status(f"Preparing validated {engine} generation…")
        threading.Thread(
            target=self._run_generate,
            args=(prompt_text, negative_prompt, int(width), int(height), model_name, lora_one,
                  lora_two, lora_three, float(lora_one_strength), float(lora_two_strength),
                  float(lora_three_strength), source, pose,
                  bool(use_stage_two), bool(use_stage_three),
                  bool(use_upscale)),
            daemon=True,
        ).start()

    @pyqtSlot(str, str, str, float)
    def queueInpaint(self, source_url: str, mask_url: str, prompt_text: str, strength: float) -> None:
        if self._busy:
            return
        source = Path(QUrl(source_url).toLocalFile())
        mask = Path(QUrl(mask_url).toLocalFile())
        prompt_text = prompt_text.strip()
        if not source.is_file() or not mask.is_file() or not prompt_text:
            self._set_status("Choose a source image, mask image, and enter inpaint instructions.")
            return
        self._set_busy(True)
        self._set_status("Preparing masked inpaint workflow…")
        threading.Thread(
            target=self._run_inpaint,
            args=(source, mask, prompt_text, float(strength)),
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
        lora_three: str,
        lora_one_strength: float,
        lora_two_strength: float,
        lora_three_strength: float,
        source: Path | None,
        pose: Path | None,
        use_stage_two: bool,
        use_stage_three: bool,
        use_upscale: bool,
    ) -> None:
        try:
            if model_name == FOUR_B_MODEL:
                required_model = Path.home() / "AI/ComfyUI/models/diffusion_models" / FOUR_B_MODEL
                ready, detail = integrations.ensure_ai_model_volume_readonly(required_model)
                if not ready:
                    raise workflow_lab.ComfyError(detail)
            client, stats = self._connect_comfyui()
            info = client.object_info()
            self._output_dir.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            if source is not None and model_name == FOUR_B_MODEL:
                current = self._run_4b_source(
                    client, info, source, adapt_prompt(prompt_text, FOUR_B_MODEL, source_image=True),
                    [lora_one, lora_two, lora_three],
                    [lora_one_strength, lora_two_strength, lora_three_strength], width, height, stamp,
                )
            elif source is not None:
                current = self._run_reference_stage(
                    client, info, STAGE_1_WORKFLOW, source,
                    adapt_prompt(prompt_text, QWEN_MODEL, source_image=True),
                    stamp, "Stage1", secondary_image=pose,
                )
            else:
                prompt = build_create_prompt(
                    info, adapt_prompt(prompt_text, model_name), width, height,
                    model_name, [lora_one, lora_two, lora_three],
                    [lora_one_strength, lora_two_strength, lora_three_strength]
                )
                # The validated distilled create graphs intentionally zero negative
                # conditioning. Keep the user's text in state for compatible stages.
                _ = negative_prompt
                current = self._submit_and_save(client, prompt, stamp, "Klein")

            if use_stage_two:
                current = self._run_reference_stage(
                    client, info, STAGE_2_WORKFLOW, current,
                    adapt_prompt(prompt_text, "lustifySDXLNSFWSFW_v20LIGHTNING.safetensors"),
                    stamp, "Stage2",
                )
            if use_stage_three:
                current = self._run_reference_stage(
                    client, info, STAGE_3_WORKFLOW, current, "", stamp, "Stage3",
                    secondary_image=source,
                )
            if use_upscale:
                current = self._run_reference_stage(
                    client, info, UPSCALE_WORKFLOW, current, "", stamp, "Upscale"
                )
            self._set_preview(QUrl.fromLocalFile(str(current)).toString())
            self._set_status(f"Complete · {current.name}")
        except Exception as exc:
            self._set_status(f"Generation failed · {exc}")
        finally:
            self._set_busy(False)

    def _run_4b_source(
        self, client, info: dict, source: Path, prompt_text: str,
        loras: list[str], strengths: list[float], width: int, height: int, stamp: str,
    ) -> Path:
        prompt = workflow_lab.workflow_to_prompt(FOUR_B_SOURCE_WORKFLOW, info)
        selected = compatible_selection(FOUR_B_MODEL, loras)
        if len(selected) > 1:
            raise workflow_lab.ComfyError("Klein 4B remains isolated to one experimental LoRA.")
        if selected:
            lora = selected[0]
            selected_strength = strengths[loras.index(lora)]
            prompt["4"]["inputs"].update({
                "lora_name": lora,
                "strength_model": selected_strength,
                "strength_clip": 0.0,
            })
        else:
            # The source workflow historically contains a LoRA loader.  When
            # no runtime-approved adapter exists, bypass it completely rather
            # than leaving a hidden/default LoRA in the graph.
            prompt["8"]["inputs"]["model"] = ["1", 0]
            prompt["5"]["inputs"]["clip"] = ["2", 0]
            prompt["6"]["inputs"]["clip"] = ["2", 0]
            prompt.pop("4", None)
        prompt["5"]["inputs"]["text"] = prompt_text
        prompt["7"]["inputs"].update({"width": width, "height": height, "batch_size": 1})
        prompt["9"]["inputs"].update({"steps": 4, "cfg": 1.0})
        uploaded = client.upload_image(source)
        prompt["11"]["inputs"]["image"] = "/".join(
            value for value in (uploaded.get("subfolder"), uploaded.get("name")) if value
        )
        validation = workflow_lab.validate_prompt(prompt, info)
        if not validation["valid"]:
            missing = validation["missing_nodes"] + validation["missing_inputs"]
            raise workflow_lab.ComfyError("Klein 4B source workflow is not runnable: " + ", ".join(missing))
        return self._submit_and_save(client, prompt, stamp, "Klein4B")

    def _submit_and_save(self, client, prompt: dict, stamp: str, stage: str) -> Path:
        safe, detail = integrations.gpu_kernel_preflight()
        if not safe:
            raise workflow_lab.ComfyError(detail)
        problems = unavailable_local_assets(prompt, MODEL_ROOTS)
        if problems:
            raise workflow_lab.ComfyError("Local asset check failed: " + " ".join(problems))
        prompt_id = client.submit(prompt)
        self._set_status(f"{stage} queued {prompt_id[:8]}…")
        result = client.wait(
            prompt_id,
            timeout=1800,
            progress=lambda value: self._set_status(
                f"{stage} {value.get('status', 'working')} · {int(value.get('elapsed', 0))}s"
            ),
            abort_check=integrations.gpu_kernel_abort_reason,
        )
        if result.status != "completed":
            raise workflow_lab.ComfyError(result.error or f"{stage} ended: {result.status}")
        saved: list[Path] = []
        for index, output in enumerate(result.outputs, 1):
            if output.get("kind") != "images":
                continue
            suffix = Path(output.get("filename", "image.png")).suffix or ".png"
            target = self._output_dir / f"GENESIS-{stage}-{stamp}-{index}{suffix}"
            target.write_bytes(client.view(output))
            saved.append(target)
        if not saved:
            raise workflow_lab.ComfyError(f"{stage} completed without an image output.")
        return saved[-1]

    def _run_reference_stage(
        self, client, info: dict, workflow: Path, input_image: Path,
        prompt_text: str, stamp: str, stage: str, secondary_image: Path | None = None,
    ) -> Path:
        if not workflow.is_file():
            raise workflow_lab.ComfyError(f"{stage} workflow is unavailable.")
        prompt = workflow_lab.workflow_to_prompt(workflow, info)
        load_nodes = sorted(
            (str(node_id) for node_id, node in prompt.items() if node.get("class_type") == "LoadImage"),
            key=lambda value: int(value) if value.isdigit() else value,
        )
        images = [input_image] + ([secondary_image] if secondary_image is not None else [])
        if len(load_nodes) < len(images):
            raise workflow_lab.ComfyError(f"{stage} workflow has too few image inputs.")
        for node_id, path in zip(load_nodes, images):
            uploaded = client.upload_image(path)
            prompt[node_id]["inputs"]["image"] = "/".join(
                value for value in (uploaded.get("subfolder"), uploaded.get("name")) if value
            )
        if prompt_text:
            controls = workflow_lab.discover_workflow_controls(prompt)
            target = controls.get("positive")
            if target:
                prompt[str(target[0])]["inputs"][target[1]] = prompt_text
        validation = workflow_lab.validate_prompt(prompt, info)
        if not validation["valid"]:
            missing = validation["missing_nodes"] + validation["missing_inputs"]
            raise workflow_lab.ComfyError(f"{stage} is not runnable: " + ", ".join(missing))
        return self._submit_and_save(client, prompt, stamp, stage)


    def _run_inpaint(self, source: Path, mask: Path, prompt_text: str, strength: float) -> None:
        try:
            client, stats = self._connect_comfyui()
            info = client.object_info()
            checkpoints = (
                info.get("CheckpointLoaderSimple", {})
                .get("input", {}).get("required", {}).get("ckpt_name", [[], {}])[0]
            )
            if INPAINT_CHECKPOINT not in checkpoints:
                raise workflow_lab.ComfyError(
                    f"Inpaint checkpoint is unavailable: {INPAINT_CHECKPOINT}"
                )

            src_up = client.upload_image(source)
            mask_up = client.upload_image(mask)
            src_name = "/".join(v for v in (src_up.get("subfolder"), src_up.get("name")) if v)
            mask_name = "/".join(v for v in (mask_up.get("subfolder"), mask_up.get("name")) if v)
            denoise = max(0.05, min(0.95, strength))
            seed = int(time.time_ns() & 0xFFFFFFFFFFFF)
            prompt = {
                "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": INPAINT_CHECKPOINT}},
                "2": {"class_type": "LoadImage", "inputs": {"image": src_name}},
                "3": {"class_type": "LoadImageMask", "inputs": {"image": mask_name, "channel": "red"}},
                "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_text, "clip": ["1", 1]}},
                "5": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["1", 1]}},
                "6": {"class_type": "VAEEncodeForInpaint", "inputs": {
                    "pixels": ["2", 0], "vae": ["1", 2], "mask": ["3", 0], "grow_mask_by": 6
                }},
                "7": {"class_type": "KSampler", "inputs": {
                    "model": ["1", 0], "seed": seed, "steps": 24, "cfg": 5.0,
                    "sampler_name": "dpmpp_2m", "scheduler": "karras",
                    "positive": ["4", 0], "negative": ["5", 0],
                    "latent_image": ["6", 0], "denoise": denoise
                }},
                "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["1", 2]}},
                "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "GENESIS-Inpaint"}},
            }
            validation = workflow_lab.validate_prompt(prompt, info)
            if not validation["valid"]:
                missing = validation["missing_nodes"] + validation["missing_inputs"]
                raise workflow_lab.ComfyError("Inpaint workflow is not runnable: " + ", ".join(missing))
            stamp = time.strftime("%Y%m%d-%H%M%S")
            current = self._submit_and_save(client, prompt, stamp, "Inpaint")
            self._set_preview(QUrl.fromLocalFile(str(current)).toString())
            self._set_status(f"Complete · {current.name}")
        except Exception as exc:
            self._set_status(f"Inpaint failed · {exc}")
        finally:
            self._set_busy(False)

    def _run_edit(self, source: Path, prompt_text: str, strength: float) -> None:
        try:
            client, stats = self._connect_comfyui()
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
                abort_check=integrations.gpu_kernel_abort_reason,
            )
            if result.status != "completed":
                raise workflow_lab.ComfyError(result.error or f"Edit ended: {result.status}")

            self._output_dir.mkdir(parents=True, exist_ok=True)
            saved: list[Path] = []
            stamp = time.strftime("%Y%m%d-%H%M%S")
            for index, output in enumerate(result.outputs, 1):
                if output.get("kind") != "images":
                    continue
                suffix = Path(output.get("filename", "image.png")).suffix or ".png"
                target = self._output_dir / f"GENESIS-Edit-{stamp}-{index}{suffix}"
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
        "posemaker": 9,
    }
    parser.add_argument("--page", choices=tuple(page_indexes), default="create")
    parser.add_argument("--banner", choices=("video", "photos"), default="video")
    args, qt_args = parser.parse_known_args()
    sys.argv = [sys.argv[0], *qt_args]
    app = QApplication(sys.argv)
    app.setApplicationName("GENESIS Cockpit")
    app.setWindowIcon(QIcon(str(PROJECT_ROOT / "genesis/assets/genesis-cockpit-icon-balanced-final.png")))
    engine = QQmlApplicationEngine()
    context = engine.rootContext()
    context.setContextProperty("genesisAssetRoot", QUrl.fromLocalFile(str(ASSET_ROOT) + "/"))
    context.setContextProperty("genesisUiRoot", QUrl.fromLocalFile(str(UI_ROOT) + "/"))
    context.setContextProperty("poseItems", load_pose_items())
    context.setContextProperty("grokPresetItems", load_grok_preset_items())
    context.setContextProperty("curatedPosePresets", load_curated_pose_presets())
    context.setContextProperty("generationProfiles", load_generation_profiles())
    context.setContextProperty("runtimeStatus", load_runtime_status())
    generation_bridge = GenerationBridge(app)
    layout_bridge = LayoutSettingsBridge(app)
    module_bridge = ModuleBridge(app)
    context.setContextProperty("genesisBridge", generation_bridge)
    context.setContextProperty("genesisLayout", layout_bridge)
    context.setContextProperty("moduleBridge", module_bridge)
    engine.load(QUrl.fromLocalFile(str(UI_ROOT / "MainPremiumLinux.qml")))
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]
    window.setProperty("pageIndex", page_indexes[args.page])
    window.setProperty("bannerMode", 1 if args.banner == "photos" else 0)
    if args.width or args.height:
        window.resize(max(900, args.width or window.width()), max(600, args.height or window.height()))
    if args.screenshot:
        window.show()
    else:
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