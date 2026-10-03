# GENESIS c0ckpit — Windows

This branch adds a Windows launcher for the existing premium GENESIS desktop UI without changing the Linux launcher.

## Quick start

1. Install 64-bit Python 3.12 on Windows and enable `py`/Python on PATH.
2. Clone or download this repository.
3. Double-click `launch-windows.bat`.
4. The launcher creates `.venv`, installs the Windows runtime packages, and starts GENESIS.

The premium UI, canvas, thumbnail picker, pose library, workflow references, RunPod routing, model profiles and generation bridge are shared with the Linux build.

## RunPod

RunPod is the recommended backend for the large 9B routes. In GENESIS select RUNPOD and enter the existing ComfyUI HTTPS proxy endpoint. No Linux service manager is required on Windows.

## Local ComfyUI

GENESIS probes local ComfyUI at `http://127.0.0.1:8188`. On Windows it does not attempt to start Linux systemd services. Start your Windows ComfyUI separately, then use LOCAL/AUTO when the required model is available.

## Model/storage folder

The Models and Storage button opens `%USERPROFILE%\AI` by default. Override this with the `GENESIS_MODEL_ROOT` environment variable if your models live elsewhere.

## Windows integrations

- Generated-image folders open in Windows Explorer through Qt.
- System Monitor opens Task Manager.
- Jellyfin Media Player is launched from common Windows install paths when found; otherwise GENESIS opens the local Jellyfin web UI.
- Pose Maker supports `run.bat`, `run.cmd` or `START.bat` under `%USERPROFILE%\AI\GENESIS_POSE_MAKER`.
- MUNGBEAN supports `START_LOCAL.bat` or `START_LOCAL.cmd` under `%USERPROFILE%\MUNGBEAN`.
- Linux systemd/ROCm service controls are deliberately not run on Windows.

## Portable build

GitHub Actions on the `windows-port` branch builds an onedir PyInstaller package named `GENESIS-Windows` and uploads a `GENESIS-Windows.zip` artifact. The package contains the QML UI, visual assets, reference workflows and Python runtime dependencies needed by the desktop shell.

Hardware-specific ComfyUI models, LoRAs and large AI model files are not bundled into the application ZIP.
