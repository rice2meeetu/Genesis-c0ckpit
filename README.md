# Genesis Cockpit

Personal Linux/ROCm creative workspace for local image workflows, photo
organisation, cameras, AI chat services, and Jellyfin.

## Current interface

The repaired Genesis backend is presented through five grouped workspaces:

- **AI Image Studio** — Generate, Pose Library, Models & LoRAs, Prompt Builder
- **Photo Studio** — Library & Faces, Photo Tools, Create / Wallpaper
- **Camera Hub**
- **AI Chat**
- **Media / Jellyfin**

The interface preserves the existing ComfyUI workflow mappings, Pose Library,
three-stage workbench, local photo database, and service integrations. Camera
services are changed only through an explicit Camera Hub action.

## Launch on the Genesis workstation

```bash
cd /home/rice2meetyou/GENESIS-Photo-Studio
./launch.sh
```

The application expects the existing workstation services and Python virtual
environment. Models, LoRAs, personal photos, databases, credentials, and
machine-specific service configuration remain local and are intentionally not
stored in this repository.

## Validation

Safe tests use neutral temporary fixtures and do not run image generation,
start or stop cameras, alter the photo library, or interrupt active jobs.

```bash
python -m unittest \
  tests.test_cockpit_repairs \
  tests.test_asset_inventory \
  tests.test_job_queue \
  tests.test_visual_browser
```
