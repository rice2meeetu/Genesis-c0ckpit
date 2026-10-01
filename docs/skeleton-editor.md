# Built-in skeleton editor — 28 September 2026

Open GENESIS Premium → Pose Library → Edit Skeleton.
This is a native GENESIS editor, not an installation of third-party OpenPose Studio.
The editor runs in the existing application process. Its optional DWPose action uses installed local detector models in a separate CPU-only process; it does not start ComfyUI, contact a remote service or run GPU inference.

## Implemented

- Drag body, hand and imported face keypoints; add/remove people and schematic hands.
- Move an entire person, zoom with the wheel, pan with the middle mouse button, Fit view.
- Import one OpenPose/DWPose JSON frame; body layouts 18 and 25, hands 21, faces 68/70.
- Accept null missing parts, flat/nested triples, and a one-frame ComfyUI list wrapper.
- Convert normalized coordinates to pixels per part, matching the installed controlnet_aux convention.
  Exports mark genesis_coordinate_space=pixels to prevent repeated scaling.
- Ask for source dimensions if missing; preserve unknown JSON metadata.
- Merge people from another JSON, scaling into the current canvas; undo/redo (50 changes).
- Save JSON and skeleton PNG atomically through file dialogs; guard unsaved changes.
- A selected library image can be a tracing overlay. A same-stem JSON sidecar supplies editable joints.
- Explicit **Extract joints (CPU)** runs installed DWPose detector weights in a bounded child process,
  with CPU-only ONNX providers, hidden GPU devices, Cancel and a 90-second limit. It converts
  a photo to editable body/hands/face keypoints. A raster skeleton map may not be detected as a person.

## Verified

CPU-only document/Qt tests cover invalid input, metadata preservation, normalized DWPose data,
merge scaling, mouse dragging, undo/redo, JSON round-trip and PNG export.
The actual Premium QML Edit Skeleton button was activated in an offscreen software-rendered smoke test.
Navigation and operation-routing regression tests: 32 passed.

## Scope remaining

DWPose ran on a neutral bundled photo and extracted two people with 18 body points each.
The Qt editor displayed both skeletons, then saved and reopened their JSON unchanged.
A simple synthetic drawing yielded no detection, as expected for that input.
No generation route was changed, and no models were downloaded.
FLUX conditioning, Depth/regional conditioning, identity engines and AMD rendered benchmarks are not implemented by this change.
RunPod/MUNGBEAN were not contacted or modified. The live and repository Pose Maker copies were not replaced.

## Preservation

Original backend, routing-test and QML edits were backed up under
/home/rice2meetyou/GENESIS-Backups/skeleton-editor-20260928-142034/.
Backend and routing-test hashes remained identical; reversing only the two QML integration edits
reproduced the original QML exactly. No git commit or staging was performed.
