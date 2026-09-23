"""Qt adapter for local Canvas composition. Never imports AI/service bridges."""
from pathlib import Path

from PyQt6.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QFileDialog, QMessageBox

from genesis.canvas_document import CanvasDocument
from genesis.qt_media_picker import choose_image


class CanvasBridge(QObject):
    changed = pyqtSignal()
    statusChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.document = CanvasDocument()
        self._status = "Add a background, then stack images or transparent cutouts."
        self._dirty = False
        self._project_path = ""

    @pyqtProperty('QVariantList', notify=changed)
    def layers(self):
        return [dict(row, source=QUrl.fromLocalFile(row["path"]).toString()) for row in self.document.layers]

    @pyqtProperty('QVariantMap', notify=changed)
    def selected(self):
        return next((dict(row) for row in self.document.layers if row["id"] == self.document.selected_id), {})

    @pyqtProperty(int, notify=changed)
    def canvasWidth(self):
        return self.document.width

    @pyqtProperty(int, notify=changed)
    def canvasHeight(self):
        return self.document.height

    @pyqtProperty(bool, notify=changed)
    def canUndo(self):
        return self.document.can_undo

    @pyqtProperty(bool, notify=changed)
    def canRedo(self):
        return self.document.can_redo

    @pyqtProperty(bool, notify=changed)
    def dirty(self):
        return self._dirty

    @pyqtProperty(str, notify=statusChanged)
    def status(self):
        return self._status

    def _message(self, message):
        self._status = message
        self.statusChanged.emit()

    def _apply(self, operation):
        try:
            if operation():
                self._dirty = True
                self.changed.emit()
                self._message("Composition updated · source files unchanged")
        except (OSError, ValueError) as exc:
            self._message(str(exc))

    @pyqtSlot(str)
    def addImage(self, url):
        parsed = QUrl(url)
        if parsed.scheme() and not parsed.isLocalFile():
            self._message("Choose a local image file.")
            return
        path = parsed.toLocalFile() if parsed.isLocalFile() else url
        self._apply(lambda: self.document.add_image(path))

    @pyqtSlot(str)
    def addSourceOnce(self, url):
        parsed = QUrl(url)
        path = parsed.toLocalFile() if parsed.isLocalFile() else url
        existing = next((row for row in self.document.layers if row["path"] == str(Path(path).resolve())), None)
        if existing:
            self.selectLayer(existing["id"])
        else:
            self.addImage(url)

    @pyqtSlot(result=bool)
    def confirmClose(self):
        return self.confirm_discard()

    @pyqtSlot()
    def chooseLayer(self):
        chosen = choose_image("GENESIS Canvas · Add image or cutout")
        if chosen:
            self.addImage(chosen)

    @pyqtSlot(str)
    def selectLayer(self, layer_id):
        if self.document.select_layer(layer_id):
            self.changed.emit()

    @pyqtSlot(str, float, float)
    def moveLayer(self, layer_id, x, y):
        self._apply(lambda: self.document.update_layer(layer_id, x=x, y=y))

    @pyqtSlot(str)
    def renameSelected(self, name):
        if self.document.selected_id:
            self._apply(lambda: self.document.update_layer(self.document.selected_id, name=name.strip()))

    @pyqtSlot(float)
    def resizeSelected(self, factor):
        row = self.selected
        if row:
            self._apply(lambda: self.document.update_layer(row["id"], width=row["width"] * factor, height=row["height"] * factor))

    @pyqtSlot(float)
    def rotateSelected(self, degrees):
        selected = self.document.selected_id
        if selected:
            layer = self.document._layer(selected)
            self._apply(lambda: self.document.update_layer(selected, rotation=layer.get("rotation", 0) + degrees))

    @pyqtSlot()
    def duplicateSelected(self):
        selected = self.document.selected_id
        if selected:
            self._apply(lambda: self.document.duplicate_layer(selected))

    @pyqtSlot(float)
    def setOpacity(self, opacity):
        if self.document.selected_id:
            self._apply(lambda: self.document.update_layer(self.document.selected_id, opacity=opacity))

    @pyqtSlot(str, bool)
    def setVisible(self, layer_id, visible):
        self._apply(lambda: self.document.update_layer(layer_id, visible=visible))

    @pyqtSlot(int)
    def reorderSelected(self, delta):
        if self.document.selected_id:
            self._apply(lambda: self.document.move_layer(self.document.selected_id, delta))

    @pyqtSlot()
    def removeSelected(self):
        if self.document.selected_id:
            self._apply(lambda: self.document.remove_layer(self.document.selected_id))

    @pyqtSlot()
    def undo(self):
        self._apply(self.document.undo)

    @pyqtSlot()
    def redo(self):
        self._apply(self.document.redo)

    def confirm_discard(self):
        if not self._dirty:
            return True
        answer = QMessageBox.question(None, "Unsaved Canvas composition", "Save your Canvas project before continuing?", QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
        if answer == QMessageBox.StandardButton.Save:
            return self.saveProject()
        return answer == QMessageBox.StandardButton.Discard

    @pyqtSlot()
    def newProject(self):
        if self.confirm_discard():
            self.document = CanvasDocument()
            self._dirty = False
            self._project_path = ""
            self.changed.emit()
            self._message("New composition · add an image to set the canvas size")

    @pyqtSlot(result=bool)
    def saveProject(self):
        if not self.document.layers:
            self._message("Add an image before saving a project.")
            return False
        initial = self._project_path or str(Path.home() / "GENESIS-Exports" / "composition.genesis-canvas.json")
        target, _ = QFileDialog.getSaveFileName(None, "Save Canvas project", initial, "Canvas project (*.genesis-canvas.json)")
        if not target:
            return False
        if not target.lower().endswith(".json"):
            target += ".genesis-canvas.json"
        try:
            self.document.save_project(target)
        except (OSError, ValueError) as exc:
            self._message(str(exc))
            return False
        self._project_path = target
        self._dirty = False
        self.changed.emit()
        self._message("Project saved · keep its linked source images in place")
        return True

    @pyqtSlot()
    def openProject(self):
        if not self.confirm_discard():
            return
        target, _ = QFileDialog.getOpenFileName(None, "Open Canvas project", self._project_path or str(Path.home()), "Canvas project (*.json)")
        if not target:
            return
        try:
            loaded = CanvasDocument.load_project(target)
        except (OSError, ValueError) as exc:
            self._message(str(exc))
            return
        self.document = loaded
        self._dirty = False
        self._project_path = target
        self.changed.emit()
        self._message("Project opened · linked images loaded")

    @pyqtSlot()
    def exportPng(self):
        if not self.document.layers:
            self._message("Add an image before exporting.")
            return
        target, _ = QFileDialog.getSaveFileName(None, "Export composition", str(Path.home() / "GENESIS-Exports" / "composition.png"), "PNG (*.png)")
        if not target:
            return
        if not target.lower().endswith(".png"):
            target += ".png"
        try:
            self.document.export_png(target)
        except (OSError, ValueError) as exc:
            self._message(str(exc))
            return
        self._message("PNG exported · save the project to keep editable layers")
