#!/usr/bin/env python3
"""
GENESIS Photo Studio - Media Viewer v0.2.1
Copyright (c) 2026 GENESIS Project

Features:
- Selectable thumbnail grid
- Preview window with metadata
- Filename, dimensions, filesize, modified date
- Navigation controls
"""

import os
import sys
import sqlite3
import datetime
from pathlib import Path
from typing import Dict

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QScrollArea, QFrame,
        QSplitter, QFileDialog, QMessageBox, QStatusBar, QProgressBar
    )
    from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread
    from PyQt6.QtGui import QPixmap, QIcon
except ImportError:
    print("ERROR: PyQt6 not installed. Run: pip install PyQt6 --break-system-packages")
    sys.exit(1)


class ThumbnailLoader(QThread):
    """Load thumbnails in background thread"""
    thumbnail_loaded = pyqtSignal(int, QPixmap)
    
    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self.running = True
        
    def run(self):
        """Load thumbnails from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, path, thumbnail, width, height, file_size, modified_date
                FROM photos
                WHERE thumbnail IS NOT NULL
                ORDER BY modified_date DESC
            """)
            
            for row in cursor.fetchall():
                if not self.running:
                    break
                media_id, file_path, thumbnail_data, width, height, file_size, modified_date = row
                
                if thumbnail_data:
                    pixmap = QPixmap()
                    pixmap.loadFromData(thumbnail_data)
                    if not pixmap.isNull():
                        scaled = pixmap.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, 
                                               Qt.TransformationMode.SmoothTransformation)
                        self.thumbnail_loaded.emit(media_id, scaled)
            
            conn.close()
        except Exception as e:
            print(f"Error loading thumbnails: {e}")
    
    def stop(self):
        self.running = False


