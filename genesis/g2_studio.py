"""Isolated GENESIS 2 Studio entry point for the original GENESIS cockpit.

This is an explicit bridge, not an implicit change to G1's generation pipeline.
No ComfyUI service is started/stopped and no model or LoRA policy is bypassed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


DEFAULT_G2_ROOT = Path.home() / "Genesis-2"


class G2StudioUnavailable(RuntimeError):
    """The separate GENESIS 2 installation cannot safely be launched."""


def studio_command(root: str | Path | None = None) -> tuple[list[str], Path]:
    """Validate the local installation without importing G2 or touching models."""
    location = Path(root).expanduser() if root is not None else DEFAULT_G2_ROOT
    if not location.is_dir():
        raise G2StudioUnavailable(f"GENESIS 2 folder missing: {location}")
    location = location.resolve()
    entry = location / "main.py"
    config = location / "profiles.json"
    ui = location / "ui" / "Main.qml"
    python = location / ".venv" / "bin" / "python"
    for name, file in (("entry point", entry), ("model profiles", config),
                       ("QML interface", ui), ("Python environment", python)):
        if not file.is_file():
            raise G2StudioUnavailable(f"GENESIS 2 {name} missing: {file}")
    if not os.access(python, os.X_OK):
        raise G2StudioUnavailable("GENESIS 2 Python environment is not executable.")
    try:
        profiles = json.loads(config.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise G2StudioUnavailable(f"GENESIS 2 profiles unreadable: {exc}") from exc
    if not isinstance(profiles, list) or not profiles or not all(
        isinstance(row, dict) and isinstance(row.get("id"), str)
        and isinstance(row.get("template"), str) for row in profiles
    ):
        raise G2StudioUnavailable("GENESIS 2 has no valid model-profile catalogue.")
    return [str(python), str(entry)], location


def launch_studio(root: str | Path | None = None) -> subprocess.Popen:
    """Open an independent G2 window. Never change G1's backend or active queue."""
    command, location = studio_command(root)
    return subprocess.Popen(
        command, cwd=str(location), stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True,
    )
