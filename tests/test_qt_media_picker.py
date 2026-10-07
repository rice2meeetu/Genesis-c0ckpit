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


def test_grid_default_after_cancel(tmp_path):
    settings = QSettings(str(tmp_path / "picker.ini"), QSettings.Format.IniFormat)
    dialog = ImagePicker(folder=tmp_path, settings=settings)
    assert dialog.view_choice.currentText() == "Thumbnail Grid"
    assert dialog.findChild(QListView, "listView").viewMode() == QListView.ViewMode.IconMode
    dialog.view_choice.setCurrentText("List")
    dialog.reject()
    second = ImagePicker(folder=tmp_path, settings=settings)
    assert second.view_choice.currentText() == "Thumbnail Grid"
    assert second.findChild(QListView, "listView").viewMode() == QListView.ViewMode.IconMode
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


def test_batch_picker_keeps_thumbnails_and_multiple_selection(tmp_path):
    from PyQt6.QtWidgets import QFileDialog, QAbstractItemView
    settings = QSettings(str(tmp_path / "batch.ini"), QSettings.Format.IniFormat)
    dialog = ImagePicker(folder=tmp_path, settings=settings, multiple=True)
    assert dialog.fileMode() == QFileDialog.FileMode.ExistingFiles
    view = dialog.findChild(QListView, "listView")
    assert view.viewMode() == QListView.ViewMode.IconMode
    assert view.selectionMode() == QAbstractItemView.SelectionMode.ExtendedSelection
    dialog.reject()


def test_picker_opens_maximized_with_thumbnail_grid(tmp_path):
    from PyQt6.QtCore import Qt
    dialog = ImagePicker(folder=tmp_path, settings=QSettings(str(tmp_path / "max.ini"), QSettings.Format.IniFormat))
    assert dialog.windowState() & Qt.WindowState.WindowMaximized
    dialog.reject()


def test_save_picker_preserves_filename_filter_and_cancel(tmp_path, monkeypatch):
    from genesis.qt_media_picker import FilePicker
    from PyQt6.QtWidgets import QFileDialog
    seen = []
    def cancel(dialog):
        seen.append(dialog)
        assert dialog.acceptMode() == QFileDialog.AcceptMode.AcceptSave
        assert dialog.fileMode() == QFileDialog.FileMode.AnyFile
        assert dialog.selectedFiles()[0] == str(tmp_path / "composition.png")
        assert dialog.defaultSuffix() == "png"
        return QFileDialog.DialogCode.Rejected
    monkeypatch.setattr(FilePicker, "exec", cancel)
    assert FilePicker.getSaveFileName(None, "Export", str(tmp_path / "composition.png"), "PNG (*.png)") == ("", "")
    assert not (tmp_path / "composition.png").exists()


def test_folder_picker_keeps_directory_selection(tmp_path, monkeypatch):
    from genesis.qt_media_picker import FilePicker
    from PyQt6.QtWidgets import QFileDialog
    def accept(dialog):
        assert dialog.fileMode() == QFileDialog.FileMode.Directory
        assert dialog.testOption(QFileDialog.Option.ShowDirsOnly)
        return QFileDialog.DialogCode.Accepted
    monkeypatch.setattr(FilePicker, "exec", accept)
    assert FilePicker.getExistingDirectory(None, "Folder", str(tmp_path)) == str(tmp_path)


def test_windows_places_preserve_defaults_and_skip_missing(tmp_path, monkeypatch):
    from pathlib import Path
    from PyQt6.QtCore import QUrl
    original = Path.is_dir
    for mounted in (True, False):
        monkeypatch.setattr(Path, "is_dir", lambda path: mounted if str(path) in ("/mnt/C", "/mnt/C/Users/p4uln") else original(path))
        dialog = ImagePicker(folder=tmp_path, settings=QSettings(str(tmp_path / "places.ini"), QSettings.Format.IniFormat))
        places = dialog.sidebarUrls()
        assert QUrl.fromLocalFile(str(Path.home())) in places
        for location in ("/mnt/C", "/mnt/C/Users/p4uln"):
            assert (QUrl.fromLocalFile(location) in places) == mounted
        assert len(places) == len(set(url.toString() for url in places))
        dialog.reject()


def test_visible_picker_renders_image_thumbnails_in_both_views(tmp_path):
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFileSystemModel
    from PyQt6.QtTest import QTest
    from PyQt6.QtWidgets import QStyleOptionViewItem
    path = tmp_path / "red.png"
    fixture_image(path)
    dialog = ImagePicker(folder=tmp_path, settings=QSettings(str(tmp_path / "render.ini"), QSettings.Format.IniFormat))
    dialog.show()
    model = dialog.findChild(QFileSystemModel)
    view = dialog.findChild(QListView, "listView")
    for _ in range(100):
        APP.processEvents()
        if model.index(str(path)).isValid() and model.rowCount(view.rootIndex()):
            break
        QTest.qWait(10)
    index = model.index(str(path))
    assert index.isValid()
    assert model.iconProvider() is not dialog.provider
    for mode, size in (("Thumbnail Grid", QSize(180, 140)), ("List", QSize(36, 36))):
        dialog.view_choice.setCurrentText(mode)
        option = QStyleOptionViewItem()
        option.decorationSize = size
        view.itemDelegate().initStyleOption(option, index)
        image = option.icon.pixmap(size).toImage()
        assert image.pixelColor(image.width() // 2, image.height() // 2) == QColor("red")
        assert not dialog.grab().isNull()
    fixture_image(path, "blue")
    view.itemDelegate().initStyleOption(option, index)
    image = option.icon.pixmap(size).toImage()
    assert image.pixelColor(image.width() // 2, image.height() // 2) == QColor("blue")
    assert len(dialog.provider.cache) <= 96
    dialog.reject()
