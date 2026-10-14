# GENESIS main integration review — October 2026

This draft combines the post-PR10 `main` history with the model/identity/Phr00t review branch (`review/model-sampling-20261014`, which contains PRs #11 and #12). It is an **integration candidate, not a verified production release**. The merge initially had 34 overlapping paths. It was assembled in an isolated worktree and repaired against tests. Do not fast-forward/merge without review.

## Verified without GPU load

- Combined Linux Python/Qt tests: **745 passed, 3 skipped, 4 subtests passed** on the full local prototype, in both the isolated working prototype and a **fresh clean checkout** with no imported pose-library images.
- The merged Qt Create interface, model selection, Phr00t source/reference controls and queue tests passed offscreen.
- Fixes include duplicated QML `generateButton` ID and pytest configuration keys, undefined locals in FaceFusion, model/finishing GPU safety gates, local Qwen Image 2.1 route reconciliation, invalid RunPod endpoint port handling and fail-open SSH startup.
- The existing distinct sampling presets and Phr00t speed work remain in the integrated code.

## Asset handling

- **Do not publish imported pose packs without explicit ownership/licensing review**. The 487 added skeleton images under `genesis/reference/assets/pose_library/` were excluded from this integration candidate; local copies were not modified. The separate `NSFW_100Lewd_v20` imported pack was never staged. A `.gitignore` rule prevents accidentally staging local pose-library files.
- The checked-in pose metadata may reference files available only on an owner's machine. Pose-library readers now filter out missing/uninstalled files before offering selectable skeletons; `tests/test_pose_index_availability_20261014.py` covers missing and traversal paths.
- Nine pre-existing UI graphic assets from the published development branch remain included to preserve visual navigation. Confirm their provenance before final main merge.

## Outstanding before main release

1. Manually review overlapping backend/UI/identity/pose source changes; conflict preference in the draft merge is not proof of semantic correctness.
2. Run platform CI and Windows packaging checks; the fresh clean-checkout Linux suite passes but does not validate Windows packaging.
3. GPU render/quality verification of provisional model Fast/Balanced step counts and identity/pose fidelity; RunPod 8189 is unverified while endpoint/credits are unavailable.
4. Keep PRs #11 and #12 and the local working checkout unchanged until integration is approved; do not assume draft PRs are merged merely because this branch exists.
