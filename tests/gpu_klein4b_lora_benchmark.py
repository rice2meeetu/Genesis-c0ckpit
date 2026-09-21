"""Controlled baseline/effect/stability benchmark for installed Klein 4B LoRAs."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageChops, ImageStat

from genesis import workflow_lab
from genesis.model_compatibility import is_compatible


ROOT = Path(__file__).resolve().parents[1]
BASE_WORKFLOW = (
    Path.home()
    / "AI/ComfyUI/user/default/workflows/GENESIS_FLUX2_KLEIN_9B_KV_OFFICIAL_T2I.json"
)
OUTPUT = ROOT / "gpu_test_outputs/klein4b-lora-benchmark"
REPORT = OUTPUT / "report.json"
MODEL = "flux-2-klein-4b.safetensors"
LORAS = (
    ("asianmix", "hina_flux2klein4b_asianMix_v4.0-lora.safetensors", 0.5),
    ("deepthroat", "klein4b-deepthroat-22epoc-k3nk.safetensors", 0.5),
)


def make_prompt(info: dict, lora: tuple[str, str, float] | None) -> dict:
    prompt = workflow_lab.workflow_to_prompt(BASE_WORKFLOW, info)
    prompt["1"]["inputs"]["unet_name"] = MODEL
    prompt["2"]["inputs"]["clip_name"] = "qwen_3_4b_fp4_flux2.safetensors"
    prompt.pop("5")
    prompt["6"]["inputs"]["model"] = ["1", 0]
    prompt["9"]["inputs"].update({"steps": 4, "width": 512, "height": 512})
    prompt["10"]["inputs"].update({"width": 512, "height": 512, "batch_size": 1})
    label = "baseline"
    if lora:
        label, filename, strength = lora
        if not is_compatible(MODEL, filename):
            raise workflow_lab.ComfyError(f"Blocked incompatible LoRA for {MODEL}: {filename}")
        prompt["15"] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {"model": ["1", 0], "lora_name": filename, "strength_model": strength},
            "_meta": {"title": f"Klein 4B LoRA: {label}"},
        }
        prompt["6"]["inputs"]["model"] = ["15", 0]
    prompt["14"]["inputs"]["filename_prefix"] = f"GENESIS-Klein4B-LoRA-{label}"
    validation = workflow_lab.validate_prompt(prompt, info)
    if not validation["valid"]:
        raise workflow_lab.ComfyError(json.dumps(validation))
    return prompt


def save_result(client, result, label: str) -> Path:
    for item in result.outputs:
        if item.get("kind") == "images":
            target = OUTPUT / f"{label}.png"
            target.write_bytes(client.view(item))
            return target
    raise workflow_lab.ComfyError("No image output")


def rms_difference(baseline: Path, candidate: Path) -> float:
    with Image.open(baseline).convert("RGB") as first, Image.open(candidate).convert("RGB") as second:
        stat = ImageStat.Stat(ImageChops.difference(first, second))
        return round(sum(value * value for value in stat.rms) ** 0.5, 4)


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    client = workflow_lab.ComfyClient(timeout=60)
    info = client.object_info()
    cases = [("baseline", None), *((item[0], item) for item in LORAS)]
    report = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "runs": []}
    baseline_path = None
    failures = 0
    for label, lora in cases:
        started = time.monotonic()
        entry = {"label": label, "lora": lora[1] if lora else None, "strength": lora[2] if lora else 0.0}
        try:
            result = client.wait(client.submit(make_prompt(info, lora)), timeout=1800)
            if result.status != "completed":
                raise workflow_lab.ComfyError(result.error or result.status)
            path = save_result(client, result, label)
            entry.update({"status": "completed", "elapsed": round(time.monotonic() - started, 3), "output": str(path)})
            if baseline_path is None:
                baseline_path = path
            else:
                entry["rms_difference_from_baseline"] = rms_difference(baseline_path, path)
            print(f"PASS {label}: {entry['elapsed']:.1f}s")
        except Exception as exc:
            failures += 1
            entry.update({"status": "failed", "elapsed": round(time.monotonic() - started, 3), "error": str(exc)})
            print(f"FAIL {label}: {type(exc).__name__}: {exc}")
        report["runs"].append(entry)
        REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
