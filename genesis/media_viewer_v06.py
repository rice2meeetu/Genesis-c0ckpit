#!/usr/bin/env python3
"""
GENESIS Photo Studio v0.6 - Multi-Face Analysis & Enhanced Export
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
        QComboBox, QGroupBox, QInputDialog, QDialog,
        QFormLayout, QLineEdit, QDialogButtonBox,
        QListWidget, QListWidgetItem, QTabWidget,
        QProgressBar, QCheckBox, QSpinBox
    )
    from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
    from PyQt6.QtGui import QPixmap, QIcon
except ImportError:
    print("ERROR: PyQt6 not installed.")
    sys.exit(1)

sys.path.append('.')
from genesis.face_detection.detector import FaceDetector
from genesis.face_groups_optimized import FaceGroupsOptimized
from genesis.auto_tag import AutoTagger, SmartSearch
from genesis.multi_face_analysis import MultiFaceAnalyzer
from genesis.enhanced_export import EnhancedExporter


class ExportWorker(QThread):
    """Background worker for exports"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, exporter, person_name, options):
        super().__init__()
        self.exporter = exporter
        self.person_name = person_name
        self.options = options
    
    def run(self):
        try:
            result = self.exporter.export_album_with_options(
                self.person_name,
                **self.options
            )
            if result:
                self.finished.emit(result)
            else:
                self.error.emit("Export failed")
        except Exception as e:
            self.error.emit(str(e))


