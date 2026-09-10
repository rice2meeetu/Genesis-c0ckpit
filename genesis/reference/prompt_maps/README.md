# GENESIS Grok Klein pose-prompt map

Source preserved from the user-supplied Grok handoff package on 2026-09-10.

Verified audit facts:
- 485 mapped pose IDs.
- 28 unique positive prompt templates.
- 1 source negative prompt reused across the whole map; runtime flags this for review.
- The 486-pose OpenPose package contains one unmapped pose: `lying/768512/lying009`.
- Source LoRA recommendations include `snofs_krea_v1_3D.safetensors` and
  `lenovo_krea2_2.safetensors`; local safetensors metadata identifies both as
  Krea 2, so GENESIS filters them out for regular Klein 9B.
- `FLUX2_KLEIN_UNLOCKED_V1.safetensors` remains blocked until verified.

The JSON source files are intentionally not rewritten. Runtime corrections and
future template-scoped negative overrides live outside the source file.
