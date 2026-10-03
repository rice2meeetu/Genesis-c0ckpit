# GENESIS on Windows

This Windows path is a frontend for the existing GENESIS premium Qt/QML interface. Image generation is expected to use the configured RunPod ComfyUI backend rather than local ROCm services.

## Install

1. Install Git and Python 3.11 or newer.
2. Clone the repository:

   ```powershell
   git clone https://github.com/rice2meeetu/Genesis-c0ckpit.git
   cd Genesis-c0ckpit
   git switch windows-bootstrap
   ```

3. Double-click `launch-windows.cmd`, or run:

   ```powershell
   .\launch-windows.ps1
   ```

The launcher creates `.venv-win`, installs the Windows frontend dependencies, configures a writable Qt runtime directory under `%TEMP%`, and starts the premium GENESIS home page.

## RunPod backend

GENESIS starts in `RUNPOD` backend mode on Windows. Enter the RunPod ComfyUI HTTPS endpoint in the GENESIS backend controls and press Connect/Refresh. The endpoint is saved by Qt settings for later sessions, but GENESIS does not poll it until you explicitly connect.

You can also set an endpoint before launch:

```powershell
$env:GENESIS_RUNPOD_URL = 'https://YOUR-ENDPOINT'
.\launch-windows.ps1
```

## Current Windows scope

The premium Qt/QML interface, pose/model workflow data, file picker, Canvas UI, and remote ComfyUI routing are intended to run on Windows. Linux workstation integrations such as systemd services, ROCm-local generation, `xdg-open`, and `gio trash` remain Linux-specific and are not required for the Windows frontend to start.
