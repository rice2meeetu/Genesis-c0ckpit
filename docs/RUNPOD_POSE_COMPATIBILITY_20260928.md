# GENESIS RunPod pose compatibility research — 2026-09-28

## Rule
Pose support is family-specific and evidence-gated. GENESIS must not route every model through one generic ControlNet graph.

## Verified/documented upstream routes

| Family / variant | Preferred pose route | Evidence status | GENESIS action |
|---|---|---|---|
| Phr00t / Qwen Rapid AIO v19/v23 | Native Qwen image edit: source/identity + pose/reference image | Upstream base is Qwen-Image-Edit-2511; Rapid supports multi-image edit. Existing GENESIS two-image pose graph preserved. | Keep current Phr00t route. Test v19 and v23 separately; v19 is favored for edit consistency, v23 for prompt adherence. |
| FLUX.2 Klein 9B Base | RefControl v2 Pose LoRA + DWPose/OpenPose skeleton as image 1 + identity/reference as image 2 | RefControl author explicitly trains/recommends Base 9B. | Primary 9B pose route. |
| FLUX.2 Klein 9B distilled | Same RefControl v2 Pose LoRA | RefControl author states it also works on distilled 9B, with potentially lower pose/identity fidelity. | Enable only after controlled render. |
| FLUX.2 Klein 9B-KV | Native multi-reference edit first | BFL officially supports multi-reference editing and KV caching. No authoritative proof found that RefControl pose LoRA is compatible while KV-cache patching is active. | Use native multi-ref pose/reference route first; test RefControl both with KV cache disabled and enabled before promotion. |
| FLUX.2 Klein 4B / 4B Base | Dedicated 4B RefControl Pose LoRA (refcontrol-pose-klein-4b.safetensors) | Dedicated adapter exists for Base 4B; uses OpenPose-style COCO-18 skeleton + reference image. | Add a separate 4B pose route; do not use 9B pose LoRA. |
| FLUX.1-dev family / FluxedUp | FLUX.1-dev ControlNet Union Pro, pose mode 4 | Shakker/InstantX model card documents pose=4, strength 0.3-0.8. | Keep GENESIS custom Union-Pro mode-4 selector. Render-test FluxedUp specifically. |
| SDXL / Lustify fallback | OpenPoseXL2 / existing Stage-1 route | Two local renders already verified. | Preserve as fallback; do not replace. |

## Klein fine-tunes present in GENESIS

### 9B architecture candidates
- MiracleIn NSFW v3 FP8
- PornMaster Flux2 Klein v3 FP8
- DarkBeast Klein9B V2 BFS FP8
- Aisha 9B variants
Local checkpoint metadata/tensor layout confirms these use the Klein 9B transformer family. PornMaster metadata explicitly starts from flux-2-klein-base-9b-fp8.safetensors. MiracleIn metadata includes multi-reference ReferenceLatent editing and a 9B merge source.

**Policy:** use the 9B RefControl pose workflow as a candidate route, but mark each fine-tune TEST_PENDING until a fixed-seed pose/identity render passes. Same architecture is not sufficient evidence of quality.

### 4B architecture candidates
- Aisha 4B distilled
- official Klein 4B / Base 4B

Use the dedicated 4B pose adapter, not the 9B adapter.

## Required RunPod validation matrix

For every model variant available on the new RunPod account:
1. inventory exact filename, checksum/size, model family, quantization and encoder;
2. verify required ComfyUI nodes through /object_info;
3. use one fixed adult-safe neutral source portrait and one fixed DWPose skeleton;
4. fixed resolution, seed and prompt per family;
5. run baseline native multi-reference edit first;
6. run family-specific pose adapter route;
7. record graph validity, successful render, pose adherence, identity retention, anatomy failure, runtime and VRAM;
8. promote to selectable only after a successful reviewed output.

## Upstream research sources
- BFL official FLUX.2 repo: https://github.com/black-forest-labs/flux2
- BFL 9B-KV cache docs: https://github.com/black-forest-labs/flux2/blob/main/docs/flux2_klein_kv_cache.md
- 9B RefControl Pose: https://huggingface.co/thedeoxen/refcontrol-FLUX.2-klein-9B-reference-pose-lora
- 4B RefControl Pose: https://huggingface.co/xocialize/refcontrol-FLUX.2-klein-4B-pose-lora
- FLUX.1 Union Pro: https://huggingface.co/Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro
- Qwen Image Edit 2511: https://qwen.ai/blog?id=qwen-image-edit-2511
- Qwen Rapid GGUF: https://huggingface.co/Novice25/Qwen-Image-Edit-Rapid-AIO-GGUF
