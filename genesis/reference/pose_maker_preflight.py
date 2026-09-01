from __future__ import annotations

import sys
import requests

BASE = "http://127.0.0.1:8188"
STAGE1 = "Qwen-Rapid-AIO-NSFW-v19.safetensors"
STAGE2 = [
    "lustifySDXLNSFW_endgame.safetensors",
    "lustifySDXLNSFWSFW_v20LIGHTNING.safetensors",
]

REQUIRED_NODES = {
    "CheckpointLoaderSimple",
    "LoadImage",
    "TextEncodeQwenImageEditPlus",
    "DWPreprocessor",
    "ConditioningZeroOut",
    "EmptyLatentImage",
    "KSampler",
    "VAEDecode",
    "VAEEncode",
    "CLIPTextEncode",
    "ReActorFaceSwap",
    "SaveImage",
}

def get(path):
    r = requests.get(BASE + path, timeout=20)
    r.raise_for_status()
    return r.json()

def inputs(info, node):
    node_info = info[node]["input"]
    return {
        **node_info.get("required", {}),
        **node_info.get("optional", {}),
    }

def combo_values(spec):
    if isinstance(spec, (list, tuple)) and spec and isinstance(spec[0], list):
        return list(spec[0])
    return []

def main():
    print("================================================")
    print("GENESIS / COMFYUI PREFLIGHT")
    print("================================================")

    try:
        stats = get("/system_stats")
        info = get("/object_info")
    except Exception as e:
        print("FAIL: ComfyUI is not reachable at", BASE)
        print("     ", repr(e))
        return 2

    print("PASS: ComfyUI API reachable")

    devices = stats.get("devices") or stats.get("system", {}).get("devices") or []
    if devices:
        for i, dev in enumerate(devices):
            if isinstance(dev, dict):
                print(f"GPU {i}: {dev.get('name', dev)}")
            else:
                print(f"GPU {i}: {dev}")
    else:
        print("WARN: system_stats returned no device list")

    missing = sorted(REQUIRED_NODES - set(info))
    if missing:
        print("FAIL: Missing required nodes:")
        for n in missing:
            print("  -", n)
        return 3
    print("PASS: All required nodes are installed")

    # Checkpoint choices
    ckpt_spec = info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"]
    ckpts = combo_values(ckpt_spec)
    print(f"INFO: ComfyUI sees {len(ckpts)} checkpoints")

    if STAGE1 in ckpts:
        print("PASS: Stage 1 checkpoint:", STAGE1)
    else:
        candidates = [x for x in ckpts if "qwen" in str(x).lower() and "rapid" in str(x).lower()]
        if candidates:
            print("PASS: Stage 1 compatible checkpoint:", candidates[0])
        else:
            print("FAIL: Stage 1 Phr00t/Qwen Rapid checkpoint not found")
            return 4

    found2 = next((x for x in STAGE2 if x in ckpts), None)
    if not found2:
        found2 = next((x for x in ckpts if "lustify" in str(x).lower()), None)
    if found2:
        print("PASS: Stage 2 checkpoint:", found2)
    else:
        print("FAIL: No Lustify checkpoint found")
        return 5

    # Stage 1 sampler/scheduler choices
    ks = inputs(info, "KSampler")
    sampler_choices = combo_values(ks.get("sampler_name"))
    scheduler_choices = combo_values(ks.get("scheduler"))
    for wanted, choices, label in [
        ("er_sde", sampler_choices, "Stage 1 sampler"),
        ("beta", scheduler_choices, "Stage 1 scheduler"),
        ("euler", sampler_choices, "Stage 2 Lightning sampler"),
        ("normal", scheduler_choices, "Stage 2 Lightning scheduler"),
    ]:
        if wanted in choices:
            print(f"PASS: {label}: {wanted}")
        else:
            print(f"FAIL: {label} '{wanted}' is unavailable")
            print("      Available:", choices)
            return 6

    # Qwen node input contract
    qwen = inputs(info, "TextEncodeQwenImageEditPlus")
    qwen_required = {"clip", "vae", "image1", "prompt"}
    missing_qwen = sorted(qwen_required - set(qwen))
    if missing_qwen:
        print("FAIL: TextEncodeQwenImageEditPlus input mismatch:", missing_qwen)
        return 7
    print("PASS: Native Qwen edit node input contract")

    # ReActor current node contract
    reactor = inputs(info, "ReActorFaceSwap")
    required_reactor = {
        "input_image",
        "source_image",
        "swap_model",
        "facedetection",
    }
    missing_reactor = sorted(required_reactor - set(reactor))
    if missing_reactor:
        print("FAIL: ReActor input mismatch:", missing_reactor)
        print("INFO: Current ReActor inputs:", sorted(reactor))
        return 8

    swap_choices = combo_values(reactor.get("swap_model"))
    detector_choices = combo_values(reactor.get("facedetection"))
    if swap_choices and "inswapper_128.onnx" not in swap_choices:
        print("FAIL: inswapper_128.onnx is not offered by ReActor")
        print("      Swap models:", swap_choices)
        return 9
    if detector_choices and "retinaface_resnet50" not in detector_choices:
        print("FAIL: retinaface_resnet50 is not offered by ReActor")
        print("      Detectors:", detector_choices)
        return 10

    print("PASS: ReActor node contract")
    print("PASS: inswapper_128 / RetinaFace configuration accepted")
    print()
    print("================================================")
    print("PREFLIGHT PASSED")
    print("The UI can now be launched with: ./run.sh")
    print("================================================")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
