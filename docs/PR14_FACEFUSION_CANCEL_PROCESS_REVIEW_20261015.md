# PR #14: cancellable local FaceFusion processes — 15 October 2026

## Confirmed pre-fix behavior

- `cancelGeneration` set the bridge cancellation flag, but local standalone FaceFusion ran using a blocking `subprocess.run(timeout=1800)`, and standalone `_run_facefusion` did **not** check the flag before adopting its result. A synthetic cancellation inside a successful subprocess returned with **Cancel requested=True, FaceFusion complete, adopted=True, finishing record=True**. Thus clicking Cancel did not stop the process or prevent the late result from being recorded.
- The crop-only NSFW FaceFusion Stage 3 subprocess likewise used blocking `subprocess.run(timeout=300)`. It eventually checked cancellation before compositing, but Cancel could not stop the subprocess promptly, leaving GENESIS Busy for up to five minutes.
- The standalone MIGraphX preflight also used a blocking subprocess with a 300-second timeout. Provider choice remains CPU by default and GPU is opt-in.

## Fix

The bridge now has a narrowly scoped `_run_local_facefusion_command` helper which starts only the specified **local** FaceFusion executable, polls child output and bridge cancellation every ~250ms, and terminates the newly created **process session** on POSIX (or that process on Windows) if Cancel or timeout occurs. After a grace period it forcibly kills only the launched session/process, never ComfyUI, RunPod or another process identified merely by name. The helper raises cancellation/timeout, returning a `CompletedProcess` only for a finished job. Both standalone and Stage 3 FaceFusion use the helper, as does the experimental GPU preflight. Additional checks prevent adopting or compositing an output after cancellation.

The manual Face Swap and standalone FaceFusion start paths reset stale cancellation flags before starting a *new* job. The worker clears cancellation and Busy when finished, and distinguishes user cancellation from a genuine runtime failure. Verified source and target inputs are preserved.

## Verification (synthetic, no model weights or personal media)

- `tests/test_pr14_facefusion_cancellation_20261015.py` adds four tests:
  - Cancel during manual FaceFusion just before a mocked subprocess returns a late output: never adopts or records it; source/target unchanged.
  - Cancel during crop-only Stage 3: never composites a late output or changes original images.
  - A **real temporary sleeping Python subprocess** is terminated promptly after Cancel; exact spawned process exited and did not leave a running child.
  - Timeout terminates and reaps exactly its own temporary child.
- Legacy tests that mocked `subprocess.run` now mock the job-scoped helper instead; expectations for success/failure, selected provider, local crop-only flow and finishing context remain the same.
- Focused regression suite: **40 passed**. Full isolated Linux suite: **799 passed, 3 skipped, 4 subtests passed**.
- Linux offscreen Face Swap page screenshot: **1400 × 900 passed** using a distinct temporary `XDG_RUNTIME_DIR` so the original desktop session stayed untouched.

## Release considerations

This patch does not demonstrate real FaceFusion GPU quality or inference success. The prior neutral-image MIGraphX run timed out after 150 seconds, so CPU remains the default and MIGraphX remains labelled experimental. FaceFusion documents both `headless-run` and CPU/MIGraphX execution providers (https://docs.facefusion.io/usage/cli-commands/general and https://docs.facefusion.io/usage/cli-arguments/execution). This fix is in GENESIS process management, not the FaceFusion model/provider setup.

Do **not** merge PR #14 until Windows CI on its new head and human release acceptance. No original live GENESIS file, model weight, FaceFusion runtime, private media or pod instance was changed for these tests. The clean-history branch must not inherit unsanitized image-metadata commits.
