# GENESIS V3 — Current State

## Verified isolated Klein 4B baseline — 2026-09-20

- Both 12-argument and 16-argument Generate calls were exercised through
  QQmlExpression; both reached the bridge without QML dispatch errors.
- Initial render cdb61534-bf66-4461-930a-5eed1b0aa457 failed at CLIPLoader:
  the encoder symlink targeted the unmounted Ai partition.
- Mounted /dev/sdc3 (label Ai) read-only at /run/media/rice2meetyou/Ai using
  udisksctl. Existing encoder link became readable. No files moved/downloaded.
- Retried as 5f7110eb-3a52-499f-9646-9d7762da1d26: ComfyUI success, output
  GENESIS_VERIFY_KLEIN4B_BASELINE_00001_.png in
  /home/rice2meetyou/AI/ComfyUI/output.
- Visually inspected output: coherent blue ceramic teapot on wooden table,
  matching the neutral prompt. Log reports 59.76 seconds.
- Exact baseline: flux-2-klein-4b.safetensors, qwen_3_4b_fp4_flux2.safetensors,
  flux2-vae.safetensors, 512x512, batch 1, seed 290829, 4 steps, Euler,
  Flux2Scheduler, CFG 1, no LoRAs or reference image.
- This verifies ONLY that baseline. Source editing, pose conditioning and
  LoRA combinations are still experimental/unverified by this test.
- Saved workflow files and ComfyUI process/flags, including
  --disable-async-offload, were unchanged.
- Next: make readiness check exact accessible files instead of trusting cached
  object_info choices; preserve this baseline while testing other routes.


Updated: 2026-09-19

## Machine/runtime

- Linux host: Ubuntu 26.04.1 on `rice2meetyou-B550M-K`.
- GPU: AMD Radeon RX 9060 XT, 16 GB class (16304 MB reported by PyTorch), gfx1200.
- ComfyUI environment recorded by the current audit: `miniforge3/envs/comfyui-reactor-rocm`, torch 2.12.0+rocm7.14.0, HIP 7.14.60850.
- Known ComfyUI generation profile has used `--lowvram --force-fp16`; the verified Klein 9B-KV profile additionally records `--preview-method none --cache-none` and excludes async offload.

## Repository

- Root: `/home/rice2meetyou/Genesis-c0ckpit`
- Branch: `main`
- HEAD when this handover was created: `268e2e0`.
- Live dirty tree at handover creation:
  - modified `systemd/genesis-assistant.service`
  - modified `systemd/genesis-llama.service`
  - modified `systemd/genesis-sillytavern.service`
  - untracked `genesis/assets/lunacy_banner/pose-library-banner-reference.png`
- Do not reset/clean these blindly.

## Verified recent milestones

- `docs/GENESIS_RESUME.md` reports 89 pytest tests passed for its Media Tools milestone and offscreen premium QML startup returned 0.
- Media Tools bridge currently covers background removal, 2x upscale, MP3 extraction and silent-video extraction; not every helper in `media_functions.py` is wired.
- Premium UI is graphite/black + antique-gold direction; visual polish remains secondary to functional generation work.
- Existing generation benchmark artifacts live under `gpu_test_outputs/`.

## Image-generation audit snapshot

The 2026-09-19 audit found configured ComfyUI access unavailable and model storage/mount state inconsistent at that moment. It must be rechecked live rather than treated as permanent.
The user identifies `/run/media/rice2meetyou/Ai/AI-Models` as the main model library when that disk is mounted.
The audit found LoRA stacking is not yet end-to-end in the premium UI: backend layers support more than the UI currently exposes/consumes.
Preset application is also incomplete as a full model + workflow + LoRA + strengths + prompts + sampler bundle.

## Known verified generation history

- Klein 9B Base Q4_K_M: baseline and selected regular-9B LoRAs have controlled render evidence in `gpu_test_outputs/klein9b-lora-benchmark/`.
- Klein 9B-KV FP8: 512, 768 and 1024 generation passed in the documented RX 9060 XT profile.
- A two-LoRA regular-9B cockpit test technically rendered but produced severe structural streaking; old UI therefore blocked stacking. Future stacking support must preserve this evidence and expose combinations as experimental until validated.
- 9B-KV and Aisha LoRA attempts previously caused heavy memory pressure/stalls; no LoRA is approved for those profiles based on that evidence.

## UI/product direction

Image Generation is the primary workspace. Keep model, LoRA filtering/stacking, source image, prompt, presets/poses, seed, denoise, CFG, steps, sampler, resolution, speed profile, preview, identity lock and output actions accessible.
Pose data should feed Image Generation; a standalone Pose Library page is not the priority.
Keep the 3-stage concept where later stages can consume the previous stage output, but routing must reflect actual model/workflow capabilities rather than assumptions.
