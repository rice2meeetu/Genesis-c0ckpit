from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from genesis.comfy_client import ComfyClient, ComfyError, PromptResult


COMFY_URL = "http://127.0.0.1:8188"

BASE_DIR = Path(__file__).resolve().parent
REFERENCE_DIR = BASE_DIR / "reference"
POSE_INDEX_PATH = REFERENCE_DIR / "pose_library_index.json"
POSE_WORKFLOW_DIR = REFERENCE_DIR / "pose_workflows"

PREFERRED_STAGE1 = "Qwen-Rapid-AIO-NSFW-v19.safetensors"

PREFERRED_STAGE2 = [
    "Lustify",
    "lustify",
]

REQUIRED_POSE_NODES = {
    "CheckpointLoaderSimple",
    "KSampler",
    "LoadImage",
    "SaveImage",
    "TextEncodeQwenImageEditPlus",
    "DWPreprocessor",
    "ReActorFaceSwap",
}

OPTIONAL_NODES = {
    "FaceDetailer": "Optional face/detail polish",
    "UltimateSDUpscale": "Optional final upscale",
    "ControlNetLoader": "ControlNet workflow support",
    "ControlNetApplyAdvanced": "Advanced ControlNet workflow support",
}

WORKFLOW_DIRS = (
    POSE_WORKFLOW_DIR,
    Path.home() / "AI" / "ComfyUI" / "user" / "default" / "workflows",
    Path.home() / "AI" / "ComfyUI" / "workflows",
)

KNOWN_WIDGET_INPUTS = {
    # Loader choices can reference models that are mounted after ComfyUI starts.
    # Preserve their positional UI values instead of discarding a value merely
    # because it is absent from the current /object_info choice list.
    "UNETLoader": ("unet_name", "weight_dtype"),
    "UnetLoaderGGUF": ("unet_name",),
    "CLIPLoader": ("clip_name", "type", "device"),
    "CheckpointLoaderSimple": ("ckpt_name",),
    "VAELoader": ("vae_name",),
    "LoadImage": ("image", None),
    "LoraLoader": ("lora_name", "strength_model", "strength_clip"),
    "LoraLoaderBypass": ("lora_name", "strength_model", "strength_clip"),
    # The second serialized widget is a frontend-only resize control, not the
    # optional IMAGE3 socket exposed by the backend schema.
    "TextEncodeQwenImageEditPlus": ("prompt", None),
    "KSampler": ("seed", None, "steps", "cfg", "sampler_name", "scheduler", "denoise"),
    "KSamplerAdvanced": (
        "add_noise", "noise_seed", None, "steps", "cfg", "sampler_name",
        "scheduler", "start_at_step", "end_at_step", "return_with_leftover_noise",
    ),
}


@dataclass
class PipelineStage:
    workflow: str | Path
    overrides: dict[str, dict[str, Any]] = field(default_factory=dict)
    carry_to_node: str | int | None = None
    name: str = "stage"


def _json_request(path: str, timeout: float = 10.0) -> Any:
    url = COMFY_URL.rstrip("/") + "/" + path.lstrip("/")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "GENESIS-Workflow-Lab/1.0"},
    )

    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()

    if not raw:
        return {}

    return json.loads(raw.decode("utf-8", "replace"))


def comfy_alive(timeout: float = 2.5) -> bool:
    try:
        _json_request("/system_stats", timeout=timeout)
        return True
    except (
        OSError,
        TimeoutError,
        urllib.error.URLError,
        json.JSONDecodeError,
    ):
        return False


def object_info() -> dict:
    data = _json_request("/object_info", timeout=20)
    return data if isinstance(data, dict) else {}


def system_stats() -> dict:
    data = _json_request("/system_stats", timeout=10)
    return data if isinstance(data, dict) else {}


def _choice_values(spec: Any) -> list:
    if isinstance(spec, (list, tuple)) and spec:
        values = spec[0]
        if isinstance(values, (list, tuple)):
            return list(values)
    return []


def _node_choices(info: dict, node_type: str, input_name: str) -> list[str]:
    try:
        input_data = info[node_type]["input"]
        spec = (input_data.get("required") or {}).get(input_name)
        if spec is None:
            spec = (input_data.get("optional") or {}).get(input_name)
    except (KeyError, TypeError, AttributeError):
        return []
    return [str(value) for value in _choice_values(spec)]


