"""GENESIS-owned ComfyUI graph editor. Graph edits do not submit GPU jobs."""
from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtCore import QObject, QSettings, QTimer, Qt, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget
from genesis.qt_media_picker import FilePicker as QFileDialog
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineUrlRequestInterceptor
from PyQt6.QtWebEngineWidgets import QWebEngineView

WORKFLOWS = Path(__file__).resolve().parent / "reference/pose_workflows"
USER_WORKFLOWS = Path.home() / "AI/ComfyUI/user/default/workflows"
LOCAL_COMFY = "http://127.0.0.1:8188"


def bundled_workflows() -> tuple[tuple[str, bool], ...]:
    """Return every bundled workflow and whether it contains a visual ComfyUI graph."""
    rows = []
    for path in sorted(WORKFLOWS.glob("*.json"), key=lambda item: item.name.casefold()):
        try:
            graph = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        visual = isinstance(graph, dict) and isinstance(graph.get("nodes"), list) and isinstance(graph.get("links"), list)
        if isinstance(graph, dict):
            rows.append((path.name, visual))
    return tuple(rows)


def visual_graph_names() -> tuple[str, ...]:
    return tuple(name for name, visual in bundled_workflows() if visual)


def graph_service_url() -> QUrl:
    """Use the same ComfyUI backend as GENESIS so remote-only nodes are available in the editor."""
    settings = QSettings("GENESIS", "c0ckpit")
    mode = (os.environ.get("GENESIS_BACKEND_MODE") or str(settings.value("backend/mode", "AUTO"))).upper()
    explicit = (os.environ.get("GENESIS_RUNPOD_URL") or os.environ.get("GENESIS_COMFY_URL") or "").strip()
    saved = str(settings.value("backend/runpod_url", "") or "").strip()
    endpoint = explicit or (saved if mode == "RUNPOD" else "") or LOCAL_COMFY
    return QUrl(endpoint.rstrip("/") + "/")


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
        self._workflow_rows = bundled_workflows()
        self._graph_names = tuple(name for name, _visual in self._workflow_rows)
        self._service_url = graph_service_url()
        self._status = "Open a saved graph to edit its complete nodes and connections. GPU queue is blocked here."

    @pyqtProperty(str, notify=statusChanged)
    def status(self):
        return self._status

    @pyqtProperty("QVariantList", constant=True)
    def workflows(self):
        return [{"name": name.removesuffix(".json").replace("GENESIS_", "").replace("_", " "),
                 "file": name, "visual": visual,
                 "format": "Visual graph" if visual else "Executable API workflow"}
                for name, visual in self._workflow_rows]

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
        self._view.setUrl(self._service_url)
        QTimer.singleShot(10000, self._loading_timeout)

    def _loading_timeout(self):
        if self._window and not self._loaded:
            self._set_status("ComfyUI graph service is slow or offline · use Reconnect")

    @pyqtSlot()
    def reconnect(self):
        if self._view:
            self._loaded = False
            self._service_url = graph_service_url()
            self._set_status("Connecting to ComfyUI graph service at " + self._service_url.toString())
            self._view.setUrl(self._service_url)
            QTimer.singleShot(10000, self._loading_timeout)

    def _on_loaded(self, success):
        if not success:
            self._loaded = False
            self._set_status("ComfyUI graph service is offline at " + self._service_url.toString() + " · use Reconnect")
            return
        self._loaded = True
        self._set_status("Graph editor ready at " + self._service_url.toString() + " · full UI graph preserved · prompt queue blocked")
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
        if name and name not in self._graph_names:
            self._set_status("Unknown GENESIS workflow")
            return
        if name:
            self._pending = WORKFLOWS / name
            if not self._pending.is_file():
                self._set_status("Workflow file is missing: " + name)
                return
            try:
                graph = json.loads(self._pending.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                self._set_status("Workflow could not be read: " + str(exc))
                return
            if not (isinstance(graph.get("nodes"), list) and isinstance(graph.get("links"), list)):
                self._set_status(name + " is an executable API workflow. It is used by Image Gen but has no saved visual node layout.")
                self._pending = None
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
