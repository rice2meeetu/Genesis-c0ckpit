# PR #14: automatic local FaceFusion Stage 3 routing review

Date: 15 October 2026. Reproduced and fixed from the sanitized PR #14 head `e8484b2` in a separate clean review worktree. User's installed GENESIS/ComfyUI and private files were not modified.

## Confirmed regression

An automatic post-generation Stage 3 request selected `facefusion_nsfw` as the snapshotted identity engine, but `_run_generate()` unconditionally resolved the **ReActor ComfyUI** operation route rather than `_person_a_face_swap_route()`. If local ComfyUI was stopped or the ReActor route was unavailable, the saved generation was followed by `Generation saved · Stage 3 skipped`, without emitting the manual Person A face-confirmation UI. This contradicted the local standalone FaceFusion route which intentionally does not depend on ComfyUI connectivity. Reproduced with synthetic PNGs and a mocked otherwise-successful remote Phr00t generation; the finished image was saved, the FaceFusion route was LOCAL, the simulated ReActor resolver raised `ValueError('Local ComfyUI/ReActor offline')`, and zero Stage 3 selection signals were emitted.

## Fix

Use `_person_a_face_swap_route()` during automatic post-generation Stage 3 preflight, which selects an explicit local-only route for the *snapshotted* `facefusion_nsfw` engine; regular ReActor continues to use its guarded local ComfyUI resolver. The manual two-Person-A-region confirmation still precedes any local swap and no face crop is submitted remotely.

Separately, `_choose_stage_three_faces` previously caught `OSError`/`ValueError` but not the `RuntimeError` emitted by a failed `threading.Thread.start()`, letting a Qt slot exception escape after saving the output. The exception is now reported cleanly; Busy and pending Stage 3 are released in its existing `finally`, leaving both images unchanged.

## Verification

- Added `tests/test_pr14_auto_facefusion_stage3_20261015.py`: three offline tests validate automatic FaceFusion selection despite unavailable ReActor, unchanged ReActor fail-closed behavior, and safe cleanup on Stage 3 thread-start failure with both images preserved.
- Existing Stage 3 and FaceFusion tests alongside new tests: **17 passed**.
- Full Linux suite in the isolated worktree: **795 passed, 3 skipped, 4 subtests passed**.
- Linux Qt Create page offscreen at 1400×900 passed using a temporary runtime directory; no live GENESIS instance or service affected.
- No private pose pack, FaceFusion weights, or user images were staged. The clean-history integration still excludes old metadata-bearing commits.

Keep PR #14 draft and unmerged pending Windows CI for the new commit, wider integration acceptance, and a controlled successful live FaceFusion inference. Provider installation alone does not demonstrate working MIGraphX; earlier neutral GPU attempt timed out after 150 seconds.