class FaceViewerV06(QMainWindow):
    """Main window with multi-face analysis and enhanced export"""
    
    def __init__(self):
        super().__init__()
        self.db_path = os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.images = []
        self.current_path = None
        self.current_faces = []
        self.filtered_images = []
        
        self.detector = FaceDetector(self.db_path)
        self.groups = FaceGroupsOptimized(self.db_path)
        self.tagger = AutoTagger(self.db_path)
        self.searcher = SmartSearch(self.db_path)
        self.analyzer = MultiFaceAnalyzer(self.db_path)
        self.exporter = EnhancedExporter(self.db_path)
        
        self.init_ui()
        self.load_images()
    
    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("GENESIS v0.6 - Multi-Face Analysis & Export")
        self.setGeometry(100, 100, 1700, 950)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setSpacing(5)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_panel = self.create_gallery()
        splitter.addWidget(left_panel)
        
        right_panel = self.create_preview()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([500, 1200])
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
            QComboBox, QLineEdit, QListWidget, QSpinBox {
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
            QTabWidget::pane { border: 1px solid #444; background: #1e1e1e; }
            QTabBar::tab {
                background: #2a2a2a;
                color: #aaa;
                padding: 8px 16px;
                border: 1px solid #444;
            }
            QTabBar::tab:selected { background: #3a3a3a; color: #fff; }
            QCheckBox { color: #e0e0e0; }
            QProgressBar {
                border: 1px solid #444;
                border-radius: 4px;
                background: #2a2a2a;
                color: #fff;
            }
            QProgressBar::chunk { background: #4a8aca; }
        """)
    
    def create_gallery(self):
        """Create gallery panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(5)
        
        # Header with controls
        header = QHBoxLayout()
        title = QLabel("📷 Media Gallery")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        header.addWidget(title)
        header.addStretch()
        
        # Person filter
        self.person_filter = QComboBox()
        self.person_filter.addItem("All Photos")
        self.person_filter.addItem("---")
        self.update_person_list()
        self.person_filter.currentTextChanged.connect(self.filter_by_person)
        header.addWidget(QLabel("Filter:"))
        header.addWidget(self.person_filter)
        
        layout.addLayout(header)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search by person name...")
        self.search_input.returnPressed.connect(self.do_search)
        search_layout.addWidget(self.search_input)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.do_search)
        search_layout.addWidget(self.search_btn)
        
        self.clear_search_btn = QPushButton("✕ Clear")
        self.clear_search_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(self.clear_search_btn)
        
        layout.addLayout(search_layout)
        
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
        
        # Tabs for different features
        tabs = QTabWidget()
        
        # Face Detection Tab
        face_tab = QWidget()
        face_layout = QVBoxLayout(face_tab)
        
        face_controls = QHBoxLayout()
        self.detect_btn = QPushButton("🔍 Detect Faces")
        self.detect_btn.clicked.connect(self.detect_faces)
        face_controls.addWidget(self.detect_btn)
        
        self.add_btn = QPushButton("➕ Add Face")
        self.add_btn.clicked.connect(self.add_face)
        face_controls.addWidget(self.add_btn)
        
        self.tag_btn = QPushButton("🏷️ Auto-Tag")
        self.tag_btn.clicked.connect(self.auto_tag)
        face_controls.addWidget(self.tag_btn)
        
        face_controls.addStretch()
        self.face_label = QLabel("Faces: 0")
        face_controls.addWidget(self.face_label)
        
        face_layout.addLayout(face_controls)
        
        self.tags_label = QLabel("Tags: None")
        self.tags_label.setStyleSheet("color: #aaa; padding: 4px;")
        face_layout.addWidget(self.tags_label)
        
        tabs.addTab(face_tab, "👤 Face Detection")
        
        # Analysis Tab
        analysis_tab = QWidget()
        analysis_layout = QVBoxLayout(analysis_tab)
        
        analysis_controls = QHBoxLayout()
        self.analyze_btn = QPushButton("📊 Analyze Current")
        self.analyze_btn.clicked.connect(self.analyze_current)
        analysis_controls.addWidget(self.analyze_btn)
        
        self.group_photos_btn = QPushButton("👥 Find Group Photos")
        self.group_photos_btn.clicked.connect(self.find_group_photos)
        analysis_controls.addWidget(self.group_photos_btn)
        
        analysis_controls.addStretch()
        analysis_layout.addLayout(analysis_controls)
        
        self.analysis_results = QLabel("Analysis results will appear here")
        self.analysis_results.setStyleSheet("color: #aaa; padding: 8px;")
        self.analysis_results.setWordWrap(True)
        analysis_layout.addWidget(self.analysis_results)
        
        tabs.addTab(analysis_tab, "📊 Analysis")
        
        # Export Tab
        export_tab = QWidget()
        export_layout = QVBoxLayout(export_tab)
        
        # Export options
        export_options = QFormLayout()
        
        self.export_person = QLineEdit()
        self.export_person.setPlaceholderText("Enter person name...")
        export_options.addRow("Person:", self.export_person)
        
        self.export_format = QComboBox()
        self.export_format.addItems(['folder', 'zip'])
        export_options.addRow("Format:", self.export_format)
        
        self.export_resize = QCheckBox("Resize images")
        export_options.addRow("", self.export_resize)
        
        self.export_maxsize = QSpinBox()
        self.export_maxsize.setRange(100, 4000)
        self.export_maxsize.setValue(1920)
        export_options.addRow("Max Size:", self.export_maxsize)
        
        export_layout.addLayout(export_options)
        
        export_buttons = QHBoxLayout()
        self.export_btn = QPushButton("📤 Export Album")
        self.export_btn.clicked.connect(self.export_album)
        export_buttons.addWidget(self.export_btn)
        
        self.collage_btn = QPushButton("🎨 Create Collage")
        self.collage_btn.clicked.connect(self.create_collage)
        export_buttons.addWidget(self.collage_btn)
        
        self.social_btn = QPushButton("📱 Social Media Export")
        self.social_btn.clicked.connect(self.social_export)
        export_buttons.addWidget(self.social_btn)
        
        export_layout.addLayout(export_buttons)
        
        self.export_progress = QProgressBar()
        self.export_progress.setVisible(False)
        export_layout.addWidget(self.export_progress)
        
        tabs.addTab(export_tab, "📤 Export")
        
        layout.addWidget(tabs)
        
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
                
        except Exception as e:
            print(f"Error loading images: {e}")
    
    def display_thumbs(self):
        """Display thumbnails"""
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        if not self.filtered_images:
            label = QLabel("No images match the filter/search.")
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
            
            # Check if photo has tags
            tags = self.tagger.get_photo_tags(path)
            if tags:
                # Check if it's a group photo
                if len(tags) >= 2:
                    btn.setStyleSheet(btn.styleSheet() + """
                        QPushButton {
                            border: 3px solid #ff6b6b;
                        }
                    """)
                else:
                    btn.setStyleSheet(btn.styleSheet() + """
                        QPushButton {
                            border: 2px solid #4a8aca;
                        }
                    """)
            
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
    
    def do_search(self):
        """Execute search"""
        query = self.search_input.text().strip()
        if not query:
            return
        
        results = self.searcher.search(person=query, limit=50)
        if results:
            self.filtered_images = [(p, 0) for p in results]
            self.display_thumbs()
            if self.filtered_images:
                self.show_image(self.filtered_images[0][0])
                self.counter.setText(f"1 / {len(self.filtered_images)}")
            self.status.showMessage(f"Found {len(results)} photos")
        else:
            QMessageBox.information(self, "No Results", f"No photos found with '{query}'")
    
    def clear_search(self):
        """Clear search"""
        self.search_input.clear()
        self.filtered_images = self.images.copy()
        self.display_thumbs()
        if self.filtered_images:
            self.show_image(self.filtered_images[0][0])
            self.counter.setText(f"1 / {len(self.filtered_images)}")
    
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
        
        self.current_faces = []
        self.face_label.setText("Faces: 0")
        
        # Show tags
        tags = self.tagger.get_photo_tags(path)
        if tags:
            tag_text = "Tags: " + ", ".join([f"{t['name']} ({t['confidence']:.0%})" for t in tags])
            self.tags_label.setText(tag_text)
        else:
            self.tags_label.setText("Tags: None")
    
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
                from PyQt6.QtGui import QImage
                
                image = cv2.imread(self.current_path)
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
        
        from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QComboBox
        
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
    
    def auto_tag(self):
        """Auto-tag current photo"""
        if not self.current_path:
            QMessageBox.warning(self, "Warning", "No image selected!")
            return
        
        self.tag_btn.setEnabled(False)
        self.tag_btn.setText("⏳ Tagging...")
        QApplication.processEvents()
        
        try:
            tags = self.tagger.tag_photo(self.current_path)
            if tags:
                tag_text = "Tags: " + ", ".join([f"{t['name']} ({t['confidence']:.0%})" for t in tags])
                self.tags_label.setText(tag_text)
                QMessageBox.information(self, "Auto-Tag Complete", f"✅ Tagged {len(tags)} faces!")
                self.display_thumbs()
            else:
                self.tags_label.setText("Tags: No faces found")
                QMessageBox.information(self, "Auto-Tag", "No faces found to tag.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Auto-tag failed: {e}")
        
        self.tag_btn.setEnabled(True)
        self.tag_btn.setText("🏷️ Auto-Tag")
    
    def analyze_current(self):
        """Analyze current photo"""
        if not self.current_path:
            QMessageBox.warning(self, "Warning", "No image selected!")
            return
        
        tags = self.tagger.get_photo_tags(self.current_path)
        if not tags:
            self.analysis_results.setText("No faces found in this photo.")
            return
        
        face_count = len(tags)
        people = [t['name'] for t in tags if t['confidence'] > 0.5]
        
        result = f"📸 Photo Analysis:\n"
        result += f"  👥 Faces found: {face_count}\n"
        if people:
            result += f"  👤 People: {', '.join(people)}\n"
        if face_count >= 2:
            result += "  📷 This is a GROUP PHOTO!\n"
        
        # Get relationships
        if face_count >= 2:
            result += "\n🤝 Relationships in this photo:\n"
            for i in range(len(people)):
                for j in range(i+1, len(people)):
                    result += f"  - {people[i]} & {people[j]}\n"
        
        self.analysis_results.setText(result)
    
    def find_group_photos(self):
        """Find group photos"""
        group_photos = self.analyzer.find_group_photos(2)
        
        if group_photos:
            result = f"👥 Found {len(group_photos)} group photos (2+ people):\n"
            for i, gp in enumerate(group_photos[:5], 1):
                result += f"  {i}. {os.path.basename(gp['path'])} ({gp['face_count']} faces)\n"
            if len(group_photos) > 5:
                result += f"  ... and {len(group_photos) - 5} more"
            self.analysis_results.setText(result)
        else:
            self.analysis_results.setText("No group photos found.")
    
    def export_album(self):
        """Export album"""
        person = self.export_person.text().strip()
        if not person:
            QMessageBox.warning(self, "Warning", "Please enter a person name!")
            return
        
        self.export_btn.setEnabled(False)
        self.export_progress.setVisible(True)
        self.export_progress.setRange(0, 0)
        
        options = {
            'output_format': self.export_format.currentText(),
            'resize': self.export_resize.isChecked(),
            'max_size': self.export_maxsize.value(),
            'add_metadata': True
        }
        
        self.export_worker = ExportWorker(self.exporter, person, options)
        self.export_worker.finished.connect(self.on_export_finished)
        self.export_worker.error.connect(self.on_export_error)
        self.export_worker.start()
    
    def on_export_finished(self, result):
        self.export_progress.setVisible(False)
        self.export_btn.setEnabled(True)
        QMessageBox.information(self, "Export Complete", f"✅ Exported to:\n{result}")
    
    def on_export_error(self, error):
        self.export_progress.setVisible(False)
        self.export_btn.setEnabled(True)
        QMessageBox.critical(self, "Export Error", f"Error: {error}")
    
    def create_collage(self):
        """Create collage"""
        person = self.export_person.text().strip()
        if not person:
            QMessageBox.warning(self, "Warning", "Please enter a person name!")
            return
        
        result = self.exporter.export_photo_collage(person)
        if result:
            QMessageBox.information(self, "Collage Created", f"✅ Collage created:\n{result}")
    
    def social_export(self):
        """Social media export"""
        person = self.export_person.text().strip()
        if not person:
            QMessageBox.warning(self, "Warning", "Please enter a person name!")
            return
        
        # Ask which platform
        from PyQt6.QtWidgets import QInputDialog
        platforms = ['instagram', 'facebook', 'twitter', 'linkedin', 'pinterest', 'all']
        platform, ok = QInputDialog.getItem(self, "Social Media Export", 
                                           "Select platform:", platforms, 0, False)
        
        if ok and platform:
            result = self.exporter.export_social_media(person, platform)
            if result:
                msg = f"✅ Exported for {platform.upper()}\n"
                if isinstance(result, dict):
                    for p, path in result.items():
                        msg += f"  {p.upper()}: {path}\n"
                else:
                    msg += f"  {result}"
                QMessageBox.information(self, "Export Complete", msg)
    
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
    
    viewer = FaceViewerV06()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
