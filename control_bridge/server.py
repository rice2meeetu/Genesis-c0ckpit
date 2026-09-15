#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import platform
import re
import shlex
import shutil
import signal
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

HOST = os.environ.get("GENESIS_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.environ.get("GENESIS_BRIDGE_PORT", "8766"))
HOME = Path.home().resolve()

DEFAULT_ROOTS = [
    HOME / "Genesis-c0ckpit",
    HOME / "GENESIS-AI-BUILDER",
    HOME / "GENESIS-Photo-Studio",
    HOME / "Documents",
    HOME / "Downloads",
    Path("/mnt/AI-Storage"),
]


def _configured_roots() -> list[Path]:
    raw = os.environ.get("GENESIS_BRIDGE_ROOTS", "")
    roots = [Path(p).expanduser().resolve() for p in raw.split(":") if p.strip()] if raw else []
    roots.extend(p.resolve() for p in DEFAULT_ROOTS if p.exists())
    unique: list[Path] = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return unique


ALLOWED_ROOTS = _configured_roots()
MAX_OUTPUT = int(os.environ.get("GENESIS_BRIDGE_MAX_OUTPUT", "200000"))
COMMAND_TIMEOUT = int(os.environ.get("GENESIS_BRIDGE_COMMAND_TIMEOUT", "120"))

DANGEROUS = [
    r"\brm\s+-[^\n]*r[^\n]*f\b",
    r"\bmkfs(?:\.|\s)",
    r"\bdd\s+.*\bof=/dev/",
    r"\bwipefs\b",
    r"\bshred\s+.*?/dev/",
    r"\b(fdisk|parted|sfdisk)\b",
    r"\bshutdown\b",
    r"\bpoweroff\b",
    r"\breboot\b",
    r"\bhalt\b",
    r"\bsystemctl\s+(?:reboot|poweroff|halt)\b",
    r"\bchmod\s+-R\s+777\s+/\b",
    r"\bchown\s+-R\s+[^\n]+\s+/\b",
]

mcp = FastMCP(
    "GENESIS Control Bridge",
    host=HOST,
    port=PORT,
    instructions=(
        "Authorized local workstation bridge for GENESIS development. "
        "Prefer read-only inspection before mutation. File tools are constrained to configured roots. "
        "Potentially destructive shell commands are blocked by default."
    ),
)


def _trim(text: str | bytes | None) -> str:
    if text is None:
        return ""
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    if len(text) > MAX_OUTPUT:
        return text[:MAX_OUTPUT] + f"\n...[truncated at {MAX_OUTPUT} chars]"
    return text


def _path(value: str, *, must_exist: bool = False) -> Path:
    p = Path(value).expanduser()
    if not p.is_absolute():
        p = HOME / p
    p = p.resolve(strict=False)
    if not any(p == root or root in p.parents for root in ALLOWED_ROOTS):
        raise ValueError(f"Path is outside configured roots: {p}")
    if must_exist and not p.exists():
        raise FileNotFoundError(str(p))
    return p


def _cwd(value: str | None) -> Path:
    if value:
        return _path(value, must_exist=True)
    preferred = HOME / "Genesis-c0ckpit"
    if preferred.exists():
        return preferred.resolve()
    return ALLOWED_ROOTS[0] if ALLOWED_ROOTS else HOME


def _command_block_reason(command: str) -> str | None:
    normalized = command.strip().lower()
    for pattern in DANGEROUS:
        if re.search(pattern, normalized):
            return f"Blocked destructive command pattern: {pattern}"
    if "sudo " in f" {normalized}" and os.environ.get("GENESIS_BRIDGE_ALLOW_SUDO", "0") != "1":
        return "sudo is disabled; set GENESIS_BRIDGE_ALLOW_SUDO=1 explicitly to enable it"
    return None


def _run(argv: list[str], *, cwd: Path | None = None, timeout: int = COMMAND_TIMEOUT) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            argv,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": _trim(result.stdout),
            "stderr": _trim(result.stderr),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": _trim(exc.stdout),
            "stderr": _trim(exc.stderr),
            "error": f"timed out after {timeout}s",
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }


