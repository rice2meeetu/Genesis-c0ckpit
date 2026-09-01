import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import webview

POSE_ROOT = Path.home() / "AI" / "GENESIS_POSE_MAKER"
POSE_APP = POSE_ROOT / "app.py"
POSE_PYTHON = Path.home() / "miniforge3" / "envs" / "genesis-ui" / "bin" / "python"
POSE_URL = "http://127.0.0.1:7861"


def alive():
    try:
        urllib.request.urlopen(POSE_URL, timeout=1)
        return True
    except Exception:
        return False


if not alive():
    subprocess.Popen(
        [str(POSE_PYTHON), str(POSE_APP)],
        cwd=str(POSE_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    for _ in range(60):
        if alive():
            break
        time.sleep(0.25)
    else:
        raise SystemExit("Pose Studio failed to start on port 7861")


webview.create_window(
    "GENESIS • POSE LIBRARY",
    POSE_URL,
    width=1500,
    height=950,
    min_size=(1000, 700),
)

webview.start(gui='qt')
