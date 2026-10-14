# PR #13 semantic review: pose picker path boundaries

15 October 2026 · local GitHub review branch, not merged.

## Confirmed defect

`qt_cockpit.load_pose_items()` read a user-imported pose index and accepted any existing `library_root / item['path']`, even when that relative path contained `../` or was absolute. Symlinked files could escape too. The shared `genesis.workflow_lab.pose_library_index()` had already been hardened, leaving a mismatch in the Qt picker.

A reproduction with disposable temporary data yielded `ESCAPED_SELECTED True`, i.e. the Qt picker offered a PNG outside its installed pose library. This is an untrusted-path selection issue, not evidence that any real personal file was exposed.

## Fix and verification

- Resolve every candidate image and only expose it if it is inside the resolved library root and exists as a file; this blocks parent traversal, outside absolute paths, missing images, and symlink escapes.
- Preserve bundled controls as the preferred source, but fall back to an existing external Pose Maker installation when the bundled index has no installed controls (e.g. private images intentionally excluded from Git).
- Add `tests/test_pose_picker_root_safety_20261015.py` for boundary checks, bundled preference, and external-library fallback.
- Full isolated Linux suite: **763 passed, 3 skipped, 4 subtests passed**. The change does not touch any existing model weights, personal pose packs, RunPod or live GENESIS processes.

## Publication status

Keep PR #13 draft while the broader semantic/identity/model-family review is incomplete, artwork provenance remains unresolved, historical artwork metadata remains in older public commits, and RunPod 8189 has not been verified live.
