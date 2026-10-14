# Genesis configuration check — 13 October 2026

## Applied fixes

- Qwen Image 2.1 defaults and dedicated text/reference graphs use the publisher quality baseline: 40 steps, CFG 1. Lower step counts remain available for drafts.
- The sampler selector includes LCM, and the scheduler selector includes ddim_uniform, matching the installed MoP DMD profile. Previously the UI could display a different entry from the effective default.
- Saved RunPod helpers preserve MPS 50% active-thread limits for Genesis. The optional shared-GPU serialization guard is disabled by default and can be re-enabled with GENESIS_SHARED_GPU_SERIALIZE=1.
- Both main instances were verified as MPS clients. GPU memory/bandwidth remain shared. This is a compute ceiling, not an exclusive reservation or guaranteed equal speed.
- Restored Genesis's virtual-environment interpreter so GGUF and Wan wrapper nodes load. Live catalog: 1,447 node types.

## Workflows and denoise

Genesis builds video graphs dynamically in genesis/wan_video.py, including Wan 2.2 5B and Wan 2.1 14B. The earlier JSON-only audit incorrectly described the 5B graph as absent.

Reference JSON templates can contain placeholder model names; Genesis substitutes installed model/encoder choices at submission. A raw-template mismatch alone does not prove the app route is broken. Missing optional model variants remain unavailable rather than downloading them automatically.

Ordinary text-to-image uses denoise 1. SDXL/SD1.5 source-image routes default to 0.65: lower values preserve more source structure, higher values permit stronger changes. Reference-conditioned Qwen and Flux editing are different: denoise 1 or a fixed scheduler is expected. Wan's start image conditions generation; lowering denoise is not a generic preservation fix.

Miraclein: 12 steps / CFG 1.1 / Euler. Pony: 25 / CFG 6 / DPM++ 2M / Karras. Realistic Vision: 25 / CFG 7 / DPM++ 2M / Karras. MoP DMD: 10 / CFG 1 / LCM / ddim_uniform. Wan 2.1 I2V: 20 / CFG 6 / uni_pc / simple / denoise 1. These are configured starting points, not a promise of best quality for every prompt.

## Remaining file issues

Two Pony slider LoRAs are zero bytes. Five newer Klein files did not match their safetensors header lengths at inspection and may still be uploading. Do not delete or overwrite an upload in progress. Replacement downloads require an exact verified source; no model bytes were fabricated or substituted.

The Wan adapter matches all 400 installed Wan 2.1 14B layer shapes and has a complete header/file length. Training provenance, trigger words and output quality are not established by that structural check.

## Validation

164 targeted tests passed. No content generations were submitted during this audit. Local QML changes appear after reopening Genesis. The pod itself was not restarted.

Sources:
- https://github.com/QwenLM/Qwen-Image-2.1/blob/main/README.md
- https://docs.nvidia.com/deploy/mps/when-to-use-mps.html
