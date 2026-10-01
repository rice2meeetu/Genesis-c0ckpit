"""Qt adapter for Canvas composition and explicitly requested image processing."""
from pathlib import Path
import os
import uuid

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
        self.document.set_size(3840, 2160)
        self.document._undo.clear()
        self._status = "Add a background, then stack images or transparent cutouts."
        self._dirty = False
        self._project_path = ""
        self.media_tools = None
        self._pending_image = None

    @pyqtProperty(bool, notify=changed)
    def busy(self):
        return bool(self.media_tools and self.media_tools.busy)

    def attach_media_tools(self, tools):
        self.media_tools = tools
        tools.busyChanged.connect(self.changed.emit)
        tools.statusChanged.connect(lambda: self._message(tools.status))
        tools.resultChanged.connect(self._receive_processed_image)

    def _receive_processed_image(self):
        if not self._pending_image or not self.media_tools.resultUrl:
            return
        document, layer_id = self._pending_image
        self._pending_image = None
        if document is self.document:
            path = QUrl(self.media_tools.resultUrl).toLocalFile()
            self._apply(lambda: document.add_processed_layer(layer_id, path))

    @pyqtSlot(str, int)
    def processSelected(self, kind, scale):
        if self.busy or not self.selected or not self.media_tools:
            return
        if kind not in {"background remover", "upscale", "standard resize"} or scale not in (2, 4):
            self._message("Unsupported image operation")
            return
        source = Path(self.selected["path"])
        suffix = "cutout" if kind == "background remover" else f"{scale}x"
        # Persistent working assets keep saved Canvas projects reopenable.
        # Only project saving and final export ask the user for a destination.
        try:
            asset_root = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "genesis/canvas-assets"
            asset_root.mkdir(parents=True, exist_ok=True)
            target = asset_root / f"{uuid.uuid4().hex}_{suffix}.png"
        except OSError as exc:
            self._message(f"Cannot prepare Canvas result: {exc}")
            return
        self._pending_image = (self.document, self.selected["id"])
        self.media_tools.process_canvas_image(source, target, kind, scale)
        if not self.busy:
            self._pending_image = None

    @pyqtSlot(int, int, result=bool)
    def createProject(self, width, height):
        from genesis.canvas_document import _size
        try:
            _size(width, height)
        except ValueError as exc:
            self._message(str(exc))
            return False
        if self.busy or not self.confirm_discard():
            return False
        self.document = CanvasDocument()
        self.document.set_size(width, height)
        self.document._undo.clear()
        self._dirty = True
        self._project_path = ""
        self.changed.emit()
        self._message(f"New transparent canvas · {width} × {height} px")
        return True

    @pyqtSlot(int, int)
    def setCanvasSize(self, width, height):
        self._apply(lambda: self.document.set_size(width, height))

    @pyqtSlot(int, int)
    def setSelectedSize(self, width, height):
        if self.selected:
            self._apply(lambda: self.document.update_layer(self.selected["id"], width=width, height=height))

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
        if self.busy:
            self._message("Wait for image processing to finish before changing projects.")
            return False
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
        if not self.document.width:
            self._message("Create a canvas before saving a project.")
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
        if not self.document.width:
            self._message("Create a canvas before exporting.")
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
