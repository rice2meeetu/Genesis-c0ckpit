"""Non-GPU tests for the optional GENESIS 2 cockpit entry point."""
import json
import os
from pathlib import Path
import stat
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from genesis.g2_studio import G2StudioUnavailable, launch_studio, studio_command


def fixture_g2(root: Path) -> Path:
    (root / ".venv" / "bin").mkdir(parents=True)
    (root / "ui").mkdir()
    (root / "main.py").write_text("# test entry\n")
    (root / "ui" / "Main.qml").write_text("import QtQuick\n")
    (root / "profiles.json").write_text(json.dumps([
        {"id": "test-native", "template": "test-native.json"}
    ]))
    python = root / ".venv" / "bin" / "python"
    python.write_text("#!/usr/bin/env python3\n")
    python.chmod(python.stat().st_mode | stat.S_IXUSR)
    return root


def test_missing_or_invalid_g2_does_not_launch():
    with TemporaryDirectory() as folder:
        root = Path(folder) / "Genesis-2"
        with pytest.raises(G2StudioUnavailable, match="folder missing"):
            studio_command(root)
        fixture_g2(root)
        (root / "profiles.json").write_text("not json")
        with pytest.raises(G2StudioUnavailable, match="profiles unreadable"):
            studio_command(root)


def test_launch_is_independent_and_does_not_start_services():
    with TemporaryDirectory() as folder:
        root = fixture_g2(Path(folder) / "Genesis-2")
        command, cwd = studio_command(root)
        assert command == [str(root / ".venv" / "bin" / "python"), str(root / "main.py")]
        assert cwd == root
        with patch("genesis.g2_studio.subprocess.Popen") as popen:
            launch_studio(root)
        popen.assert_called_once()
        args, options = popen.call_args
        assert args == (command,)
        assert options["cwd"] == str(root)
        assert options["start_new_session"] is True
        assert options["stdout"] is not None
        assert options["stderr"] is not None


def test_unexecutable_interpreter_rejected():
    with TemporaryDirectory() as folder:
        root = fixture_g2(Path(folder) / "Genesis-2")
        python = root / ".venv" / "bin" / "python"
        python.chmod(stat.S_IRUSR | stat.S_IWUSR)
        with pytest.raises(G2StudioUnavailable, match="not executable"):
            studio_command(root)

def test_cockpit_exposes_g2_without_replacing_generate():
    root = Path(__file__).resolve().parents[1]
    qml = (root / "genesis" / "qt_ui" / "MainPremiumLinux.qml").read_text()
    cockpit = (root / "qt_cockpit.py").read_text()
    assert qml.count('objectName: "openGenesis2StudioButton"') == 1
    assert qml.count('objectName: "generateButton"') == 1
    assert 'moduleBridge.triggerAction("genesis 2 studio")' in qml
    assert 'self._open_genesis_2_studio()' in cockpit
