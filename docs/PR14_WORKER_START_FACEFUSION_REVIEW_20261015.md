# GENESIS PR #14 follow-up: worker startup and FaceFusion installation readiness

15 October 2026 · Review #5524500688 · changes prepared and verified in an isolated review checkout.

## Confirmed issues

1. `queueGenerate` set `busy=True` before `Thread.start()`. If Python refused the worker thread, no worker existed to clear the flag, and `_dispatch_next_generation` exited while `busy` and `_queue_active` were both true. This left Generate disabled and queued jobs stalled.
2. `faceFusionAvailable` was declared twice. The later definition only recognized a Miniforge Python interpreter, masking otherwise valid FaceFusion `.venv/bin/python` installations. `queueFaceFusion` already supported both paths, so the UI's disabled "NOT INSTALLED" state was wrong in the `.venv` layout.

## Correction

- Wrap the generation worker's construction/start in an exception handler that clears Busy and progress on synchronous launch failure, resets the manually selected active Stage 3 engine (without overwriting an active queued snapshot), and records a meaningful status. The queued dispatcher can then advance to the next saved job normally.
- Remove the duplicate FaceFusion property and centralize Python interpreter choice in `_facefusion_python()`, used by both `faceFusionAvailable` and `queueFaceFusion`.

## Offline regression verification

`tests/test_pr14_worker_start_facefusion_20261015.py` contains six tests: manual retry after failed startup, advancing queued jobs after a failed startup, failing all queued starts without leaving Busy, matching FaceFusion `.venv` and Miniforge readiness/launch paths, and rejecting missing FaceFusion installations. All use temporary files and fake threads, **no GPU jobs or personal images**.

- Six new regressions passed.
- Complete Linux suite: **774 passed, 3 skipped, 4 subtests passed**.
- Offscreen Qt Create screen: **1400 × 900 screenshot passed**, using a distinct `XDG_RUNTIME_DIR` so the user's running singleton application remained untouched.
- Git tree does not include imported private pose PNGs. The original live GENESIS checkout, services, RunPod settings and model assets remain unchanged.

## Remaining gates

Windows CI on the new PR #14 head must pass. Other outstanding release matters include final integrated UI/feature acceptance and RunPod 8189 verification when service is available. PR #14 stays **draft and unmerged**; old metadata-bearing development commits are not brought into the clean-history candidate.
