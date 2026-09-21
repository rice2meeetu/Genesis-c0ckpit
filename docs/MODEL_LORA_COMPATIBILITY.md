# GENESIS model and LoRA compatibility

Verified against the live ComfyUI inventory through 2026-09-11. “Metadata” means
the adapter identifies its training architecture internally. “Render” means a
complete local GPU image was produced with the current GENESIS profile.

## Models

| Family | Installed models | LoRA policy |
| --- | --- | --- |
| FLUX.2 Klein 4B | `flux-2-klein-4b.safetensors` | Baseline allowed; all 4B LoRAs runtime-held pending guarded re-verification |
| FLUX.2 Klein 9B Base | `flux-2-klein-base-9b-Q4_K_M.gguf` | Baseline and three regular-9B LoRAs render verified |
| FLUX.2 Klein 9B-KV | `flux-2-klein-9b-kv-fp8.safetensors` | Baseline render verified; LoRAs blocked |
| Aisha 9B | `aisha_nsfw_beta_v8_fp8.safetensors` | LoRAs blocked |
| FLUX.1 | `flux1-dev-kontext_fp8_scaled.safetensors`, `fluxedUpFluxNSFW_40DevFp8.safetensors` | Offer known FLUX.1 adapters |
| SDXL | `biglust17_v17`, `juggernautXL_ragnarokBy`, both Lustify checkpoints | Offer metadata-confirmed SDXL adapters |
| Qwen Image | `Qwen-Rapid-AIO-NSFW-v19.safetensors` | No installed adapter verified |

## Approved selector mappings

### FLUX.2 Klein 4B

Family metadata / historical evidence still identifies these as 4B candidates:

- `F2K4BBabe_Engel_v1.0.safetensors` — metadata: `flux2_klein_4b`
- `f2k_4B_consist_20260314.safetensors` — metadata: `flux2_klein_4b`
- `klein4b-deepthroat-22epoc-k3nk.safetensors` — historical structural/render evidence
- `hina_flux2klein4b_asianMix_v4.0-lora.safetensors` — metadata: `flux2_klein_4b`, but runtime-quarantined

**Current runtime policy (2026-09-21): no Klein 4B LoRA is selectable.** Two
no-LoRA 4B baselines passed under the RX 9060 XT SVM-safe profile, while the
first current-profile AsianMix adapter test triggered
`amdgpu_amdkfd_restore_userptr_worker` warnings after sampling. Each adapter
must therefore complete a guarded post-reboot verification before being added
to the runtime-verified allowlist.

### FLUX.2 Klein 9B Base

The regular Klein 9B Base Q4_K_M GGUF is installed. Its baseline completed at
512×512 twice, 768×768, and 1024×1024. The following adapters identify as
ordinary `flux2_klein_9b` and completed controlled 512×512 renders at strength
0.65 on the RX 9060 XT:

- `Flux Klein - NSFW v2.safetensors` — render verified, 56.5 s
- `Klein_Anatomy_Revamped.safetensors` — render verified, 44.4 s
- `flux2klein_body_version_a.safetensors` — render verified, 95.3 s

The test used `qwen_3_8b_fp8mixed.safetensors`, a fixed neutral prompt, seed
390829, 512×512, four steps, CFG 1, Euler/simple, and model-only LoRA loading.
Reports and images are saved under
`gpu_test_outputs/klein9b-lora-benchmark/`.

Use one adapter at a time. A cockpit-path render stacking
`flux2klein_body_version_a` with `Klein_Anatomy_Revamped` completed at both
0.65 and 0.35 strength per adapter, but visual inspection found severe
structural streaking at both strengths. The Qt cockpit therefore blocks LoRA
stacking even though each adapter is individually render-verified.

These additional regular-9B adapters are metadata-compatible but still lack a
completed controlled render in the current matrix:

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

## External candidate research — 2026-09-20

This is discovery evidence only. No candidate below is installed, compatible, or
render-tested merely because a hosting page exists.

- The official FLUX.2 Klein 9B model card confirms unified text-to-image and
  multi-reference editing, a four-step distilled route, an 8B Qwen3 encoder,
  and an approximately 29 GB unquantized VRAM requirement. GENESIS should keep
  using measured quantized/FP8 routes on this 16 GB GPU.
- A Civitai-tracked archive identifies PornMaster Flux2 Klein V3 as a Klein 9B
  Base checkpoint (Civitai version 2763416; SHA256
  `F5B479C7F5B49BC7E0F1A163186C5C583B744A77BDF337CA9BB5B0DBE98E60C7`).
  An independently hosted FP8 derivative is about 9.57 GB, but provenance,
  workflow settings, and output quality still require local verification.
- The Aisha publisher's repository lists the installed V8 FP8 (9.43 GB), newer
  V9.7 distilled FP8 (9.43 GB), and multiple 18.2 GB BF16 variants. Newer
  filename/version alone is not proof that V9.7 is better or runnable.
- Other 9.08–9.57 GB FP8 candidates visible in current community archives
  include MoodyDesireMix v30, Snofs v12/v14, Miracle v20, KleiNova, and
  PornMaster v4/Turbo. These are benchmark candidates, not recommendations.
- Hugging Face history confirms the regular-9B files
  `FK_sloppydeepthroat_epoch_10.safetensors` and
  `FK_teeththroat.safetensors` exist in Klein 9B collections. That confirms
  provenance/family naming, not local render quality.
- Community reports are mixed: Klein 9B is praised for speed, prompt adherence,
  editing and text, while anatomy, skin texture, and character-LoRA consistency
  remain recurring complaints. Local fixed-seed adult-only comparison renders
  are required before replacing the current baseline.

Sources:
- https://huggingface.co/black-forest-labs/FLUX.2-klein-9B
- https://huggingface.co/Aisha-AI-Official/flux-2-klein-models
- https://huggingface.co/ApacheOne/TBA_quants_Klein/blob/main/Flux_2_Klein_9B-base_info.md
- https://huggingface.co/Kerstal/f2-klein-9b_model/tree/main
- https://huggingface.co/codeShare/flux-klein-9B-loras
