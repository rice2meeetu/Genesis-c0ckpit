# GENESIS Phr00t reference-framing node

This is an isolated ComfyUI v3 custom node for Phr00t / Qwen Image Edit. It is adapted from Phr00t's Apache-2.0 `fixed-textencode-node/nodes_qwen.v2.py` but uses a distinct node ID: `GenesisQwenImageEditFraming`. It does **not** overwrite `ComfyUI/comfy_extras/nodes_qwen.py`, the native `TextEncodeQwenImageEditPlus`, or the newer Qwen Image 2.1 nodes.

## Local installation

The tested installation is at `~/AI/ComfyUI/custom_nodes/genesis_qwen_framing/__init__.py`. To reinstall it on this machine, copy this directory's `__init__.py` there and restart only the **local** `genesis-comfyui.service` while its queue is empty. The systemd service preserves the current ROCm flags. Check `/object_info` on local port 8188 for `GenesisQwenImageEditFraming` and the original Qwen nodes afterward.

GENESIS automatically selects the framing node only for Phr00t image-reference workflows when that node is present and the requested empty-latent dimensions are no more than 1,500,000 pixels. T2I and larger Quality-sized requests use the native encoder. This avoids expanding multiple reference latents to very large dimensions on a 16 GB card. RunPod can retain the native fallback without installing this custom node.

## Safety, rollback and verified behavior

No ROCm or kernel modifications are required. To roll back, change nothing in `comfy_extras`; remove the `genesis_qwen_framing` custom-node folder and restart local ComfyUI. GENESIS then uses the original encoder automatically. Do not restart RunPod ComfyUI 8188 (brother) or 8189 for this local change.

2026-10-14 checks: registered alongside native Qwen and Qwen 2.1 nodes, real text-to-image and real object-image edits completed. At 768 x 512, 4 steps, CFG 1.0, same source/prompt/seed on warmed Phr00t v23 Q2: native 27.14s; framing node 20.23s. The framing node kept the full teapot and handle in frame. Single tests are not universal throughput guarantees. Earlier GPU cold-load period logged AMD SVM workqueue latency warnings without a GPU reset; do not treat one successful benchmark as proof that all ROCm workloads are stable. Three-reference support has graph/CPU tests and a real local GPU render. Using the **same three synthetic images, prompt, seed 141029, Phr00t v23 Q2, 768x512, 4 steps, CFG 1.0**, the enhanced node completed in **38.64s** versus **71.63s** with the native `TextEncodeQwenImageEditPlus` (about 46% faster). Both images retained the requested blue teapot with its spout and handle. This one-run A/B does not prove human identity retention or exact human pose matching, and does not guarantee the same speed on other hardware/models. At 768x512, the optional node is used; 2264x1360 Quality falls back to the native node because the total latent pixels exceed 1.5 million.
