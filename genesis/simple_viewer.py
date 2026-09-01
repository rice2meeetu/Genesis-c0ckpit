#!/usr/bin/env python3
"""
GENESIS Simple Viewer - Standalone, no external dependencies
"""

import os
import sys
import sqlite3
from pathlib import Path

# Try to import PyQt6
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QScrollArea, QSplitter,
        QStatusBar, QFileDialog, QMessageBox
    )
    from PyQt6.QtCore import Qt, QSize
    from PyQt6.QtGui import QPixmap, QIcon
except ImportError:
    print("❌ PyQt6 not installed!")
    print("Run: sudo apt install python3-pyqt6 -y")
    sys.exit(1)


class SimpleViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_path = os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.images = []
        self.current_path = None
        self.batch_size = 50
        self.offset = 0
        
        self.init_ui()
        self.load_images()
    
    def init_ui(self):
        self.setWindowTitle("📷 GENESIS Simple Viewer")
        self.setGeometry(100, 100, 1400, 800)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Gallery
        left = self.create_gallery()
        splitter.addWidget(left)
        
        # Right: Preview
        right = self.create_preview()
        splitter.addWidget(right)
        
        splitter.setSizes([500, 900])
        layout.addWidget(splitter)
        
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")
        
        self.apply_style()
    
    def apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QWidget { background-color: #1e1e1e; color: #ddd; }
            QPushButton {
                background-color: #3a3a3a;
                color: #ddd;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #4a4a4a; }
            QLabel { color: #ddd; }
            QScrollArea { border: none; background: #1a1a1a; }
        """)
    
    def create_gallery(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("📸 Gallery")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        
        self.load_btn = QPushButton("📥 Load More")
        self.load_btn.clicked.connect(self.load_more)
        header.addWidget(self.load_btn)
        
        layout.addLayout(header)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(5)
        self.grid_layout.setContentsMargins(5, 5, 5, 5)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        scroll.setWidget(self.grid_widget)
        layout.addWidget(scroll)
        
        self.info = QLabel("0 images loaded")
        self.info.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(self.info)
        
        return panel
    
    def create_preview(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        self.preview = QLabel("Select an image")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(400)
        self.preview.setStyleSheet("""
            QLabel {
                border: 2px solid #444;
                border-radius: 8px;
                background-color: #1a1a1a;
                color: #666;
            }
        """)
        layout.addWidget(self.preview)
        
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
    
    def load_images(self):
        """Load first batch of images"""
        self.load_btn.setEnabled(False)
        self.load_btn.setText("⏳ Loading...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute("SELECT COUNT(*) FROM photos")
            total = cursor.fetchone()[0]
            self.total_images = total
            
            # Load first batch
            cursor.execute("""
                SELECT path FROM photos 
                ORDER BY id DESC 
                LIMIT ? OFFSET ?
            """, (self.batch_size, self.offset))
            
            results = cursor.fetchall()
            conn.close()
            
            for row in results:
                self.images.append(row[0])
            
            self.offset += len(results)
            self.display_thumbs()
            self.update_info()
            
            if self.offset < self.total_images:
                self.load_btn.setEnabled(True)
                self.load_btn.setText(f"📥 Load More ({self.total_images - self.offset} remaining)")
            else:
                self.load_btn.setEnabled(False)
                self.load_btn.setText("✅ All loaded")
            
            if self.images:
                self.show_image(self.images[0])
                self.counter.setText(f"1 / {len(self.images)}")
            
        except Exception as e:
            self.status.showMessage(f"❌ Error: {e}")
            self.load_btn.setEnabled(True)
            self.load_btn.setText("📥 Load More")
    
    def load_more(self):
        """Load next batch"""
        self.load_btn.setEnabled(False)
        self.load_btn.setText("⏳ Loading...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT path FROM photos 
                ORDER BY id DESC 
                LIMIT ? OFFSET ?
            """, (self.batch_size, self.offset))
            
            results = cursor.fetchall()
            conn.close()
            
            for row in results:
                self.images.append(row[0])
            
            self.offset += len(results)
            self.display_thumbs()
            self.update_info()
            
            if self.offset < self.total_images:
                self.load_btn.setEnabled(True)
                self.load_btn.setText(f"📥 Load More ({self.total_images - self.offset} remaining)")
            else:
                self.load_btn.setEnabled(False)
                self.load_btn.setText("✅ All loaded")
            
        except Exception as e:
            self.status.showMessage(f"❌ Error: {e}")
            self.load_btn.setEnabled(True)
            self.load_btn.setText("📥 Load More")
    
    def display_thumbs(self):
        """Display thumbnails"""
        # Clear existing if this is first load
        if self.offset <= self.batch_size:
            for i in reversed(range(self.grid_layout.count())):
                widget = self.grid_layout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
        
        start_idx = self.grid_layout.count()
        
        for idx in range(start_idx, len(self.images)):
            path = self.images[idx]
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
                QPushButton:hover { border: 2px solid #6a8aaa; }
            """)
            btn.clicked.connect(lambda checked, p=path: self.show_image(p))
            
            # Load thumbnail
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
        """Show image in preview"""
        self.current_path = path
        
        if not os.path.exists(path):
            return
        
        # Update counter
        for idx, p in enumerate(self.images):
            if p == path:
                self.counter.setText(f"{idx+1} / {len(self.images)}")
                break
        
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(600, 500, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
            self.preview.setPixmap(scaled)
            self.info_label.setText(os.path.basename(path))
        
        self.status.showMessage(f"Viewing: {os.path.basename(path)}")
    
    def update_info(self):
        self.info.setText(f"📸 {len(self.images)} / {self.total_images} images loaded")
    
    def prev_image(self):
        if not self.images or not self.current_path:
            return
        for idx, p in enumerate(self.images):
            if p == self.current_path and idx > 0:
                self.show_image(self.images[idx-1])
                break
    
    def next_image(self):
        if not self.images or not self.current_path:
            return
        for idx, p in enumerate(self.images):
            if p == self.current_path and idx < len(self.images) - 1:
                self.show_image(self.images[idx+1])
                break


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    viewer = SimpleViewer()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
