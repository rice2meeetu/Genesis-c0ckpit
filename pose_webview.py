"""Open the maintained Pose Library instead of the removed external web app."""
from pathlib import Path
import subprocess


def main():
    root = Path(__file__).resolve().parent
    return subprocess.call([str(root/'.venv/bin/python'), str(root/'qt_cockpit_linux_premium.py'), '--page', 'poses'], cwd=str(root))


if __name__ == '__main__':
    raise SystemExit(main())
