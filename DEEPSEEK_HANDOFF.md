# GENESIS c0ckpit — DeepSeek Handoff

AUTHORITATIVE BUILD: ~/Genesis-c0ckpit
GitHub: git@github.com:rice2meeetu/Genesis-c0ckpit.git
Branch: main
Verified baseline: 5829c43

RULES:
- Continue the existing build; do not start over.
- Inspect git status, branch, log, source tree, tests, UI, ComfyUI integration and current workflows before editing.
- Never guess verifiable state.
- Preserve the current UI and live repo; older Qt ZIPs are reference only.
- Do not delete or replace working models, LoRAs, workflows, ROCm or ComfyUI environments.
- Checkpoint before major edits, run tests/compile checks, review git diff.
- Never commit secrets, tokens, SSH keys or passwords.
- Use a dedicated branch such as deepseek/<task-name> and push via GitHub for review.

KNOWN PATHS:
/mnt/AI-Storage/ComfyUI/models
/mnt/AI-Storage/ComfyUI/models/unet/flux-2-klein-base-9b-Q4_K_M.gguf
/mnt/AI-Storage/ComfyUI/models/text_encoders/t5xxl-restored-fp8.safetensors
/mnt/AI-Storage/ComfyUI/models/vae/flux2-vae.safetensors

KNOWN KLEIN/KREA LORAS:
snofs_krea_v1_3D.safetensors
Klein_Anatomy_Revamped.safetensors
FLUX2_KLEIN_UNLOCKED_V1.safetensors
Flux Klein - NSFW v2.safetensors
lenovo_krea2_2.safetensors
flux2klein_body_version_a.safetensors

FIRST TASK:
1. Read this file.
2. Verify current git state.
3. Map entry points/UI/navigation.
4. Inspect ComfyUI workflow discovery and Klein 9B loader usage.
5. Inspect Qwen/AI integration.
6. Run existing tests.
7. Report verified current state before changing code.
