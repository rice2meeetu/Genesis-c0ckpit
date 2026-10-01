# GENESIS shared RunPod state — 1 October 2026

## Required constraints
Preserve dirty main and all uncommitted work. Never reset or git add all.
Do not stop the pod: brother is using it. Do not restart his ComfyUI.
Local Klein 9B diagnostics remain prohibited. GPU render tests below have NOT been completed.

## Connection and storage
Pod: a53n3go0xeu1z0. SSH root@69.30.85.51 port 22173.
Local key path: ~/.ssh/runpod_genesis (never commit private key).
GENESIS endpoint: http://127.0.0.1:18189 via SSH forward to pod localhost:8189.
8189 uses /workspace/paul/{user,input,output,temp}; 8188 is the other instance.
Both run from /workspace/runpod-slim/ComfyUI.
Shared /workspace volume source: d09caa58-e5ff-4822-ac74-b4c63cb980f3, fuse.geesefs.
extra_model_paths.yaml maps /workspace/models checkpoints, diffusion_models, text_encoders, vae.
Added loras and controlnet paths with backup. These new paths need process reload; neither process restarted.

## Whole-volume inventory
39684540352 /workspace/models/LLM/powerful-brain/Qwen_Qwen3.5-122B-A10B-IQ4_XS/Qwen_Qwen3.5-122B-A10B-IQ4_XS-00001-of-00002.gguf
28789649792 /workspace/models/LLM/powerful-brain/Qwen_Qwen3.5-122B-A10B-IQ4_XS/Qwen_Qwen3.5-122B-A10B-IQ4_XS-00002-of-00002.gguf
908724576 /workspace/models/LLM/powerful-brain/mmproj-Qwen_Qwen3.5-122B-A10B-f16.gguf
28431843583 /workspace/models/checkpoints/Qwen-Rapid-AIO-NSFW-v19.safetensors
9078656088 /workspace/models/diffusion_models/Miraclein NSFW v3.0 FP8 - Klein9B - 12steps,euler,cfg1.1.safetensors
9433032568 /workspace/models/diffusion_models/aisha_nsfw_beta_v9_7_distilled_fp8.safetensors
9078610848 /workspace/models/diffusion_models/darkBeastMar0326Latest_dbkleinv2BFS.safetensors
9433131176 /workspace/models/diffusion_models/miracleinNSFWGeneration_10Fp8.safetensors
9567300780 /workspace/models/diffusion_models/pornmasterFlux2Klein_v3-fp8.safetensors
0 /workspace/models/diffusion_models/pornmasterFlux2Klein_v3.safetensors
336211292 /workspace/models/flux2-vae.safetensors
16381517176 /workspace/models/text_encoders/qwen_3_8b.safetensors
1917190144 /workspace/models/text_encoders/qwen_3_8b_fp4mixed.safetensors
8664848742 /workspace/models/text_encoders/qwen_3_8b_fp8mixed.safetensors
336211292 /workspace/models/vae/flux2-vae.safetensors

## File integrity
All five nonempty diffusion checkpoints passed safetensors header/data-length completeness checks:
Miraclein v3; Aisha v9.7 distilled FP8; DarkBeast; miracleinNSFWGeneration_10Fp8; PornMaster v3 FP8.
pornmasterFlux2Klein_v3.safetensors is ZERO BYTES and must not be selected.
DarkBeast is a FULL CHECKPOINT, not a LoRA. It was corrected from loras to diffusion_models.
No real LoRA, ControlNet, ReActor/Inswapper/PuLID weights were found in the whole-volume search.
LLM weights are a separate brain and must not be indexed as image UNETs.

## GENESIS changes and verification
qt_cockpit.py remote constants updated to actual Aisha FP8, Miraclein v3 and DarkBeast filenames.
Miraclein v3 defaults: 12 steps, Euler, CFG 1.1.
Backup: /home/rice2meetyou/GENESIS-Backups/runpod-mappings-1790834284.
39 focused tests passed: qt_generation_profiles, model_compatibility, runpod_lora_wiring.
Four mapped checkpoints passed live workflow node/asset-list validation on 8189.
These checks do NOT prove rendering quality, pose fidelity or identity fidelity.
Remote profiles still have restrictive LoRA limits; do not claim multi-LoRA is fully enabled remotely.
A filename ending _10 is not proof of version ten; release ordering remains unverified.

## Outstanding work
Verify one-stage versus source-required reference workflows and GUI runtime refresh.
Verify Qwen v19 dependencies and route; map alternate Miraclein only after configuration review.
Install and validate missing general face-swap nodes/assets without interrupting brother's jobs.
Verify shared LoRA paths after suitable instance reload; currently no LoRA files to expose.
FluxedUp, Kontext, Lustify, Juggernaut were not found on this mounted volume.
Do not report presets or GPU smoke tests as verified: none performed in this session.
Mungbean connection/integration remains unverified.
User can use existing mapped complete models, but full live generation has not been smoke-tested.

## Saved Windows pose table
Copied byte-for-byte to /home/rice2meetyou/Documents/Pose_Table.csv from
/mnt/C/Users/p4uln/P4bLOH/Pabz_Ultimate_Pose_Tagger/table (2).csv.
More prompt tables located under Windows Downloads and Desktop/Documentz/p4bz.
Candidate list: /tmp/windows-pose-table-candidates.txt. Additional copies not yet made.