@mcp.tool()
def health() -> dict[str, Any]:
    """Return bridge health, machine identity, configured roots, and available desktop helpers."""
    helpers = ["git", "bash", "python3", "gnome-screenshot", "grim", "scrot", "xdg-open", "ydotool", "wmctrl"]
    return {
        "ok": True,
        "bridge": "GENESIS Control Bridge",
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "host": HOST,
        "port": PORT,
        "roots": [str(p) for p in ALLOWED_ROOTS],
        "helpers": {name: shutil.which(name) for name in helpers},
    }


@mcp.tool()
def system_info() -> dict[str, Any]:
    """Return useful Linux/GENESIS system information without changing anything."""
    commands = {
        "uptime": ["uptime"],
        "memory": ["bash", "-lc", "free -h"],
        "disk": ["bash", "-lc", "df -h / /mnt/AI-Storage 2>/dev/null || df -h /"],
        "gpu": ["bash", "-lc", "rocminfo 2>/dev/null | grep -E 'Name:|Marketing Name' | head -20 || true"],
        "sessions": ["bash", "-lc", "loginctl list-sessions --no-legend 2>/dev/null || true"],
    }
    return {name: _run(argv) for name, argv in commands.items()}


@mcp.tool()
def list_directory(path: str) -> dict[str, Any]:
    """List a directory inside an allowed root."""
    p = _path(path, must_exist=True)
    if not p.is_dir():
        raise NotADirectoryError(str(p))
    items = []
    for child in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
        try:
            stat = child.stat()
            items.append({
                "name": child.name,
                "path": str(child),
                "type": "dir" if child.is_dir() else "file",
                "size": stat.st_size,
                "modified": stat.st_mtime,
            })
        except OSError as exc:
            items.append({"name": child.name, "path": str(child), "error": str(exc)})
    return {"path": str(p), "items": items[:2000], "truncated": len(items) > 2000}


@mcp.tool()
def read_file(path: str, max_chars: int = 200000) -> dict[str, Any]:
    """Read a UTF-8 text file inside an allowed root."""
    p = _path(path, must_exist=True)
    if not p.is_file():
        raise ValueError(f"Not a file: {p}")
    data = p.read_text(encoding="utf-8", errors="replace")
    limit = max(1, min(max_chars, MAX_OUTPUT))
    return {"path": str(p), "content": data[:limit], "truncated": len(data) > limit}


