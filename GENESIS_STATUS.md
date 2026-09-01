# GENESIS Photo Studio Status

## Current Version
GENESIS v0.10 + Cockpit work in progress
Branch: genesis-cockpit
Latest checkpoint: d2e82fd

## Project Root
/home/rice2meetyou/GENESIS-Photo-Studio

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
- Home quick-launch strip added for Media, Local AI, llama.cpp, SillyTavern,
  ComfyUI, and status refresh
- Functional Local AI control page added with real status and launch controls
- Existing Jellyfin Desktop/MPV/ModernZ system integrated without modification
- Existing llama.cpp ROCm, SillyTavern, and ComfyUI installations integrated
  through guarded user services with duplicate-process prevention
- SillyTavern RP/image/expression/TTS/memory readiness is shown explicitly
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
- Live-test one complete Klein generation from the cockpit while ComfyUI is
  running; the working saved workflow itself remains untouched
- Physically verify the updated mouse gestures during real Jellyfin playback
- Clear the Windows NTFS dirty flag in Windows and remount `/mnt/C` read/write,
  then live-test the guarded SillyTavern start button
- Live-test llama.cpp and ComfyUI user-service startup outside the Codex sandbox
- Configure TTS only if the existing AllTalk/Genesis Voice backend becomes
  available; do not install a replacement implicitly
- Configure vector/chat memory as a separate backed-up SillyTavern milestone
- Reconcile the older experimental/untracked viewer files without deleting them
- Visually smoke-test the full cockpit on the host desktop; the Codex sandbox
  cannot attach to display `:0`, but the selected `.venv` has Tk, Pillow, and
  imagehash available

## Working Tree Note

The branch contains substantial pre-existing uncommitted and untracked work.
Do not discard, reset, or bulk-clean it. Back up touched files before changes and
stage only deliberate milestone files.

## Rules

- GENESIS main only
- Do not mix Shinobi
- Do not mix GENESIS Mini
- Do not mix Pose Maker branch
- Use Git commits after major milestones
