"""Repeatable live benchmark for the official GENESIS Klein 9B-KV workflow."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from genesis import workflow_lab


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "genesis/reference/pose_workflows/GENESIS_FLUX2_KLEIN_9B_KV_OFFICIAL_T2I.json"
OUTPUT = ROOT / "gpu_test_outputs/klein9b-benchmark"
REPORT = OUTPUT / "report.json"
PROFILES = ((512, 512, 2), (768, 768, 1), (1024, 1024, 1))


def free_metrics(stats: dict) -> dict:
    system = stats.get("system") or {}
    device = (stats.get("devices") or [{}])[0]
    return {
        "ram_free": int(system.get("ram_free") or 0),
        "vram_free": int(device.get("vram_free") or 0),
    }


def make_prompt(info: dict, width: int, height: int, seed: int, label: str) -> dict:
    prompt = workflow_lab.workflow_to_prompt(WORKFLOW, info)
    prompt["7"]["inputs"]["noise_seed"] = seed
    prompt["9"]["inputs"].update({"steps": 4, "width": width, "height": height})
    prompt["10"]["inputs"].update({"width": width, "height": height, "batch_size": 1})
    prompt["14"]["inputs"]["filename_prefix"] = f"GENESIS-Klein9B-KV-Benchmark-{label}"
    validation = workflow_lab.validate_prompt(prompt, info)
    if not validation["valid"]:
        raise workflow_lab.ComfyError(json.dumps(validation))
    return prompt


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    client = workflow_lab.ComfyClient(timeout=60)
    stats = client.system_stats()
    if not workflow_lab.gpu_acceleration_available(stats):
        print("FAIL: ComfyUI is not GPU accelerated", file=sys.stderr)
        return 2
    info = client.object_info()
    report = {
        "workflow": str(WORKFLOW),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "server_argv": (stats.get("system") or {}).get("argv") or [],
        "device": ((stats.get("devices") or [{}])[0]).get("name"),
        "runs": [],
    }
    failures = 0
    run_number = 0
    for width, height, repeats in PROFILES:
        for repeat in range(1, repeats + 1):
            run_number += 1
            label = f"{width}x{height}-r{repeat}"
            seed = 290829 + run_number
            before = free_metrics(client.system_stats())
            started = time.monotonic()
            entry = {"profile": label, "width": width, "height": height, "seed": seed, "before": before}
            try:
                result = client.wait(client.submit(make_prompt(info, width, height, seed, label)), timeout=1800)
                entry.update({"status": result.status, "elapsed": round(time.monotonic() - started, 3)})
                if result.status != "completed":
                    raise workflow_lab.ComfyError(result.error or result.status)
                saved = []
                for index, item in enumerate(result.outputs, 1):
                    if item.get("kind") != "images":
                        continue
                    target = OUTPUT / f"{label}-{index}.png"
                    target.write_bytes(client.view(item))
                    saved.append(str(target))
                if not saved:
                    raise workflow_lab.ComfyError("No image output")
                entry["outputs"] = saved
                entry["after"] = free_metrics(client.system_stats())
                print(f"PASS {label}: {entry['elapsed']:.1f}s")
            except Exception as exc:
                failures += 1
                entry.update({"status": "failed", "elapsed": round(time.monotonic() - started, 3), "error": str(exc)})
                print(f"FAIL {label}: {type(exc).__name__}: {exc}")
            report["runs"].append(entry)
            REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
            if failures:
                break
        if failures:
            break
    report["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
