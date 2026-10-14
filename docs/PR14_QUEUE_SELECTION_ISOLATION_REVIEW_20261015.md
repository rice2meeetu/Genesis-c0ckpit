# PR #14 queue-state code review follow-up — 15 October 2026

Source: GitHub code review #5524183546. This patch was assembled in an isolated Git worktree, leaving the original desktop GENESIS checkout, ComfyUI backend, model weights, personal images, and RunPod unchanged.

## Confirmed defects

A queued job previously copied its saved Stage 2, FaceID, output size, reference budget and extra reference URL to shared GenerationBridge fields and left them there. The next manual generation could then run with controls different from those still shown in the Qt UI.

A job queued with **no selected character** also carried a `None` character snapshot, previously interpreted as an absence of an override. The worker could therefore read a later-selected character. The queued-route fallback similarly needed an explicit queue-active condition.

During remediation, additional regression checks found two failure paths: FaceID bridge fields were not initialized in the constructor, and rejected `queueGenerateAdvanced` requests could leave a stale `_next_generation_controls` object available to later callers.

## Fix

- Define FaceID defaults in the bridge constructor.
- Copy current UI-owned settings immediately before queue dispatch; apply that job's saved settings only while `queueGenerateAdvanced` synchronously captures them; restore UI-owned settings, route and character overrides in `finally`, even when preparation fails.
- Determine whether queued overrides are active from `_queue_active`, rather than checking whether a character object is non-null. A deliberately empty queue-time character selection therefore stays empty.
- Do not strand pending jobs on unexpected synchronous launch exceptions. Preserve an already-running worker if one exists.
- Clear `_next_generation_controls` on rejected/aborted requests, but do not destroy the controls dict passed to a successfully launched asynchronous worker.
- Preserve the previously verified Stage 3 engine snapshot and its asynchronous busy-transition cleanup.

## Tests

`tests/test_pr14_queued_selection_isolation_20261015.py` covers: captured queued-job settings vs later UI-owned selections; no-character queue snapshots; a later manual generation selecting the current FaceID/output/extra-reference/character settings; invalid source rejection without stale controls; and launch exceptions without stuck queue state. Existing Mirage/Miraclein and Qwen Image 2.1 tests now inspect the controls during synchronous dispatch instead of relying on leaked post-return state.

- Focused queue/reference suite: **54 passed**.
- Broader Qwen/Miraclein/queue focused validation: **34 passed**.
- Full isolated Linux suite: **768 passed, 3 skipped, 4 subtests passed**.
- Linux Qt Create page offscreen screenshot: **pass** at 1400×900.

## Release

Windows CI on the new PR #14 head is still required after commit. Keep the PR in draft: RunPod 8189 live validation remains unavailable, and this patch has not been installed into the user's active GENESIS checkout. Do not merge PR #13 and PR #14 both. The clean-history branch must not inherit metadata-bearing old review commits.
