# PR #14 follow-up: FaceFusion descendants after launcher exit (15 October 2026)

## Confirmed defect

PR #14 head `c8c978c` introduced a FaceFusion cancellation-aware helper but gated all cleanup on `process.poll() is None`. A wrapper may exit normally while a helper process remains in its new POSIX session and holds the inherited stdout pipe open. `Popen.communicate()` then continues to time out. After an operation Cancel/timeout, `poll()` reports that the parent has exited, so cleanup is skipped and the FaceFusion-owned descendant is left alive. A real isolated Python launcher/helper simulation reproduced `TimeoutExpired`, launcher exit code `0`, and a still-running process group. The test harness explicitly cleaned up that original group.

## Correction

Treat *successful completion of the entire communicating process* (not merely `poll()` of the parent) as the criterion for skipping cleanup. A boolean `completed` becomes true only after `communicate()` returns and cancellation has been checked. On cancellation, timeout or exception, POSIX cleanup sends `SIGTERM` to the unique new session's process group even if the parent already exited, waits for pipes to close, and escalates to group `SIGKILL` if needed. No service names or unrelated process IDs are targeted. For Windows, the existing targeted child-only termination remains; descendant-tree handling on Windows has not been established and should not be claimed as verified.

Python documents that `communicate(timeout=...)` does not terminate a child and that proper cleanup involves termination plus another `communicate()` call: https://docs.python.org/3/library/subprocess.html

## No-GPU verification

- Added two POSIX-only real-process regressions to `tests/test_pr14_facefusion_cancellation_20261015.py`: both timeout and cancellation are exercised **after** a temporary launcher exits while a harmless sleeping descendant holds stdout. Tests assert the child is no longer runnable, and use unconditional test-owned process-group cleanup if an assertion fails.
- Test also handles the normal race in which Linux removes a `/proc/<pid>` file mid-read while the child exits. Four repeated 6-test focused suite runs all passed.
- Full Linux suite at the isolated reviewed worktree: **801 passed, 3 skipped, 4 subtests passed**.
- Linux Qt Face Swap page 1400x900 offscreen smoke passed. No personal media, FaceFusion model weights, ComfyUI or RunPod services were read or modified beyond safe process-state inspection. The user's original checkout and existing in-progress changes remain untouched.

## Release gates

Run Windows CI on the new PR head. Actual live FaceFusion inference and RunPod 8189 still need verification. Keep PR #14 draft and unmerged pending final acceptance. The clean-history tree must not inherit earlier metadata-bearing artwork commits.
