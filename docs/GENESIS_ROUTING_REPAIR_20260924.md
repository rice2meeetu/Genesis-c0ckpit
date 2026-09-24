# GENESIS routing repair and safe verification — 2026-09-24

## Result
186 automated tests passed. All 13 page destinations passed an isolated offscreen navigation check. This is not certification that every button or live integration works.

## Repairs
- ReActor, Edit and Inpaint capture the selected Local/RunPod destination when queued, including its endpoint. Changing the selector cannot redirect an already queued worker.
- Media AI upscale and batch upscale use the same routing context rather than a stale environment endpoint. Standard Resize remains a CPU operation; requested AI upscale does not silently fall back to CPU.
- Operations require an already-ready backend. AUTO prefers safe local, then ready remote; it does not start services or retry a failed operation elsewhere.
- Local upscaling respects the GPU safety guard before connection/submission and while waiting. Remote work does not use the local GPU guard.
- FaceFusion is explicitly labelled local image-only and refuses AUTO/RunPod, preventing an unexpected local launch. RunPod FaceFusion/video support is not implemented.
- Edit/Inpaint/reference graphs validate required components before submission. Edit uses the shared guarded save path, preserves its one-hour timeout, and creates a missing output directory.
- Navigation tests use empty preset fixtures rather than reading user payloads.

## Evidence
Implementation: genesis/backend_bridge.py (resolve_operation); qt_cockpit.py (validate_operation_prompt, queueFaceSwap, queueEdit, queueInpaint, _run_routed_operation, _submit_and_save); genesis/media_bridge.py (_start_upscale); genesis/media_functions.py (upscale_enhance); qt_cockpit_linux_premium.py (router wiring); genesis/qt_ui/MainPremiumLinux.qml (accurate labels).

Regression coverage: tests/test_operation_routing.py and tests/test_premium_navigation.py. Full safe suite: 186 passed in 3.02 seconds using system Python, offscreen Qt, isolated temporary settings/cache/output and no pytest cache. Command: python3 -m pytest tests --ignore=tests/test_pose_prompt_profiles.py -p no:cacheprovider --basetemp=/tmp/genesis-final-safe-tests -q (with isolated Qt/settings environment).

Six tests in test_pose_prompt_profiles.py were deliberately excluded because they load real preset payloads. No preset content was examined or altered in this repair.

Separate navigation harness: /tmp/genesis-audit-20260924/navigation_check.py. Network connections and subprocess launches were blocked, runtime state stubbed offline and presets empty. It verified the selected page and exactly one visible stack child for Create, Poses, Workflow, Media, Photos, Cameras, Entertainment, System, Edit, Pose Maker, Settings, AI and Face Swap. Entertainment remains an intentionally retired empty slot. This checks page routing, not each control's complete live behavior.

## Remaining uncertainties / unfinished features
- No real local or RunPod generation, three-stage output quality, AI upscale, face inference, camera playback, Jellyfin playback or assistant reply was tested.
- Premium Canvas still does not expose the repaired backend Edit/Inpaint operations as new controls. No UI redesign was performed.
- Independent remembered generation settings for each backend mode are not established by these tests.
- Workflow and Settings pages include launchers rather than complete integrated editors; Pose Maker remains a separate workbench.
- Existing Pose source/reference/stage semantics were not changed or guessed.
- A ready backend does not guarantee every operation's models are installed. Actual workflow checks can reject missing components; there is no cross-backend retry.

No paid services were started, dependencies installed, jobs interrupted or photo-library files modified. Changes are a local checkpoint, not a GitHub deployment.

## Follow-up: desktop shortcut and live health checks

Created executable ~/Desktop/GENESIS-Cockpit.desktop, backed by desktop/GENESIS-Cockpit.desktop, targeting this checkout and Create page. desktop-file-validate passed; launcher/application/icon exist. Existing Image Studio and RunPod shortcuts are unchanged. Desktop trust/interactive launch was not confirmed.

Read-only localhost HTTP checks: Jellyfin /System/Info/Public and camera service /api returned HTTP 200. ComfyUI :8188, assistant :8083, FaceFusion :7860 and LM Studio :1234 refused connections. These results establish endpoint reachability only, not playback or inference. Initial sandbox-denied probes were repeated with approved access; no services started or jobs submitted.
