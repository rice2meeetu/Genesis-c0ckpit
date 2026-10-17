# Local GENESIS speed verification — 2026-10-14

Host: rice2meetyou-B550M-K (Ubuntu; AMD Radeon RX 9060 XT, 16 GB). ROCm PyTorch: `2.9.1+rocm7.2.1`; ComfyUI: `0.38.0`; backend bound to `127.0.0.1:8188`. GENESIS's RunPod 8189 configuration was not changed.

## Verified live action

The installed `~/.config/systemd/user/genesis-comfyui.service` initially used:
`--reserve-vram 1 --bf16-unet --preview-method none --listen 127.0.0.1 --port 8188`.
Logs confirmed `Using async weight offloading with 2 streams`, contrary to the repository's documented ROCm stability guard.

After checking `/queue` was empty, backed up the installed user unit to:
`~/.config/systemd/user/genesis-comfyui.service.before-speed-audit-20261014-150258`.
Added **only** `--disable-async-offload`, ran `systemd-analyze --user verify`,
reloaded user systemd, and restarted the service. Service remained online
and `/system_stats` reported the RX 9060 XT. Queue was empty.

The exact installed profile is preserved as
`systemd/genesis-comfyui-rx9060xt-warm-cache.service` (an optional sample,
not installed via its filename). The original more conservative versioned
`systemd/genesis-comfyui.service` was not modified.

## Measured output

Neutral SDXL DonutsDeliveryMix workflow on local ComfyUI, PreviewImage, no
identity processing, one output, fixed settings per comparison. A fresh seed
was used for each iteration.

| Workflow | Before disabling async | After disabling async |
| --- | ---: | ---: |
| 512x512, 8 steps, first run | 43.199 s | 12.029 s |
| 512x512, 8 steps, warmed run 2 | 1.505 s | 1.504 s |
| 512x512, 8 steps, warmed run 3 | 1.504 s | 1.504 s |
| 1024x1024, 25 steps, DPM++ SDE/Karras, warm | not identical run | 24.24 s |
| 1024x1024, 25 steps, same settings, repeat | not identical run | 23.55 s |

**Interpretation:** Warm-cache 512 performance was effectively unchanged by
disabling async offload. Do **not** attribute the cold-run difference to this flag;
OS filesystem/ROCm compilation caches and memory state differ. A previous
ComfyUI log showed 94.58 s for 1024x1024/25-step SDXL, but its warm/cold state
was not matched here, so this is not a controlled measured speedup.

The fast 8-step 512 render and 25-step 1024 render are *different quality and
resolution profiles*. No 9B, IP-Adapter, OpenPose, ReActor or RunPod identity
pipeline speedup was established by these benchmarks.

## Why the new optional profile keeps cache enabled

Repository's older safe fallback has `--lowvram --cache-none
--disable-pinned-memory --disable-dynamic-vram --disable-mmap`; its own notes
say that cache-none trades away repeated-node reuse. The active and copied
profile deliberately preserve `--reserve-vram 1` and ComfyUI default
node caching, to retain excellent warmed repeat performance. That is a speed
choice, **not a complete replacement** for the older, more conservative
KFD/SVM mitigation profile. If ROCm stalls/illegal-address errors recur, review
and restore those safety mitigations instead of pursuing speed at any cost.

`scripts/benchmark_local_sdxl_cache.py` contains the non-destructive
repeatability test (three 512x512 PreviewImage generations; it refuses to run
with a nonempty queue). Run from the machine:
`python3 scripts/benchmark_local_sdxl_cache.py some_label`.

## Validation

- 151 targeted non-GPU tests passed on this checkout.
- Both 512x512 before/after series completed successfully.
- Both 1024x1024 warm renders completed successfully.
- Live ComfyUI restarted successfully and accepted queued jobs after the change.
- No ROCm installation, OS kernel, brother's ComfyUI or RunPod changes.
- Existing working-tree edits and historic safe unit preserved.