@mcp.tool()
def write_file(path: str, content: str, create_parents: bool = False) -> dict[str, Any]:
    """Write a UTF-8 text file atomically inside an allowed root."""
    p = _path(path)
    if create_parents:
        p.parent.mkdir(parents=True, exist_ok=True)
    if not p.parent.exists():
        raise FileNotFoundError(str(p.parent))
    fd, tmp_name = tempfile.mkstemp(prefix=f".{p.name}.", dir=str(p.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, p)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return {"ok": True, "path": str(p), "bytes": len(content.encode("utf-8"))}


@mcp.tool()
def run_command(command: str, cwd: str | None = None, timeout: int = COMMAND_TIMEOUT) -> dict[str, Any]:
    """Run an authorized shell command. Destructive command patterns and sudo are blocked by default."""
    reason = _command_block_reason(command)
    if reason:
        return {"ok": False, "blocked": True, "reason": reason}
    workdir = _cwd(cwd)
    timeout = max(1, min(int(timeout), 900))
    return _run(["bash", "-lc", command], cwd=workdir, timeout=timeout)


@mcp.tool()
def git_status(repo: str | None = None) -> dict[str, Any]:
    """Return branch, status, and recent commits for a Git repository."""
    workdir = _cwd(repo)
    return {
        "repo": str(workdir),
        "branch": _run(["git", "branch", "--show-current"], cwd=workdir),
        "status": _run(["git", "status", "--short", "--branch"], cwd=workdir),
        "recent": _run(["git", "log", "-8", "--oneline", "--decorate"], cwd=workdir),
    }


@mcp.tool()
def list_processes(filter_text: str = "") -> dict[str, Any]:
    """List processes, optionally filtering by case-insensitive text."""
    result = _run(["ps", "-eo", "pid,ppid,stat,etimes,comm,args", "--sort=-etimes"])
    lines = result.get("stdout", "").splitlines()
    if filter_text:
        needle = filter_text.lower()
        lines = [line for line in lines if needle in line.lower()]
    return {"ok": result["ok"], "processes": lines[:1000], "truncated": len(lines) > 1000}


@mcp.tool()
def launch_app(command: str, cwd: str | None = None) -> dict[str, Any]:
    """Launch a desktop application or long-running process detached from the bridge."""
    reason = _command_block_reason(command)
    if reason:
        return {"ok": False, "blocked": True, "reason": reason}
    workdir = _cwd(cwd)
    log_dir = HOME / ".local" / "state" / "genesis-control-bridge"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "launched-apps.log"
    log = open(log_path, "a", encoding="utf-8")
    proc = subprocess.Popen(
        ["bash", "-lc", command],
        cwd=str(workdir),
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        close_fds=True,
    )
    return {"ok": True, "pid": proc.pid, "command": command, "cwd": str(workdir), "log": str(log_path)}


@mcp.tool()
def terminate_process(pid: int, force: bool = False) -> dict[str, Any]:
    """Terminate a user-owned process by PID. PID 1 and the bridge process are protected."""
    pid = int(pid)
    if pid <= 1 or pid == os.getpid():
        return {"ok": False, "blocked": True, "reason": "protected process"}
    try:
        os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
        return {"ok": True, "pid": pid, "signal": "SIGKILL" if force else "SIGTERM"}
    except ProcessLookupError:
        return {"ok": False, "error": "process not found", "pid": pid}
    except PermissionError:
        return {"ok": False, "error": "permission denied", "pid": pid}


@mcp.tool()
def take_screenshot(output_path: str | None = None) -> dict[str, Any]:
    """Capture the current desktop using an available Linux screenshot helper."""
    if output_path:
        target = _path(output_path)
    else:
        shots = HOME / "Pictures" / "GENESIS-Screenshots"
        shots.mkdir(parents=True, exist_ok=True)
        # Screenshot output is explicitly permitted even when Pictures is not a general file root.
        target = shots / f"genesis-{int(time.time())}.png"

    candidates: list[list[str]] = []
    if shutil.which("gnome-screenshot"):
        candidates.append(["gnome-screenshot", "-f", str(target)])
    if shutil.which("grim"):
        candidates.append(["grim", str(target)])
    if shutil.which("scrot"):
        candidates.append(["scrot", str(target)])

    errors = []
    for argv in candidates:
        result = _run(argv, timeout=30)
        if result["ok"] and target.exists():
            return {"ok": True, "path": str(target), "bytes": target.stat().st_size, "tool": argv[0]}
        errors.append({"tool": argv[0], "result": result})
    return {"ok": False, "error": "No screenshot helper succeeded", "attempts": errors}


@mcp.tool()
def desktop_action(action: str, text: str = "") -> dict[str, Any]:
    """Perform an optional desktop action using ydotool when installed: type, key, or click."""
    exe = shutil.which("ydotool")
    if not exe:
        return {"ok": False, "error": "ydotool is not installed/configured"}
    action = action.strip().lower()
    if action == "type":
        return _run([exe, "type", "--key-delay", "5", text], timeout=30)
    if action == "key":
        # Accept ydotool key expressions such as '29:1 46:1 46:0 29:0'.
        args = shlex.split(text)
        return _run([exe, "key", *args], timeout=30)
    if action == "click":
        args = shlex.split(text or "0xC0")
        return _run([exe, "click", *args], timeout=30)
    return {"ok": False, "error": "action must be one of: type, key, click"}


if __name__ == "__main__":
    transport = os.environ.get("GENESIS_BRIDGE_TRANSPORT", "streamable-http")
    mcp.run(transport=transport)
