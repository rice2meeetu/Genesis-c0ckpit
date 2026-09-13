from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlComponent, QQmlEngine


ROOT = Path(__file__).resolve().parents[1]
QML = ROOT / "genesis" / "qt_ui" / "PremiumPoseBrowser.qml"


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    engine = QQmlEngine()
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML)))
    if component.status() == QQmlComponent.Status.Error:
        for error in component.errors():
            print(error.toString(), file=sys.stderr)
        return 1
    item = component.create()
    if item is None:
        for error in component.errors():
            print(error.toString(), file=sys.stderr)
        return 2
    item.deleteLater()
    app.processEvents()
    print("GENESIS PREMIUM POSE BROWSER QML: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
