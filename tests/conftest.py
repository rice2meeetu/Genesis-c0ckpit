"""One widget-capable Qt application for all bridge and picker tests."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtWidgets import QApplication
APP = QApplication.instance() or QApplication([])
