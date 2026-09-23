# GENESIS cockpit — repair and UI verification

23 September 2026

## Changes installed

- Generate, progress and result preview now stay in the centre workspace instead of being buried below model settings.
- Compact layouts fit a 1120 × 720 window; normal layouts were inspected at 1440 × 900. Source panels, settings, preset grids and media cards adapt to available space.
- Improved placeholder contrast, keyboard focus borders and long-button tooltips. Replaced disabled Compare/History placeholders with working Canvas/Results navigation.
- Advanced generation forwards all selected LoRA strengths rather than resetting them. Text-to-image creation applies available steps, CFG, sampler, scheduler, denoise and seed controls without replacing graph links.
- Remote upscaling uses the configured RunPod address and its model catalog instead of requiring a local upscaler. Remote final-upscale availability no longer depends on local model files; the remote workflow still validates assets before submission.
- Image and media exports are staged and published only after success. Invalid output extensions are rejected; existing exports and originals survive processing errors. Image-processing outputs use PNG to preserve alpha.
- Batch status reports partial failures. Duplicate removal accepts files only from the current review and handles Trash errors. Result folder opening handles directories with dots correctly.
- Fixed conflicting Qt test applications and isolated navigation tests from the running app's singleton lock.

## Verification

- 164 tests passed; one pre-existing dependency deprecation warning.
- Tests exercise real image resize/transparency, FFmpeg extraction, Canvas transforms/save/load/export, duplicate scans, workflow contracts, assistant/build bridges and regression paths for the repairs above.
- Create, Media Tools, Canvas, AI Assistant, Photos, Cameras, Entertainment, System, Settings, Poses, Workflow, Pose Maker and Face Swap rendered successfully without QML errors.
- Create was visually checked at 1440 × 900 and 1120 × 720; Media Tools and Canvas also inspected.
- Camera Hub and Jellyfin returned HTTP 200.
- Whitespace checks passed.

## Remaining live verification

- RunPod pod `a5yw5n79egqcxy` is stopped, confirmed in its console. Its ComfyUI endpoint returns HTTP 404. Restart price is $0.53/hour; no restart or purchase was performed.
- New real model generation, source-image stages, final upscale and face-swap quality have not been certified by this pass. Earlier connectivity verification completed a simple image job, not a model-generation quality test.
- Local assistant services at ports 8082 and 8083 are stopped. Their live inference remains unverified.
- Background-removal and face-worker files exist; this pass did not execute local GPU workloads or change the recorded GPU safety restrictions. FaceFusion exists at the lowercase local installation path; its live operation was not tested.
- The existing desktop process needs to be reopened to load these code/UI changes. It was left intact to preserve any unsaved work.

Existing uncommitted project changes were preserved. No driver/model installation, Git push, paid pod start or private-key change was performed.
