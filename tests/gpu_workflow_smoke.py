"""Bounded live ComfyUI GPU smoke renders for GENESIS workflows."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from genesis import workflow_lab


ROOT = Path("/home/rice2meetyou/AI/ComfyUI/user/default/workflows")
OUTPUT = Path(__file__).resolve().parents[1] / "gpu_test_outputs"
SOURCE = "example.png"


def prepare(path: Path, info: dict, *, lora_strength: float | None = None) -> dict:
    prompt = workflow_lab.workflow_to_prompt(path, info)
    if "9B_KV" in path.stem:
        # Smoke-test the base 9B pipeline without loading incompatible 4B LoRAs
        # or invoking the optional face-swap stage.
        for node_id, node in list(prompt.items()):
            node_type = node.get("class_type")
            if node_type not in {"LoraLoaderBypass", "ReActorFaceSwap"}:
                continue
            inputs = node.get("inputs") or {}
            replacements = {}
            if node_type == "LoraLoaderBypass":
                replacements = {0: inputs.get("model"), 1: inputs.get("clip")}
            else:
                replacements = {0: inputs.get("input_image") or inputs.get("image")}
            for consumer in prompt.values():
                for key, value in list((consumer.get("inputs") or {}).items()):
                    if isinstance(value, list) and len(value) == 2 and str(value[0]) == str(node_id):
                        replacement = replacements.get(int(value[1]))
                        if replacement is not None:
                            consumer["inputs"][key] = replacement
            prompt.pop(node_id)
    controls = workflow_lab.discover_workflow_controls(prompt)
    overrides: dict[str, dict] = {}

    for name, value in (("steps", 4), ("cfg", 1.0), ("width", 512),
                        ("height", 512), ("denoise", 0.75), ("seed", 290829)):
        if name in controls:
            node_id, input_name = controls[name]
            overrides.setdefault(str(node_id), {})[input_name] = value

    for node_id, node in prompt.items():
        node_type = node.get("class_type")
        inputs = node.get("inputs") or {}
        title = str((node.get("_meta") or {}).get("title", "")).lower()
        if node_type == "LoadImage" and "image" in inputs:
            overrides.setdefault(str(node_id), {})["image"] = SOURCE
        if node_type == "LoraLoader" and lora_strength is not None:
            overrides.setdefault(str(node_id), {}).update({
                "lora_name": "FLUX2_KLEIN_UNLOCKED_V1.safetensors",
                "strength_model": lora_strength,
                "strength_clip": 0.0,
            })
        if node_type == "SaveImage":
            overrides.setdefault(str(node_id), {})["filename_prefix"] = (
                f"GENESIS_SMOKE_{path.stem}_{lora_strength if lora_strength is not None else 'base'}"
            )
        if "text" in inputs and isinstance(inputs["text"], str) and "negative" not in title:
            overrides.setdefault(str(node_id), {})["text"] = (
                "studio portrait photograph, neutral background, detailed skin, soft cinematic light"
            )

    return workflow_lab.workflow_to_prompt(path, info, overrides)


def render(client: workflow_lab.ComfyClient, name: str, prompt: dict) -> list[Path]:
    validation = workflow_lab.validate_prompt(prompt, client.object_info())
    if not validation["valid"]:
        raise workflow_lab.ComfyError(json.dumps(validation))
    started = time.monotonic()
    result = client.wait(client.submit(prompt), timeout=1800)
    if result.status != "completed":
        raise workflow_lab.ComfyError(result.error or result.status)
    OUTPUT.mkdir(exist_ok=True)
    saved = []
    for index, item in enumerate(result.outputs, 1):
        if item.get("kind") != "images":
            continue
        suffix = Path(item.get("filename", "output.png")).suffix or ".png"
        target = OUTPUT / f"{name}-{index}{suffix}"
        target.write_bytes(client.view(item))
        saved.append(target)
    print(f"PASS {name}: {time.monotonic() - started:.1f}s, {len(saved)} image(s)")
    return saved


def main() -> int:
    client = workflow_lab.ComfyClient()
    stats = client.system_stats()
    if not workflow_lab.gpu_acceleration_available(stats):
        print("FAIL: ComfyUI is not GPU accelerated", file=sys.stderr)
        return 2
    info = client.object_info()
    jobs = (
        ("phroot", ROOT / "GENESIS_PHROOT_MEMORY_SAFE.json", None),
        ("fluxup", ROOT / "GENESIS_FLUXUP_T2I_RX9060.json", None),
        ("klein9b-base", ROOT / "GENESIS_FLUX2_KLEIN_9B_KV_LORA_REACTOR.json", None),
        ("klein4b-base", ROOT / "FLUX2_Klein_Deepthroat_FaceSwap.json", 0.0),
        ("klein4b-lora", ROOT / "FLUX2_Klein_Deepthroat_FaceSwap.json", 0.45),
    )
    failures = 0
    selected = set(sys.argv[1:])
    for name, path, strength in jobs:
        if selected and name not in selected:
            continue
        try:
            render(client, name, prepare(path, info, lora_strength=strength))
        except Exception as exc:
            failures += 1
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
