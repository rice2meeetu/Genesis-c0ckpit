# GENESIS Cockpit Integrations

Date: 2026-08-22

## Existing applications used

GENESIS launches and monitors these existing installations; it does not replace
or reinstall them.

| System | Existing location / endpoint | GENESIS behavior |
|---|---|---|
| Jellyfin Desktop | Flatpak `org.jellyfin.JellyfinDesktop`; server `127.0.0.1:8096` | Opens the completed Jellyfin + MPV/ModernZ media system and reports server/desktop state. |
| llama.cpp ROCm | `/mnt/AI-Storage/llama.cpp/build-rocm/bin/llama-server`; `127.0.0.1:8081` | Starts Rocinante-X-12B Q5_K_M with 12,288 context through `genesis-llama.service`; refuses duplicate starts when health is already online. |
| ComfyUI ROCm | `~/AI/ComfyUI`; existing `comfyui-reactor-rocm` environment; `127.0.0.1:8188` | Starts through `genesis-comfyui.service`, reports GPU/backend state, opens when ready, and avoids duplicate starts. |
| go2rtc | Existing `go2rtc.service`; `127.0.0.1:1984` | Existing camera page reports offline state and refuses to open dead live links silently. |

Installed user units are stored in `~/.config/systemd/user/`. Versioned copies
are in `systemd/`. Logs go to `~/.local/state/genesis/`.


- Group Auto RP: ready through the existing bounded group controls.
  ComfyUI must be online.
- Expressions: neutral/joy support exists; the larger sprite batch remains
  deliberately deferred after the earlier storage incident.
- TTS: unavailable because the configured AllTalk/Genesis Voice backend is not
  installed/running locally. GENESIS marks this unavailable and does not install
  a replacement.
- Vector/chat memory: pending and deliberately shown as pending.

## Current blocker

No NTFS write blocker is currently active. `/mnt/C` was subsequently verified
on `127.0.0.1:8000`. If the Windows volume becomes dirty/read-only again, GENESIS
safely from Windows.

## Validation

- Python compilation and whitespace validation passed.
- All seven cockpit pages construct successfully without requiring a backend.
- Every visible Tk/ttk button has a command.
- Status rendering passed for online, stopped, unavailable, and read-only states.
- Duplicate-service prevention passed: an online endpoint returns without a
  `systemctl start` call.
- Service definitions pass `systemd-analyze --user verify`; the only warning is
  from Ubuntu's unrelated `spice-vdagent.service`.
- Jellyfin health detection passed against the live local server.
  and relevant executable/model paths were verified.

The Codex sandbox cannot access the host user-systemd bus or ROCm device, so it
did not load the 8.7 GB language model or start ComfyUI for a GPU job. GENESIS
runs outside that sandbox and will use the installed user units. Endpoint checks
and prior working-stack results remain preserved.
