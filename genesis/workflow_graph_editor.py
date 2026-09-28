"""GENESIS-owned ComfyUI graph editor. Graph edits do not submit GPU jobs."""
from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, Qt, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineUrlRequestInterceptor
from PyQt6.QtWebEngineWidgets import QWebEngineView

WORKFLOWS = Path(__file__).resolve().parent / "reference/pose_workflows"
USER_WORKFLOWS = Path.home() / "AI/ComfyUI/user/default/workflows"
LOCAL_COMFY = QUrl("http://127.0.0.1:8188/")
GRAPH_NAMES = (
    "GENESIS_MIRACLEIN_9B_T2I.json",
    "GENESIS_MIRACLEIN_9B_EDIT.json",
    "GENESIS_PORNMASTER_9B_T2I.json",
    "GENESIS_PORNMASTER_9B_EDIT.json",
    "GENESIS_DARKBEAST_9B_IDENTITY.json",
)


class GraphRequestGuard(QWebEngineUrlRequestInterceptor):
    """The editor permits graph/file operations but blocks Comfy prompt submission."""

    def interceptRequest(self, info):
        url = info.requestUrl()
        if (info.requestMethod() == b"POST"
                and url.host() in {"127.0.0.1", "localhost"}
                and url.path().rstrip("/") in {"/prompt", "/api/prompt"}):
            info.block(True)


class LocalGraphPage(QWebEnginePage):
    def acceptNavigationRequest(self, url, kind, is_main_frame):
        if is_main_frame and url.scheme() not in {"about", "http"}:
            return False
        if is_main_frame and url.scheme() == "http" and url.host() not in {"127.0.0.1", "localhost"}:
            return False
        return super().acceptNavigationRequest(url, kind, is_main_frame)

