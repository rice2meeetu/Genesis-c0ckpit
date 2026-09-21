"""CPU-only image picker with bounded thumbnails and a read-only preview."""
from collections import OrderedDict
from pathlib import Path

from PyQt6.QtCore import QSettings, QSize, Qt
from PyQt6.QtGui import QIcon, QImageReader, QPixmap
from PyQt6.QtWidgets import (
    QComboBox, QFileDialog, QFileIconProvider, QLabel, QListView,
    QSizePolicy, QToolButton, QVBoxLayout, QWidget,
)

IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)"
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def read_image(path, bound):
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    size = reader.size()
    if size.isValid():
        reader.setScaledSize(size.scaled(bound, Qt.AspectRatioMode.KeepAspectRatio))
    return reader.read(), size


class ThumbnailProvider(QFileIconProvider):
    def __init__(self):
        super().__init__()
        self.cache = OrderedDict()

    def icon(self, value):
        if not hasattr(value, "absoluteFilePath") or value.suffix().lower() not in {x[1:] for x in EXTENSIONS}:
            return super().icon(value)
        path = value.absoluteFilePath()
        try:
            stat = Path(path).stat()
            key = (path, stat.st_mtime_ns, stat.st_size)
            if key not in self.cache:
                image, _ = read_image(path, QSize(180, 140))
                if image.isNull():
                    return super().icon(value)
                self.cache[key] = QIcon(QPixmap.fromImage(image))
                while len(self.cache) > 96:
                    self.cache.popitem(last=False)
            self.cache.move_to_end(key)
            return self.cache[key]
        except OSError:
            return super().icon(value)


class ImagePicker(QFileDialog):
    def __init__(self, parent=None, title="GENESIS · Select image", folder=None, settings=None):
        self.settings = settings if settings is not None else QSettings("GENESIS", "MediaPicker")
        initial = folder or self.settings.value("folder", str(Path.home()))
        if not Path(initial).is_dir():
            initial = str(Path.home())
        super().__init__(parent, title, str(initial))
        self.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        self.setOption(QFileDialog.Option.ReadOnly, True)
        self.setFileMode(QFileDialog.FileMode.ExistingFile)
        self.setNameFilter(IMAGE_FILTER)
        self.setViewMode(QFileDialog.ViewMode.List)
        self.resize(1380, 860)
        self.setMinimumSize(960, 620)
        self.provider = ThumbnailProvider()
        self.setIconProvider(self.provider)
        for name in ("listModeButton", "detailModeButton"):
            button = self.findChild(QToolButton, name)
            if button is not None:
                button.hide()
        self.setStyleSheet("""
            QWidget { background: #141414; color: #e9e6df; font-size: 13px; }
            QLineEdit, QListView, QTreeView { background: #0d0d0d; border: 1px solid #343434; }
            QPushButton, QToolButton, QComboBox { padding: 7px; border: 1px solid #52452f; border-radius: 4px; }
            QPushButton:hover, QToolButton:hover { background: #302719; }
            QListView::item:selected, QTreeView::item:selected { background: #51412b; }
        """)
        self.view_choice = QComboBox(self)
        self.view_choice.addItems(["Thumbnail Grid", "List"])
        saved = self.settings.value("view", "Thumbnail Grid")
        self.view_choice.setCurrentText(saved if saved in ("Thumbnail Grid", "List") else "Thumbnail Grid")
        self.view_choice.currentTextChanged.connect(self.change_view)
        layout = self.layout()
        layout.addWidget(self.view_choice, layout.rowCount(), 0, 1, 2)
        panel = QWidget(self)
        panel.setMinimumWidth(440)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        panel_layout = QVBoxLayout(panel)
        heading = QLabel("SELECTED IMAGE", panel)
        heading.setStyleSheet("color: #f3d28b; font-weight: bold; letter-spacing: 2px")
        panel_layout.addWidget(heading)
        self.preview = QLabel("Select an image to preview", panel)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(360, 400)
        self.preview.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.preview.setStyleSheet("background: #080808; border: 1px solid #343434")
        panel_layout.addWidget(self.preview, 1)
        self.details = QLabel("Your source files stay unchanged.", panel)
        self.details.setWordWrap(True)
        panel_layout.addWidget(self.details)
        layout.addWidget(panel, 0, layout.columnCount(), layout.rowCount(), 1)
        layout.setColumnStretch(1, 3)
        layout.setColumnStretch(layout.columnCount() - 1, 2)
        sidebar = self.findChild(QListView, "sidebar")
        if sidebar is not None:
            sidebar.setMinimumWidth(135)
        self._preview_image = None
        self.currentChanged.connect(self.show_preview)
        self.directoryEntered.connect(self.clear_preview)
        self.finished.connect(self.save_preferences)
        self.change_view(self.view_choice.currentText())

    def change_view(self, mode):
        # Touch only the file view, never QFileDialog's places sidebar.
        self.setViewMode(QFileDialog.ViewMode.List)
        view = self.findChild(QListView, "listView")
        if view is not None:
            grid = mode == "Thumbnail Grid"
            view.setViewMode(QListView.ViewMode.IconMode if grid else QListView.ViewMode.ListMode)
            view.setIconSize(QSize(180, 140) if grid else QSize(36, 36))
            view.setGridSize(QSize(210, 184) if grid else QSize())
            view.setResizeMode(QListView.ResizeMode.Adjust)
            view.setWordWrap(grid)
        self.settings.setValue("view", mode)

    def save_preferences(self, _result):
        self.settings.setValue("folder", self.directory().absolutePath())
        self.settings.setValue("view", self.view_choice.currentText())
        self.settings.sync()

    def clear_preview(self, _path=""):
        self._preview_image = None
        self.preview.clear()
        self.preview.setText("Select an image to preview")
        self.details.setText("Your source files stay unchanged.")

    def show_preview(self, path):
        self.clear_preview()
        if Path(path).suffix.lower() not in EXTENSIONS or not Path(path).is_file():
            return
        image, original = read_image(path, QSize(1600, 1600))
        if image.isNull():
            self.preview.setText("Preview unavailable")
            return
        self._preview_image = image
        self.details.setText(f"{Path(path).name}\n{original.width()} × {original.height()} px\nRead-only preview")
        self.render_preview()

    def render_preview(self):
        if self._preview_image is not None:
            self.preview.setPixmap(QPixmap.fromImage(self._preview_image).scaled(
                self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_preview_image"):
            self.render_preview()


def choose_image(title="GENESIS · Select image", folder=None):
    dialog = ImagePicker(title=title, folder=folder)
    if dialog.exec() == QFileDialog.DialogCode.Accepted:
        files = dialog.selectedFiles()
        if files and Path(files[0]).is_file():
            return files[0]
    return ""
