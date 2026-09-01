"""Safe launch and status helpers for existing GENESIS applications.

This module never installs, updates, or rewrites an integrated application.  It
only probes local endpoints, starts predeclared user services, and opens the
already-installed interfaces.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
import webbrowser
from dataclasses import asdict, dataclass
from pathlib import Path


JELLYFIN_URL = "http://127.0.0.1:8096"
LLAMA_URL = "http://127.0.0.1:8081"
SILLYTAVERN_URL = "http://127.0.0.1:8000"
COMFYUI_URL = "http://127.0.0.1:8188"
GO2RTC_URL = "http://127.0.0.1:1984"
LM_STUDIO_URL = "http://127.0.0.1:1234"
FACEFUSION_URL = "http://127.0.0.1:7860"
SWARMUI_URL = "http://127.0.0.1:7801"

LLAMA_SERVICE = "genesis-llama.service"
SILLYTAVERN_SERVICE = "genesis-sillytavern.service"
COMFYUI_SERVICE = "genesis-comfyui.service"

LLAMA_BINARY = Path(
    "/mnt/AI-Storage/llama.cpp/build-rocm/bin/llama-server"
)
LLAMA_MODEL = Path(
    "/mnt/AI-Storage/LLM-Models/"
    "Rocinante-X-12B-v1-Heretic-Uncensored.Q5_K_M.gguf"
)
SILLYTAVERN_ROOT = Path("/mnt/C/Users/p4uln/SillyTavern")
COMFYUI_ROOT = Path.home() / "AI" / "ComfyUI"
COMFYUI_PYTHON_CANDIDATES = (
    Path.home()
    / "miniforge3/envs/comfyui-reactor-rocm/bin/python",
    COMFYUI_ROOT / ".venv/bin/python",
    COMFYUI_ROOT / "venv/bin/python",
)
FACEFUSION_ROOT_CANDIDATES = (
    Path.home() / "AI" / "facefusion",
    Path.home() / "AI" / "FaceFusion",
)
SWARMUI_ROOT_CANDIDATES = (
    Path.home() / "AI" / "SwarmUI",
    Path.home() / "AI" / "StableSwarmUI",
)
LM_STUDIO_PATH_CANDIDATES = (
    Path.home() / ".local/share/LM Studio",
    Path.home() / ".local/share/lm-studio",
    Path.home() / "Applications/LM_Studio.AppImage",
)


def first_existing(candidates):
    """Return the first existing path, retaining the preferred path if absent."""
    paths = tuple(Path(path) for path in candidates)
    return next((path for path in paths if path.exists()), paths[0])


COMFYUI_PYTHON = first_existing(COMFYUI_PYTHON_CANDIDATES)
FACEFUSION_ROOT = first_existing(FACEFUSION_ROOT_CANDIDATES)
SWARMUI_ROOT = first_existing(SWARMUI_ROOT_CANDIDATES)
LM_STUDIO_PATH = first_existing(LM_STUDIO_PATH_CANDIDATES)


@dataclass(frozen=True)
class IntegrationDiagnostic:
    name: str
    installed: bool
    online: bool
    endpoint: str | None = None
    service: str | None = None
    service_state: str | None = None
    runtime: str | None = None
    blocked_reason: str | None = None

    def to_dict(self):
        return asdict(self)


def _request_json(url: str, timeout: float = 1.5):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "GENESIS-Cockpit/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read(1024 * 1024)
    if not payload:
        return {}
    return json.loads(payload.decode("utf-8", "replace"))


def endpoint_online(url: str, path: str = "/", timeout: float = 1.5):
    try:
        _request_json(url.rstrip("/") + path, timeout=timeout)
        return True
    except json.JSONDecodeError:
        # HTML endpoints (notably SillyTavern) are still healthy responses.
        return True
    except (OSError, urllib.error.URLError, TimeoutError):
        return False


def mount_is_writable(path: Path):
    if not path.exists() or not os.access(path, os.R_OK):
        return False
    try:
        result = subprocess.run(
            ["findmnt", "-no", "OPTIONS", "--target", str(path)],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        lines = [line.strip() for line in result.stdout.splitlines() if line]
        if lines:
            options = set(lines[-1].split(","))
            return "rw" in options and "ro" not in options
    except (OSError, subprocess.TimeoutExpired):
        pass
    return os.access(path, os.W_OK)


def process_running(pattern: str):
    try:
        return subprocess.run(
            ["pgrep", "-f", pattern],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
            check=False,
        ).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def service_state(name: str):
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", name],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        return result.stdout.strip() or "unavailable"
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"


def start_user_service(name: str, already_online=False):
    if already_online:
        return True, "Already running — no duplicate started."
    try:
        reload_result = subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if reload_result.returncode != 0:
            return False, (
                reload_result.stderr.strip()
                or reload_result.stdout.strip()
                or "Unable to reload user services."
            )
        result = subprocess.run(
            ["systemctl", "--user", "start", name],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)
    if result.returncode == 0:
        return True, "Start requested."
    return False, result.stderr.strip() or result.stdout.strip() or "Start failed."


def open_url(url: str):
    return webbrowser.open(url)


def launch_jellyfin_desktop():
    if shutil.which("flatpak") is None:
        return False, "Flatpak is unavailable."
    try:
        subprocess.Popen(
            ["flatpak", "run", "org.jellyfin.JellyfinDesktop", "--desktop"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        if process_running("org.jellyfin.JellyfinDesktop"):
            return True, "Jellyfin Desktop focused or already running."
        return True, "Jellyfin Desktop launch requested."
    except OSError as error:
        return False, str(error)


def integration_diagnostics():
    """Return structured, non-mutating diagnostics for the local AI stack."""
    llama_online = endpoint_online(LLAMA_URL, "/health")
    silly_online = endpoint_online(SILLYTAVERN_URL, "/")
    comfy_online = endpoint_online(COMFYUI_URL, "/system_stats")
    jellyfin_online = endpoint_online(JELLYFIN_URL, "/System/Info/Public")
    go2rtc_online = endpoint_online(GO2RTC_URL, "/api/streams")
    lm_studio_online = endpoint_online(LM_STUDIO_URL, "/v1/models")
    facefusion_online = endpoint_online(FACEFUSION_URL, "/")
    swarmui_online = endpoint_online(SWARMUI_URL, "/")

    silly_installed = (SILLYTAVERN_ROOT / "server.js").is_file()
    silly_writable = mount_is_writable(SILLYTAVERN_ROOT)

    return {
        item.name: item.to_dict()
        for item in (
            IntegrationDiagnostic(
                "ComfyUI",
                COMFYUI_PYTHON.is_file() and (COMFYUI_ROOT / "main.py").is_file(),
                comfy_online,
                COMFYUI_URL,
                COMFYUI_SERVICE,
                service_state(COMFYUI_SERVICE),
                str(COMFYUI_PYTHON),
            ),
            IntegrationDiagnostic(
                "llama.cpp",
                LLAMA_BINARY.is_file() and LLAMA_MODEL.is_file(),
                llama_online,
                LLAMA_URL,
                LLAMA_SERVICE,
                service_state(LLAMA_SERVICE),
                str(LLAMA_BINARY),
            ),
            IntegrationDiagnostic(
                "SillyTavern",
                silly_installed,
                silly_online,
                SILLYTAVERN_URL,
                SILLYTAVERN_SERVICE,
                service_state(SILLYTAVERN_SERVICE),
                str(SILLYTAVERN_ROOT),
                (
                    "Windows volume is read-only"
                    if silly_installed and not silly_writable
                    else None
                ),
            ),
            IntegrationDiagnostic(
                "Jellyfin",
                shutil.which("flatpak") is not None,
                jellyfin_online,
                JELLYFIN_URL,
                runtime="org.jellyfin.JellyfinDesktop",
            ),
            IntegrationDiagnostic(
                "go2rtc",
                shutil.which("go2rtc") is not None or go2rtc_online,
                go2rtc_online,
                GO2RTC_URL,
                "go2rtc.service",
                service_state("go2rtc.service"),
            ),
            IntegrationDiagnostic(
                "LM Studio",
                LM_STUDIO_PATH.exists() or lm_studio_online,
                lm_studio_online,
                LM_STUDIO_URL,
                runtime=str(LM_STUDIO_PATH),
            ),
            IntegrationDiagnostic(
                "FaceFusion",
                FACEFUSION_ROOT.exists() or facefusion_online,
                facefusion_online,
                FACEFUSION_URL,
                runtime=str(FACEFUSION_ROOT),
            ),
            IntegrationDiagnostic(
                "SwarmUI",
                SWARMUI_ROOT.exists() or swarmui_online,
                swarmui_online,
                SWARMUI_URL,
                runtime=str(SWARMUI_ROOT),
            ),
        )
    }


def status_snapshot():
    diagnostics = integration_diagnostics()
    llama_online = diagnostics["llama.cpp"]["online"]
    silly_online = diagnostics["SillyTavern"]["online"]
    comfy_online = diagnostics["ComfyUI"]["online"]
    jellyfin_server = diagnostics["Jellyfin"]["online"]
    go2rtc_online = diagnostics["go2rtc"]["online"]

    comfy_gpu = "RX 9060 XT / ROCm configured"
    if comfy_online:
        try:
            stats = _request_json(COMFYUI_URL + "/system_stats")
            devices = stats.get("devices") or []
            if devices:
                comfy_gpu = devices[0].get("name") or comfy_gpu
        except Exception:
            pass

    return {
        "jellyfin_server": jellyfin_server,
        "jellyfin_desktop": process_running("org.jellyfin.JellyfinDesktop"),
        "llama_online": llama_online,
        "llama_installed": LLAMA_BINARY.is_file() and LLAMA_MODEL.is_file(),
        "llama_service": service_state(LLAMA_SERVICE),
        "llama_model": LLAMA_MODEL.name,
        "llama_endpoint": LLAMA_URL,
        "llama_context": 12288,
        "silly_online": silly_online,
        "silly_installed": (SILLYTAVERN_ROOT / "server.js").is_file(),
        "silly_writable": mount_is_writable(SILLYTAVERN_ROOT),
        "silly_service": service_state(SILLYTAVERN_SERVICE),
        "comfy_online": comfy_online,
        "comfy_installed": COMFYUI_PYTHON.is_file()
        and (COMFYUI_ROOT / "main.py").is_file(),
        "comfy_service": service_state(COMFYUI_SERVICE),
        "comfy_gpu": comfy_gpu,
        "go2rtc_online": go2rtc_online,
        "integrations": diagnostics,
    }
