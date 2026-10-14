# PR #14: remaining Busy-state worker launch failures

15 October 2026 — follow-up isolated code review after fixing the generation worker and FaceFusion availability in `42ee007`.

## Confirmed regression

Seven other GENESIS operations set `GenerationBridge._busy=True` and then called `threading.Thread(...).start()` without launch-error recovery: Character reference set, Finishing, Wan image-to-video, manual Person A face swap, local FaceFusion, Inpaint, and Image Edit. If the Python thread fails to start, no worker exists to execute its usual cleanup, so the GUI can remain stuck in Busy mode. This was directly reproduced for FaceFusion, Inpaint, and Image Edit by replacing thread start with an exception (no GPU or network was used): each raised an exception and left `busy=True`.

## Correction

A `GenerationBridge._start_busy_worker` helper starts those already-Busy workers and, if thread construction or `.start()` fails synchronously, reports a concise error and resets Busy. The normal successful launch is not changed. The existing queued Stage 1 generation uses its own exception-safe start logic from `42ee007`; its per-job settings and Stage 3 controls remain unchanged. Face swap retains manual region confirmation, FaceFusion remains local-only, and Wan still requires an eligible remote endpoint.

## Verification

- Eight new offline tests in `tests/test_pr14_other_busy_worker_start_20261015.py` check FaceFusion, Inpaint, Edit, Wan, confirmed-region face swap, Character reference set, helper successful startup, and helper constructor error.
- Entire Linux suite from isolated branch: **782 passed, 3 skipped, 4 subtests passed**.
- 1400 × 900 offscreen Linux Create-page rendered successfully in a unique temporary `XDG_RUNTIME_DIR`, without stopping the live desktop singleton.
- No personal images, model files or private pose pack added to Git; no backend calls or RunPod credits used.

Keep draft PR #14 unmerged pending current-head Windows CI and final release acceptance. The user's original dirty working checkout was not modified.