def model_inventory(info: dict | None = None) -> dict[str, list[str]]:
    """Discover checkpoints, diffusion models, LoRAs and VAEs from ComfyUI."""
    if info is None:
        info = object_info()

    def combined(node_inputs: list[tuple[str, str]]) -> list[str]:
        values: set[str] = set()
        for node_type, input_name in node_inputs:
            values.update(_node_choices(info, node_type, input_name))
        return sorted(values, key=str.lower)

    return {
        "checkpoints": combined([
            ("CheckpointLoaderSimple", "ckpt_name"),
        ]),
        "diffusion_models": combined([
            ("UNETLoader", "unet_name"),
            ("UNETLoader", "model_name"),
        ]),
        "loras": combined([
            ("LoraLoader", "lora_name"),
            ("LoraLoaderModelOnly", "lora_name"),
            ("Flux2KleinLoraLoader", "lora_name"),
            ("FluxLoraLoader", "lora_name"),
        ]),
        "vaes": combined([
            ("VAELoader", "vae_name"),
        ]),
        "text_encoders": combined([
            ("CLIPLoader", "clip_name"),
            ("DualCLIPLoader", "clip_name1"),
            ("DualCLIPLoader", "clip_name2"),
        ]),
    }


def gpu_metrics(stats: dict | None = None) -> dict:
    """Normalize ComfyUI device statistics for live cockpit monitoring."""
    stats = stats if stats is not None else system_stats()
    devices = stats.get("devices") or (stats.get("system") or {}).get("devices") or []
    if not devices or not isinstance(devices[0], dict):
        return {"name": "unknown", "vram_total": 0, "vram_free": 0, "vram_used": 0, "usage_percent": 0.0}
    device = devices[0]
    total = int(device.get("vram_total") or device.get("total_memory") or 0)
    free = int(device.get("vram_free") or device.get("free_memory") or 0)
    used = max(0, total - free)
    return {
        "name": str(device.get("name") or device.get("type") or "detected"),
        "vram_total": total,
        "vram_free": free,
        "vram_used": used,
        "usage_percent": round((used / total * 100), 1) if total else 0.0,
    }


def available_checkpoints(info: dict | None = None) -> list[str]:
    if info is None:
        info = object_info()

    try:
        spec = info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"]
    except (KeyError, TypeError):
        return []

    if isinstance(spec, (list, tuple)) and spec:
        values = spec[0]
        if isinstance(values, (list, tuple)):
            return [str(x) for x in values]

    return []


def _find_stage2_checkpoint(checkpoints: list[str]) -> str | None:
    lowered = [(x, x.lower()) for x in checkpoints]

    for wanted in PREFERRED_STAGE2:
        needle = wanted.lower()

        for original, low in lowered:
            if needle in low:
                return original

    return None


def gpu_name(stats: dict | None = None) -> str:
    if stats is None:
        stats = system_stats()

    devices = stats.get("devices")

    if not devices and isinstance(stats.get("system"), dict):
        devices = stats["system"].get("devices")

    if not isinstance(devices, list) or not devices:
        return "unknown"

    first = devices[0]

    if isinstance(first, dict):
        return str(
            first.get("name")
            or first.get("type")
            or first.get("device")
            or "detected"
        )

    return str(first)


def gpu_acceleration_available(stats: dict | None = None) -> bool:
    """Return True only when ComfyUI reports a non-CPU render device."""
    if stats is None:
        stats = system_stats()

    system = stats.get("system") if isinstance(stats, dict) else {}
    argv = system.get("argv") if isinstance(system, dict) else []
    if any(str(value).lower() == "--cpu" for value in (argv or [])):
        return False

    devices = stats.get("devices") if isinstance(stats, dict) else None
    if not devices and isinstance(system, dict):
        devices = system.get("devices")
    if not isinstance(devices, list):
        return False

    for device in devices:
        if not isinstance(device, dict):
            continue
        identity = " ".join(
            str(device.get(key) or "")
            for key in ("type", "name", "device")
        ).strip().lower()
        if identity and identity not in {"cpu", "cpu cpu"} and not identity.startswith("cpu "):
            return True
    return False


