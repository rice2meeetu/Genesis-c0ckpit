# GENESIS Photo Studio Status

## Current Version
GENESIS v0.10 + Cockpit stabilization
Branch: main
Latest checkpoint: 7d4ca55

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
- Cockpit Klein 4B Fast generation live-tested end to end at 512x512: queued,
  completed in 56 seconds, exported, and visually verified without modifying
  the saved workflow
- `/mnt/C` confirmed mounted read/write and the guarded SillyTavern user service
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
- Configure vector/chat memory as a separate backed-up SillyTavern milestone
- Reconcile the older experimental/untracked viewer files without deleting them

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
