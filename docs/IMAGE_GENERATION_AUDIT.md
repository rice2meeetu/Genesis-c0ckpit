# Image Generation audit — 2026-09-19

Status: partial audit, not a render certification or exhaustive web survey. No models downloaded, disks mounted, services restarted or generation settings changed during this audit.

## Verified machine state

- GPU: AMD Radeon RX 9060 XT, gfx1200, 16304 MB reported by PyTorch.
- Environment: miniforge3/envs/comfyui-reactor-rocm; torch 2.12.0+rocm7.14.0; HIP 7.14.60850; GPU detection succeeds. No render or kernel benchmark run.
- OS: Ubuntu 26.04.1; kernel 7.0.0-31-generic.
- ComfyUI configured API refused connection. Live node/loader inventory cannot currently be validated.
- sdc3 is labelled Ai but unmounted. /run/media/rice2meetyou/Ai and /run/media/rice2meetyou/New Volume are absent.
- AI-Storage is mounted at /mnt/AI-Storage. Existing broken links were preserved, not repaired by guessing.

| Configured engine | Current filesystem evidence |
| --- | --- |
| Klein 4B | Model and Qwen3 4B encoder links broken |
| Klein 9B Base GGUF | Model present in models/unet; Qwen3 8B encoder unavailable |
| Klein 9B-KV | Model and encoder links broken |
| Phr00t/Qwen AIO | Checkpoint link broken; saved workflows remain |
| Aisha | Model unavailable |
| FluxedUp | Filesystem report says ready, but premium Create has no supported route; this is not render validation |

Registry scan reports 6 reachable LoRAs and 35 workflow files, not a complete semantic validation. Several additional LoRA links are broken. These counts are a timestamped snapshot only.

## Code findings

- Premium UI exposes one LoRA and passes None as the second selection.
- Backend text-to-image helper can chain up to three; Qt slot accepts two; 4B source path consumes only the first. Stacking is not end-to-end complete.
- Preset loader/application supplies prompt text, not a complete model/LoRA/strength/workflow bundle. Pose negative prompts are loaded but not applied by premium applyPose.
- Qwen source path receives the pose image; the 4B source path does not. 9B source-image requests are rejected by the current application, despite upstream editing support.
- Base 9B code forces 4 steps and CFG 1. Publisher example uses 50 steps/guidance 4; confirm exact quantized model provenance and graph semantics before changing settings.
- Inventory uses basename matching and can conflate duplicate names. Readiness uses token matches and should not be equated with runnable graphs.
- Unknown-family model plus unknown-family LoRA currently passes equality-based compatibility; this should fail closed.
- Cross-family community LoRAs are enabled without local validation. Separate experimental entries from verified compatibility.
- Trigger extraction includes training tag frequencies: these are not necessarily activation phrases.
- Inventory loads at launch, not continuously. No recurring web monitoring or automatic updates configured.

## Evidence and research

- [ComfyUI Klein guide](https://docs.comfy.org/tutorials/flux/flux-2-klein): separate 4B/9B encoders and Base/Distilled generation/edit graphs. A Qwen3 text encoder is not the Qwen Image editing model.
- [BFL Base 9B model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B): undistilled model, multi-reference editing, 50-step reference example. Local GGUF conversion still needs provenance verification.
- [Qwen Image Edit 2511](https://huggingface.co/Qwen/Qwen-Image-Edit-2511): multi-image editing and selected integrated LoRAs. This does not prove compatibility/settings for the user's separate AIO checkpoint.
- [ComfyUI-GGUF maintainer](https://github.com/city96/ComfyUI-GGUF): quantization can reduce memory; LoRA loading described as experimental. No speed guarantee for this Radeon.
- [Reddit compatibility discussion](https://www.reddit.com/r/StableDiffusion/comments/1qfs15y/curious_about_flux_2_klein_lora_compatibility/): conflicting community reports; useful leads, not a verified compatibility table.
- [AMD current compatibility matrix](https://rocm.docs.amd.com/en/latest/compatibility/compatibility-matrix.html): current page is ROCm 10.0. Do not upgrade the installed 7.14 environment solely because a newer version exists; exact Radeon/OS support still requires checking.
- Civitai retrieval failed; no Civitai metadata was verified in this pass. Searches also returned irrelevant hits, excluded from conclusions.

## SDXL Stage-1 pose verification — 2026-09-20

The Pose Library skeleton -> OpenPoseXL2 -> Lustify SDXL Lightning Stage-1 route completed two independent ComfyUI renders successfully. Outputs were `GENESIS_STAGE1_SDXL_POSE_00001_.png` and `GENESIS_STAGE1_SDXL_POSE_00002_.png`. The existing Phr00t/Qwen route was not changed. Status: render-verified on the local RX 9060 XT ROCm system.

## Proposed next milestone

1. Confirm whether Ai should be mounted or models intentionally relocated. Do not download replacements until this is resolved.
2. Restore authorized storage access, then check ComfyUI startup and live object_info without changing the GPU environment.
3. Build a rescanable inventory using ComfyUI-relative identifiers, missing-file reasons, source/version/hash metadata and separate installed/compatible/render-tested states.
4. General-purpose Image Generation workspace: source image + model + compatible ordered LoRA slots with individual strengths + preset/pose selection. Preview all applied changes; preserve user overrides and source image.
5. General-purpose presets need explicit compatible-family constraints, workflow ID, prompts, optional reference, adapter IDs/weights and sampler settings. Do not guess adapter associations from preset names.
6. Benchmark neutral images: fixed source/prompt/seed, batch one, 512/768 before larger sizes; compare cold and warm time, VRAM, errors and quality. Start with restored 4B distilled as a candidate for fast iteration, then compare 9B quantized. These are proposed tests, not measured recommendations.
7. Keep generation/refinement/upscaling sequential; evaluate offload and tiled decode only against measured memory pressure. Pin working environment before any optimization experiments.
8. Validate each adapter alone before combinations. Existing explicit sexual presets/adapters were not tuned or expanded in this audit.
