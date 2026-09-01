#!/usr/bin/env python3
"""
GENESIS Photo Studio v0.4 - Face Groups & Export (Fixed)
"""

import os
import sys
import sqlite3
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QScrollArea, QFrame,
        QSplitter, QFileDialog, QMessageBox, QStatusBar,
        QComboBox, QListWidget, QListWidgetItem, QGroupBox,
        QInputDialog, QDialog, QFormLayout, QLineEdit, QDialogButtonBox
    )
    from PyQt6.QtCore import Qt, QSize
    from PyQt6.QtGui import QPixmap, QIcon
except ImportError:
    print("ERROR: PyQt6 not installed.")
    sys.exit(1)

sys.path.append('.')
from genesis.face_detection.detector import FaceDetector
from genesis.face_groups_optimized import FaceGroupsOptimized


class FaceViewerV04Fixed(QMainWindow):
    """Main window with face groups and export"""
    
    def __init__(self):
        super().__init__()
        self.db_path = os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.images = []
        self.current_path = None
        self.current_faces = []
        self.filtered_images = []
        
        self.detector = FaceDetector(self.db_path)
        self.groups = FaceGroupsOptimized(self.db_path)
        
        self.init_ui()
        self.load_images()
    
    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("GENESIS v0.4 - Face Groups & Export")
        self.setGeometry(100, 100, 1600, 900)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setSpacing(5)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_panel = self.create_gallery()
        splitter.addWidget(left_panel)
        
        right_panel = self.create_preview()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([500, 1100])
        layout.addWidget(splitter)
        
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")
        
        self.apply_theme()
    
    def apply_theme(self):
        """Apply dark theme"""
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QWidget { background-color: #1e1e1e; color: #e0e0e0; }
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #4a4a4a; }
            QPushButton:disabled { background-color: #2a2a2a; color: #666; }
            QLabel { color: #e0e0e0; }
            QComboBox, QListWidget {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }
            QListWidget::item:selected { background-color: #4a6a8a; }
            QGroupBox {
                border: 1px solid #444;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                color: #e0e0e0;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
        """)
    
    def create_gallery(self):
        """Create gallery panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(5)
        
        header = QHBoxLayout()
        title = QLabel("📷 Media Gallery")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        header.addWidget(title)
        header.addStretch()
        
        self.person_filter = QComboBox()
        self.person_filter.addItem("All Photos")
        self.person_filter.addItem("---")
        self.update_person_list()
        self.person_filter.currentTextChanged.connect(self.filter_by_person)
        header.addWidget(QLabel("Filter:"))
        header.addWidget(self.person_filter)
        
        layout.addLayout(header)
        
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
        
        return panel
    
    def create_preview(self):
        """Create preview panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
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
        
        # Face Detection Group
        face_group = QGroupBox("👤 Face Detection")
        face_layout = QVBoxLayout(face_group)
        
        face_controls = QHBoxLayout()
        self.detect_btn = QPushButton("🔍 Detect Faces")
        self.detect_btn.clicked.connect(self.detect_faces)
        face_controls.addWidget(self.detect_btn)
        
        self.add_btn = QPushButton("➕ Add Face")
        self.add_btn.clicked.connect(self.add_face)
        face_controls.addWidget(self.add_btn)
        
        face_controls.addStretch()
        self.face_label = QLabel("Faces: 0")
        face_controls.addWidget(self.face_label)
        
        face_layout.addLayout(face_controls)
        layout.addWidget(face_group)
        
        # Export Group
        export_group = QGroupBox("📤 Export")
        export_layout = QVBoxLayout(export_group)
        
        export_controls = QHBoxLayout()
        self.export_album_btn = QPushButton("📁 Create Album")
        self.export_album_btn.clicked.connect(self.create_album)
        export_controls.addWidget(self.export_album_btn)
        
        export_controls.addStretch()
        export_layout.addLayout(export_controls)
        
        layout.addWidget(export_group)
        
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
    
    def update_person_list(self):
        """Update person filter dropdown"""
        self.person_filter.clear()
        self.person_filter.addItem("All Photos")
        
        for name in self.detector.known_names:
            self.person_filter.addItem(name)
    
    def load_images(self):
        """Load images from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='photos'
            """)
            
            if cursor.fetchone():
                cursor.execute("SELECT path, id FROM photos ORDER BY id DESC LIMIT 100")
                self.images = cursor.fetchall()
            else:
                self.images = []
            
            conn.close()
            
            self.filtered_images = self.images.copy()
            print(f"📸 Loaded {len(self.images)} images")
            self.display_thumbs()
            
            if self.images:
                self.counter.setText(f"1 / {len(self.images)}")
                self.show_image(self.images[0][0])
            else:
                self.status.showMessage("No images found.")
                
        except Exception as e:
            print(f"Error loading images: {e}")
    
    def display_thumbs(self):
        """Display thumbnails"""
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        if not self.filtered_images:
            label = QLabel("No images match the filter.")
            label.setStyleSheet("color: #666; padding: 20px;")
            self.grid_layout.addWidget(label, 0, 0)
            return
        
        cache_dir = Path("cache/thumbnails")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        for idx, (path, img_id) in enumerate(self.filtered_images):
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
                }
            """)
            btn.clicked.connect(lambda checked, p=path: self.show_image(p))
            
            thumb_path = cache_dir / (Path(path).stem + ".jpg")
            if thumb_path.exists():
                pixmap = QPixmap(str(thumb_path))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(90, 90, Qt.AspectRatioMode.KeepAspectRatio)
                    btn.setIcon(QIcon(scaled))
                    btn.setIconSize(QSize(90, 90))
            
            row = idx // 6
            col = idx % 6
            self.grid_layout.addWidget(btn, row, col)
    
    def filter_by_person(self, name: str):
        """Filter images by person"""
        if name == "All Photos" or name == "---":
            self.filtered_images = self.images.copy()
        else:
            photos = self.groups.get_person_photos_from_db(name)
            self.filtered_images = [(p, 0) for p in photos]
        
        self.display_thumbs()
        
        if self.filtered_images:
            self.show_image(self.filtered_images[0][0])
            self.counter.setText(f"1 / {len(self.filtered_images)}")
        
        self.status.showMessage(f"Filtered: {len(self.filtered_images)} images")
    
    def show_image(self, path):
        """Show image in preview"""
        self.current_path = path
        
        if not os.path.exists(path):
            return
        
        for idx, (p, id_) in enumerate(self.filtered_images):
            if p == path:
                self.counter.setText(f"{idx+1} / {len(self.filtered_images)}")
                break
        
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(600, 500, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
            self.preview.setPixmap(scaled)
            self.status.showMessage(f"Viewing: {os.path.basename(path)}")
        
        self.current_faces = []
        self.face_label.setText("Faces: 0")
    
    def detect_faces(self):
        """Detect faces in current image"""
        if not self.current_path:
            QMessageBox.warning(self, "Warning", "No image selected!")
            return
        
        self.detect_btn.setEnabled(False)
        self.detect_btn.setText("⏳ Detecting...")
        QApplication.processEvents()
        
        try:
            faces = self.detector.detect_faces(self.current_path)
            self.current_faces = faces
            self.face_label.setText(f"Faces: {len(faces)}")
            
            if faces:
                import cv2
                import numpy as np
                from PyQt6.QtGui import QImage
                
                image = cv2.imread(self.current_path)
                if image is None:
                    raise Exception("Could not load image")
                    
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                for face in faces:
                    loc = face['location']
                    top, right, bottom, left = loc['top'], loc['right'], loc['bottom'], loc['left']
                    cv2.rectangle(image_rgb, (left, top), (right, bottom), (0, 255, 0), 2)
                    label = f"{face['name']} ({face['confidence']:.0%})"
                    cv2.putText(image_rgb, label, (left, top-10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                height, width, channel = image_rgb.shape
                bytes_per_line = 3 * width
                qimage = QImage(image_rgb.data, width, height, bytes_per_line, 
                              QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qimage)
                scaled = pixmap.scaled(600, 500, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
                self.preview.setPixmap(scaled)
                
                details = [f"Found {len(faces)} faces:"]
                for i, face in enumerate(faces):
                    details.append(f"  Face {i+1}: {face['name']} ({face['confidence']:.0%}%)")
                QMessageBox.information(self, "Faces Found", "\n".join(details))
            else:
                QMessageBox.information(self, "No Faces", "No faces detected.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Face detection failed: {e}")
        
        self.detect_btn.setEnabled(True)
        self.detect_btn.setText("🔍 Detect Faces")
    
    def add_face(self):
        """Add a name to a detected face"""
        if not self.current_faces:
            QMessageBox.warning(self, "Warning", "No faces detected!")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Face Name")
        layout = QVBoxLayout(dialog)
        
        form = QFormLayout()
        face_combo = QComboBox()
        for i, face in enumerate(self.current_faces):
            face_combo.addItem(f"Face {i+1}: {face['name']} ({face['confidence']:.0%}%)")
        form.addRow("Select Face:", face_combo)
        
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter name...")
        form.addRow("Name:", name_input)
        layout.addLayout(form)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            face_idx = face_combo.currentIndex()
            name = name_input.text().strip()
            
            if not name:
                QMessageBox.warning(self, "Warning", "Please enter a name!")
                return
            
            face = self.current_faces[face_idx]
            success = self.detector.save_face(name, face['encoding'], self.current_path)
            
            if success:
                QMessageBox.information(self, "Success", f"✅ Face saved as '{name}'!")
                self.update_person_list()
                self.detect_faces()
            else:
                QMessageBox.critical(self, "Error", "❌ Failed to save face!")
    
    def create_album(self):
        """Create album for current person"""
        name, ok = QInputDialog.getText(self, "Create Album", "Enter person name:")
        if ok and name.strip():
            album_dir = self.groups.create_person_album(name.strip())
            if album_dir:
                QMessageBox.information(self, "Success", f"✅ Album created at:\n{album_dir}")
    
    def prev_image(self):
        """Go to previous image"""
        if not self.filtered_images:
            return
        
        for idx, (path, id_) in enumerate(self.filtered_images):
            if path == self.current_path and idx > 0:
                self.show_image(self.filtered_images[idx-1][0])
                break
    
    def next_image(self):
        """Go to next image"""
        if not self.filtered_images:
            return
        
        for idx, (path, id_) in enumerate(self.filtered_images):
            if path == self.current_path and idx < len(self.filtered_images) - 1:
                self.show_image(self.filtered_images[idx+1][0])
                break


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    viewer = FaceViewerV04Fixed()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
