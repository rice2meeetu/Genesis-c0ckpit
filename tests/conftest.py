"""One widget-capable Qt application for all bridge and picker tests."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from PyQt6.QtWidgets import QApplication
APP = QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated_user_settings(monkeypatch, tmp_path):
    """Keep routes, caches, and UI preferences outside the user's real settings."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    for key in ("GENESIS_RUNPOD_URL", "GENESIS_COMFY_URL", "GENESIS_BACKEND_MODE",
                "GENESIS_RUNPOD_AUTOCONNECT", "GENESIS_RUNPOD_SSH_HOST"):
        monkeypatch.delenv(key, raising=False)