def health_report() -> dict:
    report = {
        "online": False,
        "gpu": "unknown",
        "missing_required_nodes": [],
        "optional_nodes": {},
        "checkpoints": [],
        "stage1_checkpoint": None,
        "stage2_checkpoint": None,
        "ready": False,
        "error": None,
    }

    try:
        info = object_info()
        stats = system_stats()
    except Exception as exc:
        report["error"] = str(exc)
        return report

    report["online"] = True
    report["gpu"] = gpu_name(stats)

    installed = set(info.keys())

    report["missing_required_nodes"] = sorted(
        REQUIRED_POSE_NODES - installed
    )

    report["optional_nodes"] = {
        node: node in installed
        for node in OPTIONAL_NODES
    }

    checkpoints = available_checkpoints(info)
    report["checkpoints"] = checkpoints

    report["stage1_checkpoint"] = (
        PREFERRED_STAGE1
        if PREFERRED_STAGE1 in checkpoints
        else next(
            (
                x
                for x in checkpoints
                if "qwen" in x.lower()
                and "rapid" in x.lower()
            ),
            None,
        )
    )

    report["stage2_checkpoint"] = _find_stage2_checkpoint(checkpoints)

    report["ready"] = (
        report["online"]
        and not report["missing_required_nodes"]
        and report["stage1_checkpoint"] is not None
    )

    return report


def health_report_text() -> str:
    r = health_report()

    if not r["online"]:
        return (
            "COMFYUI: OFFLINE\n"
            f"ERROR: {r['error'] or 'backend unavailable'}"
        )

    lines = [
        "GENESIS WORKFLOW LAB HEALTH",
        f"ComfyUI: ONLINE",
        f"GPU: {r['gpu']}",
        "",
    ]

    if r["missing_required_nodes"]:
        lines.append("MISSING REQUIRED NODES:")
        lines.extend(
            f"  - {node}"
            for node in r["missing_required_nodes"]
        )
    else:
        lines.append("Required Pose nodes: PASS")

    lines.append("")
    lines.append(
        "Stage 1 checkpoint: "
        + str(r["stage1_checkpoint"] or "NOT FOUND")
    )
    lines.append(
        "Stage 2 checkpoint: "
        + str(r["stage2_checkpoint"] or "NOT FOUND")
    )

    lines.append("")
    lines.append("OPTIONAL NODES:")

    for node, present in r["optional_nodes"].items():
        lines.append(
            f"  {'FOUND' if present else 'NOT INSTALLED'} · "
            f"{node} · {OPTIONAL_NODES[node]}"
        )

    lines.append("")
    lines.append(
        "STATUS: READY"
        if r["ready"]
        else "STATUS: NEEDS ATTENTION"
    )

    return "\n".join(lines)