class WorkflowGraphBridge(QObject):
    statusChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._window = None
        self._view = None
        self._profile = None
        self._guard = None
        self._pending = None
        self._loaded = False
        self._status = "Open a saved graph to edit its nodes and connections. GPU queue is blocked here."

    @pyqtProperty(str, notify=statusChanged)
    def status(self):
        return self._status

    @pyqtProperty("QVariantList", constant=True)
    def workflows(self):
        return [{"name": name.removesuffix(".json").replace("GENESIS_", "").replace("_", " "),
                 "file": name} for name in GRAPH_NAMES]

    def _set_status(self, status):
        self._status = status
        self.statusChanged.emit()
        if self._window:
            self._window.setWindowTitle("GENESIS · Workflow Graph · " + status)

    def _create_window(self):
        window = QMainWindow()
        window.resize(1420, 900)
        window.setWindowTitle("GENESIS · Workflow Graph")
        container = QWidget(window)
        layout = QVBoxLayout(container)
        toolbar = QHBoxLayout()
        label = QLabel("ComfyUI graph · Edit and save here. GPU queue is blocked in this window.")
        toolbar.addWidget(label, 1)
        for caption, callback in (("Load JSON", self.chooseGraph),
                                  ("New graph", self.newGraph),
                                  ("Reconnect", self.reconnect),
                                  ("Save As…", self.saveGraphAs)):
            button = QPushButton(caption)
            button.clicked.connect(callback)
            toolbar.addWidget(button)
        layout.addLayout(toolbar)
        self._profile = QWebEngineProfile("GENESIS-Workflow-Editor", window)
        self._guard = GraphRequestGuard(self._profile)
        self._profile.setUrlRequestInterceptor(self._guard)
        self._view = QWebEngineView(container)
        self._view.setPage(LocalGraphPage(self._profile, self._view))
        self._view.loadFinished.connect(self._on_loaded)
        layout.addWidget(self._view, 1)
        window.setCentralWidget(container)
        self._window = window
        self._view.setUrl(LOCAL_COMFY)
        QTimer.singleShot(10000, self._loading_timeout)

    def _loading_timeout(self):
        if self._window and not self._loaded:
            self._set_status("ComfyUI graph service is slow or offline · use Reconnect")

    @pyqtSlot()
    def reconnect(self):
        if self._view:
            self._loaded = False
            self._set_status("Connecting to local ComfyUI graph service…")
            self._view.setUrl(LOCAL_COMFY)
            QTimer.singleShot(10000, self._loading_timeout)

    def _on_loaded(self, success):
        if not success:
            self._loaded = False
            self._set_status("Local ComfyUI is offline · use Reconnect after starting it")
            return
        self._loaded = True
        self._set_status("Graph editor ready · prompt queue blocked")
        if self._pending:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(900, self._load_pending)

    def _load_pending(self, retries=20):
        if not self._pending or not self._view:
            return
        path = self._pending
        graph = json.loads(path.read_text(encoding="utf-8"))
        payload = json.dumps(graph, separators=(",", ":"))
        code = ("(function(){if(!window.app || !app.graph || typeof app.loadGraphData !== 'function')"
                "return 'waiting'; Promise.resolve(app.loadGraphData(" + payload + "))"
                ".catch(e=>console.error('GENESIS graph load',e)); return 'started';})()")

        def result(state):
            if state == "waiting" and retries > 0:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(500, lambda: self._load_pending(retries - 1))
            elif state == "started":
                self._pending = None
                self._set_status("Loaded " + path.name + " · edit nodes, then Save As…")
            else:
                self._set_status("Graph could not load: " + str(state))
        self._view.page().runJavaScript(code, result)

    @pyqtSlot(str)
    def openGraph(self, name=""):
        if name and name not in GRAPH_NAMES:
            self._set_status("Unknown GENESIS workflow")
            return
        if name:
            self._pending = WORKFLOWS / name
            if not self._pending.is_file():
                self._set_status("Workflow file is missing: " + name)
                return
        if self._window is None:
            self._create_window()
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()
        if self._pending and self._loaded:
            self._load_pending()

    @pyqtSlot()
    def chooseGraph(self):
        path, _ = QFileDialog.getOpenFileName(
            self._window, "Load a ComfyUI graph", str(USER_WORKFLOWS), "JSON workflow (*.json)"
        )
        if not path:
            return
        try:
            graph = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(graph.get("nodes"), list) or not isinstance(graph.get("links"), list):
                raise ValueError("Choose a visual ComfyUI workflow JSON")
            self._pending = Path(path)
            if self._loaded:
                self._load_pending()
            else:
                self._set_status("Selected " + self._pending.name + " · waiting for graph service")
        except (OSError, ValueError) as exc:
            self._set_status(str(exc))

    @pyqtSlot()
    def newGraph(self):
        if self._view:
            self._clear_when_ready()

    def _clear_when_ready(self, retries=20):
        if not self._view:
            return
        def cleared(result):
            if result == "waiting" and retries > 0:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(500, lambda: self._clear_when_ready(retries - 1))
            elif result == "cleared":
                self._set_status("New blank graph · Save As… when ready")
        self._view.page().runJavaScript(
            "window.app && app.graph ? (app.graph.clear(), \"cleared\") : \"waiting\"", cleared
        )

    @pyqtSlot()
    def saveGraphAs(self):
        if not self._view:
            return
        USER_WORKFLOWS.mkdir(parents=True, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(
            self._window, "Save GENESIS workflow", str(USER_WORKFLOWS / "GENESIS_CUSTOM.json"),
            "JSON workflow (*.json)"
        )
        if not path:
            return
        target = Path(path)
        if target.suffix.lower() != ".json":
            target = target.with_suffix(".json")

        def save(graph):
            if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list):
                self._set_status("Graph is not ready to save")
                return
            temporary = target.with_name(target.name + ".tmp")
            try:
                temporary.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
                temporary.replace(target)
                self._set_status("Saved " + target.name)
            except OSError as exc:
                self._set_status("Save failed: " + str(exc))
        self._view.page().runJavaScript(
            "window.app && app.graph ? app.graph.serialize() : null", save
        )
