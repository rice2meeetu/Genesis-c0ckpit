# Runtime Flags Verification

> **2026-09-22 GPU hardening update:** References below to `--n-gpu-layers 99` describe the pre-hardening configuration observed during the incident investigation. Forced 99-layer GPU offload was removed from the deployed Builder, Assistant, and Qwen services, and from the repository Assistant/Qwen unit definitions after repeated ROCm VRAM allocation failures were correlated with KFD/SVM instability. Builder now has a permanent 30-second restart backoff; the other heavy GPU services also resolve to 30-second backoffs. No GPU workload was started as part of this change, and post-change static safety tests passed.

# CPU/GPU runtime checkpoint — 2026-09-20

> **Safety addendum — 2026-09-21:** the current RX 9060 XT profile additionally
> disables pinned memory, dynamic VRAM and safetensors mmap. Live ComfyUI now
> includes `--disable-pinned-memory --disable-dynamic-vram --disable-mmap` and
> remains on-demand/inactive while idle. This supersedes the launch line below
> for current operation; the 2026-09-20 text is retained as historical evidence.

Scope: general runtime stability only. No preset, LoRA, image workflow, driver,
CPU clock, voltage, thread-count or power-limit changes.

## Live machine inspection

- Host: rice2meetyou-B550M-K.
- CPU: AMD Ryzen 5 5600GT, 6 physical cores / 12 logical CPUs.
- GPU: Radeon RX 9060 XT, 17,095,983,104 bytes VRAM reported by sysfs.
- RAM: 30 GiB usable reported by `free`; roughly 23 GiB available at inspection.
- ComfyUI service was inactive and port 8188 refused connections.
- First VRAM snapshot: 16,485,900,288 bytes used, approximately 96% of total.
- Port 8080: Qwen3-Coder-30B-A3B-Instruct-UD-Q3_K_XL under
  `genesis-builder.service`, with `--ctx-size 16384 --n-gpu-layers 99`.
- Port 8082: the same model under `genesis-qwen.service`, with
  `--ctx-size 8192 --n-gpu-layers 99`. Its logs repeatedly report a failed
  12,994.11 MiB device allocation and out-of-memory errors. Systemd's restart
  counter was 17,584 at one snapshot and continued increasing.

These are timestamped observations, not permanent inventory assertions.

## Change made

Preserve the saved four-flag memory profile and explicitly disable async offload:

```text
--lowvram --force-fp16 --preview-method none --cache-none --disable-async-offload
```

The earlier RX 9060 XT benchmark report records repeatable
`hipErrorIllegalAddress` failures with async offloading enabled. The installed
ComfyUI parser explicitly supports `--disable-async-offload`.

The repository service and installed user service received only this flag.
Existing installed `Conflicts` directives were preserved. The original unit is
backed up at
`/home/rice2meetyou/.config/systemd/user/genesis-comfyui.service.preflags.Q7zeX8`.
User systemd configuration was reloaded; no service was started or stopped.

## Verification

- Four runtime-profile regression tests passed locally and on the target PC.
- Target PC full suite: **93 passed**, one existing dependency warning.
- Installed ComfyUI argument parser accepted the complete launch command
  without importing models or running GPU inference.
- Repository and installed units passed `systemd-analyze --user verify` (exit 0).
  It also reported existing warnings in unrelated remote-control/spice units;
  those files were not modified.
- `systemctl --user show` confirmed the installed command includes
  `--disable-async-offload`; ComfyUI remained inactive with MainPID 0.
- `git diff --check` passed.

## Not verified / next action

No GPU render, peak-VRAM test, image-quality comparison, or complete staged
pipeline was run. These flags cannot free memory held by other processes and
do not guarantee freedom from OOM. CPU thread defaults remain unchanged.

Request permission before stopping the failing duplicate `genesis-qwen`
service or temporarily pausing `genesis-builder`. Then recheck GPU memory,
start ComfyUI deliberately, and run a small neutral workload before any
larger or multi-stage memory test. Do not enable async offloading casually.

The unfinished UI/preset commit `3476323` was not installed, tested or included
in this checkpoint. Other pre-existing service edits and artwork were preserved.
