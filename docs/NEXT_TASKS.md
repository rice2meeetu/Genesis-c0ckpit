# GENESIS V3 — Next Tasks

Updated: 2026-09-20

## Completed 2026-09-20 — capability-aware LoRA stack controls

- Image Generation now exposes up to three ordered LoRA slots for regular Klein 9B Base, each with an independent 0.00–1.00 strength.
- Klein 4B remains isolated to one experimental LoRA; Klein 9B-KV and Phr00t/Qwen expose no LoRA slots because those routes are not validated.
- Duplicate selections and invalid strengths fail closed. Existing Phr00t/Qwen, SDXL/OpenPoseXL2, and staged workflow routes were not changed.
- Verification: 95 pytest tests passed; Python compile passed; premium QML offscreen startup remained alive for five seconds with no QML error output.
- Files changed: `genesis/qt_ui/MainPremiumLinux.qml`, `qt_cockpit.py`, `genesis/generation_pipeline.py`, and `tests/test_qt_generation_profiles.py`.
- Best next action: run isolated controlled renders for each newly exposed experimental LoRA and each proposed stack before promoting any combination to render-tested.

## Follow-up — legacy Generate compatibility

- Restored the original 12-argument QML Generate overload alongside the new
  16-argument overload. The existing Main.qml pose buttons retain their source,
  pose, stage switches, and original model-specific strength defaults.
- Added regression tests for forwarding and both exported Qt signatures.
- Verification: 97 tests passed. No GPU render was submitted for this fix.
- Changed: qt_cockpit.py and tests/test_qt_generation_profiles.py.
- Next: exercise both QML calls with a mocked submitter, then run an isolated
  non-explicit baseline render. Preserve current ComfyUI flags and saved graphs.

## Immediate takeover sequence

1. Recheck live mounts, especially `/run/media/rice2meetyou/Ai/AI-Models`, and reconcile the 2026-09-19 audit with current storage state.
2. Recheck ComfyUI service/API and live node inventory without changing the working ROCm stack.
3. Produce a rescanable canonical model/LoRA/workflow inventory. Use stable relative IDs plus file existence, family, metadata/hash/source where available, and separate installed/compatible/render-tested states.
4. Finish model -> compatible LoRA selector behavior. Support ordered LoRA slots and individual strengths in the UI/backend, while keeping unsafe/unverified combinations clearly experimental or blocked.
5. Make preset/pose application a complete generation bundle where data exists: compatible family/model, workflow ID, prompt/negative prompt, optional reference, LoRA IDs/weights, sampler/scheduler/steps/CFG/resolution. Preserve user overrides intentionally.
6. Verify source/reference routing per family. Do not pretend text-to-image and image-edit graphs are interchangeable.
7. Run controlled neutral benchmarks after inventory/routing is correct: fixed prompt/source/seed, batch 1, 512 then 768, cold/warm timing, VRAM/RAM/errors and output inspection. Preserve benchmark reports.
8. Only after functional verification, continue premium UI polish.

## Media/Canvas backlog

Media hardening still needs atomic output writes, extension validation, cancellation, codec/container fallback and explicit AI-vs-standard resize behavior.
Canvas still needs real cutout/layer manipulation, transforms, undo/redo and export.

## Handoff requirement

Before stopping work, update this file with:
- completed items;
- exact files changed;
- tests/renders actually run and results;
- new blockers;
- the single best next command/action.

Also update `docs/CURRENT_STATE.md` if machine, model inventory, architecture, tests, or verified behavior changed.
