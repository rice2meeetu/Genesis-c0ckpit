# Klein 9B-KV profile for RX 9060 XT 16 GB

Validated 2026-09-06 against ComfyUI 0.34.0 on the local AMD Radeon RX
9060 XT using `flux-2-klein-9b-kv-fp8.safetensors`,
`qwen_3_8b_fp8mixed.safetensors`, and `flux2-vae.safetensors`.

## Production defaults

- Architecture: official Flux2 graph, not the legacy AuraFlow/KSampler graph
- Scheduler: `Flux2Scheduler`
- Sampler: Euler through `SamplerCustomAdvanced`
- Steps: 4
- CFG: 1.0
- Latent: `EmptyFlux2LatentImage`
- KV cache: `FluxKVCache`
- Batch: 1
- Default resolution: 1024x1024
- Diagnostic fallback: 512x512
- LoRAs: disabled until explicitly verified as Klein 9B-KV compatible
- ReActor: add only after the base image has decoded successfully

## ComfyUI launch profile

The block below is the historical render-tested profile from 2026-09-06. It is
now superseded for live GENESIS use by the SVM-safe additions shown afterward.

```text
--lowvram --force-fp16 --preview-method none --cache-none
```

Current live safety additions (2026-09-21):

```text
--disable-async-offload --disable-pinned-memory --disable-dynamic-vram --disable-mmap
```

`--disable-mmap` is retained while the RX 9060 XT/gfx1200 mmap/HMM/KFD SVM
issue remains under investigation; do not remove it based on the older benchmark.

`--async-offload` is excluded because this exact ROCm/PyTorch build produced a
repeatable `hipErrorIllegalAddress` during sampler cleanup with it enabled.
`--cache-none` costs some repeated-node performance but prevented the large
retained-memory state seen during the earlier mixed-workflow session.

## Stress results

| Profile | Result | Time | RAM free after | VRAM free after |
| --- | --- | ---: | ---: | ---: |
| 512x512 run 1 | PASS | 85.7 s | 24.28 GB | 16.29 GB |
| 512x512 run 2 | PASS | 74.7 s | 23.13 GB | 16.29 GB |
| 768x768 | PASS | 78.2 s | 23.20 GB | 16.29 GB |
| 1024x1024 | PASS | 81.9 s | 24.09 GB | 16.28 GB |

All four runs completed in one persistent ComfyUI process. The server remained
responsive after the sequence, and all outputs decoded into coherent RGB PNGs.
The machine therefore supports 1024x1024 Klein 9B-KV generation with this
profile. The earlier OOM is attributed to the legacy workflow plus a dirty,
mixed-model memory state, not a general hardware limitation.

Raw measurements and outputs are under `gpu_test_outputs/klein9b-benchmark/`.

## Model distinctions

- Klein 9B-KV is step- and guidance-distilled. Keep it at 4 steps and CFG 1.0.
- Klein 9B Base is a different checkpoint intended for higher-step workflows.
- KV caching accelerates reference-image editing; the checkpoint also supports
  text-to-image generation.
- Negative conditioning is zeroed in the distilled graph. Do not graft a
  legacy negative-prompt KSampler path onto this workflow.
