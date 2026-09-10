"""Run one controlled regular Klein 9B LoRA compatibility probe."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from genesis import workflow_lab  # noqa: E402
from tests.gpu_klein9b_benchmark import make_prompt  # noqa: E402


APPROVED_LORAS = {
    "body": "flux2klein_body_version_a.safetensors",
    "nsfw-v2": "Flux Klein - NSFW v2.safetensors",
    "anatomy": "Klein_Anatomy_Revamped.safetensors",
}
OUT = REPO / "gpu_test_outputs" / "klein9b-lora-benchmark"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", choices=APPROVED_LORAS)
    parser.add_argument("--strength", type=float, default=0.65)
    args = parser.parse_args()

    client = workflow_lab.ComfyClient(timeout=60)
    info = client.object_info()
    lora = APPROVED_LORAS[args.profile]
    seed = 390829
    prompt = make_prompt(info, 512, 512, seed, f"lora-{args.profile}")
    prompt["genesis_lora_probe"] = {
        "class_type": "LoraLoaderModelOnly",
        "inputs": {
            "model": ["126", 0],
            "lora_name": lora,
            "strength_model": args.strength,
        },
        "_meta": {"title": f"GENESIS regular 9B probe: {lora}"},
    }
    prompt["134"]["inputs"]["model"] = ["genesis_lora_probe", 0]
    prompt["107"]["inputs"]["text"] = (
        "A man sitting alone on a train, showing quiet disappointment through "
        "subtle facial expression and posture. Natural lighting, candid photography style."
    )
    prompt["9"]["inputs"]["filename_prefix"] = f"GENESIS-Klein9B-LoRA-{args.profile}"

    validation = workflow_lab.validate_prompt(prompt, info)
    if not validation["valid"]:
        raise workflow_lab.ComfyError(json.dumps(validation))

    OUT.mkdir(parents=True, exist_ok=True)
    report_path = OUT / f"{args.profile}.json"
    report = {
        "profile": args.profile,
        "model": "flux-2-klein-base-9b-Q4_K_M.gguf",
        "encoder": "qwen_3_8b_fp8mixed.safetensors",
        "lora": lora,
        "strength": args.strength,
        "seed": seed,
        "size": [512, 512],
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    started = time.monotonic()
    try:
        result = client.wait(client.submit(prompt), timeout=1800)
        report["status"] = result.status
        report["elapsed"] = round(time.monotonic() - started, 3)
        report["error"] = result.error
        outputs = []
        if result.status == "completed":
            for index, item in enumerate(result.outputs, 1):
                if item.get("kind") != "images":
                    continue
                target = OUT / f"{args.profile}-{index}.png"
                target.write_bytes(client.view(item))
                outputs.append(str(target))
        report["outputs"] = outputs
    except Exception as exc:
        report.update(
            status="failed",
            elapsed=round(time.monotonic() - started, 3),
            error=f"{type(exc).__name__}: {exc}",
            outputs=[],
        )
    report["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "completed" and report["outputs"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
