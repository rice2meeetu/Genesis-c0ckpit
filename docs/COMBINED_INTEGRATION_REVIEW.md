# Combined routing, pose, identity, and SDXL candidate

This isolated candidate integrates the reviewed heads of PR #7 (`e792d1c`), #8
(`f6e5ad8`), and #9 (`5cabe4a`). It has not been applied to the dirty live checkout.

## Conflict decisions

- Use the #8 remote ownership rule: GENESIS uses remote 8189 / local tunnel 18189;
  remote 8188 endpoints are rejected. Local ComfyUI's own 8188 endpoint is unchanged.
- Keep #8's explicit Connect behavior. Saved endpoints and legacy autoconnect
  settings do not authorize background RunPod polling at startup.
- Keep #8's newer pose/identity separation, model-specific settings, SDXL graphs,
  live identity-engine availability, source-pack metadata, and independent finishing.
- Preserve #7's unique imported assets, FLUX.1 discovery metadata, catalog/stage
  role fixes, Qwen 2.1 and local route tests. Do not replace the current premium
  shell's artwork and layout with #7's older cosmetic variants. The assets are
  retained even where not currently displayed.
- Restore the legacy Aisha face-swap graph rather than overwriting it with #7's
  T2I-only graph. #8's separate `GENESIS_AISHA_9B_T2I.json` supplies the T2I route.
- Keep #8's native v19 image mapping. The incoming generic v23 pose insertion
  must not run on v19, where it consumes the secondary image before native mapping.
- De-duplicate the Qwen 2.1 and v23 Q2 model-registry entries introduced by the
  automatic merge. Do not resolve these conflicts by replacing entire routing
  implementations with the older branch.

## Corrections after integration

The preset UI now calls the existing ModuleBridge method, rather than a missing
method on GenerationBridge. Offline profile selection uses an explicit
`profileSelectable` flag while `selectable` / `routeReady` continue to govern
execution. Arbitrary unavailable rows cannot enter the Create selector merely
because they carry a configured-stage flag.

One local allowlist now governs profile readiness, route resolution, queueing,
generation workers, and model-based refinement. Installed 9B and Qwen 2.1 BF16
assets remain discoverable but cannot execute locally without runtime evidence.
The existing 4B, Phr00t Q4/Q2, and Donuts SDXL routes still require a ready route
and the kernel fault guard. This does not alter model weights or claim every
large model is safe on the local 16 GB AMD GPU.

Blocked/stale remote endpoints return an offline status at UI startup without
contacting 8188 or silently using the local backend. Optional SSH tunnel failure
no longer prevents the cockpit from opening to let the user repair settings.

Tests now mock the active custom file picker, isolate settings/cache locations,
use deterministic checked-in schemas, and use the protected 8189 role. Default
pytest discovery is restricted to the automated `tests/` suite instead of legacy
root-level interactive scripts. The absent external Pose Maker consumer is
reported as a skip, not counted as verified.

## Remaining verification

The broad isolated routing/pose/SDXL suite passed 466 tests with one external
Pose Maker skip. Python compilation, shell syntax, and whitespace checks passed.
No live GPU generation, SSH tunnel, RunPod changes, or external Pose Maker
execution was performed. Windows remains a separate candidate pending actual
Windows startup/package verification. Do not treat these automated results as
proof of untested external runtime behavior.
