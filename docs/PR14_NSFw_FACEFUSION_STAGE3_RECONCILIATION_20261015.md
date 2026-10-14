# GENESIS PR #14 — installed NSFW FaceFusion Stage 3 reconciliation

Review date: 15 October 2026. Addresses confirmed original-installation regression in [PR #14 code review #5525602117](https://github.com/rice2meeetu/Genesis-c0ckpit/pull/14#pullrequestreview-5525602117).

## Verified original installation

The user's uncommitted original GENESIS checkout has a working file layout beneath `.runtime/facefusion-nsfw-modern`: `facefusion.py`, `facefusion.ini`, and a local `.venv/bin/python` exist. The installed ONNX runtime declares MIGraphX and CPU providers, and the installed config requests MIGraphX. This does **not** verify a successful live GPU inference. The active original GENESIS app lists NSFW FaceFusion as a fourth Stage 3 identity engine and processes only two manually reviewed Person A face crops locally. PR #14 originally omitted both the exact runtime location and this Stage 3 choice, risking feature loss at merge.

## Changes in the isolated integration candidate

- Discover the exact `.runtime/facefusion-nsfw-modern` installation, with **no silent fallback to older SFW FaceFusion directories**. The runtime remains local and **is not committed** to Git.
- Restore the QML Stage 3 choice `NSFW FaceFusion · Local`, readiness gating, backend whitelist, and finishing availability based on installed FaceFusion rather than online ComfyUI/ReActor nodes.
- Route this engine via explicit `Route('LOCAL', '')`, including when the source generation was RunPod or local ComfyUI is offline. The **ComfyUI connection is never invoked** for the standalone FaceFusion Stage 3 step.
- Preserve manual confirmation of **both** target and source Person A regions and the SHA/pixel checks in the existing Face Region picker. Send only corresponding private local face crops to the standalone command, composite the returned crop into the selected target region, and preserve the original files, other faces and scene background. The queued `_active_stage_three_engine` snapshot wins over a later UI engine selection.
- Preserve PR #14's separate ReActor workflows, queue-state isolation, local-only safety gates, and the generation route's finishing context.

## Validation

- No-GPU tests `tests/test_pr14_nsfw_facefusion_reconcile_20261015.py`: strict root; QML option and readiness; no-Comfy local route; offline finishing availability; successful CPU/MIGraphX command selection with local crop-only compositing, pinned Stage 3 engine and immutable original photos; failed subprocess output not composited; Stage 3 dual manual face confirmation and local-only handoff. All **7 tests passed**.
- 32 focused Stage 3/queue/identity tests passed.
- Entire isolated Linux suite: **789 passed, 3 skipped, 4 subtests passed**.
- Linux Create page Qt offscreen screenshot at 1400×900 passed using a separate temp `XDG_RUNTIME_DIR`. The user's running GENESIS app and original dirty checkout (36 tracked modifications, 83 untracked files) remained untouched.
- Zero private pose PNGs or FaceFusion executables/weights were added to the code branch. The previously published artwork-metadata commits remain outside its ancestry.

## Remaining release checks

Windows packaging CI needs to rerun on the reconciled commit. RunPod 8189 remains unavailable, local ComfyUI 8188 has a stopped (`T`) process, and the isolated tests do not constitute a live FaceFusion GPU-quality benchmark. The GPU provider must be confirmed by a controlled nonpersonal live test before asserting successful MIGraphX inference.

Keep PR #14 **draft and unmerged** until release acceptance. Do not merge overlapping older PRs or reset the user's existing local worktree.
