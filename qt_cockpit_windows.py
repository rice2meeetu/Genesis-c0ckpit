"""Windows launcher for the GENESIS premium cockpit.

This keeps the validated GENESIS/RunPod generation stack intact while replacing
Linux-only desktop actions with Windows-safe equivalents. The existing Linux
launcher and runtime are not modified.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

if sys.platform != "win32":
    raise SystemExit("qt_cockpit_windows.py is intended for Windows.")

# The premium launcher uses this for its single-instance lock. Windows has no
# XDG runtime directory, so point it at the current user's temp directory.
os.environ.setdefault("XDG_RUNTIME_DIR", tempfile.gettempdir())

from PyQt6.QtCore import QUrl, pyqtSlot
from PyQt6.QtGui import QDesktopServices

import qt_cockpit
import qt_cockpit_linux_premium as premium
from genesis import integrations

PROJECT_ROOT = Path(__file__).resolve().parent


def _open_path(path: Path, label: str, bridge) -> None:
    path.mkdir(parents=True, exist_ok=True)
    ok = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))
    bridge._set_status(f"{label} opened" if ok else f"Could not open {label}")


@pyqtSlot()
def _windows_show_preview_in_folder(self) -> None:
    source = Path(QUrl(self._preview).toLocalFile())
    if not self._preview or not source.is_file():
        self._set_status("No generated preview is available yet.")
        return
    ok = QDesktopServices.openUrl(QUrl.fromLocalFile(str(source.parent)))
    self._set_status("Generated image folder opened" if ok else "Could not open the generated image folder.")


def _windows_process_running(pattern: str) -> bool:
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        return pattern.casefold() in result.stdout.casefold()
    except (OSError, subprocess.TimeoutExpired):
        return False


def _windows_gpu_preflight():
    return True, "Windows GPU safety is delegated to the selected ComfyUI backend."


def _windows_service_state(_name: str) -> str:
    return "external"


def _windows_start_user_service(_name: str, already_online=False):
    if already_online:
        return True, "Already running."
    return False, "Windows services are not auto-started by GENESIS; start the local backend or select RunPod."


def _windows_launch_jellyfin_desktop():
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Jellyfin Media Player" / "JellyfinMediaPlayer.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Jellyfin Media Player" / "JellyfinMediaPlayer.exe",
    ]
    for executable in candidates:
        if executable.is_file():
            try:
                subprocess.Popen([str(executable)])
                return True, "Jellyfin Media Player launch requested."
            except OSError as exc:
                return False, str(exc)
    if QDesktopServices.openUrl(QUrl(integrations.JELLYFIN_URL)):
        return True, "Jellyfin opened in the browser."
    return False, "Jellyfin is unavailable."


def _run_batch(candidate: Path, cwd: Path, env=None):
    return subprocess.Popen(
        ["cmd.exe", "/d", "/c", str(candidate)],
        cwd=str(cwd),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )


def _windows_pose_maker(self) -> None:
    root = Path.home() / "AI" / "GENESIS_POSE_MAKER"
    url = "http://127.0.0.1:7861"
    if integrations.endpoint_online(url, "/", timeout=0.8):
        integrations.open_url(url)
        self._set_status("Pose Maker workbench opened")
        return
    launcher = next((p for p in (root / "run.bat", root / "run.cmd", root / "START.bat") if p.is_file()), None)
    if launcher is None:
        self._set_status("Pose Maker is not installed for Windows")
        return
    try:
        _run_batch(launcher, root)
        self._set_status("Pose Maker launch requested")
    except OSError as exc:
        self._set_status(f"Pose Maker failed · {exc}")


def _windows_open_grok_runpod(self) -> None:
    from genesis.backend_routing import normalize_endpoint

    router = self.backend_router
    if router is None or router.mode != "RUNPOD":
        self._set_status("Select RUNPOD before opening MUNGBEAN from GENESIS.")
        return
    try:
        endpoint = normalize_endpoint(router.endpoint)
    except ValueError as exc:
        self._set_status(str(exc))
        return
    if not endpoint:
        self._set_status("Set the RunPod ComfyUI endpoint before opening MUNGBEAN.")
        return
    root = Path.home() / "MUNGBEAN"
    launcher = next((p for p in (root / "START_LOCAL.bat", root / "START_LOCAL.cmd") if p.is_file()), None)
    if launcher is None:
        self._set_status("MUNGBEAN Windows launcher is not installed")
        return
    env = os.environ.copy()
    env["COMFY_URL"] = endpoint
    try:
        _run_batch(launcher, root, env=env)
        self._set_status("MUNGBEAN launched for RunPod")
    except OSError as exc:
        self._set_status(f"MUNGBEAN launch failed · {exc}")


def _windows_legacy(self, action: str) -> None:
    try:
        subprocess.Popen(
            [sys.executable, str(PROJECT_ROOT / "main.py")],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        self._set_status(f"{action} · full GENESIS workspace opened")
    except OSError as exc:
        self._set_status(f"{action} failed · {exc}")


_original_trigger_action = qt_cockpit.ModuleBridge.triggerAction


@pyqtSlot(str)
def _windows_trigger_action(self, action: str) -> None:
    key = action.strip().lower()
    if not key:
        return
    if "monitor" in key:
        try:
            subprocess.Popen(["taskmgr.exe"])
            self._set_status("Task Manager opened")
        except OSError as exc:
            self._set_status(f"Task Manager failed · {exc}")
        return
    if "storage" in key or "model" in key:
        target = Path(os.environ.get("GENESIS_MODEL_ROOT", str(Path.home() / "AI"))).expanduser()
        _open_path(target, "Models and storage", self)
        return
    if any(word in key for word in ("movie", "video library")):
        ok, detail = _windows_launch_jellyfin_desktop()
        self._set_status(detail if ok else f"Jellyfin failed · {detail}")
        return
    if "pose maker" in key or "pose workbench" in key:
        _windows_pose_maker(self)
        return
    if "grok imagine" in key or "mungbean" in key:
        _windows_open_grok_runpod(self)
        return
    if "comfyui" in key or key == "manage service":
        if integrations.endpoint_online(integrations.COMFYUI_URL, "/system_stats"):
            integrations.open_url(integrations.COMFYUI_URL)
            self._set_status("ComfyUI opened")
        else:
            self._set_status("Local ComfyUI is offline · start it separately or select RunPod")
        return
    if any(word in key for word in ("camera", "grid", "recordings", "hub")):
        if integrations.endpoint_online(integrations.GO2RTC_URL, "/api/streams"):
            integrations.open_url(integrations.GO2RTC_URL)
            self._set_status("Camera Hub opened")
        else:
            self._set_status("Camera Hub is offline on Windows")
        return
    if "ai settings" in key or "ai assistant" in key:
        if integrations.endpoint_online(integrations.QWEN_URL, "/health"):
            integrations.open_url(integrations.QWEN_URL)
            self._set_status("GENESIS AI opened")
        else:
            self._set_status("Local GENESIS AI service is offline on Windows")
        return
    _original_trigger_action(self, action)


def install_windows_compatibility() -> None:
    qt_cockpit.GenerationBridge.showPreviewInFolder = _windows_show_preview_in_folder
    qt_cockpit.ModuleBridge.triggerAction = _windows_trigger_action
    qt_cockpit.ModuleBridge._pose_maker = _windows_pose_maker
    qt_cockpit.ModuleBridge._open_grok_runpod = _windows_open_grok_runpod
    qt_cockpit.ModuleBridge._legacy = _windows_legacy
    integrations.process_running = _windows_process_running
    integrations.gpu_kernel_preflight = _windows_gpu_preflight
    integrations.service_state = _windows_service_state
    integrations.start_user_service = _windows_start_user_service
    integrations.launch_jellyfin_desktop = _windows_launch_jellyfin_desktop


if __name__ == "__main__":
    install_windows_compatibility()
    raise SystemExit(premium.main())