def pose_library_index() -> list[dict]:
    if not POSE_INDEX_PATH.is_file():
        return []

    try:
        data = json.loads(
            POSE_INDEX_PATH.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
    except (OSError, json.JSONDecodeError):
        return []

    if isinstance(data, list):
        return [
            x for x in data
            if isinstance(x, dict)
        ]

    if isinstance(data, dict):
        for key in (
            "poses",
            "items",
            "library",
            "entries",
        ):
            value = data.get(key)

            if isinstance(value, list):
                return [
                    x for x in value
                    if isinstance(x, dict)
                ]

    return []


def pose_library_categories() -> list[str]:
    cats = {
        str(item.get("category")).strip()
        for item in pose_library_index()
        if item.get("category")
    }

    return ["All"] + sorted(cats, key=str.lower)


def filter_pose_library(
    category: str = "All",
    search: str = "",
) -> list[dict]:
    items = pose_library_index()

    category = (category or "All").strip()
    search = (search or "").strip().lower()

    out = []

    for item in items:
        if (
            category.lower() != "all"
            and str(item.get("category", "")).lower()
            != category.lower()
        ):
            continue

        if search:
            haystack = json.dumps(
                item,
                ensure_ascii=False,
            ).lower()

            if search not in haystack:
                continue

        out.append(item)

    return out


def pose_library_page(
    category: str = "All",
    search: str = "",
    page: int = 1,
    page_size: int = 24,
) -> dict:
    page = max(1, int(page or 1))
    page_size = max(1, min(100, int(page_size or 24)))

    items = filter_pose_library(category, search)

    total = len(items)
    pages = max(1, (total + page_size - 1) // page_size)

    if page > pages:
        page = pages

    start = (page - 1) * page_size
    end = start + page_size

    return {
        "items": items[start:end],
        "page": page,
        "pages": pages,
        "total": total,
        "page_size": page_size,
    }


def pose_route_status(
    pose_present: bool,
    pose_source_kind: str,
    pose_mode: str,
) -> str:
    mode = (pose_mode or "").upper()
    kind = (pose_source_kind or "photo").lower()

    if mode.startswith("PROMPT ONLY"):
        return (
            "WRITTEN PROMPT ONLY · "
            "no pose image will be used"
        )

    if not pose_present:
        return (
            "WRITTEN PROMPT ONLY · "
            "add a pose image or library skeleton "
            "for exact geometry"
        )

    if mode.startswith("DIRECT"):
        return (
            "DIRECT PHOTO · advanced appearance-reference "
            "path"
        )

    if (
        kind == "skeleton"
        and not mode.startswith("EXTRACT")
    ):
        return (
            "LIBRARY SKELETON → Stage 1 · "
            "no DWPose conversion required"
        )

    return (
        "POSE PHOTO → DWPose geometry → "
        "rendered skeleton → Stage 1"
    )


def workflow_node_types(workflow: dict) -> list[str]:
    found: set[str] = set()

    nodes = workflow.get("nodes")

    if isinstance(nodes, list):
        for node in nodes:
            if not isinstance(node, dict):
                continue

            node_type = (
                node.get("type")
                or node.get("class_type")
            )

            if node_type:
                found.add(str(node_type))

    for value in workflow.values():
        if (
            isinstance(value, dict)
            and value.get("class_type")
        ):
            found.add(str(value["class_type"]))

    return sorted(found, key=str.lower)


def load_workflow(workflow: str | Path | dict) -> dict:
    if isinstance(workflow, dict):
        return json.loads(json.dumps(workflow))
    value = json.loads(Path(workflow).read_text(encoding="utf-8", errors="replace"))
    if not isinstance(value, dict):
        raise ValueError("Workflow JSON root is not an object")
    return value


def is_api_workflow(workflow: dict) -> bool:
    return bool(workflow) and not isinstance(workflow.get("nodes"), list) and all(
        isinstance(value, dict) and value.get("class_type")
        for value in workflow.values()
    )


def _input_specs(info: dict, node_type: str) -> list[tuple[str, Any]]:
    node = info.get(node_type) or {}
    inputs = node.get("input") or {}
    return list((inputs.get("required") or {}).items()) + list((inputs.get("optional") or {}).items())


def _matches_widget(value: Any, spec: Any) -> bool:
    choices = _choice_values(spec)
    if choices:
        return value in choices
    kind = spec[0] if isinstance(spec, (list, tuple)) and spec else None
    if kind in ("INT", "FLOAT"):
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "BOOLEAN":
        return isinstance(value, bool)
    if kind == "STRING":
        return isinstance(value, str)
    return True


def _widget_inputs(node: dict, specs: list[tuple[str, Any]], linked: set[str]) -> dict:
    widgets = node.get("widgets_values") or []
    if isinstance(widgets, dict):
        return {name: value for name, value in widgets.items() if name not in linked}
    node_type = str(node.get("type") or "")
    known = KNOWN_WIDGET_INPUTS.get(node_type)
    if known:
        return {
            name: widgets[index]
            for index, name in enumerate(known)
            if name and index < len(widgets) and name not in linked
        }
    values = list(widgets) if isinstance(widgets, list) else []
    result: dict[str, Any] = {}
    cursor = 0
    for name, spec in specs:
        if name in linked:
            continue
        while cursor < len(values) and not _matches_widget(values[cursor], spec):
            cursor += 1
        if cursor < len(values):
            result[name] = values[cursor]
            cursor += 1
    return result


def workflow_to_prompt(
    workflow: str | Path | dict,
    info: dict,
    overrides: dict[str | int, dict[str, Any]] | None = None,
) -> dict:
    """Convert a ComfyUI UI workflow to executable API prompt format."""
    value = load_workflow(workflow)
    if is_api_workflow(value):
        prompt = value
    else:
        nodes = {
            str(node["id"]): node
            for node in value.get("nodes") or []
            if isinstance(node, dict) and node.get("id") is not None
        }
        links = {
            int(link[0]): link
            for link in value.get("links") or []
            if isinstance(link, list) and len(link) >= 6
        }
        prompt: dict[str, dict] = {}
        ignored = {"Note", "PrimitiveNode", "Reroute"}
        for node_id, node in nodes.items():
            node_type = str(node.get("type") or "")
            mode = int(node.get("mode") or 0)
            if mode != 0 or node_type in ignored:
                continue
            if node_type not in info:
                raise ComfyError(f"Node {node_id} uses unavailable type {node_type}")
            inputs: dict[str, Any] = {}
            linked_names: set[str] = set()
            for input_value in node.get("inputs") or []:
                link_id = input_value.get("link")
                if link_id is None:
                    continue
                link = links.get(int(link_id))
                if not link:
                    raise ComfyError(f"Node {node_id} has missing link {link_id}")
                source_id, source_slot = str(link[1]), int(link[2])
                if source_id not in nodes or int(nodes[source_id].get("mode") or 0) != 0:
                    raise ComfyError(f"Node {node_id} depends on disabled node {source_id}")
                name = str(input_value["name"])
                inputs[name] = [source_id, source_slot]
                linked_names.add(name)
            specs = _input_specs(info, node_type)
            inputs.update(_widget_inputs(node, specs, linked_names))
            prompt[node_id] = {
                "class_type": node_type,
                "inputs": inputs,
                "_meta": {"title": node.get("title") or node_type},
            }
    for node_id, values in (overrides or {}).items():
        key = str(node_id)
        if key not in prompt:
            raise ComfyError(f"Override targets unknown executable node {key}")
        prompt[key].setdefault("inputs", {}).update(values)
    return prompt


def workflow_parameters(workflow: str | Path | dict, info: dict) -> list[dict]:
    """Return editable primitive inputs after converting a workflow."""
    prompt = workflow_to_prompt(workflow, info)
    parameters = []
    for node_id, node in prompt.items():
        for name, value in (node.get("inputs") or {}).items():
            if isinstance(value, list) and len(value) == 2:
                continue
            choices = _node_choices(info, node["class_type"], name)
            parameters.append({
                "node_id": node_id,
                "node_type": node["class_type"],
                "title": (node.get("_meta") or {}).get("title", node["class_type"]),
                "input": name,
                "value": value,
                "choices": choices,
            })
    return parameters


def workflow_browser(extra_dirs: list[str | Path] | None = None) -> list[dict]:
    """Index bundled, ComfyUI and user-selected workflow directories."""
    directories = [*WORKFLOW_DIRS, *(extra_dirs or [])]
    found: dict[str, dict] = {}
    for directory in directories:
        directory = Path(directory).expanduser()
        if not directory.is_dir():
            continue
        for path in directory.rglob("*.json"):
            # ComfyUI's workflow index and hidden metadata are not workflows.
            if path.name.startswith(".") or path.name.endswith(".index.json"):
                continue
            resolved = str(path.resolve())
            try:
                workflow = load_workflow(path)
                node_types = workflow_node_types(workflow)
            except Exception as exc:
                found[resolved] = {"path": resolved, "name": path.stem, "valid": False, "error": str(exc), "node_types": []}
                continue
            found[resolved] = {
                "path": resolved,
                "name": path.stem,
                "valid": True,
                "error": None,
                "node_types": node_types,
                "stage": next((part for part in ("STAGE_1", "STAGE_2", "STAGE_3") if part in path.name.upper()), None),
            }
    return sorted(found.values(), key=lambda item: (item["name"].lower(), item["path"]))




def discover_workflow_controls(prompt: dict) -> dict:
    """
    Automatically discover editable controls inside a ComfyUI prompt.
    Returns a mapping of control -> (node_id, input_name).
    """
    mapping = {}

    aliases = {
        "cfg": {"cfg"},
        "steps": {"steps"},
        "seed": {"seed", "noise_seed"},
        "width": {"width"},
        "height": {"height"},
        "denoise": {"denoise"},
        "sampler": {"sampler_name"},
        "scheduler": {"scheduler"},
        "model": {"ckpt_name", "model_name", "unet_name"},
        "lora": {"lora_name"},
        "vae": {"vae_name"},
        "encoder": {"clip_name", "text_encoder"},
        "positive": {"text", "prompt", "positive"},
        "negative": {"negative"},
    }

    for node_id, node in prompt.items():
        inputs = node.get("inputs", {})
        for control, names in aliases.items():
            if control in mapping:
                continue
            for name in names:
                if name in inputs:
                    mapping[control] = (node_id, name)
                    break

    return mapping


def apply_negative_prompt(prompt: dict, text: str = "") -> str | None:
    """Attach a dedicated CLIP conditioning node to every sampler negative input."""
    negative_id = next(
        (
            str(node_id)
            for node_id, node in prompt.items()
            if node.get("class_type") == "CLIPTextEncode"
            and "negative" in str((node.get("_meta") or {}).get("title", "")).lower()
        ),
        None,
    )

    if negative_id is None:
        source_id = next(
            (
                str(inputs["positive"][0])
                for node in prompt.values()
                if node.get("class_type") in {"KSampler", "KSamplerAdvanced"}
                for inputs in [node.get("inputs") or {}]
                if isinstance(inputs.get("positive"), list)
                and len(inputs["positive"]) == 2
                and str(inputs["positive"][0]) in prompt
                and prompt[str(inputs["positive"][0])].get("class_type") == "CLIPTextEncode"
            ),
            None,
        )
        if source_id is None:
            return None

        negative_id = "__genesis_negative__"
        suffix = 2
        while negative_id in prompt:
            negative_id = f"__genesis_negative_{suffix}__"
            suffix += 1
        source = prompt[source_id]
        prompt[negative_id] = json.loads(json.dumps(source))
        prompt[negative_id]["_meta"] = {"title": "GENESIS Negative Prompt"}

    prompt[negative_id].setdefault("inputs", {})["text"] = str(text or "")
    prompt[negative_id]["inputs"].pop("negative", None)
    for node in prompt.values():
        if node.get("class_type") in {"KSampler", "KSamplerAdvanced"}:
            node.setdefault("inputs", {})["negative"] = [negative_id, 0]
    return negative_id

def validate_prompt(prompt: dict, info: dict) -> dict:
    missing_nodes = sorted({node["class_type"] for node in prompt.values() if node.get("class_type") not in info})
    missing_inputs = []
    for node_id, node in prompt.items():
        required = (info.get(node.get("class_type"), {}).get("input", {}).get("required") or {})
        for name in required:
            if name not in (node.get("inputs") or {}):
                missing_inputs.append(f"{node_id}.{name}")
    return {"valid": not missing_nodes and not missing_inputs, "missing_nodes": missing_nodes, "missing_inputs": missing_inputs}


def inspect_workflow(path: str | Path) -> dict:
    path = Path(path)

    report = {
        "path": str(path),
        "valid": False,
        "node_types": [],
        "missing_nodes": [],
        "error": None,
    }

    try:
        workflow = json.loads(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
    except Exception as exc:
        report["error"] = str(exc)
        return report

    if not isinstance(workflow, dict):
        report["error"] = "Workflow JSON root is not an object."
        return report

    report["valid"] = True
    report["node_types"] = workflow_node_types(workflow)

    if comfy_alive():
        try:
            installed = set(object_info().keys())

            report["missing_nodes"] = [
                node
                for node in report["node_types"]
                if node not in installed
            ]
        except Exception as exc:
            report["error"] = str(exc)

    return report


def built_in_workflows() -> list[Path]:
    if not POSE_WORKFLOW_DIR.is_dir():
        return []

    return sorted(
        POSE_WORKFLOW_DIR.glob("*.json"),
        key=lambda p: p.name.lower(),
    )


if __name__ == "__main__":
    print(health_report_text())
    print()
    print(
        "Pose library:",
        len(pose_library_index()),
        "indexed entries",
    )

    print("Built-in workflows:")

    for workflow in built_in_workflows():
        result = inspect_workflow(workflow)

        print(
            f"  {workflow.name}: "
            f"{len(result['node_types'])} node types, "
            f"{len(result['missing_nodes'])} missing"
        )
