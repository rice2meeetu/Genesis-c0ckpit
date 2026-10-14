# GENESIS verification — 7 October 2026

## Current result

Dedicated Characters page uses the existing Character A library and shared selection. Master controls are protected. Face/body/pose/ignore categories, review/approval, gallery previews and zoom are available. Existing references remain intact; legacy body/pose roles are interpreted without rewriting the library. No Character B identity was introduced.

The Reference Builder now generates seven candidate requests (front, left/right three-quarter, profile, back, upper body, full body), stores them unapproved, and creates a separate review contact sheet. The sheet is never treated as an identity reference. A failed batch preserves earlier candidates; cancellation is supported. Candidate/reference mutation controls are disabled during generation. Explicit requested angles can select matching approved references when Create is using the saved master; arbitrary manually loaded source images are not replaced. Face finishing still receives the saved master.

The old external Pose Maker launcher has been replaced with the maintained Pose Library. The existing source/pose handoff contract is consumed by the premium cockpit and preserves separate image roles. It no longer depends on the missing legacy web application or its obsolete model workflows. The formerly skipped test now tests this maintained integration and passes.

## SDXL files, LoRAs and settings

Both files exist under `/home/rice2meetyou/AI/ComfyUI/models/checkpoints/`:

- `donutsdeliverymixV4_v41.safetensors` — 6,938,051,602 bytes.
- `biglustydonutmixNSFW_v12.safetensors` — 6,938,462,898 bytes.

Their tensor header offsets match their file sizes. Local catalog entries are in `genesis/model_registry.py`; compatibility is in `genesis/model_compatibility.py`; source/pose generation and controls are in `qt_cockpit.py`. Both use `genesis/reference/pose_workflows/GENESIS_SDXL_SHARED_T2I.json` as a base graph. Source images replace the empty latent through VAEEncode at runtime. OpenPoseXL2 controls conditioning without replacing that source latent.

Compatible optional files under `/home/rice2meetyou/AI/ComfyUI/models/loras/`:

- `add-detail-xl.safetensors` — 228,452,344 bytes.
- `face_xl_v0_1.safetensors` — 223,735,220 bytes.
- `skin texture style v4.safetensors` — 912,552,748 bytes.

All three can be chained with independent strengths. Training tags extracted for add-detail are not guaranteed activation phrases; no activation words were extracted for the other two. No authoritative list of further intended adapters was supplied, so no additional adapters or URLs were invented.

Normal SDXL defaults remain **25 steps**, CFG 4, Karras, source denoise 0.65 (text-only 1.0). Donuts uses dpmpp_sde; BigLusty uses dpmpp_3m_sde. No SDXL default was changed to 40 steps. The normal user flow remains load image → optionally choose pose → typed prompt or pose prompt → Generate. Finishing toggles remain user controlled.

## Installed missing weights

ReSwapper `models/reswapper/reswapper_256.onnx` (554,298,280 bytes) and HyperSwap `models/hyperswap/hyperswap_1a_256.onnx` (402,742,682 bytes) were installed from the sources documented by the installed ReActor plugin. Both were checked against Hugging Face LFS SHA-256 values and are listed by the live backend.

The legacy upscale workflow's exact missing assets are now installed and publisher-hash verified:

- `models/checkpoints/Realistic_Vision_V6.0_NV_B1.safetensors` — 4,265,096,996 bytes; [publisher](https://huggingface.co/SG161222/Realistic_Vision_V6.0_B1_noVAE/blob/main/Realistic_Vision_V6.0_NV_B1.safetensors).
- `models/vae/vae-ft-mse-840000-ema-pruned.safetensors` — 334,641,190 bytes; [publisher](https://huggingface.co/stabilityai/sd-vae-ft-mse-original).

The old Final upscale graph now validates and completed a real 128→256 image upscale. Independent UltraSharp finishing is also available. The legacy SD1.5 upscale graph has its own saved settings; these do not alter SDXL generation defaults.

## FaceFusion and actual execution providers

[FaceFusion 3.9.1](https://github.com/facefusion/facefusion/tree/3.9.1) is installed separately at `Genesis-c0ckpit/.runtime/facefusion`, with an isolated environment and onnxruntime-migraphx 1.27.1. Its normal model/content checks were retained. A reproducible installer and configuration template are included in the repository. Local image-only and RunPod video exclusions remain enforced.

Fixed the FaceFusion launcher referencing undefined variables, relative output paths, and local ReActor finishing ignoring the selected engine. FaceFusion exposes explicit AMD GPU (MIGraphX) and CPU choices. AMD GPU mode preflights real device access and model-session provider initialization and stops on failure; CPU is not substituted as a successful GPU result.

**GPU face swapping is not verified.** The tool environment has no `/dev/kfd` or `/dev/dri`, HIP reports zero devices, and a real MIGraphX model session cannot initialize. A filesystem-access request did not expose those devices. ComfyUI runs separately and reports the RX 9060 XT for diffusion. Its installed ReActor swapper explicitly uses `CPUExecutionProvider`, with a preexisting comment that its ROCm path stalled. Successful ReActor face tests therefore prove CPU face-swap inference, not GPU swapping. That existing provider configuration was preserved.

FaceFusion completed a CPU swap through the actual GENESIS launch function, producing a readable changed output. All three ReActor engines completed actual swaps on generated neutral portraits with changed readable outputs. The user’s actual Character A likeness has not been evaluated.

## Verification

**473 automated tests passed, 4 subtests passed, no skips.** Tests include current backend exclusions, local routes, supported model settings, source/pose prompt handling, reference approvals, batch failures, reference sheets, selected local face engines, FaceFusion execution and rejection of silent GPU fallback. QML component loading and full Characters page rendering were checked.

Both SDXL models completed live local 512×512 image-to-image tests at 25 steps. Donuts also completed source + OpenPoseXL2 + all three LoRAs at 25 steps. A complete seven-candidate batch ran on an isolated temporary profile at 512×512 and 25 steps; every candidate remained unapproved and the master file hash stayed unchanged. The derived sheet was rendered and reviewed.

**Image-quality limit:** the SDXL batch produced candidates but did not reliably obey every requested viewpoint/framing; several profile/body requests remained frontal portraits. The builder does not claim that an angle label proves the image achieved that angle. Human review and explicit approval remain required. This is not proof of preserved likeness or reliable multi-view synthesis. No actual user character profile was modified during smoke testing.

RunPod jobs, endpoints, existing exclusions and launcher backend preference were preserved. The existing normal launcher defaults to RUNPOD; LOCAL selection is required for local work. Old manual root face-detection scripts are outside the maintained test suite; their GUI-environment dependencies were not installed or falsely reported as tested.

## Backup

Code and verification changes are saved in local Git checkpoints and portable bundles. Git does not back up the separately installed model weights, runtime dependencies, or private character image files. The public GitHub push remains unapproved and has not been performed.
