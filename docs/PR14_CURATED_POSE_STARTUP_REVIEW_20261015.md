# PR #14 semantic review: Curated 18 skeleton pairing

Date: 15 October 2026. Review-only branch; original GENESIS checkout, RunPod, local ComfyUI and model files unchanged.

## Confirmed fault

The Qt application built `curatedPosePresets` with `load_curated_pose_presets()` **without the installed pose rows**, so the Curated 18 collection could not bind declared skeletons even if the index contained them. The loader also resolved declarations only beneath the bundled library root, while installed private pose files are commonly located in `~/AI/GENESIS_POSE_MAKER/assets/pose_library` (or a historical Downloads import). A synthetic exact-match test returned `requiresPoseSelection=True` despite an indexed installed skeleton.

This does **not** change the Full 70 collection: those prompts remain text presets requiring an explicitly selected skeleton. Linking a Full 70 entry to an arbitrary similar-named image would be incorrect.

## Corrective change

- Load the complete, verified pose index once in the Linux Qt launcher; keep the visible twelve-item initial picker unchanged, but pass the full index into both Curated 18 pairing and linked-pose entries.
- Resolve Curated 18 declarations against the bundled library and both recognized legacy external Pose Maker roots. Pair only exact relative paths inside those roots and only if the resolved path belongs to the already-indexed, installed set. Do not guess filenames or silently use missing assets.
- Add `tests/test_curated_external_startup_20261015.py` to cover external positive matches, a path escape decoy, missing/unindexed controls and the startup wiring.

## Verification

- Synthetic reproduction before patch: both the ordinary startup call and an explicit externally indexed pose returned `requiresPoseSelection=True` without the linked image.
- User host, read-only, after patch: 486 installed indexed pose entries; all **18 Curated 18** presets resolved exact declared installed files. The first twelve visible entries were unchanged.
- 14 focused tests passed, 2 optional import tests skipped. Full Linux suite: **765 passed, 3 skipped, 4 subtests passed**.
- Offscreen Linux Poses page rendered 1400×900 successfully. No GPU generation or RunPod connection.

## Release status

This is a follow-up fix directly on top of PR #14's sanitized main-based integration commit. No older metadata-bearing PR #13 history was merged or rewritten. PR #14 stays draft pending Windows CI on the new head, final semantic review and RunPod 8189 checks when available. The earlier public Git history remains accessible on separate branches.
