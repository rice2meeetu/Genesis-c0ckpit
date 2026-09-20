# GENESIS Photo Studio Status

## Current Version
GENESIS v0.10 + Cockpit stabilization
Branch: main
Latest checkpoint: dbc170c

## Project Root
/home/rice2meetyou/Genesis-c0ckpit

## Current State

Completed:
- Git repository created
- Database module created
- Scanner module created
- Thumbnail engine created
- Media Viewer and PyQt6 viewer iterations created
- GPU detection module created
- Metadata backfill, face detection, smart search, multi-face analysis,
  export, cloud/mobile/backup, and performance milestones completed
- Lightweight six-camera go2rtc Camera Hub added
- Cockpit dashboard shell and dark cockpit theme added
- Configurable cockpit artwork, banner framing, zoom, and X/Y position added
- Artwork framing Cancel/window-close now restores the prior live preview
  ComfyUI, and status refresh
- Functional Local AI control page added with real status and launch controls
- Existing Jellyfin Desktop/MPV/ModernZ system integrated without modification
  through guarded user services with duplicate-process prevention
- Silent no-selection and unavailable-camera control paths now give feedback
- Core image-generation panel now uses existing ComfyUI workflows without
  rewriting them: workflow/model/LoRA selection, source-image upload, prompt,
  one-button Generate, progress, validation, and GENESIS-Exports output
- Home is now task-oriented around Photos + Duplicate Lab, FLUX generation,
  ReActor face swap, the Pose Library, Camera Hub, and model/workflow status
- The dashboard remembers and reopens the most recent photo project folder
- FLUX/Klein and ReActor cockpit entries select a matching indexed workflow
  when available and give clear guidance when one has not been indexed yet
- AI control has direct create shortcuts for FLUX, ReActor, poses, and preflight
- Recovery comparison confirmed the current face engine and newest supporting
  tools match `working-tree-20260822-223305` byte-for-byte; the canonical
  checkpoint keeps optimized grouping, batch detection, person management,
  v09 feature coverage, and the v10 working performance reference
- `./launch.sh` and `./launch_genesis.sh` now open the full Tk cockpit through
  the existing `.venv`; they no longer divert into experimental viewer builds
- Jellyfin MPV Shim controls aligned across native/Flatpak profiles; shim
  autostart disabled so it only runs when explicitly launched
- Cockpit Klein 4B Fast generation live-tested end to end at 512x512: queued,
  completed in 56 seconds, exported, and visually verified without modifying
  the saved workflow
  live-started successfully on `127.0.0.1:8000`
- ComfyUI and llama.cpp user-service startup paths live-tested successfully;
  llama.cpp returned a healthy response and ComfyUI was restored with an empty
  queue and RX 9060 XT GPU acceleration available
- All ten Qt Cockpit pages launched successfully on the host display; automated
  Wayland/XWayland screenshots remain black and are not treated as a visual pass
- Current automated suite passes: 71 tests

## Current Architecture

GENESIS
|
├── main.py
|
└── genesis/
    ├── database.py
    ├── scanner.py
    ├── thumbnails.py
    ├── media_viewer.py
    └── gpu.py

## Current Build Target

GENESIS Cockpit stabilization

Next:
- Physically verify the updated mouse gestures during real Jellyfin playback
- Perform a human visual pass of the full Cockpit on the host desktop; all ten
  pages launch, but automated Wayland/XWayland captures are black
- Configure TTS only if the existing AllTalk/Genesis Voice backend becomes
  available; do not install a replacement implicitly
- Reconcile the older experimental/untracked viewer files without deleting them

## Working Tree Note

The branch is currently clean and synchronized with `origin/main`. Preserve this
verified baseline: back up touched files before risky changes and stage only
deliberate milestone files.

## Rules

- GENESIS main only
- Do not mix Shinobi
- Do not mix GENESIS Mini
- Do not mix Pose Maker branch
- Use Git commits after major milestones

## GPU Safety Incident — 2026-09-21

- Safety reproduction used one isolated Klein 4B baseline only: 512x512, 4 steps,
  no LoRA. It completed successfully in 80.45 seconds and produced
  `gpu_test_outputs/klein4b-lora-benchmark/baseline-safety.png` (512x512 PNG).
- During that single ComfyUI/ROCm workload, kernel 7.0.0-31 reproduced the
  AMDGPU/KFD workqueue warning sequence in `svm_range_restore_work`,
  `amdgpu_amdkfd_restore_userptr_worker`, and `svm_range_deferred_list_work`.
  `svm_range_restore_work` escalated through 11, 19, 35, 67 and 131 reports.
- No GPU reset, ring timeout, GPU page fault, OOM kill, or machine check was
  observed in the controlled test window. The warning pattern nevertheless
  matches the family seen before the earlier machine freeze, so it is treated
  as a safety signal rather than a harmless benchmark result.
- The same warning family occurred on the previous boot. The isolated 4B test
  reproduced it without TTS, llama.cpp, Builder, or another heavy GPU service,
  so simultaneous GENESIS services are not required to trigger the condition.
- ROCm package audit found 225 `amdrocm-*` packages, all version 7.14.1; the
  active HIP/HSA libraries resolve to `/opt/rocm/core-7.14`. The configured old
  ROCm 7.2 Noble repository is not supplying the active runtime packages.
- All heavy GPU services were stopped after the test and remain disabled/inactive.
  No further SVM/KFD warnings appeared while idle.
- Keep the existing mutual-exclusion and 8-second transition guard. Do not run
  Klein 9B, full LoRA benchmark suites, GPU stress tests, or overlapping ROCm
  workloads until the kernel/KFD SVM issue has a verified mitigation.
- Do not change ROCm, AMDGPU, firmware, or kernel merely to experiment. Current
  evidence points toward the kernel AMDGPU/KFD SVM/userptr path under ROCm
  memory activity; it does not establish hardware failure or a definitive root
  cause.
