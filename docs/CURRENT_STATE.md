# GENESIS V3 — Current State

## Verified regular Klein 9B single-LoRA render — 2026-09-20

- Prompt `a33263b4-4330-4dc1-8aeb-05f72ca745fe` completed successfully on the existing ComfyUI GPU stack.
- Workflow: regular Klein 9B GGUF (`flux-2-klein-base-9b-Q4_K_M.gguf`) with `qwen_3_8b_fp8mixed.safetensors`, `flux2-vae.safetensors`, and one approved LoRA: `Flux Klein - NSFW v2.safetensors` at model strength 0.35.
- Neutral test: blue ceramic teapot product photograph; 512x512, batch 1, seed 290832, 4 steps, Euler, simple scheduler, CFG 1.0.
- Output: `/home/rice2meetyou/AI/ComfyUI/output/GENESIS_VERIFY_KLEIN9B_LORA_NEUTRAL_00001_.png`, PNG RGB 512x512, 280072 bytes, SHA-256 `3754398b0a981845e54133151c58a2372745754d97ac7e217651a655258e2eac`.
- ComfyUI execution time was approximately 87.1 seconds. The image rendered successfully but showed noticeable teapot shape distortion, so this LoRA remains experimental and is not promoted as a quality preset.
- ComfyUI flags remained `--lowvram --force-fp16 --preview-method none --cache-none --disable-async-offload --listen 127.0.0.1 --port 8188`.
- Comparison render with `Klein_Anatomy_Revamped.safetensors` at the same strength, seed, prompt, and settings also completed successfully in approximately 46.4 seconds. Output: `/home/rice2meetyou/AI/ComfyUI/output/GENESIS_VERIFY_KLEIN9B_ANATOMY_NEUTRAL_00001_.png`, SHA-256 `993a50933fe02d8fad9e618636fa195ea799b13db084c5f33284e7fb6ead4c77`.
- No-LoRA control completed in approximately 42.3 seconds. Output: `/home/rice2meetyou/AI/ComfyUI/output/GENESIS_VERIFY_KLEIN9B_BASE_NEUTRAL_00001_.png`, SHA-256 `c644695c54c6cb68c0ac6a2193f320c7c39a565556ddf544c5393ffc5455ab9b`.
- All three regular 9B images share the same distorted teapot silhouette. This points to the current regular 9B workflow/profile rather than a single LoRA.
- An isolated no-LoRA 8-step control also completed in approximately 50.3 seconds. Output: `/home/rice2meetyou/AI/ComfyUI/output/GENESIS_VERIFY_KLEIN9B_BASE_STEPS8_NEUTRAL_00001_.png`, SHA-256 `5d49b2079ff803a62bb1194085a0d18592cd3e76241bb2b254dcf92f527b2d45`. The silhouette remained distorted, so increasing steps alone did not resolve it.
- No sampler, guidance, or saved workflow was changed. Regular 9B remains render-tested but not quality-promoted; the verified 4B baseline remains protected.

## Two-image neutral Face Swap function — 2026-09-20

- Premium Linux UI now exposes a dedicated Face Swap page at page 12, with separate target-image and source-identity pickers.
- `GenerationBridge.queueFaceSwap(target_url, source_url)` runs the preserved `STAGE_3_REACTOR_ROCM.json` route without changing Image Generation or the staged pose buttons.
- The route uses `ReActorFaceSwap`, `inswapper_128.onnx`, and `retinaface_resnet50`; restoration remains disabled by default so the result can be inspected before any enhancement.
- Neutral two-image validation passed with prompt `a1e824cb-09f7-4548-a539-a90830382422`. Output: `/home/rice2meetyou/AI/ComfyUI/output/GENESIS_VERIFY_FACESWAP_TWO_IMAGE_NEUTRAL_00001_.png`.
- The UI states that the isolated tool is for ordinary, non-explicit images and warns that extreme angles, occlusion, hands, hair, and lighting mismatch can distort faces.
- Normal cockpit outputs default to `/home/rice2meetyou/GENESIS-Exports`; direct ComfyUI validation outputs remain under `/home/rice2meetyou/AI/ComfyUI/output`.

## Verified isolated Klein 4B adapter render — 2026-09-20

- ComfyUI prompt `f17b0ed4-f341-4ec5-a1bb-5b2cdf5c083e` completed successfully on the existing GPU stack.
- Workflow was `FLUX2_Klein_Deepthroat_FaceSwap.json` with the face-swap stage bypassed for an adapter-only check.
- Adapter: `hina_flux2klein4b_asianMix_v4.0-lora.safetensors`, model strength 0.45, CLIP strength 0.45.
- Neutral prompt: blue ceramic teapot product photograph; 512x512, seed 290830, 4 steps, CFG 1.0, `res_multistep` / `simple`.
- Output: `/home/rice2meetyou/AI/ComfyUI/output/GENESIS_VERIFY_KLEIN4B_HINAFP_NEUTRAL_00001_.png`, PNG RGB 512x512, 325211 bytes, SHA-256 `f47e99920fc8f78531c9b3455db575d0ab870ccf04ee5265f71efaa142584d28`.
- ComfyUI execution time was approximately 49.6 seconds. This verifies one neutral 4B adapter render only; it does not promote other adapters or multi-LoRA combinations.
- No workflow files, model files, or launch flags changed.

## Verified source-image routing — 2026-09-20

- Attached source image was transferred to `/home/rice2meetyou/AI/ComfyUI/input/GENESIS_SOURCE_JENNY.jpeg` with matching SHA-256 `cb401844d261259ae7b46b6103a66b7f3f942ebe8ed1746dcc2d9b987642c2ec`.
- Prompt `f475c076-8247-4273-aead-3908a9bf3a5a` completed successfully using the Klein 4B workflow's native ReActor source-image path.
- Face-swap stage used the uploaded source image; generated target prompt was a neutral shoulder-up portrait. Adapter was removed for this routing check.
- Output: `/home/rice2meetyou/AI/ComfyUI/output/GENESIS_VERIFY_SOURCE_JENNY_NEUTRAL_00001_.png`, PNG RGB 512x512, 305758 bytes, SHA-256 `77c4b12ca34c922c99d4cdef472b8734fe558c17e24717117993a858ed85fba4`.
- ComfyUI execution time was approximately 77.7 seconds. This verifies source-image routing only; it does not promote explicit prompts, other face-swap inputs, or multi-LoRA combinations.
- The uploaded source remains in ComfyUI input storage and is not committed to GitHub.

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
