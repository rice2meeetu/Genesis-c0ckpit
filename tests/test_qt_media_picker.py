"""CPU-only widget regression tests; no generation bridges or services."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtCore import QFileInfo, QSettings, QSize
from PyQt6.QtGui import QImage, QColor
from PyQt6.QtWidgets import QApplication, QListView
from genesis.qt_media_picker import ImagePicker, ThumbnailProvider, read_image

APP = QApplication.instance() or QApplication([])


def fixture_image(path, color="red"):
    image = QImage(640, 480, QImage.Format.Format_RGB32)
    image.fill(QColor(color))
    assert image.save(str(path))


def test_grid_default_and_view_survives_cancel(tmp_path):
    settings = QSettings(str(tmp_path / "picker.ini"), QSettings.Format.IniFormat)
    dialog = ImagePicker(folder=tmp_path, settings=settings)
    assert dialog.view_choice.currentText() == "Thumbnail Grid"
    assert dialog.findChild(QListView, "listView").viewMode() == QListView.ViewMode.IconMode
    dialog.view_choice.setCurrentText("List")
    dialog.reject()
    second = ImagePicker(folder=tmp_path, settings=settings)
    assert second.view_choice.currentText() == "List"
    assert second.findChild(QListView, "listView").viewMode() == QListView.ViewMode.ListMode
    second.reject()


def test_bad_preference_falls_back_to_grid(tmp_path):
    settings = QSettings(str(tmp_path / "picker.ini"), QSettings.Format.IniFormat)
    settings.setValue("view", "unknown")
    dialog = ImagePicker(folder=tmp_path, settings=settings)
    assert dialog.view_choice.currentText() == "Thumbnail Grid"
    dialog.reject()


def test_preview_is_bounded_and_source_unchanged(tmp_path):
    path = tmp_path / "sample.png"
    fixture_image(path)
    before = path.read_bytes()
    image, original = read_image(path, QSize(180, 140))
    assert original.width() == 640
    assert image.width() <= 180 and image.height() <= 140
    dialog = ImagePicker(folder=tmp_path, settings=QSettings(str(tmp_path / "p.ini"), QSettings.Format.IniFormat))
    dialog.show_preview(str(path))
    assert dialog._preview_image is not None
    assert "640 × 480" in dialog.details.text()
    dialog.show_preview(str(tmp_path / "missing.png"))
    assert dialog._preview_image is None
    assert path.read_bytes() == before
    dialog.reject()


def test_thumbnails_refresh_after_file_change(tmp_path):
    path = tmp_path / "sample.png"
    fixture_image(path)
    provider = ThumbnailProvider()
    red = provider.icon(QFileInfo(str(path))).pixmap(100, 100).toImage()
    fixture_image(path, "blue")
    blue = provider.icon(QFileInfo(str(path))).pixmap(100, 100).toImage()
    assert red.pixelColor(20, 20) != blue.pixelColor(20, 20)
