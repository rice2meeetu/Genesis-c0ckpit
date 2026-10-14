# GENESIS model-sampling reconciliation — 14 October 2026

## Scope and safety

This change reconciles selected-model sampling defaults, editable Fast/Balanced/Quality step budgets, and Stage 1 model selection. It preserves the previous local worktree, all model files, ComfyUI runtime flags, RunPod configuration, saved reference workflows, Phr00t reference ordering, and identity/LoRA settings. It is **not** a claim that every model has been render-benchmarked or that upstream PR #11 is ready to merge.

## Model profiles (text-to-image)

| Route | Fast | Balanced | Quality | CFG & qualifications |
|---|---:|---:|---:|---|
| Aisha 9B **Standard Base** local | 24 | 36 | 50 | 4.0; undistilled baseline 50; fast tiers provisional. |
| Klein 9B Base Q4 | 24 | 36 | 50 | 4.0; also remove stale hard-coded 4/1 in Create graph builder. Local route remains catalog-gated until verified. |
| Aisha 9B v9.7 **Distilled**, RunPod FP8/BF16 | 4 | 4 | 4 | 1.0; reference graph deliberately uses 5 steps. |
| Klein 9B distilled, RunPod | 4 | 4 | 4 | 1.0; reference graph deliberately uses 5 steps. |
| DarkBeast 9B V2 BFS | 5 | 5 | 5 | 1.0; dedicated source graph 5/1. |
| PornMaster **v3 Base** RunPod | 24 | 36 | 50 | 4.0, without an explicit Turbo adapter. Legacy reference is 5/1 and needs a live render audit before changing. Do NOT confuse with v4 Turbo. |
| PornMaster **v4 Turbo** local | 4 | 8 | 8 | 1.0 Fast; 1.5 Balanced/Quality; edit workflow 4/2. |
| Miraclein 9B | 12 | 12 | 12 | 1.1; preserve model's 12-step workflow. |
| Phr00t v19 | 4 | 6 | 6 | preserve previous per-version sampler, scheduler, CFG and reference behavior. |
| Phr00t v23 | 4 | 4 | 4 | preserve v23 CFG 1.0 previews / CFG 1.2 quality. |
| Qwen Image 2.1 | 20 | 30 | 40 | 1.0; Fast/Balanced are provisional, Quality remains publisher baseline. |
| Conventional SDXL models and SD 1.5 | 12 | 18 | 25 | preserve respective per-model CFG/samplers. |
| Mixture of Perverts Insta DMD | 6 | 8 | 10 | 1.0; LCM/ddim_uniform; author range 6–14. |

Fast/Balanced steps for non-distilled Base, Qwen 2.1 and conventional SDXL are **performance candidates** rather than measured quality-optimal presets. Model-native image dimensions are scaled separately. Phr00t is not overwritten by generic profiles.

## Specific integration issues addressed

- Aisha 9B Base previously showed **50 steps on Fast** because only image dimensions changed. Now 24-step Fast and 36-step Balanced are explicit, with 50 retained as Quality.
- DarkBeast BFS, RunPod Aisha distilled, and RunPod Klein distilled previously inherited Miraclein's 12-step text route; each receives dedicated per-model defaults.
- RunPod `build_create_prompt` previously constructed non-Miraclein models with Miraclein's 12/1.1 KSampler template; it now writes the selected model's defaults. Klein 9B Base no longer hard-codes 4/1.
- Stage 1 picker previously filtered out an otherwise selected model, displaying a stale different name even though the selected model path/card referred to the correct model. The picker now shares the complete `generationModel` ordering. Generation stays gated by readiness.

## Sources and limits

- Official BFL model guidance: https://huggingface.co/black-forest-labs/FLUX.2-klein-base-9B and https://github.com/black-forest-labs/flux2
- DarkBeast V2 BFS model guidance: https://pre.seaart.ai/models/detail/c96419c6d8aabad0c8451da64d0fb03a
- PornMaster base-versus-turbo guidance: https://huggingface.co/ApacheOne/TBA_quants_Klein/blob/main/Flux_2_Klein_9B-base_info.md
- MoP Insta DMD recommended sampling: https://civarchive.com/models/1854124?modelVersionId=2811401

Local unit/UI tests were run with `./.venv/bin/python -m pytest -q tests`, including new route and graph regressions. **RunPod 8189 has no live server/credits for GPU checks**; do not claim those tests passed. A local ComfyUI job was already running during this change; the GUI and backend were deliberately not restarted. **New presets are on disk but become visible only after safely reopening GENESIS**, once the running generation completes.

Repository has substantial unrelated pre-existing uncommitted work. Do not stage every untracked item: backups, private pose assets and RunPod configuration must remain outside PRs. PR #11 stays draft and based on `fix/reactor-identity-restore-20261013`; reconcile the different history before merging to main.
