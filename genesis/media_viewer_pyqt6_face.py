#!/usr/bin/env python3
"""
GENESIS Photo Studio v0.3 - PyQt6 with Face Detection
"""

import os
import sys
import sqlite3
import datetime
import pickle
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QScrollArea, QFrame,
        QSplitter, QFileDialog, QMessageBox, QStatusBar, QProgressBar,
        QLineEdit, QDialog, QDialogButtonBox, QFormLayout, QComboBox
    )
    from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread
    from PyQt6.QtGui import QPixmap, QIcon, QImage
except ImportError:
    print("ERROR: PyQt6 not installed. Run: pip install PyQt6 --break-system-packages")
    sys.exit(1)

try:
    import cv2
    import face_recognition
    import numpy as np
except ImportError:
    print("ERROR: Face detection packages not installed.")
    print("Run: pip install opencv-python face-recognition numpy --break-system-packages")
    sys.exit(1)


class FaceDetector:
    """Face detection engine for PyQt6"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.known_encodings = []
        self.known_names = []
        self.load_known_faces()
    
    def load_known_faces(self):
        """Load known faces from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='face_data'
            """)
            
            if cursor.fetchone():
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
        try:
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            results = []
            for i, (location, encoding) in enumerate(zip(face_locations, face_encodings)):
                name = "Unknown"
                confidence = 0.0
                
                if self.known_encodings:
                    matches = face_recognition.compare_faces(self.known_encodings, encoding, 0.6)
                    if True in matches:
                        match_idx = matches.index(True)
                        name = self.known_names[match_idx]
                    
                    distances = face_recognition.face_distance(self.known_encodings, encoding)
                    confidence = 1.0 - min(distances) if len(distances) > 0 else 0.0
                
                top, right, bottom, left = location
                results.append({
                    'location': {'top': top, 'right': right, 'bottom': bottom, 'left': left},
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
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS face_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    encoding BLOB NOT NULL,
                    image_path TEXT,
                    created_at TEXT
                )
            """)
            
            encoding_blob = pickle.dumps(encoding)
            now = datetime.datetime.now().isoformat()
            
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