class MediaViewer(QMainWindow):
    """Main Media Viewer Window"""
    
    def __init__(self, db_path: str = None):
        super().__init__()
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.thumbnails = {}
        self.selected_id = None
        self.loader = None
        self.thumbnail_buttons = {}
        
        self.init_ui()
        self.load_thumbnails()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("GENESIS Photo Studio - Media Viewer v0.2.1")
        self.setGeometry(100, 100, 1200, 800)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left_panel = self.create_thumbnail_panel()
        splitter.addWidget(left_panel)
        right_panel = self.create_preview_panel()
        splitter.addWidget(right_panel)
        splitter.setSizes([480, 720])
        main_layout.addWidget(splitter)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(150)
        self.progress.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress)
        
        self.apply_styles()
        
    def create_thumbnail_panel(self) -> QWidget:
        """Create the thumbnail grid panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        header = QLabel("📷 Media Gallery")
        header.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        layout.addWidget(header)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(8)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        scroll.setWidget(self.grid_widget)
        layout.addWidget(scroll)
        
        controls = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_thumbnails)
        controls.addWidget(refresh_btn)
        controls.addStretch()
        count_label = QLabel("Total: 0")
        count_label.setObjectName("count_label")
        controls.addWidget(count_label)
        layout.addLayout(controls)
        
        return panel
    
    def create_preview_panel(self) -> QWidget:
        """Create the preview and metadata panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(400)
        self.preview_label.setStyleSheet("""
            QLabel {
                border: 2px solid #555;
                border-radius: 8px;
                background-color: #1a1a1a;
            }
        """)
        self.preview_label.setText("Select an image to preview")
        layout.addWidget(self.preview_label)
        
        metadata_frame = QFrame()
        metadata_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #444;
                border-radius: 6px;
                background-color: #2a2a2a;
                padding: 8px;
            }
        """)
        metadata_layout = QVBoxLayout(metadata_frame)
        metadata_layout.setSpacing(4)
        
        self.metadata_labels = {}
        fields = [
            ("filename", "📄 Filename:", ""),
            ("dimensions", "📐 Dimensions:", ""),
            ("filesize", "💾 Filesize:", ""),
            ("modified", "📅 Modified:", ""),
            ("id", "🆔 ID:", "")
        ]
        
        for key, label, value in fields:
            container = QWidget()
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(2, 2, 2, 2)
            
            label_widget = QLabel(label)
            label_widget.setStyleSheet("font-weight: bold; color: #aaa;")
            label_widget.setFixedWidth(100)
            
            value_widget = QLabel(value)
            value_widget.setObjectName(f"metadata_{key}")
            value_widget.setStyleSheet("color: #fff;")
            value_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            
            container_layout.addWidget(label_widget)
            container_layout.addWidget(value_widget, 1)
            metadata_layout.addWidget(container)
            self.metadata_labels[key] = value_widget
        
        layout.addWidget(metadata_frame)
        
        nav_layout = QHBoxLayout()
        prev_btn = QPushButton("◀ Previous")
        prev_btn.clicked.connect(self.navigate_prev)
        next_btn = QPushButton("Next ▶")
        next_btn.clicked.connect(self.navigate_next)
        export_btn = QPushButton("💾 Export")
        export_btn.clicked.connect(self.export_selected)
        
        nav_layout.addWidget(prev_btn)
        nav_layout.addWidget(next_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(export_btn)
        layout.addLayout(nav_layout)
        
        return panel
    
    def apply_styles(self):
        """Apply dark theme stylesheet"""
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QLabel { color: #e0e0e0; }
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border: 1px solid #777;
            }
            QPushButton:pressed { background-color: #2a2a2a; }
            QScrollArea { border: none; background-color: #1a1a1a; }
            #count_label { color: #aaa; font-size: 12px; }
        """)
    
    def load_thumbnails(self):
        """Load thumbnails from database"""
        if not os.path.exists(self.db_path):
            self.status_bar.showMessage(f"Database not found: {self.db_path}")
            return
        
        self.clear_grid()
        self.progress.setVisible(True)
        self.progress.setValue(0)
        
        self.loader = ThumbnailLoader(self.db_path)
        self.loader.thumbnail_loaded.connect(self.add_thumbnail)
        self.loader.finished.connect(self.on_load_finished)
        self.loader.start()
        
        self.status_bar.showMessage("Loading thumbnails...")
    
    def clear_grid(self):
        """Clear all thumbnails from grid"""
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.thumbnails.clear()
        self.thumbnail_buttons.clear()
        self.selected_id = None
        self.update_count()
    
    def add_thumbnail(self, media_id: int, pixmap: QPixmap):
        """Add a thumbnail to the grid"""
        btn = QPushButton()
        btn.setIcon(QIcon(pixmap))
        btn.setIconSize(QSize(140, 140))
        btn.setFixedSize(QSize(150, 150))
        btn.setStyleSheet("""
            QPushButton {
                border: 2px solid #444;
                border-radius: 4px;
                background-color: #2a2a2a;
                padding: 2px;
            }
            QPushButton:hover {
                border: 2px solid #6a8aaa;
                background-color: #3a3a3a;
            }
            QPushButton:checked {
                border: 3px solid #4a8aca;
                background-color: #3a5a7a;
            }
        """)
        btn.setCheckable(True)
        
        self.thumbnails[media_id] = pixmap
        self.thumbnail_buttons[media_id] = btn
        btn.clicked.connect(lambda checked, mid=media_id: self.select_thumbnail(mid))
        
        row = len(self.thumbnails) // 6
        col = len(self.thumbnails) % 6
        self.grid_layout.addWidget(btn, row, col)
        self.update_count()
    
    def select_thumbnail(self, media_id: int):
        """Select a thumbnail and show preview"""
        for mid, btn in self.thumbnail_buttons.items():
            btn.setChecked(mid == media_id)
        
        self.selected_id = media_id
        
        if media_id in self.thumbnails:
            pixmap = self.thumbnails[media_id]
            scaled = pixmap.scaled(600, 500, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
            self.preview_label.setPixmap(scaled)
            self.load_metadata(media_id)
            self.status_bar.showMessage(f"Selected ID: {media_id}")
    
    def load_metadata(self, media_id: int):
        """Load metadata for selected media"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT path, width, height, file_size, modified_date
                FROM photos
                WHERE id = ?
            """, (media_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                file_path, width, height, file_size, modified_date = row
                
                self.metadata_labels["filename"].setText(os.path.basename(file_path))
                self.metadata_labels["dimensions"].setText(f"{width} × {height}")
                
                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                self.metadata_labels["filesize"].setText(size_str)
                
                if modified_date:
                    try:
                        dt = datetime.datetime.fromisoformat(modified_date)
                        self.metadata_labels["modified"].setText(dt.strftime("%Y-%m-%d %H:%M:%S"))
                    except:
                        self.metadata_labels["modified"].setText(str(modified_date))
                else:
                    self.metadata_labels["modified"].setText("Unknown")
                
                self.metadata_labels["id"].setText(str(media_id))
                
        except Exception as e:
            print(f"Error loading metadata: {e}")
    
    def navigate_prev(self):
        """Navigate to previous image"""
        if not self.thumbnails:
            return
        ids = sorted(self.thumbnails.keys())
        if self.selected_id is None:
            self.select_thumbnail(ids[-1] if ids else None)
            return
        try:
            idx = ids.index(self.selected_id)
            self.select_thumbnail(ids[idx - 1] if idx > 0 else ids[-1])
        except ValueError:
            self.select_thumbnail(ids[0] if ids else None)
    
    def navigate_next(self):
        """Navigate to next image"""
        if not self.thumbnails:
            return
        ids = sorted(self.thumbnails.keys())
        if self.selected_id is None:
            self.select_thumbnail(ids[0] if ids else None)
            return
        try:
            idx = ids.index(self.selected_id)
            self.select_thumbnail(ids[idx + 1] if idx < len(ids) - 1 else ids[0])
        except ValueError:
            self.select_thumbnail(ids[0] if ids else None)
    
    def export_selected(self):
        """Export selected image"""
        if self.selected_id is None:
            QMessageBox.information(self, "Export", "No image selected")
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT path FROM photos WHERE id = ?", (self.selected_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                source_path = row[0]
                if os.path.exists(source_path):
                    dest_path, _ = QFileDialog.getSaveFileName(
                        self, "Export Image", 
                        os.path.basename(source_path),
                        "Images (*.jpg *.jpeg *.png *.gif *.bmp)"
                    )
                    if dest_path:
                        import shutil
                        shutil.copy2(source_path, dest_path)
                        QMessageBox.information(self, "Export", f"Image exported to:\n{dest_path}")
                else:
                    QMessageBox.warning(self, "Export", f"Source file not found:\n{source_path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Error exporting: {e}")
    
    def on_load_finished(self):
        """Handle thumbnail loading completion"""
        self.progress.setVisible(False)
        self.status_bar.showMessage(f"Loaded {len(self.thumbnails)} thumbnails")
        if self.thumbnails and self.selected_id is None:
            self.select_thumbnail(sorted(self.thumbnails.keys())[0])
    
    def update_count(self):
        """Update the thumbnail count label"""
        count_label = self.findChild(QLabel, "count_label")
        if count_label:
            count_label.setText(f"Total: {len(self.thumbnails)}")
    
    def closeEvent(self, event):
        """Clean up on close"""
        if self.loader:
            self.loader.stop()
            self.loader.wait()
        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("GENESIS Media Viewer")
    
    db_path = os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
    if not os.path.exists(db_path):
        db_path = "database/genesis.db"
    
    viewer = MediaViewer(db_path)
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
