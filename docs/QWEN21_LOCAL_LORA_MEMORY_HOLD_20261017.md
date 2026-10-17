# Qwen Image 2.1 — local LoRA safety hold (17 October 2026)

- Installed file: `NSFW Qwen by TheseAlpacas V2.safetensors` (76 MiB), exact SHA-256
  `83aba822ad8ee10a1e836828f5088259d93bce7b5f3419b46dbc0258c2be46a9`,
  matching the published upstream Qwen Image 2.1 LoRA. This verifies file identity,
  **not** that local inference will fit in system memory or finish.
- Attempt: ComfyUI local `qwen_image_2.1_bf16.safetensors` with its GENESIS
  text-to-image graph; 512×512, four steps, LoRA strength 0.6, neutral still-life.
  Queue accepted job; no completed output was recorded.
- At 18:01:26 Australia/Perth, Linux kernel `global_oom` killed
  `genesis-comfyui.service` Python process PID 434665 with anonymous RSS
  ~13.6 GB. System 32 GB RAM, 8 GB swap, RX 9060 XT 16 GB VRAM.
  Desktop Commander became temporarily unavailable, then reconnected;
  kernel had not rebooted. ComfyUI service recovered with an empty queue.
- **Action:** Do not enable this adapter on the current local Qwen 2.1
  route. Keep family/filename gating conservative. No evidence that the
  2.1 LoRA was the intrinsic bug, only that this full inference route
  exceeded local memory under tested conditions.
- Klein 4B LoRAs remain held following an earlier KFD/SVM warning; Phr00t
  has no confirmed matching local 20B/Qwen Image LoRA. Do not silently
  substitute this Qwen Image 2.1 adapter for Phr00t.
- Future re-validation: check RAM/swap and free VRAM; review the Qwen 2.1
  text/vision encoders' memory load, offload/cache strategy, and lower-memory
  precision with rollback protection. Prefer adequate-memory RunPod 8189 if
  available, without touching the sibling ComfyUI on 8188.
- The feature-help commit `01d44d5` is separately verified (819 passing
  local tests before the adapter identification). This note and the
  safety-hold regression are included in its PR #17 follow-up.

No model weights, device drivers, private credentials, or GPU configs were
changed in this incident review.
