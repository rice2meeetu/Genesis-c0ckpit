# PR #14: local FaceFusion MIGraphX provider validation and safe default

Date: 15 October 2026. All checks used the user's configured **local** NSFW FaceFusion installation; no RunPod credits or services, user media, model weights, or original dirty GENESIS working files were modified.

## Verified deployment

- Active original GENESIS: `<repo>/.runtime/facefusion-nsfw-modern`, with `facefusion.py`, `.venv/bin/python`, and `facefusion.ini` present. That runtime's ONNX Runtime 1.27.1 advertises `MIGraphXExecutionProvider` and `CPUExecutionProvider`; the config requests MIGraphX. Advertised providers are not proof of successful GPU inference.
- GPU kernel fault preflight: clean before and after the test. Local ComfyUI Python process remained stopped (`T`); it was never resumed or restarted.
- Existing benign NASA portrait source and target under `/tmp/genesis-reactor-neutral-20261015` were used only as a nonpersonal processing test. No personal images were used.

## Runtime smoke test and important test-harness correction

- An initial CLI run launched outside the FaceFusion repo; its processor discovery failed, so `--face-swapper-model` was unrecognized. **This was a test-harness mistake**, because GENESIS already supplies `cwd=str(ff_root)` when invoking FaceFusion. Running `headless-run --help` from the correct directory confirmed `--face-swapper-model inswapper_128` is supported. No code change to that argument is required.
- A second outside-directory run progressed to an empty processor model state; this has the same root cause and is not a GENESIS runtime defect.
- Final smoke used the real FaceFusion working directory, installed CLI flags/model, MIGraphX provider, `headless-run`, and temporary jobs/output under `/tmp/genesis-facefusion-migraphx-neutral-20261015`. It reached `Processing step 1 of 1` but **timed out after 150 seconds (exit 124) without writing an image**. There was no demonstrated successful inference. The bounded process exited and no FaceFusion job remained running; the kernel fault preflight remained clean. Thus MIGraphX is **installed and selectable but not yet performance/quality verified** on this RX 9060 XT.

## Corrective release selection

PR #14 previously defaulted to `migraphx`, unlike the user's existing working installation, which explicitly defaulted to `cpu` while allowing GPU opt-in. This change restores `cpu` as the default, and labels MIGraphX as *experimental* in the QML selector. It does not remove GPU support. A controlled live inference/quality/VRAM regression must succeed before changing the default to MIGraphX.

New tests `tests/test_pr14_facefusion_safe_default_20261015.py` verify CPU as the bridge default, explicit MIGraphX selection, provider changes blocked during Busy, unknown provider ignored, and accurate Qt text/selection. All **3 tests passed**. Full isolated Linux suite: **792 passed, 3 skipped, 4 subtests passed**. Offscreen Linux Face Swap page rendered successfully at 1400×900 with a separate temporary Qt runtime to avoid interfering with the user's running app.

## Remaining release checks

Windows CI must rerun on the new head. The original running GENESIS checkout remains unchanged, and PR #14 stays draft/unmerged. Local ComfyUI is stopped and RunPod 8189 is unavailable; neither was modified for this validation.
