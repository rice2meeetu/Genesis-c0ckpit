# GENESIS model and LoRA compatibility

Verified against the live ComfyUI inventory on 2026-09-06. “Metadata” means
the adapter identifies its training architecture internally. “Render” means a
complete local GPU image was produced with the current GENESIS profile.

## Models

| Family | Installed models | LoRA policy |
| --- | --- | --- |
| FLUX.2 Klein 4B | `flux-2-klein-4b.safetensors` | Offer metadata-confirmed 4B adapters |
| FLUX.2 Klein 9B-KV | `flux-2-klein-9b-kv-fp8.safetensors` | Baseline render verified; LoRAs blocked |
| Aisha 9B | `aisha_nsfw_beta_v8_fp8.safetensors` | LoRAs blocked |
| FLUX.1 | `flux1-dev-kontext_fp8_scaled.safetensors`, `fluxedUpFluxNSFW_40DevFp8.safetensors` | Offer known FLUX.1 adapters |
| SDXL | `biglust17_v17`, `juggernautXL_ragnarokBy`, both Lustify checkpoints | Offer metadata-confirmed SDXL adapters |
| Qwen Image | `Qwen-Rapid-AIO-NSFW-v19.safetensors` | No installed adapter verified |

## Approved selector mappings

### FLUX.2 Klein 4B

- `F2K4BBabe_Engel_v1.0.safetensors` — metadata: `flux2_klein_4b`
- `hina_flux2klein4b_asianMix_v4.0-lora.safetensors` — metadata: `flux2_klein_4b`

The downloaded `klein4b-deepthroat-22epoc-k3nk.safetensors` remains blocked:
its filename says 4B but its embedded metadata does not identify a base model.

### FLUX.2 Klein 9B Base

The following identify as ordinary `flux2_klein_9b` adapters. They require the
separate undistilled Klein 9B Base checkpoint, which is not installed:

- `Flux Klein - NSFW v2.safetensors`
- `Klein_Anatomy_Revamped.safetensors`
- `flux2klein_body_version_a.safetensors`
- `flux2klein_tocowgirl.safetensors`
- `FK_sloppydeepthroat_epoch_10.safetensors`
- `FK_teeththroat.safetensors`

### FLUX.2 Klein 9B-KV

No LoRA is approved. A live test with `Flux Klein - NSFW v2` attached all 112
patches but stalled during model initialization, filled nearly all 16 GB VRAM,
and pushed swap use to 8 GB. The service was stopped cleanly. This is not a
usable render pass.

### Aisha 9B

No LoRA is approved. Live tests with `Flux Klein - NSFW v2` and the smaller
rank-16 `flux2klein_body_version_a` both validated their graphs but stalled the
service during model initialization. Aisha remains usable without a LoRA.

### FLUX.1

- `Flux-NSFW-uncensored.safetensors`
- `alimama-creative---FLUX.1-Turbo-Alpha/diffusion_pytorch_model.safetensors`

### SDXL

- `add-detail-xl.safetensors` and its duplicate `(1)` copy
- `latent-consistency---lcm-lora-sdxl/pytorch_lora_weights.safetensors`
- `genshin impact pierro-V1.safetensors`

## Installed but unapproved

These files lack enough internal architecture evidence, target an uninstalled
model family, or have not completed the required render test:

- `FLUX2_KLEIN_UNLOCKED_V1.safetensors`
- `flux2klein_cowgirl.safetensors`
- `flux2klein_bj.safetensors`
- `FutaCockCloseUp-v2.safetensors`
- `comfy-wrapped-loras/pytorch_lora_weights.safetensors`
- `consistence_edit_v1.safetensors`, `consistence_edit_v2.safetensors`
- `f2k_4B_consist_20260314.safetensors`
- `f2k_9B_lcs_consist_20260415.safetensors`
- `f2k_9B_lcs_consist_preview_20260328.safetensors`
- `k_blackanal.safetensors`
- `lenovo_krea2.safetensors`, `lenovo_krea2_2.safetensors`
- `snofs_krea_v1_3D.safetensors`
