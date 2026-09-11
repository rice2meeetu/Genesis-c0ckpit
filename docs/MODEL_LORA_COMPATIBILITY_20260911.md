# GENESIS verified model and LoRA compatibility

Generated: 2026-09-11T20:28:31

This report is metadata-based. It does not claim visual quality or trigger words.
No app configuration was changed by this scan.

## Aisha evidence

- Aisha embedded workflow references `flux-2-klein-9b-fp8.safetensors`.
- Embedded workflow references `nsfw_aio_v4_000014750.safetensors`.

## LoRA metadata results

| File | Declared base | Result |
|---|---|---|
| `Flux Klein - NSFW v2.safetensors` | `flux2_klein_9b` | CONFIRMED: FLUX.2 Klein 9B family |
| `FLUX2_KLEIN_UNLOCKED_V1.safetensors` | `not declared` | UNVERIFIED: no base-model metadata |
| `flux2klein_body_version_a.safetensors` | `flux2_klein_9b` | CONFIRMED: FLUX.2 Klein 9B family |
| `hina_flux2klein4b_asianMix_v4.0-lora.safetensors` | `flux2_klein_4b` | CONFIRMED: Klein 4B only; not for Aisha/Klein 9B |
| `klein4b-deepthroat-22epoc-k3nk.safetensors` | `not declared` | UNVERIFIED: filename suggests Klein 4B; do not use with Aisha |
| `Klein_Anatomy_Revamped.safetensors` | `flux2_klein_9b` | CONFIRMED: FLUX.2 Klein 9B family |
| `lenovo_krea2_2.safetensors` | `krea2` | CONFIRMED: Krea2 only; not for Klein/Aisha |
| `snofs_krea_v1_3D.safetensors` | `krea2` | CONFIRMED: Krea2 only; not for Klein/Aisha |

## Installed model files

- `/home/rice2meetyou/AI/AI-Models/diffusion_models/aisha_nsfw_beta_v8_fp8.safetensors` — 9,433,074,464 bytes — MODEL FILE: inspect embedded workflow
- `/home/rice2meetyou/AI/ComfyUI/models/checkpoints/Qwen-Rapid-AIO-NSFW-v19.safetensors` — 28,431,843,583 bytes — MODEL FILE: Phr00t/Qwen Stage 1; not a Klein LoRA target
- `/home/rice2meetyou/AI/ComfyUI/models/diffusion_models/flux-2-klein-4b.safetensors` — 7,751,105,712 bytes — UNVERIFIED: filename suggests Klein 4B; do not use with Aisha
- `/home/rice2meetyou/AI/ComfyUI/models/diffusion_models/flux-2-klein-9b-kv-fp8.safetensors` — 9,818,935,984 bytes — MODEL FILE: no LoRA verdict
- `/home/rice2meetyou/AI/ComfyUI/models/diffusion_models/fluxup-Q4_K_M.gguf` — 6,799,817,888 bytes — MODEL FILE: FluxUp; requires matching FLUX family LoRA
- `/home/rice2meetyou/AI/ComfyUI/models/diffusion_models/fluxup-restored-Q4_K_S.gguf` — 6,799,817,888 bytes — MODEL FILE: FluxUp; requires matching FLUX family LoRA
- `/home/rice2meetyou/AI/ComfyUI/models/facedetection/detection_Resnet50_Final.pth` — 109,497,761 bytes — MODEL FILE: no LoRA verdict
- `/home/rice2meetyou/AI/ComfyUI/models/facedetection/parsing_parsenet.pth` — 85,331,193 bytes — MODEL FILE: no LoRA verdict
- `/home/rice2meetyou/AI/ComfyUI/models/facerestore_models/codeformer-v0.1.0.pth` — 376,637,898 bytes — MODEL FILE: no LoRA verdict
- `/home/rice2meetyou/AI/ComfyUI/models/facerestore_models/GFPGANv1.3.pth` — 348,632,874 bytes — MODEL FILE: no LoRA verdict
- `/home/rice2meetyou/AI/ComfyUI/models/facerestore_models/GFPGANv1.4.pth` — 348,632,874 bytes — MODEL FILE: no LoRA verdict
- `/home/rice2meetyou/AI/ComfyUI/models/text_encoders/qwen_3_4b_fp4_flux2.safetensors` — 3,848,213,998 bytes — MODEL FILE: Phr00t/Qwen Stage 1; not a Klein LoRA target
- `/home/rice2meetyou/AI/ComfyUI/models/text_encoders/qwen_3_8b_fp8mixed.safetensors` — 8,664,848,742 bytes — MODEL FILE: Phr00t/Qwen Stage 1; not a Klein LoRA target
- `/home/rice2meetyou/AI/ComfyUI/models/text_encoders/t5xxl-restored-fp8.safetensors` — 5,157,348,688 bytes — MODEL FILE: no LoRA verdict
- `/home/rice2meetyou/AI/ComfyUI/models/unet/flux-2-klein-base-9b-Q4_K_M.gguf` — 5,909,829,920 bytes — MODEL FILE: no LoRA verdict
- `/home/rice2meetyou/AI/ComfyUI/models/vae/flux2-vae.safetensors` — 336,211,292 bytes — MODEL FILE: no LoRA verdict

## Safe conclusions

- Aisha is evidenced as a FLUX.2 Klein 9B-based model.
- LoRAs explicitly declaring `flux2_klein_9b` are the strongest candidates for Aisha.
- LoRAs explicitly declaring `flux2_klein_4b` must remain in a separate Klein 4B profile.
- LoRAs explicitly declaring `krea2` must not be placed in the Klein/Aisha profile.
- Persephone compatibility remains unverified unless its own model and LoRA metadata identify the same base family.
- Trigger words were not inferred from filenames.
