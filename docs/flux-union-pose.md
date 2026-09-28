# FLUX.1 Union Pro structural pose route

The original InstantX/Shakker `FLUX.1-dev-ControlNet-Union-Pro.safetensors` is stored once in `/mnt/AI-Storage/ComfyUI/models/controlnet`. The default ComfyUI `models/controlnet` path points there. No model copy or `extra_model_paths.yaml` edit is necessary.

This v1 checkpoint uses `control_type: [4]` for pose. ComfyUI's generic **Set Union ControlNet Type → openpose** sets `[0]` for a different Union family and must not be used with this checkpoint. The local custom node **GENESIS FLUX.1 Union Pro v1 Pose (mode 4)** copies the ControlNet and selects `[4]`.

For a general-purpose FLUX.1-dev workflow, connect the Pose Library PNG to `Load Image`, the Union checkpoint to `ControlNetLoader`, then the control net through the GENESIS pose selector to `ControlNetApplyAdvanced`. Feed its conditioning into a compatible FLUX.1-dev sampler. Tune strength and timing against actual outputs; no rendered result has been validated yet.

The editor can extract DWPose keypoints on CPU, adjust or merge multiple people, and export PNG/JSON. A depth preprocessor can be evaluated next for overlapping subjects after the base pose route renders. Keep an unconditioned and pose-only baseline for comparison. Person A/B regional conditioning and identity correction are later stages.

Do not run generation or mark this route production-ready until a controlled AMD/KFD render has passed. Verify checkpoint SHA256 `981a01d6a9575e90820275eda61b33d4ecab0928c68a4f31b132b9687930f90a` (6,603,953,920 bytes) before use.