class FaceViewer(QMainWindow):
    """Main window with face detection"""
    
    def __init__(self):
        super().__init__()
        self.db_path = os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.images = []
        self.current_path = None
        self.current_faces = []
        
        self.detector = FaceDetector(self.db_path)
        self.init_ui()
        self.load_images()
    
    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("GENESIS v0.3 - Face Detection (PyQt6)")
        self.setGeometry(100, 100, 1400, 800)
        
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setSpacing(5)
        
        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Gallery
        left_panel = self.create_gallery()
        splitter.addWidget(left_panel)
        
        # Right panel - Preview
        right_panel = self.create_preview()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([400, 1000])
        layout.addWidget(splitter)
        
        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")
    
    def create_gallery(self):
        """Create gallery panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(5)
        
        # Header
        header = QLabel("📷 Media Gallery")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        layout.addWidget(header)
        
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
        
        return panel
    
    def create_preview(self):
        """Create preview panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # Preview label
        self.preview = QLabel("Select an image to preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(400)
        self.preview.setStyleSheet("""
            QLabel {
                border: 2px solid #444;
                border-radius: 8px;
                background-color: #1a1a1a;
                color: #888;
            }
        """)
        layout.addWidget(self.preview)
        
        # Controls
        controls = QHBoxLayout()
        
        self.detect_btn = QPushButton("🔍 Detect Faces")
        self.detect_btn.clicked.connect(self.detect_faces)
        controls.addWidget(self.detect_btn)
        
        self.add_btn = QPushButton("➕ Add Face")
        self.add_btn.clicked.connect(self.add_face)
        controls.addWidget(self.add_btn)
        
        self.face_label = QLabel("Faces: 0")
        controls.addWidget(self.face_label)
        
        controls.addStretch()
        layout.addLayout(controls)
        
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
        
        # Apply dark style
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QWidget { background-color: #1e1e1e; color: #e0e0e0; }
            QPushButton {
                background-color: #3a3a3a;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #4a4a4a; }
            QPushButton:disabled { background-color: #2a2a2a; color: #666; }
            QLabel { color: #e0e0e0; }
            QComboBox, QLineEdit {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }
            QDialog {
                background-color: #2a2a2a;
            }
            QDialog QLabel {
                color: #e0e0e0;
            }
        """)
        
        return panel
    
    def load_images(self):
        """Load images from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if photos table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='photos'
            """)
            
            if cursor.fetchone():
                cursor.execute("SELECT path, id FROM photos ORDER BY id DESC LIMIT 50")
                self.images = cursor.fetchall()
            else:
                # Try to find images in current directory
                from pathlib import Path
                image_files = list(Path('.').glob('*.jpg')) + list(Path('.').glob('*.png'))
                self.images = [(str(f), 0) for f in image_files[:50]]
            
            conn.close()
            
            print(f"📸 Loaded {len(self.images)} images")
            self.display_thumbs()
            
            if self.images:
                self.counter.setText(f"1 / {len(self.images)}")
                self.show_image(self.images[0][0])
            else:
                self.status.showMessage("No images found. Add some photos to the database.")
                
        except Exception as e:
            print(f"Error loading images: {e}")
            self.status.showMessage(f"Error: {e}")
    
    def display_thumbs(self):
        """Display thumbnails"""
        # Clear grid
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        cache_dir = Path("cache/thumbnails")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        for idx, (path, img_id) in enumerate(self.images):
            if not os.path.exists(path):
                continue
            
            # Create thumbnail button
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
            
            # Try to load thumbnail
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
    
    def show_image(self, path):
        """Show image in preview"""
        self.current_path = path
        
        if not os.path.exists(path):
            return
        
        # Update counter
        for idx, (p, id_) in enumerate(self.images):
            if p == path:
                self.counter.setText(f"{idx+1} / {len(self.images)}")
                break
        
        # Load and display image
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(600, 500, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
            self.preview.setPixmap(scaled)
            self.status.showMessage(f"Viewing: {os.path.basename(path)}")
            
        # Reset face detection
        self.current_faces = []
        self.face_label.setText("Faces: 0")
    
    def detect_faces(self):
        """Detect faces in current image"""
        if not self.current_path or not os.path.exists(self.current_path):
            QMessageBox.warning(self, "Warning", "No image selected!")
            return
        
        self.detect_btn.setEnabled(False)
        self.detect_btn.setText("⏳ Detecting...")
        QApplication.processEvents()
        
        try:
            # Detect faces
            faces = self.detector.detect_faces(self.current_path)
            self.current_faces = faces
            
            # Update count
            self.face_label.setText(f"Faces: {len(faces)}")
            
            # Show image with face rectangles
            if faces:
                # Load image with OpenCV
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
                
                # Convert to QPixmap
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
                QMessageBox.information(self, "No Faces", "No faces detected in this image.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Face detection failed: {e}")
        
        self.detect_btn.setEnabled(True)
        self.detect_btn.setText("🔍 Detect Faces")
    
    def add_face(self):
        """Add a name to a detected face"""
        if not self.current_faces:
            QMessageBox.warning(self, "Warning", "No faces detected! Click 'Detect Faces' first.")
            return
        
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Face Name")
        layout = QVBoxLayout(dialog)
        
        # Face selection
        form = QFormLayout()
        face_combo = QComboBox()
        for i, face in enumerate(self.current_faces):
            face_combo.addItem(f"Face {i+1}: {face['name']} ({face['confidence']:.0%}%)")
        form.addRow("Select Face:", face_combo)
        
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter name...")
        form.addRow("Name:", name_input)
        layout.addLayout(form)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
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
                # Refresh detection
                self.detect_faces()
            else:
                QMessageBox.critical(self, "Error", "❌ Failed to save face!")
    
    def prev_image(self):
        """Go to previous image"""
        if not self.images:
            return
        
        for idx, (path, id_) in enumerate(self.images):
            if path == self.current_path and idx > 0:
                self.show_image(self.images[idx-1][0])
                break
    
    def next_image(self):
        """Go to next image"""
        if not self.images:
            return
        
        for idx, (path, id_) in enumerate(self.images):
            if path == self.current_path and idx < len(self.images) - 1:
                self.show_image(self.images[idx+1][0])
                break


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    viewer = FaceViewer()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
