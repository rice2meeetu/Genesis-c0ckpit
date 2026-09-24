"""Qt bridge exposing tested GENESIS media operations to QML."""

from __future__ import annotations

import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QFileDialog

from genesis.media_functions import (
    OperationResult,
    batch_remove_background,
    batch_upscale,
    extract_media,
    face_organizer_scan,
    find_duplicates_in_folder,
    remove_background,
    upscale_enhance,
)


class MediaBridge(QObject):
    statusChanged = pyqtSignal()
    busyChanged = pyqtSignal()
    resultChanged = pyqtSignal()
    reviewChanged = pyqtSignal()
    _completed = pyqtSignal(object)
    _failed = pyqtSignal(str)
    _duplicatesReady = pyqtSignal(object)
    _facesReady = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.backend_router = None
        self._status = "Media tools ready"
        self._busy = False
        self._result_url = ""
        self._duplicate_pairs: list[dict] = []
        self._face_groups: list[dict] = []
        self._completed.connect(self._finish)
        self._failed.connect(self._fail)
        self._duplicatesReady.connect(self._set_duplicates)
        self._facesReady.connect(self._set_faces)

    @pyqtProperty(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @pyqtProperty(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @pyqtProperty(str, notify=resultChanged)
    def resultUrl(self) -> str:
        return self._result_url

    @pyqtProperty("QVariantList", notify=reviewChanged)
    def duplicatePairs(self) -> list[dict]:
        return self._duplicate_pairs

    @pyqtProperty("QVariantList", notify=reviewChanged)
    def faceGroups(self) -> list[dict]:
        return self._face_groups

    @pyqtSlot(object)
    def _set_duplicates(self, result: dict) -> None:
        pairs: list[dict] = []
        for group in result.get("exact_groups", []):
            if group:
                pairs.extend({"left": group[0], "right": other, "distance": 0, "kind": "EXACT"} for other in group[1:])
        pairs.extend({**item, "kind": "NEAR"} for item in result.get("near_pairs", []))
        self._duplicate_pairs = pairs
        self._face_groups = []
        self.reviewChanged.emit()
        self._set_busy(False)
        self._set_status(f"{len(pairs)} duplicate comparisons ready for review")

    @pyqtSlot(object)
    def _set_faces(self, groups: list[dict]) -> None:
        self._face_groups = groups
        self._duplicate_pairs = []
        self.reviewChanged.emit()
        self._set_busy(False)
        self._set_status(f"{len(groups)} face groups ready for review")

    @pyqtSlot(str)
    def openPath(self, value: str) -> None:
        raw = value
        if raw.startswith("file://"):
            from PyQt6.QtCore import QUrl
            raw = QUrl(raw).toLocalFile()
        path = Path(raw).expanduser().resolve()
        if path.exists():
            subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._set_status(f"Opened {path.name}")
        else:
            self._set_status("File no longer exists")

    @pyqtSlot()
    def openResultFolder(self) -> None:
        if not self._result_url:
            self._set_status("No saved result yet")
            return
        from PyQt6.QtCore import QUrl
        raw = QUrl(self._result_url).toLocalFile() if self._result_url.startswith("file://") else self._result_url
        path = Path(raw).expanduser().resolve()
        folder = path if path.is_dir() else path.parent
        if folder.is_dir():
            subprocess.Popen(["xdg-open", str(folder)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._set_status(f"Opened {folder.name or folder}")
        else:
            self._set_status("Result folder no longer exists")

    @pyqtSlot(str)
    def trashDuplicate(self, value: str) -> None:
        path = Path(value).expanduser().resolve()
        if not path.is_file():
            self._set_status("Duplicate file no longer exists")
            return
        if not shutil.which("gio"):
            self._set_status("Desktop Trash is unavailable; nothing removed")
            return
        if not any(str(path) in (pair.get("left"), pair.get("right")) for pair in self._duplicate_pairs):
            self._set_status("Choose a file from the current duplicate review")
            return
        try:
            result = subprocess.run(["gio", "trash", str(path)], capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.TimeoutExpired):
            self._set_status("Could not move duplicate to Trash; please check the file")
            return
        if result.returncode:
            self._set_status("Could not move duplicate to Trash")
            return
        self._duplicate_pairs = [
            pair for pair in self._duplicate_pairs
            if pair.get("left") != str(path) and pair.get("right") != str(path)
        ]
        self.reviewChanged.emit()
        self._set_status(f"Moved {path.name} to Trash · recoverable")

    def _set_status(self, value: str) -> None:
        self._status = value
        self.statusChanged.emit()

    def _set_busy(self, value: bool) -> None:
        self._busy = value
        self.busyChanged.emit()

    def _start(self, label: str, operation: Callable[[], OperationResult]) -> None:
        if self._busy:
            return
        self._result_url = ""
        self.resultChanged.emit()
        self._set_busy(True)
        self._set_status(f"{label}…")
        def run() -> None:
            try:
                self._completed.emit(operation())
            except Exception as exc:
                self._failed.emit(str(exc))

        threading.Thread(target=run, daemon=True).start()

    def _start_upscale(self, label, operation):
        from genesis.backend_routing import use_route
        try:
            route = self.backend_router.resolve_operation('upscale') if self.backend_router else None
        except ValueError as exc:
            self._set_status(str(exc))
            return
        def routed():
            if route is None:
                return operation()
            with use_route(route):
                return operation()
        self._start((route.destination + ' · ' if route else '') + label, routed)

    @pyqtSlot(object)
    def _finish(self, result: OperationResult) -> None:
        self._result_url = result.output.as_uri() if result.output else ""
        self.resultChanged.emit()
        self._set_busy(False)
        backend = "standard resize/enhance (AI unavailable)" if result.backend == "pillow" else result.backend
        failures = result.details.get("failures", [])
        completed = result.details.get("count")
        summary = f"Saved {completed} files with {backend}" if completed is not None else f"Saved with {backend}"
        if failures:
            summary += f" · {len(failures)} failed: {failures[0].get('error', 'unknown error')}"
        self._set_status(summary)

    @pyqtSlot(str)
    def _fail(self, message: str) -> None:
        self._set_busy(False)
        self._set_status(f"Failed: {message}")

    def _choose_image(self, title: str) -> Path | None:
        from genesis.qt_media_picker import choose_image
        value = choose_image(title)
        return Path(value) if value else None

    @pyqtSlot()
    def chooseAndRemoveBackground(self) -> None:
        if self._busy:
            return
        source = self._choose_image("Choose image for background removal")
        if not source:
            return
        target, _ = QFileDialog.getSaveFileName(
            None, "Save transparent cutout",
            str(source.with_name(source.stem + "_cutout.png")), "PNG (*.png)",
        )
        if target:
            self._start("Removing background", lambda: remove_background(source, target))

    @pyqtSlot(float)
    @pyqtSlot(float, bool)
    def chooseAndUpscale(self, scale: float = 2.0, prefer_ai: bool = True) -> None:
        if self._busy:
            return
        source = self._choose_image("Choose image to upscale")
        if not source:
            return
        target, _ = QFileDialog.getSaveFileName(
            None, "Save upscaled image",
            str(source.with_name(source.stem + f"_{scale:g}x.png")), "PNG (*.png)",
        )
        if target:
            if prefer_ai:
                self._start_upscale(f"AI upscaling {scale:g}×",
                    lambda: upscale_enhance(source, target, scale=scale, prefer_ai=True, require_ai=True))
            else:
                self._start(f"Standard resize {scale:g}×",
                    lambda: upscale_enhance(source, target, scale=scale, prefer_ai=False))
    def _choose_images(self, title: str) -> list[Path]:
        values, _ = QFileDialog.getOpenFileNames(
            None, title, str(Path.home()), "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)"
        )
        return [Path(value) for value in values]

    @pyqtSlot()
    def chooseAndBatchRemoveBackground(self) -> None:
        if self._busy:
            return
        sources = self._choose_images("Choose images for batch background removal")
        if not sources:
            return
        folder = QFileDialog.getExistingDirectory(None, "Choose output folder", str(Path.home()))
        if folder:
            self._start("Batch background removal", lambda: batch_remove_background(sources, folder))

    @pyqtSlot(float)
    def chooseAndBatchUpscale(self, scale: float = 4.0) -> None:
        if self._busy:
            return
        sources = self._choose_images("Choose images for batch upscale")
        if not sources:
            return
        folder = QFileDialog.getExistingDirectory(None, "Choose output folder", str(Path.home()))
        if folder:
            self._start_upscale(f"Batch upscaling {scale:g}×", lambda: batch_upscale(sources, folder, scale=scale))

    @pyqtSlot()
    def chooseAndFindDuplicates(self) -> None:
        if self._busy:
            return
        folder = QFileDialog.getExistingDirectory(None, "Choose image library to scan", str(Path.home()))
        if not folder:
            return
        self._set_busy(True)
        self._set_status("Scanning for duplicates…")
        def run() -> None:
            try:
                result = find_duplicates_in_folder(folder)
                self._duplicatesReady.emit(result)
            except Exception as exc:
                self._failed.emit(str(exc))
        threading.Thread(target=run, daemon=True).start()

    @pyqtSlot()
    def chooseAndScanFaces(self) -> None:
        if self._busy:
            return
        folder = QFileDialog.getExistingDirectory(None, "Choose photo library to organise", str(Path.home()))
        if not folder:
            return
        self._set_busy(True)
        self._set_status("Grouping faces…")
        def run() -> None:
            try:
                groups = face_organizer_scan(folder)
                self._facesReady.emit(groups)
            except Exception as exc:
                self._failed.emit(str(exc))
        threading.Thread(target=run, daemon=True).start()

    @pyqtSlot()
    def chooseAndExtractAudio(self) -> None:
        if self._busy:
            return
        source, _ = QFileDialog.getOpenFileName(
            None, "Choose video or audio source", str(Path.home()),
            "Media (*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.mpeg *.mpg *.mp3 *.wav *.flac *.m4a)",
        )
        if not source:
            return
        source_path = Path(source)
        target, _ = QFileDialog.getSaveFileName(
            None, "Save extracted MP3",
            str(source_path.with_name(source_path.stem + "_audio.mp3")), "MP3 (*.mp3)",
        )
        if target:
            self._start(
                "Extracting MP3",
                lambda: extract_media(source_path, target, kind="audio", audio_format="mp3"),
            )

    @pyqtSlot()
    def chooseAndExtractVideo(self) -> None:
        if self._busy:
            return
        source, _ = QFileDialog.getOpenFileName(
            None, "Choose video source", str(Path.home()),
            "Video (*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.mpeg *.mpg)",
        )
        if not source:
            return
        source_path = Path(source)
        target, _ = QFileDialog.getSaveFileName(
            None, "Save extracted video",
            str(source_path.with_name(source_path.stem + "_video.mp4")), "MP4 (*.mp4)",
        )
        if target:
            self._start(
                "Extracting video",
                lambda: extract_media(source_path, target, kind="video"),
            )

    @pyqtSlot()
    def clearResult(self) -> None:
        self._result_url = ""
        self.resultChanged.emit()
        self._set_status("Media tools ready")
