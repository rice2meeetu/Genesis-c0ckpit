# GENESIS V3 — Next Tasks

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


Updated: 2026-09-20

## Readiness correction — 2026-09-20

### Accessible LoRA rescan — 2026-09-20

- Live inventory: 17 base models, 31 LoRAs, 6 VAEs, 5 encoders, and 35 workflows.
- Regular Klein 9B approved compatibility: `Flux Klein - NSFW v2`, `Klein_Anatomy_Revamped`, `flux2klein_body_version_a`, `FK_sloppydeepthroat_epoch_10`, and `FK_teeththroat`.
- Klein 4B approved experimental compatibility: `F2K4BBabe_Engel_v1.0`, `f2k_4B_consist_20260314`, `hina_flux2klein4b_asianMix_v4.0-lora`, and `klein4b-deepthroat-22epoc-k3nk`.
- Klein 9B-KV has no approved LoRAs. Similar filenames such as `FLUX2_KLEIN_UNLOCKED_V1`, `Flux-NSFW-uncensored`, `flux2klein_bj`, `flux2klein_cowgirl`, and `FutaCockCloseUp-v2` remain blocked/unverified.
- No files were downloaded, moved, deleted, or modified. Next action remains one controlled neutral render per experimental adapter before promotion.

### Attached source-image validation — 2026-09-20

- Transferred the attached `jenny.jpeg` to ComfyUI input as `GENESIS_SOURCE_JENNY.jpeg`; local and remote SHA-256 both equal `cb401844d261259ae7b46b6103a66b7f3f942ebe8ed1746dcc2d9b987642c2ec`.
- Ran prompt `f475c076-8247-4273-aead-3908a9bf3a5a` through the Klein 4B native ReActor source-image route with a neutral shoulder-up portrait prompt and no adapter.
- Render completed in approximately 77.7 seconds. Output: `GENESIS_VERIFY_SOURCE_JENNY_NEUTRAL_00001_.png`, 512x512 PNG, SHA-256 `77c4b12ca34c922c99d4cdef472b8734fe558c17e24717117993a858ed85fba4`.
- This validates source-image routing only. The source image is retained in ComfyUI input storage and excluded from the repository.
- No protected pose routes, workflows, or launch flags changed.

- Corrected `genesis/model_registry.py` so Klein 4B readiness does not require a LoRA. The previously matched `FLUX2_KLEIN_UNLOCKED_V1.safetensors` is blocked/unverified and must not make the profile appear ready.
- Added a regression check in `tests/test_model_compatibility.py`.
- Verification: 79 tests passed; live readiness reports Klein 4B ready with no LoRA evidence; branch pushed as `a5d0c95`.
- No model files, workflows, or ComfyUI launch flags changed.
- Single best next action: rescan exact accessible model assets and run one controlled neutral render per newly exposed experimental LoRA before promoting combinations.

## Completed 2026-09-20 — capability-aware LoRA stack controls

- Image Generation now exposes up to three ordered LoRA slots for regular Klein 9B Base, each with an independent 0.00–1.00 strength.
- Klein 4B remains isolated to one experimental LoRA; Klein 9B-KV and Phr00t/Qwen expose no LoRA slots because those routes are not validated.
- Duplicate selections and invalid strengths fail closed. Existing Phr00t/Qwen, SDXL/OpenPoseXL2, and staged workflow routes were not changed.
- Verification: 95 pytest tests passed; Python compile passed; premium QML offscreen startup remained alive for five seconds with no QML error output.
- Files changed: `genesis/qt_ui/MainPremiumLinux.qml`, `qt_cockpit.py`, `genesis/generation_pipeline.py`, and `tests/test_qt_generation_profiles.py`.
- Best next action: run isolated controlled renders for each newly exposed experimental LoRA and each proposed stack before promoting any combination to render-tested.

## Follow-up — legacy Generate compatibility

- Restored the original 12-argument QML Generate overload alongside the new
  16-argument overload. The existing Main.qml pose buttons retain their source,
  pose, stage switches, and original model-specific strength defaults.
- Added regression tests for forwarding and both exported Qt signatures.
- Verification: 97 tests passed. No GPU render was submitted for this fix.
- Changed: qt_cockpit.py and tests/test_qt_generation_profiles.py.
- Next: exercise both QML calls with a mocked submitter, then run an isolated
  non-explicit baseline render. Preserve current ComfyUI flags and saved graphs.

## Protected route live validation — 2026-09-20

- Live ComfyUI object inventory validated the saved STAGE 1 Phr00t/Qwen,
  STAGE 2 Lustify SDXL, and STAGE 3 ReActor ROCm workflows.
- All three workflow graphs reported valid with no missing nodes or inputs.
- GPU acceleration reported available and the ComfyUI queue was empty.
- No route files, model files, or launch settings were changed.

## Immediate takeover sequence

1. Recheck live mounts, especially `/run/media/rice2meetyou/Ai/AI-Models`, and reconcile the 2026-09-19 audit with current storage state.
2. Recheck ComfyUI service/API and live node inventory without changing the working ROCm stack.
3. Produce a rescanable canonical model/LoRA/workflow inventory. Use stable relative IDs plus file existence, family, metadata/hash/source where available, and separate installed/compatible/render-tested states.
4. Finish model -> compatible LoRA selector behavior. Support ordered LoRA slots and individual strengths in the UI/backend, while keeping unsafe/unverified combinations clearly experimental or blocked.
5. Make preset/pose application a complete generation bundle where data exists: compatible family/model, workflow ID, prompt/negative prompt, optional reference, LoRA IDs/weights, sampler/scheduler/steps/CFG/resolution. Preserve user overrides intentionally.
6. Verify source/reference routing per family. Do not pretend text-to-image and image-edit graphs are interchangeable.
7. Run controlled neutral benchmarks after inventory/routing is correct: fixed prompt/source/seed, batch 1, 512 then 768, cold/warm timing, VRAM/RAM/errors and output inspection. Preserve benchmark reports.
8. Only after functional verification, continue premium UI polish.

## Media/Canvas backlog

Media hardening still needs atomic output writes, extension validation, cancellation, codec/container fallback and explicit AI-vs-standard resize behavior.
Canvas still needs real cutout/layer manipulation, transforms, undo/redo and export.

## Handoff requirement

Before stopping work, update this file with:
- completed items;
- exact files changed;
- tests/renders actually run and results;
- new blockers;
- the single best next command/action.

Also update `docs/CURRENT_STATE.md` if machine, model inventory, architecture, tests, or verified behavior changed.
