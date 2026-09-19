"""Qt bridge exposing tested GENESIS media operations to QML."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QFileDialog

from genesis.media_functions import (
    OperationResult,
    extract_media,
    remove_background,
    upscale_enhance,
)


class MediaBridge(QObject):
    statusChanged = pyqtSignal()
    busyChanged = pyqtSignal()
    resultChanged = pyqtSignal()
    _completed = pyqtSignal(object)
    _failed = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._status = "Media tools ready"
        self._busy = False
        self._result_url = ""
        self._completed.connect(self._finish)
        self._failed.connect(self._fail)

    @pyqtProperty(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @pyqtProperty(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @pyqtProperty(str, notify=resultChanged)
    def resultUrl(self) -> str:
        return self._result_url

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

    @pyqtSlot(object)
    def _finish(self, result: OperationResult) -> None:
        self._result_url = result.output.as_uri() if result.output else ""
        self.resultChanged.emit()
        self._set_busy(False)
        backend = "standard resize/enhance (AI unavailable)" if result.backend == "pillow" else result.backend
        self._set_status(f"Saved with {backend}")

    @pyqtSlot(str)
    def _fail(self, message: str) -> None:
        self._set_busy(False)
        self._set_status(f"Failed: {message}")

    def _choose_image(self, title: str) -> Path | None:
        value, _ = QFileDialog.getOpenFileName(
            None, title, str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff)",
        )
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
    def chooseAndUpscale(self, scale: float = 2.0) -> None:
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
            self._start(
                f"Upscaling {scale:g}×",
                lambda: upscale_enhance(source, target, scale=scale, prefer_ai=True),
            )
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
            None, "Save video without audio",
            str(source_path.with_name(source_path.stem + "_silent.mp4")), "MP4 (*.mp4)",
        )
        if target:
            self._start(
                "Extracting silent video",
                lambda: extract_media(source_path, target, kind="video"),
            )

    @pyqtSlot()
    def clearResult(self) -> None:
        self._result_url = ""
        self.resultChanged.emit()
        self._set_status("Media tools ready")
