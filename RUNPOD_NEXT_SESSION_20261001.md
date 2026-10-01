# GENESIS RunPod next-session state — 1 October 2026

## DO NOT START OVER
- Preserve the dirty working tree at /home/rice2meetyou/Genesis-c0ckpit. Never reset/clean it and never git add .
- Baseline handover commit: 85d9b34 and RUNPOD_SHARED_STATE_20261001.md.
- Brother's shared/global RunPod volume: hushed_magenta_raccoon, shown in RunPod at 181.8 GB. Do not create a replacement volume.
- Old pod a53n3go0xeu1z0 is no longer reachable. Old SSH 69.30.85.51:22173 returns Connection refused.
- Old GENESIS tunnel was local http://127.0.0.1:18189 -> remote ComfyUI 8189.
- User has no usable RunPod balance now. DO NOT deploy/start paid GPU work until user has credit or brother supplies a running pod. Do not stop brother's pod.

## V23
- Qwen-Rapid-NSFW-v23_Q8_0.gguf download had been in /workspace/models/diffusion_models/ as a .gguf.part.
- Last confirmed download progress before pod became unavailable: 51.7%.
- Completion is UNKNOWN because the pod/tunnel died before verification.
- FIRST ACTION when the shared volume is mounted again: inspect the v23 file and .part status before downloading anything. Do not redownload blindly.

## GENESIS wiring found this session
- Existing RunPod integration is already present; do not rebuild it.
- qt_cockpit.py has REMOTE_PHR00T_MODEL v23 and REMOTE_PHR00T_V19_MODEL v19.
- V19 is Qwen-Rapid-AIO-NSFW-v19.safetensors under /workspace/models/checkpoints/ and needs its OWN proper workflow.
- Current code incorrectly routes V19 through STAGE_1_PHR00T_POSE.json; v23 uses PHR00T_QWEN_RAPID_V23.json.
- Existing code supports chaining up to 3 model-only LoRAs via insert_model_only_loras().
- Remote profile/UI gate still restricts Klein profiles and qwen-image compatibility rules block unverified LoRAs.
- At last live volume inventory, no actual LoRA weights and no ReActor/PuLID weights were found. Do not claim they work until present.
- Do not restart brother's ComfyUI just to refresh paths.
- Exclude Lustify, FluxedUp and Kontext from this RunPod task.
- Four main Klein checkpoints were complete/mapped; live render/pose/identity quality remains unverified.

## Next work
1. With no RunPod credit, continue local code-only work safely: make a dedicated V19 workflow/routing and clean preset/LoRA plumbing.
2. Preserve all unrelated dirty changes; inspect diffs before editing.
3. Run focused unit/workflow validation only; no paid GPU renders.
4. When RunPod is available again, attach the EXISTING hushed_magenta_raccoon volume, inspect V23 first, get the new SSH endpoint, restore 18189 -> 8189, then validate assets/presets without unnecessary renders.
