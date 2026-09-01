#!/usr/bin/env python3
"""
GENESIS Photo Studio v0.7 - Performance Optimizations
Faster loading, caching, and lazy loading
"""

import os
import sys
import sqlite3
from pathlib import Path
import time

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QScrollArea, QFrame,
        QSplitter, QMessageBox, QStatusBar, QComboBox,
        QGroupBox, QInputDialog, QDialog, QFormLayout,
        QLineEdit, QDialogButtonBox, QProgressBar,
        QTabWidget, QCheckBox, QSpinBox, QListWidget
    )
    from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer
    from PyQt6.QtGui import QPixmap, QIcon
except ImportError:
    print("ERROR: PyQt6 not installed.")
    sys.exit(1)

sys.path.append('.')
from genesis.optimized_cache import OptimizedCache, LazyLoader, OptimizedDB
from genesis.face_detection.detector import FaceDetector
from genesis.face_groups_optimized import FaceGroupsOptimized
from genesis.auto_tag import AutoTagger
from genesis.multi_face_analysis import MultiFaceAnalyzer


class LoadWorker(QThread):
    """Background loading worker"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, loader, batch_size=50):
        super().__init__()
        self.loader = loader
        self.batch_size = batch_size
        self.running = True
    
    def run(self):
        try:
            total = self.loader.get_total_count()
            images = []
            offset = 0
            
            while self.running and offset < total:
                batch = self.loader.load_batch(offset, self.batch_size)
                images.extend(batch)
                self.progress.emit(int((offset + len(batch)) / total * 100))
                offset += self.batch_size
            
            self.finished.emit(images)
        except Exception as e:
            self.error.emit(str(e))
    
    def stop(self):
        self.running = False


class ThumbnailWorker(QThread):
    """Background thumbnail generator"""
    thumbnail_ready = pyqtSignal(str, QPixmap)
    progress = pyqtSignal(int)
    finished = pyqtSignal()
    
    def __init__(self, cache, image_paths, size=150):
        super().__init__()
        self.cache = cache
        self.image_paths = image_paths
        self.size = size
        self.running = True
    
    def run(self):
        total = len(self.image_paths)
        for i, path in enumerate(self.image_paths):
            if not self.running:
                break
            try:
                # Get cached thumbnail
                img = self.cache.get_cached_thumbnail(path, self.size)
                if img:
                    # Convert to QPixmap
                    from PyQt6.QtGui import QImage
                    if img.mode == 'RGB':
                        data = img.tobytes('raw', 'RGB')
                        qimage = QImage(data, img.width, img.height, 
                                      img.width * 3, QImage.Format.Format_RGB888)
                    else:
                        img = img.convert('RGB')
                        data = img.tobytes('raw', 'RGB')
                        qimage = QImage(data, img.width, img.height,
                                      img.width * 3, QImage.Format.Format_RGB888)
                    
                    pixmap = QPixmap.fromImage(qimage)
                    if not pixmap.isNull():
                        scaled = pixmap.scaled(self.size, self.size, 
                                              Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)
                        self.thumbnail_ready.emit(path, scaled)
                
                self.progress.emit(int((i + 1) / total * 100))
            except Exception as e:
                # Skip failed thumbnails
                pass
        
        self.finished.emit()


class FaceViewerV07(QMainWindow):
    """Main window with performance optimizations"""
    
    def __init__(self):
        super().__init__()
        self.db_path = os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.images = []
        self.current_path = None
        self.filtered_images = []
        self.thumbnails = {}
        self.loading = False
        self.batch_size = 50
        self.current_batch = 0
        self.total_images = 0
        self.loaded_images = []
        
        # Initialize optimized components
        self.cache = OptimizedCache(self.db_path)
        self.loader = LazyLoader(self.db_path)
        self.db_optimized = OptimizedDB(self.db_path)
        self.detector = FaceDetector(self.db_path)
        self.groups = FaceGroupsOptimized(self.db_path)
        self.tagger = AutoTagger(self.db_path)
        self.analyzer = MultiFaceAnalyzer(self.db_path)
        
        # Workers
        self.load_worker = None
        self.thumb_worker = None
        
        self.init_ui()
        self.load_images()
    
    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("⚡ GENESIS v0.7 - Performance Optimized")
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
        
        # Performance stats in status bar
        self.stats_label = QLabel("⚡ Performance: Ready")
        self.status.addPermanentWidget(self.stats_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status.addPermanentWidget(self.progress_bar)
        
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
                text-align: center;
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
        title = QLabel("⚡ Media Gallery")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        header.addWidget(title)
        header.addStretch()
        
        # Performance settings
        batch_label = QLabel("Batch:")
        header.addWidget(batch_label)
        self.batch_combo = QComboBox()
        self.batch_combo.addItems(['25', '50', '100', '200'])
        self.batch_combo.setCurrentText('50')
        self.batch_combo.currentTextChanged.connect(self.change_batch_size)
        header.addWidget(self.batch_combo)
        
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
        
        # Load more button
        load_more_layout = QHBoxLayout()
        self.load_more_btn = QPushButton("📥 Load More")
        self.load_more_btn.clicked.connect(self.load_more)
        load_more_layout.addWidget(self.load_more_btn)
        load_more_layout.addStretch()
        
        self.image_count_label = QLabel("0 images loaded")
        load_more_layout.addWidget(self.image_count_label)
        
        layout.addLayout(load_more_layout)
        
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
        
        # Tabs
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
        
        # Cache Tab
        cache_tab = QWidget()
        cache_layout = QVBoxLayout(cache_tab)
        
        cache_controls = QHBoxLayout()
        self.clear_cache_btn = QPushButton("🗑️ Clear Cache")
        self.clear_cache_btn.clicked.connect(self.clear_cache)
        cache_controls.addWidget(self.clear_cache_btn)
        
        self.preload_btn = QPushButton("📥 Preload Thumbnails")
        self.preload_btn.clicked.connect(self.preload_thumbnails)
        cache_controls.addWidget(self.preload_btn)
        
        cache_controls.addStretch()
        cache_layout.addLayout(cache_controls)
        
        self.cache_stats_label = QLabel("Cache stats: Loading...")
        self.cache_stats_label.setStyleSheet("color: #aaa; padding: 8px;")
        cache_layout.addWidget(self.cache_stats_label)
        
        tabs.addTab(cache_tab, "💾 Cache")
        
        # Export Tab
        export_tab = QWidget()
        export_layout = QVBoxLayout(export_tab)
        
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
        
        export_layout.addLayout(export_buttons)
        
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
    
    def change_batch_size(self, size):
        """Change batch size"""
        self.batch_size = int(size)
        self.status.showMessage(f"Batch size: {self.batch_size}")
    
    def load_images(self):
        """Load images with lazy loading"""
        if self.loading:
            return
        
        self.loading = True
        self.load_more_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.status.showMessage("Loading images...")
        
        # Start background loading
        self.load_worker = LoadWorker(self.loader, self.batch_size)
        self.load_worker.progress.connect(self.on_load_progress)
        self.load_worker.finished.connect(self.on_load_finished)
        self.load_worker.error.connect(self.on_load_error)
        self.load_worker.start()
    
    def on_load_progress(self, value):
        """Update load progress"""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(value)
    
    def on_load_finished(self, images):
        """Finish loading"""
        self.loading = False
        self.load_more_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.images = images
        self.loaded_images = images.copy()
        self.filtered_images = images.copy()
        self.total_images = len(images)
        
        self.image_count_label.setText(f"{len(self.images)} images loaded")
        self.update_cache_stats()
        
        # Display thumbnails
        self.display_thumbs()
        
        if self.images:
            self.counter.setText(f"1 / {len(self.images)}")
            self.show_image(self.images[0][0])
        
        self.status.showMessage(f"✅ Loaded {len(self.images)} images")
        
        # Preload thumbnails in background
        self.preload_thumbnails()
    
    def on_load_error(self, error):
        """Handle load error"""
        self.loading = False
        self.load_more_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status.showMessage(f"❌ Error: {error}")
        QMessageBox.critical(self, "Error", f"Failed to load images: {error}")
    
    def load_more(self):
        """Load more images"""
        if self.loading:
            return
        
        # Load next batch
        offset = len(self.images)
        batch = self.loader.load_batch(offset, self.batch_size)
        
        if batch:
            self.images.extend(batch)
            self.loaded_images = self.images.copy()
            self.filtered_images = self.images.copy()
            self.image_count_label.setText(f"{len(self.images)} images loaded")
            self.display_thumbs()
            self.status.showMessage(f"Loaded {len(batch)} more images")
        else:
            QMessageBox.information(self, "Done", "No more images to load")
            self.load_more_btn.setEnabled(False)
    
    def display_thumbs(self):
        """Display thumbnails with caching"""
        # Clear grid
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        if not self.filtered_images:
            label = QLabel("No images match the filter/search.")
            label.setStyleSheet("color: #666; padding: 20px;")
            self.grid_layout.addWidget(label, 0, 0)
            return
        
        # Start thumbnail generation in background
        paths = [p for p, _ in self.filtered_images if os.path.exists(p)]
        
        self.thumb_worker = ThumbnailWorker(self.cache, paths, 150)
        self.thumb_worker.thumbnail_ready.connect(self.add_thumbnail)
        self.thumb_worker.finished.connect(self.on_thumbnails_done)
        self.thumb_worker.start()
        
        self.status.showMessage("Generating thumbnails...")
    
    def add_thumbnail(self, path, pixmap):
        """Add thumbnail to grid"""
        # Find the position of this path
        for idx, (p, _) in enumerate(self.filtered_images):
            if p == path:
                btn = QPushButton()
                btn.setFixedSize(100, 100)
                btn.setIcon(QIcon(pixmap))
                btn.setIconSize(QSize(90, 90))
                
                # Check if photo has tags
                tags = self.tagger.get_photo_tags(path)
                if tags:
                    if len(tags) >= 2:
                        btn.setStyleSheet("""
                            QPushButton {
                                border: 3px solid #ff6b6b;
                                border-radius: 4px;
                                background-color: #2a2a2a;
                            }
                            QPushButton:hover {
                                border: 3px solid #ff8a8a;
                            }
                        """)
                    else:
                        btn.setStyleSheet("""
                            QPushButton {
                                border: 2px solid #4a8aca;
                                border-radius: 4px;
                                background-color: #2a2a2a;
                            }
                            QPushButton:hover {
                                border: 2px solid #6aaaca;
                            }
                        """)
                else:
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
                
                row = idx // 6
                col = idx % 6
                self.grid_layout.addWidget(btn, row, col)
                break
    
    def on_thumbnails_done(self):
        """Thumbnails generation complete"""
        self.status.showMessage("✅ Thumbnails ready")
    
    def filter_by_person(self, name: str):
        """Filter images by person"""
        if name == "All Photos" or name == "---":
            self.filtered_images = self.loaded_images.copy()
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
        
        # Search using optimized database
        results = self.db_optimized.query_photos_by_person(query, 100)
        
        if results:
            self.filtered_images = [(p[0], 0) for p in results]
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
        self.filtered_images = self.loaded_images.copy()
        self.display_thumbs()
        if self.filtered_images:
            self.show_image(self.filtered_images[0][0])
            self.counter.setText(f"1 / {len(self.filtered_images)}")
    
    def show_image(self, path):
        """Show image in preview"""
        self.current_path = path
        
        if not os.path.exists(path):
            return
        
        for idx, (p, _) in enumerate(self.filtered_images):
            if p == path:
                self.counter.setText(f"{idx+1} / {len(self.filtered_images)}")
                break
        
        # Quick load with cache
        start_time = time.time()
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(600, 500, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
            self.preview.setPixmap(scaled)
            
            load_time = (time.time() - start_time) * 1000
            self.status.showMessage(f"Viewing: {os.path.basename(path)} ({load_time:.0f}ms)")
        
        # Show tags
        tags = self.tagger.get_photo_tags(path)
        if tags:
            tag_text = "Tags: " + ", ".join([f"{t['name']} ({t['confidence']:.0%})" for t in tags])
            self.tags_label.setText(tag_text)
            self.face_label.setText(f"Faces: {len(tags)}")
        else:
            self.tags_label.setText("Tags: None")
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
            
            # Cache face data
            self.cache.save_face_data(self.current_path, faces)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Face detection failed: {e}")
        
        self.detect_btn.setEnabled(True)
        self.detect_btn.setText("🔍 Detect Faces")
    
    def add_face(self):
        """Add a name to a detected face"""
        if not hasattr(self, 'current_faces') or not self.current_faces:
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
                self.update_person_list()
    
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
    
    def export_album(self):
        """Export album"""
        person = self.export_person.text().strip()
        if not person:
            QMessageBox.warning(self, "Warning", "Please enter a person name!")
            return
        
        self.export_btn.setEnabled(False)
        self.status.showMessage(f"Exporting album for {person}...")
        
        # Use optimized export
        try:
            from genesis.enhanced_export import EnhancedExporter
            exporter = EnhancedExporter(self.db_path)
            
            result = exporter.export_album_with_options(
                person,
                output_format=self.export_format.currentText(),
                resize=self.export_resize.isChecked(),
                max_size=self.export_maxsize.value(),
                add_metadata=True
            )
            
            if result:
                QMessageBox.information(self, "Export Complete", f"✅ Exported to:\n{result}")
                self.status.showMessage(f"Export complete: {result}")
            else:
                QMessageBox.critical(self, "Export Failed", "Failed to export album")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export error: {e}")
        
        self.export_btn.setEnabled(True)
    
    def clear_cache(self):
        """Clear cache"""
        reply = QMessageBox.question(self, "Clear Cache", 
                                     "This will clear all cached thumbnails. Continue?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.cache.clear_cache()
            self.update_cache_stats()
            self.status.showMessage("Cache cleared")
    
    def preload_thumbnails(self):
        """Preload thumbnails"""
        self.status.showMessage("Preloading thumbnails...")
        paths = [p for p, _ in self.loaded_images[:100] if os.path.exists(p)]
        self.cache.batch_generate_thumbnails(paths, 150)
        self.status.showMessage("Preloading thumbnails... background")
    
    def update_cache_stats(self):
        """Update cache statistics"""
        stats = self.cache.get_cache_stats()
        self.cache_stats_label.setText(
            f"📊 Cache Stats: {stats['thumbnails']} thumbnails, "
            f"{stats['optimized']} optimized, {stats['metadata_size']} metadata entries"
        )
        self.stats_label.setText(f"⚡ {stats['thumbnails']} cached | {len(self.images)} images")
    
    def prev_image(self):
        """Go to previous image"""
        if not self.filtered_images:
            return
        for idx, (path, _) in enumerate(self.filtered_images):
            if path == self.current_path and idx > 0:
                self.show_image(self.filtered_images[idx-1][0])
                break
    
    def next_image(self):
        """Go to next image"""
        if not self.filtered_images:
            return
        for idx, (path, _) in enumerate(self.filtered_images):
            if path == self.current_path and idx < len(self.filtered_images) - 1:
                self.show_image(self.filtered_images[idx+1][0])
                break


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    viewer = FaceViewerV07()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
