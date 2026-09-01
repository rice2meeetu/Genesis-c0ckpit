#!/usr/bin/env python3
"""
GENESIS Photo Studio v0.10 - Working Optimized Viewer
"""

import os
import sys
import sqlite3
import time
from pathlib import Path

# Import PyQt6
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QScrollArea, QFrame,
        QSplitter, QMessageBox, QStatusBar, QComboBox,
        QGroupBox, QInputDialog, QFileDialog
    )
    from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
    from PyQt6.QtGui import QPixmap, QIcon
except ImportError:
    print("ERROR: PyQt6 not installed.")
    print("Run: sudo apt install python3-pyqt6 -y")
    sys.exit(1)

sys.path.append('.')
from genesis.face_detection.detector import FaceDetector


class LoadWorker(QThread):
    """Background thread for loading images"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, db_path, offset=0, limit=50):
        super().__init__()
        self.db_path = db_path
        self.offset = offset
        self.limit = limit
        self.running = True

    def run(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get total count
            cursor.execute("SELECT COUNT(*) FROM photos")
            total = cursor.fetchone()[0]

            # Load batch
            cursor.execute("""
                SELECT path, id FROM photos
                ORDER BY id DESC
                LIMIT ? OFFSET ?
            """, (self.limit, self.offset))

            results = cursor.fetchall()
            conn.close()

            self.progress.emit(min(100, int((self.offset + len(results)) / total * 100) if total > 0 else 0))
            self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit([])


class ThumbnailWorker(QThread):
    """Background thread for loading thumbnails"""
    thumbnail_ready = pyqtSignal(str, QPixmap)

    def __init__(self, image_paths, size=150):
        super().__init__()
        self.image_paths = image_paths
        self.size = size
        self.running = True

    def run(self):
        for path in self.image_paths:
            if not self.running:
                break
            try:
                # Try cache first
                thumb_path = Path("cache/thumbnails") / (Path(path).stem + ".jpg")
                if thumb_path.exists():
                    pixmap = QPixmap(str(thumb_path))
                    if not pixmap.isNull():
                        scaled = pixmap.scaled(self.size, self.size,
                                              Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)
                        self.thumbnail_ready.emit(path, scaled)
                        continue

                # Generate from original
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    scaled = pixmap.scaled(self.size, self.size,
                                          Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)
                    self.thumbnail_ready.emit(path, scaled)
            except:
                pass


class OptimizedViewer(QMainWindow):
    """Main optimized viewer window"""

    def __init__(self):
        super().__init__()
        self.db_path = os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.detector = FaceDetector(self.db_path)
        self.images = []
        self.current_path = None
        self.batch_size = 50
        self.total_loaded = 0
        self.total_images = 0
        self.thumbnails = {}

        self.init_ui()
        self.load_initial_batch()

    def init_ui(self):
        self.setWindowTitle("📷 GENESIS v0.10 - Optimized Viewer")
        self.setGeometry(100, 100, 1500, 850)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setSpacing(5)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Gallery
        left_panel = self.create_gallery()
        splitter.addWidget(left_panel)

        # Right panel - Preview
        right_panel = self.create_preview()
        splitter.addWidget(right_panel)

        splitter.setSizes([500, 1000])
        layout.addWidget(splitter)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("📷 Optimized Viewer Ready")

        self.apply_theme()

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QWidget { background-color: #1e1e1e; color: #e0e0e0; }
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #4a4a4a; }
            QPushButton:disabled { background-color: #2a2a2a; color: #666; }
            QLabel { color: #e0e0e0; }
            QScrollArea { border: none; background: #1a1a1a; }
        """)

    def create_gallery(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Header
        header = QHBoxLayout()
        title = QLabel("📸 Media Gallery")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        header.addWidget(title)
        header.addStretch()

        self.load_more_btn = QPushButton("📥 Load More")
        self.load_more_btn.clicked.connect(self.load_more)
        header.addWidget(self.load_more_btn)

        layout.addLayout(header)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(5)
        self.grid_layout.setContentsMargins(5, 5, 5, 5)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll.setWidget(self.grid_widget)
        layout.addWidget(scroll)

        # Status
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(self.status_label)

        return panel

    def create_preview(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Preview
        self.preview = QLabel("Select an image to preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(400)
        self.preview.setStyleSheet("""
            QLabel {
                border: 2px solid #444;
                border-radius: 8px;
                background-color: #1a1a1a;
                color: #666;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.preview)

        # Info
        self.info_label = QLabel("No image selected")
        self.info_label.setStyleSheet("color: #888; padding: 5px;")
        layout.addWidget(self.info_label)

        # Navigation
        nav = QHBoxLayout()
        prev_btn = QPushButton("◀ Previous")
        prev_btn.clicked.connect(self.prev_image)
        nav.addWidget(prev_btn)

        next_btn = QPushButton("Next ▶")
        next_btn.clicked.connect(self.next_image)
        nav.addWidget(next_btn)

        nav.addStretch()
        self.counter = QLabel("0 / 0")
        nav.addWidget(self.counter)

        layout.addLayout(nav)

        return panel

    def load_initial_batch(self):
        self.load_more_btn.setEnabled(False)
        self.load_more_btn.setText("⏳ Loading...")

        # Get total count
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM photos")
            self.total_images = cursor.fetchone()[0]
            conn.close()
        except:
            self.total_images = 0

        self.worker = LoadWorker(self.db_path, 0, self.batch_size)
        self.worker.finished.connect(self.on_batch_loaded)
        self.worker.error.connect(self.on_load_error)
        self.worker.start()

    def on_batch_loaded(self, batch):
        if batch:
            self.images.extend(batch)
            self.total_loaded += len(batch)
            self.display_thumbs()
            self.update_status()

            remaining = self.total_images - self.total_loaded
            if remaining > 0:
                self.load_more_btn.setEnabled(True)
                self.load_more_btn.setText(f"📥 Load More ({remaining} remaining)")
            else:
                self.load_more_btn.setEnabled(False)
                self.load_more_btn.setText("✅ All loaded")

        self.status.showMessage(f"Loaded {self.total_loaded} images")

    def on_load_error(self, error):
        self.status.showMessage(f"❌ Error: {error}")
        self.load_more_btn.setEnabled(True)
        self.load_more_btn.setText("📥 Load More")

    def load_more(self):
        self.load_more_btn.setEnabled(False)
        self.load_more_btn.setText("⏳ Loading...")

        self.worker = LoadWorker(self.db_path, self.total_loaded, self.batch_size)
        self.worker.finished.connect(self.on_batch_loaded)
        self.worker.error.connect(self.on_load_error)
        self.worker.start()

    def display_thumbs(self):
        start_idx = self.grid_layout.count()

        for idx in range(start_idx, len(self.images)):
            path = self.images[idx][0]
            if not os.path.exists(path):
                continue

            btn = QPushButton()
            btn.setFixedSize(100, 100)
            btn.setStyleSheet("""
                QPushButton {
                    border: 2px solid #444;
                    border-radius: 4px;
                    background-color: #2a2a2a;
                }
                QPushButton:hover {
                    border: 2px solid #6a8aaa;
                    background-color: #3a3a3a;
                }
            """)
            btn.clicked.connect(lambda checked, p=path: self.show_image(p))

            # Try to load thumbnail
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(90, 90, Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.SmoothTransformation)
                btn.setIcon(QIcon(scaled))
                btn.setIconSize(QSize(90, 90))

            row = idx // 6
            col = idx % 6
            self.grid_layout.addWidget(btn, row, col)

    def show_image(self, path):
        self.current_path = path

        if not os.path.exists(path):
            return

        # Update counter
        for idx, (p, _) in enumerate(self.images):
            if p == path:
                self.counter.setText(f"{idx+1} / {len(self.images)}")
                break

        # Load and display
        start_time = time.time()
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(600, 500, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
            self.preview.setPixmap(scaled)
            load_time = (time.time() - start_time) * 1000
            self.info_label.setText(f"{os.path.basename(path)} ({load_time:.0f}ms)")

        self.status.showMessage(f"Viewing: {os.path.basename(path)}")

    def update_status(self):
        if self.total_images > 0:
            progress = (self.total_loaded / self.total_images) * 100
            self.status_label.setText(
                f"📸 {self.total_loaded} / {self.total_images} images ({progress:.1f}% loaded)"
            )

    def prev_image(self):
        if not self.images:
            return
        for idx, (path, _) in enumerate(self.images):
            if path == self.current_path and idx > 0:
                self.show_image(self.images[idx-1][0])
                break

    def next_image(self):
        if not self.images:
            return
        for idx, (path, _) in enumerate(self.images):
            if path == self.current_path and idx < len(self.images) - 1:
                self.show_image(self.images[idx+1][0])
                break


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    viewer = OptimizedViewer()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
