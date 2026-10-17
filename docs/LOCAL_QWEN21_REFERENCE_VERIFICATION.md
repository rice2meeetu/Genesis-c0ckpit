# Local Qwen Image 2.1 reference verification

## Contract that must be checked

A completed generation does not establish that reference images were consumed. The installed ComfyUI V3 Autogrow parser discarded the old nested `images` dictionary. API submissions require `images.image_1` and `images.image_2`; ComfyUI reconstructs the dictionary for the node internally. This affects local reference generation, not plain text-to-image.

The local route now:

- Uses the dedicated local diffusion and encoder loaders installed in ComfyUI.
- Preserves source-first, pose-second reference ordering; rejects missing/reordered reference wiring before submission.
- Flattens Autogrow image connections for the ComfyUI API.
- Maps the smaller selected width/height to the native reference resolution, rounded to 32; output proportions follow the first reference.
- Uses source-initialized latents only when an actual source is present and denoise is below 1.0. Their size follows the same resolution.
- Leaves remote submissions, saved shared workflow JSON, other model routes, and ROCm startup flags unchanged.

## Regression verification

Run `python -m pytest tests/test_qwen_image21_workflow.py tests/test_qwen_image21_local_contract.py -q` from the GENESIS environment. The contract tests exercise source-only, pose-only, and source-plus-pose generation with real workflow assembly and validators, and verify prompt, negative prompt, seed, sampler, scheduler, CFG, steps, denoise, size and asset wiring.

The installed-runtime test uses ComfyUI's real V3 parser against the generated production graph. By default it finds `~/AI/ComfyUI/.venv/bin/python`; set `GENESIS_TEST_COMFY_ROOT` for another installation. **A skip is not a local-runtime pass.** No models or GPU jobs are loaded by that parser test. The fixture contains selected node schemas captured from local `/object_info`; refresh and inspect it when those node contracts change. The fixture is not proof that a future backend still has the same schema.

For a release check, compare the assembled graph with fresh `/object_info`, verify the server parser retains the intended references, then perform a bounded generation. Check output aspect ratio, requested pose and resemblance separately. Do not equate prompt wording or successful completion with identity preservation. Preserve the source files, dirty checkout, other routes and launch flags. Back up edits first.

## Verified local results on 8 October 2026

- Corrected two-reference, 512 resolution, 25 steps: completed in 195 seconds (caller).
- Corrected two-reference, 768 resolution, 25 steps: completed in 259 seconds (caller), 640×928 output. Raised hands stayed in frame; facial resemblance improved visually. Strict identity and exact skeleton alignment were not quantitatively measured.
- Corrected 1024 test: reference encoding and model loading progressed, but the 290-second caller deadline expired before an output completed. Cleanup stopped the service; the backend was restarted using its existing mechanism. This is not proof of a GPU hang or unsupported resolution.

The app's Balanced controls (768×1152) were verified to produce the same entire prompt graph as the successful 768 test. Fast maps to 512; Quality maps to 1024. The local source-edit default was subsequently set explicitly to 768×768 after a second bounded 1024 test failed to complete; text-to-image and remote defaults stay at 1024. Quality remains selectable with a limitation note. Existing full-strength denoise remains 1.0; the earlier low-denoise results predated the image-connection fix and must not be treated as proof of a model limitation.

Tests used an independent five-minute service-stop watchdog with cleanup. This watchdog belongs to the diagnostic harness; it was not added to normal app generation. Normal app timeout behavior is unchanged.

A targeted adjacent regression run passed 188 tests: Qwen workflow and runtime contract, Stage 1 selection, model controls, stage wiring, pose/identity routing, backend and operation routing, cancellation/client safety, runtime launch profile, workflow conversion, local configuration and premium UI contracts. These tests do not imply that every other model has been GPU-tested.

## Final 1024 follow-up

A second corrected 1024 test was allowed 470 seconds with an independent 480-second watchdog because the first test had made measurable loading progress. Reference encoding and diffusion model loading completed; the GPU was active, but no image completed before the deadline. Cleanup stopped the service and requested a normal restart. This confirms that 1024 did not finish within either test budget, not that the GPU necessarily hung. No further 1024 retries were scheduled. The local source-edit default is now 768×768; plain text-to-image and remote defaults are unchanged. The UI explains the verified Balanced setting and the 1024 test limitation.
