#!/usr/bin/env python3
"""
GENESIS Simple Viewer with Face Detection
"""

import os
import sys
import sqlite3
import pickle
from pathlib import Path
from datetime import datetime

# Try to import PyQt6
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QScrollArea, QSplitter,
        QStatusBar, QFileDialog, QMessageBox, QInputDialog,
        QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QComboBox
    )
    from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
    from PyQt6.QtGui import QPixmap, QIcon, QImage
except ImportError:
    print("❌ PyQt6 not installed!")
    print("Run: sudo apt install python3-pyqt6 -y")
    sys.exit(1)

# Add face_recognition
try:
    import face_recognition
    import cv2
    import numpy as np
    FACE_DETECTION_AVAILABLE = True
except ImportError:
    print("⚠️ Face detection not available")
    print("Run: pip install face_recognition opencv-python numpy --break-system-packages")
    FACE_DETECTION_AVAILABLE = False


class FaceDetector:
    """Simple face detector"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.known_encodings = []
        self.known_names = []
        self.load_faces()
    
    def load_faces(self):
        """Load known faces from database"""
        if not FACE_DETECTION_AVAILABLE:
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS face_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    encoding BLOB NOT NULL,
                    image_path TEXT,
                    created_at TEXT
                )
            """)
            
            cursor.execute("SELECT name, encoding FROM face_data")
            for name, encoding_blob in cursor.fetchall():
                if encoding_blob:
                    encoding = pickle.loads(encoding_blob)
                    self.known_names.append(name)
                    self.known_encodings.append(encoding)
            
            conn.close()
            print(f"✅ Loaded {len(self.known_names)} known faces")
        except Exception as e:
            print(f"Error loading faces: {e}")
    
    def detect_faces(self, image_path: str):
        """Detect faces in image"""
        if not FACE_DETECTION_AVAILABLE or not os.path.exists(image_path):
            return []
        
        try:
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            results = []
            for location, encoding in zip(face_locations, face_encodings):
                name = "Unknown"
                confidence = 0.0
                
                if self.known_encodings:
                    matches = face_recognition.compare_faces(self.known_encodings, encoding, 0.6)
                    if True in matches:
                        match_idx = matches.index(True)
                        name = self.known_names[match_idx]
                    
                    distances = face_recognition.face_distance(self.known_encodings, encoding)
                    confidence = 1.0 - min(distances) if len(distances) > 0 else 0.0
                
                results.append({
                    'location': location,
                    'name': name,
                    'confidence': confidence,
                    'encoding': encoding
                })
            
            return results
        except Exception as e:
            print(f"Error detecting faces: {e}")
            return []
    
    def save_face(self, name: str, encoding, image_path: str):
        """Save face to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            encoding_blob = pickle.dumps(encoding)
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO face_data (name, encoding, image_path, created_at)
                VALUES (?, ?, ?, ?)
            """, (name, encoding_blob, image_path, now))
            
            conn.commit()
            conn.close()
            
            # Update memory
            self.known_names.append(name)
            self.known_encodings.append(encoding)
            
            return True
        except Exception as e:
            print(f"Error saving face: {e}")
            return False


class SimpleViewerWithFaces(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db_path = os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.images = []
        self.current_path = None
        self.current_faces = []
        self.batch_size = 50
        self.offset = 0
        
        # Initialize face detector
        self.detector = FaceDetector(self.db_path)
        
        self.init_ui()
        self.load_images()
    
    def init_ui(self):
        self.setWindowTitle("👤 GENESIS Simple Viewer + Face Detection")
        self.setGeometry(100, 100, 1500, 850)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Gallery
        left = self.create_gallery()
        splitter.addWidget(left)
        
        # Right: Preview with controls
        right = self.create_preview()
        splitter.addWidget(right)
        
        splitter.setSizes([500, 1000])
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
            QPushButton:disabled { background-color: #2a2a2a; color: #666; }
            QLabel { color: #ddd; }
            QScrollArea { border: none; background: #1a1a1a; }
            QGroupBox {
                border: 1px solid #444;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
            QLineEdit, QComboBox {
                background-color: #2a2a2a;
                color: #ddd;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }
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
        
        # Preview
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
        
        # Face detection controls
        controls = QHBoxLayout()
        
        self.detect_btn = QPushButton("🔍 Detect Faces")
        self.detect_btn.clicked.connect(self.detect_faces)
        controls.addWidget(self.detect_btn)
        
        self.add_face_btn = QPushButton("➕ Add Face")
        self.add_face_btn.clicked.connect(self.add_face)
        controls.addWidget(self.add_face_btn)
        
        controls.addStretch()
        self.face_label = QLabel("Faces: 0")
        controls.addWidget(self.face_label)
        
        layout.addLayout(controls)
        
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
    
    def load_images(self):
        """Load first batch of images"""
        self.load_btn.setEnabled(False)
        self.load_btn.setText("⏳ Loading...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM photos")
            total = cursor.fetchone()[0]
            self.total_images = total
            
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
        self.current_faces = []
        self.face_label.setText("Faces: 0")
        
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
    
    def detect_faces(self):
        """Detect faces in current image"""
        if not self.current_path:
            QMessageBox.warning(self, "Warning", "No image selected!")
            return
        
        if not FACE_DETECTION_AVAILABLE:
            QMessageBox.warning(self, "Warning", "Face detection not available!")
            return
        
        self.detect_btn.setEnabled(False)
        self.detect_btn.setText("⏳ Detecting...")
        QApplication.processEvents()
        
        try:
            faces = self.detector.detect_faces(self.current_path)
            self.current_faces = faces
            self.face_label.setText(f"Faces: {len(faces)}")
            
            if faces:
                # Show image with face rectangles
                image = cv2.imread(self.current_path)
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                for face in faces:
                    top, right, bottom, left = face['location']
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
                
                # Show details
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
            QMessageBox.warning(self, "Warning", "No faces detected! Click 'Detect Faces' first.")
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
                self.detect_faces()  # Refresh
            else:
                QMessageBox.critical(self, "Error", "❌ Failed to save face!")
    
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
    if not FACE_DETECTION_AVAILABLE:
        print("⚠️ Face detection not available. Install face_recognition.")
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    viewer = SimpleViewerWithFaces()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
