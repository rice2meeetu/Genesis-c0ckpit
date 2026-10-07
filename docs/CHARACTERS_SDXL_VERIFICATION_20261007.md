# GENESIS Characters and local SDXL audit — 7 October 2026

Repository: `/home/rice2meetyou/Genesis-c0ckpit`. Existing dirty changes were retained; no reset, clean, stash or commits performed. Existing character data was not rewritten during validation.

## Implemented

- Dedicated Characters sidebar page (page 15), registered in both launchers.
- Existing `CharacterReferences.qml` and `genesis/character_library.py` reused; no Character B identity or second library.
- Master image selection and saved Character A profiles; master replacement/removal disabled in the gallery UI.
- Face/body/pose/ignore gallery filters, review filter, explicit approval, zoom preview, gallery replacement/removal. Source image files are not modified.
- Legacy references remain usable. New builder candidates are stored unapproved. Ignored/unapproved references are excluded from preferred selection and supplemental identity input; pose-category references are excluded from supplemental identity inputs.
- Create has a saved-character selector and Manage Characters link. Character selection is shared through the existing bridge.
- Reference Builder prepares master + angle/pose instructions in Create; saved generated images can be imported for review and approval.
- Both SDXL models added to the local filesystem readiness catalog, exposing the existing source-edit route and compatible LoRAs.

## Model files and wiring

| Model | Exact local file | Size in bytes |
|---|---|---:|
| DonutsDeliveryMix V4.1 | `/home/rice2meetyou/AI/ComfyUI/models/checkpoints/donutsdeliverymixV4_v41.safetensors` | 6,938,051,602 |
| BigLustyDonutMix NSFW v1.2 | `/home/rice2meetyou/AI/ComfyUI/models/checkpoints/biglustydonutmixNSFW_v12.safetensors` | 6,938,462,898 |

Each file contains 2,515 tensors; header offsets agree with file length. This does not verify provenance or GPU inference quality.

`genesis/model_registry.py` now includes both local profiles. `genesis/model_compatibility.py` classifies both as SDXL. `qt_cockpit.py` defines the filenames, supported source models, shared graph builder, sampler defaults, SDXL LoRA insertion, and generation branch. Base graph: `/home/rice2meetyou/Genesis-c0ckpit/genesis/reference/pose_workflows/GENESIS_SDXL_SHARED_T2I.json`.

With a loaded source: LoadImage → ImageScale → VAEEncode → KSampler source latent. Optional pose: OpenPoseXL2 → ControlNetApplyAdvanced controls positive/negative conditioning while retaining the source latent. Without a source the graph uses an empty latent for text-to-image. The file name containing T2I does not prevent the runtime source-image graph mutation.

User flow remains: load image → optionally choose pose → use the pose's prompt or type instructions → Generate. Typed text takes precedence; otherwise the selected pose prompt is passed. The existing source default denoise is 0.65, text-only default 1.0; user-selected denoise is honored. Existing finishing toggles remain user controlled.

## LoRA files and data

Directory: `/home/rice2meetyou/AI/ComfyUI/models/loras/`.

| Compatible local SDXL LoRA | Size in bytes | Current trigger extraction |
|---|---:|---|
| `add-detail-xl.safetensors` | 228,452,344 | `portrait`, `all`, `misc`, `anime` extracted from training-tag metadata |
| `face_xl_v0_1.safetensors` | 223,735,220 | No trigger terms extracted |
| `skin texture style v4.safetensors` | 912,552,748 | No trigger terms extracted |

The local scanner reads these files, the compatibility filter exposes them to both models, and the SDXL graph chains selected adapters through model and CLIP. Up to three adapters are supported with individual strengths. They are optional, not automatically applied. Training tags are not evidence of required activation phrases. No trigger phrases or download URLs were invented.

No supplied authoritative list identifies further intended SDXL LoRAs or their required activation terms; those cannot be declared complete. Other locally present Flux/Klein LoRAs are excluded by family compatibility.

Pose weight present: `/home/rice2meetyou/AI/ComfyUI/models/controlnet/OpenPoseXL2.safetensors`.

## Verification and remaining gaps

108 focused tests passed: character persistence and approvals, QML component loading, SDXL source latent/denoise/seed, optional pose conditioning, typed/pose prompt fallback, finishing contracts, model defaults, local routing, RunPod endpoint exclusions, compatibility and LoRA wiring. The full premium Characters page rendered successfully with an isolated offscreen runtime; reviewed its screenshot. No GPU generation or live RunPod mutation performed.

Earlier broader checks exposed existing stale tests: seven `test_runpod_runtime_contract.py` failures using excluded 8188 endpoints, and one `test_local_workflow_configuration.py` failure referencing removed `STAGE_2_WORKFLOW`. Those behaviors were not changed to make stale tests pass.

Remaining: visual GPU identity-quality verification; automatic best-angle matching; batch multi-angle character-sheet generation; automatic attachment of generation outputs to candidate galleries (currently explicit import). SDXL source encoding preserves source information but cannot guarantee an unchanged face. Existing face finishing requires its runtime nodes/assets to be available and enabled; this audit did not certify a live face-lock inference run.

RunPod routing, endpoints, exclusions, launch configuration and network state were not changed by this work.


## Final extended verification

The current automated suite finishes: **466 passed, 1 skipped, 4 subtests passed**. The skipped test explicitly requires the absent external legacy `/home/rice2meetyou/AI/GENESIS_POSE_MAKER/app.py`; it is not reported as passing. Its recovered ZIP lacks the handoff consumer and contains older workflow configurations, so it was not restored. The bundled skeleton editor's interaction, save and export test passes after mocking the actual GENESIS file picker. The stale remote fixture was changed to 8189 while preserving the 8188 exclusion tests. The obsolete refinement test now checks the current selected workflow. `pytest.ini` targets the maintained `tests/` suite; root `test_face_v03.py` is an older manual database smoke script whose OpenCV/face-recognition dependencies are not present in the GUI environment.

Live local ComfyUI reports the AMD RX 9060 XT and validates both SDXL source/pose graphs with all three adapters. Both models completed actual local source-image generation at **25 steps**, saving readable 512×512 PNGs. DonutsDelivery also completed a source + OpenPoseXL2 + all three SDXL LoRA generation at **25 steps**. These were neutral synthetic smoke inputs, not a test of likeness to a real character. No model default was changed to 40 steps.

ReSwapper `/home/rice2meetyou/AI/ComfyUI/models/reswapper/reswapper_256.onnx` (554,298,280 bytes) and HyperSwap `/home/rice2meetyou/AI/ComfyUI/models/hyperswap/hyperswap_1a_256.onnx` (402,742,682 bytes) were downloaded from the installed ReActor documentation's publisher sources and checked against Hugging Face LFS SHA-256 values. The running backend now lists both alongside Inswapper. All three engines pass finishing asset/node availability checks. A face-swap inference quality test has not been performed.

The independent finishing path validates refine, face lock and UltraSharp upscale against the live backend. The older Final upscale graph still lacks `Realistic_Vision_V6.0_NV_B1.safetensors` and `vae-ft-mse-840000-ema-pruned.safetensors`; local availability blocks that old path. The supported independent UltraSharp action is available. FaceFusion remains uninstalled and its UI explicitly shows this; no FaceFusion inference is claimed.

The normal launcher currently defaults to RUNPOD by existing configuration. LOCAL must be selected for local SDXL execution. This preference was preserved. No remote GPU jobs or RunPod configuration changes were made by these checks.
