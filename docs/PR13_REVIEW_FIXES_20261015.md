# PR #13 follow-up: confirmed review defects (15 October 2026)

Four reproduced defects from GitHub review #5522485587 are addressed here without changing or restarting the user's local GENESIS installation, the ComfyUI service, the RunPod pod, or any model weights.

1. **Local-only face swaps:** `BackendBridge.resolve_operation('face_swap')` now selects only a ready, safe local ComfyUI, regardless of `AUTO`, `LOCAL`, or `RUNPOD` mode. Both manual ReActor and Stage 3 Person A correction are pinned to a local route; the low-level worker rejects remote routes before preparing or uploading face crops. Remote-generation output remains saved if local ReActor is unavailable; the user sees a Stage 3 skip/error rather than an unapproved fallback to RunPod.
2. **Queued engine snapshots:** the selected Inswapper/ReSwapper/HyperSwap engine is saved in each queued job, installed in a job-specific active setting, and used when its Person A crop correction runs. The user's current UI choice is not overwritten by queue dispatch. Engine changes while a generation is running are blocked, and the active engine is cleared after the job finishes.
3. **Replacing approved references:** a different replacement image receives `reference_approved=False`; the old image's approval is not transferred. Categories and gallery role can be preserved. Changing the master identity reference requires explicit `confirm_master=True` (not exposed in the ordinary gallery picker).
4. **Adding references:** new references default to unapproved even when a category is omitted. Explicitly reviewed references can still be approved. Existing legacy references without metadata retain their historic behavior and are not silently rewritten.

## Verification

- Full isolated Linux suite: **756 passed, 3 skipped, 4 subtests passed** (`PYTHONPATH=$PWD .venv/bin/python -m pytest -q tests`, using the user's preexisting GENESIS venv).
- Dedicated regression tests in `tests/test_pr13_review_fixes_20261015.py`; existing operation routing, image finishing, character-library, and Stage 3 tests updated for the explicit local-only and approval requirements.
- Read-only `/object_info` on local ComfyUI port 8188 advertised `ReActorFaceSwapOpt`, `ReActorOptions`, `LoadImage`, `SaveImage`, and Inswapper/ReSwapper/HyperSwap choices. This is node-discovery evidence, not proof of GPU swap performance or model weight integrity.
- **Outstanding:** Windows CI on this new PR head, real local ReActor GPU swap quality/composition test, cross-platform GUI interaction, and the existing broader PR #13 merge/artwork review. Keep PR in draft; do not merge based on test results alone.
