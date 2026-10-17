# GENESIS UI and settings-isolation audit — 17 October 2026

The real Linux premium QML was exercised offscreen with isolated user settings. The complete repository test suite passed (817 tests plus four subtests), including the final remote-reselect guard. Repeat the full suite after every substantive change.

## Verified interactions

- Stack navigation across all sixteen workspace page indices; existing home-card, media-tool, character, canvas and pose-page interaction tests.
- Fast, Balanced and Quality change the documented size/steps/CFG/reference-area fields without silently resetting user-selected sampler, scheduler, denoise, prompt, seed, LoRA selections/strengths or Native/2K/4K output target.
- Changing source photos within Image-to-Image retains unrelated settings. Selecting a model that's already selected also retains controls while still allowing an explicit RunPod route refresh.
- A skeleton with no authored metadata changes pose input only; selecting a text pose applies its explicit settings and authored text without overwriting unrelated advanced controls.
- Text-to-Image and Image-to-Image retain manually revised positive/negative prompts, chosen seed and LoRA selections. Model-mode-specific defaults can still change sampling to match the route, and Text-to-Image disables source-dependent Stage 3.
- Three independent LoRA choices and strengths, output target, extra reference and stage-state controls have focused regression coverage. Model changes can still clear incompatible LoRA selections by design.

## Boundaries

These are automated QML/bridge, Python and model-contract verifications; they are **not** a live RunPod 8189 or every-model GPU render certification. The separate installed local ComfyUI (127.0.0.1:8188) remains running. Standalone FaceFusion/MIGraphX and all hardware-backed media operations require their own live checks. Changes were made in the existing protected local checkout without modifying the ComfyUI model files, user's images, desktop shortcut or saved RunPod selection.
