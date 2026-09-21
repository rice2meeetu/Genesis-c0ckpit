# GENESIS next-GPT handover — 2026-09-21

## Start here

- User: Paul. Work directly and concisely; avoid repeating questions or circling through old attempts.
- Connect through Remote Desktop Commander to the online `rice2meetyou-B550M-K` device.
- Repository: `/home/rice2meetyou/Genesis-c0ckpit`, branch `main`.
- Read `GENESIS_STATUS.md` before making changes. Its final diagnostic checkpoint is authoritative.
- Last substantive commit: `7c3b4fc` (`Bypass hidden Klein LoRA and record diagnostic handover`).
- Static verification: `122 passed, 1 warning`; the warning is a harmless `pkg_resources` deprecation.

## Safety state

- Current OS is Ubuntu 26.04.1, kernel `7.0.0-31-generic`, RX 9060 XT 16 GB, 32 GB RAM.
- Current boot read-only checks found zero KFD/SVM warnings, ATA errors, GPU resets, ring timeouts, page faults, panic, or OOM.
- This is only a clean idle/light-workload baseline. It is not clearance for stress testing.
- Heavy GENESIS services are disabled; leave ComfyUI, Ollama, llama, Qwen, voice, and Builder disabled.
- Do not run Klein 9B, LoRA suites, GPU benchmarks, stress tests, or overlapping GPU workloads.
- Do not change ROCm, AMDGPU, firmware, or kernel just to experiment.
- Prior evidence: Klein 4B no-LoRA passed twice; one AsianMix LoRA run reproduced escalating `amdgpu_amdkfd_restore_userptr_worker` warnings.
- Never erase, repartition, clone over, or retire a drive until the replacement installation and copied data are independently verified.

## Current decision and next sequence

- Paul will buy a new physical SSD after payday; a 100 GB OneDrive/Microsoft trial is not useful for this.
- Keep the present Ubuntu disk and Windows disk untouched as rollback sources.
- Preferred fresh target: Ubuntu 24.04.4 LTS with AMD-supported 6.17 HWE, then a clean supported ROCm/PyTorch stack.
- RunPod is available later for heavy model work; do not request or expose credentials during setup.
- Until the SSD arrives, limit work to documentation, UI/non-GPU changes, read-only diagnostics, and backups.
- After migration: static tests → idle kernel baseline → one guarded Klein 4B no-LoRA run → shutdown/log review → at most one explicitly approved LoRA.
- A fresh direct SMART read of the Kingston SA400 still needs sudo; do it only when Paul is ready to type the password himself.
- Root filesystem was 91% used with about 14 GB free; avoid large downloads or duplicate environments.

## GENESIS work remaining

- This handover is GENESIS-only. Jellyfin/player work stays with the current GPT and is out of scope here.
- Continue safe UI, documentation, static-test, and read-only diagnostic work while preserving the GPU limits above.
- Media pickers should default to Thumbnail Grid for source images, poses, and generated results.
- A selected image needs a larger preview panel, and the picker should remember the last chosen view.
- Show Paul the complete Media Viewer and Canvas layouts/end result before locking the design.
- Aim for a premium visual finish without making implementation depend on Figma-only capabilities.
- A splash screen is a later optional polish item, not a current priority.
- Keep storage usage low and leave the new-SSD/Ubuntu 24.04.4 migration plan intact.

## Handoff rule

Lead with a read-only state check. Explain any risk before mutation, obtain explicit approval for destructive work, and preserve the current rollback path.


## UI takeover update — 2026-09-21

- Read the final UI review checkpoint in GENESIS_STATUS.md as well as the safety
  checkpoint. Safety limits and migration decisions are unchanged.
- Shared Qt Thumbnail Grid + large preview + remembered view are implemented.
  Media Viewer and Canvas layouts are now available through Media Tools.
  Design remains pending Paul's visual review. Canvas GPU edits stay on hold.
- Static suite is now 126 passed, one existing deprecation warning; software
  screenshots work without the earlier black Wayland capture limitation.
- Existing uncommitted genesis/media_functions.py changes predated this takeover
  and were deliberately left untouched. Do not assume the working tree is clean.
- No push was performed. Keep Jellyfin work in the other chat.
