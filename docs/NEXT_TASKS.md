# GENESIS V3 — Next Tasks

Updated: 2026-09-19

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
