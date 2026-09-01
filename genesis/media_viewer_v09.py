#!/usr/bin/env python3
"""
GENESIS Photo Studio v0.9 - Cloud, Mobile, Backup & Sharing
Complete integration of all features
"""

import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QLabel, QPushButton, QScrollArea, QFrame,
        QSplitter, QMessageBox, QStatusBar, QComboBox,
        QGroupBox, QInputDialog, QDialog, QFormLayout,
        QLineEdit, QDialogButtonBox, QProgressBar,
        QTabWidget, QCheckBox, QSpinBox, QListWidget,
        QListWidgetItem, QTreeWidget, QTreeWidgetItem,
        QTableWidget, QTableWidgetItem, QHeaderView,
        QTextEdit, QFileDialog
    )
    from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
    from PyQt6.QtGui import QPixmap, QIcon
except ImportError:
    print("ERROR: PyQt6 not installed.")
    sys.exit(1)

sys.path.append('.')
from genesis.optimized_cache import OptimizedCache
from genesis.face_detection.detector import FaceDetector
from genesis.face_groups_optimized import FaceGroupsOptimized
from genesis.auto_tag import AutoTagger
from genesis.timeline import TimelineAnalyzer
from genesis.analytics_dashboard import AnalyticsDashboard
from genesis.advanced_filtering import AdvancedFilter
from genesis.smart_collections import SmartCollection
from genesis.cloud_sync import CloudSync, MobileSync
from genesis.backup_restore import BackupManager
from genesis.sharing import SharingManager


class FaceViewerV09(QMainWindow):
    """Main window with all v0.9 features"""
    
    def __init__(self):
        super().__init__()
        self.db_path = os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.images = []
        self.current_path = None
        self.filtered_images = []
        
        # Initialize all modules
        self.cache = OptimizedCache(self.db_path)
        self.detector = FaceDetector(self.db_path)
        self.groups = FaceGroupsOptimized(self.db_path)
        self.tagger = AutoTagger(self.db_path)
        self.timeline = TimelineAnalyzer(self.db_path)
        self.analytics = AnalyticsDashboard(self.db_path)
        self.filter = AdvancedFilter(self.db_path)
        self.collections = SmartCollection(self.db_path)
        self.cloud = CloudSync(self.db_path)
        self.mobile = MobileSync(self.db_path)
        self.backup = BackupManager(self.db_path)
        self.sharing = SharingManager(self.db_path)
        
        self.init_ui()
        self.load_images()
    
    def init_ui(self):
        """Initialize UI"""
        self.setWindowTitle("☁️ GENESIS v0.9 - Cloud, Mobile, Backup & Sharing")
        self.setGeometry(100, 100, 1800, 1000)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setSpacing(5)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_panel = self.create_gallery()
        splitter.addWidget(left_panel)
        
        right_panel = self.create_preview()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([500, 1300])
        layout.addWidget(splitter)
        
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("☁️ GENESIS v0.9 Ready")
        
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
            QComboBox, QLineEdit, QListWidget, QSpinBox, QTableWidget {
                background-color: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }
            QTableWidget::item { color: #e0e0e0; }
            QHeaderView::section {
                background-color: #3a3a3a;
                color: #e0e0e0;
                padding: 4px;
                border: 1px solid #444;
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
            QTreeWidget { background: #2a2a2a; color: #e0e0e0; border: 1px solid #444; }
            QTextEdit { background: #2a2a2a; color: #e0e0e0; border: 1px solid #444; }
        """)
    
    def create_gallery(self):
        """Create gallery panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(5)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("☁️ Media Gallery")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        header.addWidget(title)
        header.addStretch()
        
        # Filters
        self.person_filter = QComboBox()
        self.person_filter.addItem("All Photos")
        for name in self.detector.known_names:
            self.person_filter.addItem(name)
        self.person_filter.currentTextChanged.connect(self.filter_by_person)
        header.addWidget(QLabel("Filter:"))
        header.addWidget(self.person_filter)
        
        layout.addLayout(header)
        
        # Search
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search by person name...")
        self.search_input.returnPressed.connect(self.do_search)
        search_layout.addWidget(self.search_input)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.do_search)
        search_layout.addWidget(self.search_btn)
        
        self.clear_btn = QPushButton("✕ Clear")
        self.clear_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(self.clear_btn)
        
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
        
        # Status
        status_layout = QHBoxLayout()
        self.image_count = QLabel("0 images")
        status_layout.addWidget(self.image_count)
        status_layout.addStretch()
        self.load_more_btn = QPushButton("📥 Load More")
        self.load_more_btn.clicked.connect(self.load_more)
        status_layout.addWidget(self.load_more_btn)
        layout.addLayout(status_layout)
        
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
        
        # Face Tab
        face_tab = self.create_face_tab()
        tabs.addTab(face_tab, "👤 Face")
        
        # Timeline Tab
        timeline_tab = self.create_timeline_tab()
        tabs.addTab(timeline_tab, "📅 Timeline")
        
        # Analytics Tab
        analytics_tab = self.create_analytics_tab()
        tabs.addTab(analytics_tab, "📊 Analytics")
        
        # Collections Tab
        collections_tab = self.create_collections_tab()
        tabs.addTab(collections_tab, "📂 Collections")
        
        # Cloud Tab
        cloud_tab = self.create_cloud_tab()
        tabs.addTab(cloud_tab, "☁️ Cloud")
        
        # Backup Tab
        backup_tab = self.create_backup_tab()
        tabs.addTab(backup_tab, "💾 Backup")
        
        # Sharing Tab
        sharing_tab = self.create_sharing_tab()
        tabs.addTab(sharing_tab, "📤 Share")
        
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
    
    def create_face_tab(self):
        """Create face detection tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        controls = QHBoxLayout()
        self.detect_btn = QPushButton("🔍 Detect Faces")
        self.detect_btn.clicked.connect(self.detect_faces)
        controls.addWidget(self.detect_btn)
        
        self.add_btn = QPushButton("➕ Add Face")
        self.add_btn.clicked.connect(self.add_face)
        controls.addWidget(self.add_btn)
        
        self.tag_btn = QPushButton("🏷️ Auto-Tag")
        self.tag_btn.clicked.connect(self.auto_tag)
        controls.addWidget(self.tag_btn)
        
        controls.addStretch()
        self.face_label = QLabel("Faces: 0")
        controls.addWidget(self.face_label)
        layout.addLayout(controls)
        
        self.tags_label = QLabel("Tags: None")
        self.tags_label.setStyleSheet("color: #aaa; padding: 4px;")
        layout.addWidget(self.tags_label)
        
        layout.addStretch()
        return tab
    
    def create_timeline_tab(self):
        """Create timeline tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        controls = QHBoxLayout()
        self.timeline_btn = QPushButton("📅 Show Timeline")
        self.timeline_btn.clicked.connect(self.show_timeline)
        controls.addWidget(self.timeline_btn)
        
        self.person_timeline = QLineEdit()
        self.person_timeline.setPlaceholderText("Person name...")
        controls.addWidget(self.person_timeline)
        
        self.person_timeline_btn = QPushButton("👤 Show")
        self.person_timeline_btn.clicked.connect(self.show_person_timeline)
        controls.addWidget(self.person_timeline_btn)
        
        controls.addStretch()
        layout.addLayout(controls)
        
        self.timeline_text = QLabel("Click 'Show Timeline' to view")
        self.timeline_text.setStyleSheet("color: #aaa; padding: 8px;")
        self.timeline_text.setWordWrap(True)
        layout.addWidget(self.timeline_text)
        
        layout.addStretch()
        return tab
    
    def create_analytics_tab(self):
        """Create analytics tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        controls = QHBoxLayout()
        self.analytics_btn = QPushButton("📊 Show Dashboard")
        self.analytics_btn.clicked.connect(self.show_analytics)
        controls.addWidget(self.analytics_btn)
        
        self.top_faces_btn = QPushButton("👤 Top Faces")
        self.top_faces_btn.clicked.connect(self.show_top_faces)
        controls.addWidget(self.top_faces_btn)
        
        controls.addStretch()
        layout.addLayout(controls)
        
        self.analytics_text = QLabel("Click 'Show Dashboard' to view analytics")
        self.analytics_text.setStyleSheet("color: #aaa; padding: 8px; font-family: monospace;")
        self.analytics_text.setWordWrap(True)
        layout.addWidget(self.analytics_text)
        
        layout.addStretch()
        return tab
    
    def create_collections_tab(self):
        """Create collections tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        controls = QHBoxLayout()
        self.list_collections_btn = QPushButton("📂 List Collections")
        self.list_collections_btn.clicked.connect(self.list_collections)
        controls.addWidget(self.list_collections_btn)
        
        self.create_predef_btn = QPushButton("⚡ Create Predefined")
        self.create_predef_btn.clicked.connect(self.create_predefined)
        controls.addWidget(self.create_predef_btn)
        
        controls.addStretch()
        layout.addLayout(controls)
        
        self.collections_list = QListWidget()
        self.collections_list.itemClicked.connect(self.view_collection)
        layout.addWidget(self.collections_list)
        
        return tab
    
    def create_cloud_tab(self):
        """Create cloud tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        controls = QHBoxLayout()
        self.cloud_status_btn = QPushButton("☁️ Check Status")
        self.cloud_status_btn.clicked.connect(self.check_cloud_status)
        controls.addWidget(self.cloud_status_btn)
        
        self.cloud_backup_btn = QPushButton("💾 Backup to Cloud")
        self.cloud_backup_btn.clicked.connect(self.cloud_backup)
        controls.addWidget(self.cloud_backup_btn)
        
        self.mobile_export_btn = QPushButton("📱 Mobile Export")
        self.mobile_export_btn.clicked.connect(self.mobile_export)
        controls.addWidget(self.mobile_export_btn)
        
        controls.addStretch()
        layout.addLayout(controls)
        
        self.cloud_text = QLabel("Cloud sync status will appear here")
        self.cloud_text.setStyleSheet("color: #aaa; padding: 8px; font-family: monospace;")
        self.cloud_text.setWordWrap(True)
        layout.addWidget(self.cloud_text)
        
        layout.addStretch()
        return tab
    
    def create_backup_tab(self):
        """Create backup tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        controls = QHBoxLayout()
        self.backup_list_btn = QPushButton("📦 List Backups")
        self.backup_list_btn.clicked.connect(self.list_backups)
        controls.addWidget(self.backup_list_btn)
        
        self.backup_create_btn = QPushButton("📦 Create Backup")
        self.backup_create_btn.clicked.connect(self.create_backup)
        controls.addWidget(self.backup_create_btn)
        
        self.backup_restore_btn = QPushButton("🔄 Restore Backup")
        self.backup_restore_btn.clicked.connect(self.restore_backup)
        controls.addWidget(self.backup_restore_btn)
        
        controls.addStretch()
        layout.addLayout(controls)
        
        self.backup_list_widget = QListWidget()
        self.backup_list_widget.itemClicked.connect(self.select_backup)
        layout.addWidget(self.backup_list_widget)
        
        return tab
    
    def create_sharing_tab(self):
        """Create sharing tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        controls = QHBoxLayout()
        self.share_list_btn = QPushButton("📤 List Shares")
        self.share_list_btn.clicked.connect(self.list_shares)
        controls.addWidget(self.share_list_btn)
        
        self.share_create_btn = QPushButton("📤 Create Share")
        self.share_create_btn.clicked.connect(self.create_share)
        controls.addWidget(self.share_create_btn)
        
        self.share_link_btn = QPushButton("🔗 Get Link")
        self.share_link_btn.clicked.connect(self.get_share_link)
        controls.addWidget(self.share_link_btn)
        
        controls.addStretch()
        layout.addLayout(controls)
        
        self.share_list_widget = QListWidget()
        self.share_list_widget.itemClicked.connect(self.select_share)
        layout.addWidget(self.share_list_widget)
        
        return tab
    
    def load_images(self):
        """Load images"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT path FROM photos ORDER BY id DESC LIMIT 100")
            self.images = cursor.fetchall()
            conn.close()
            
            self.filtered_images = self.images.copy()
            self.image_count.setText(f"{len(self.images)} images")
            self.display_thumbs()
            
            if self.images:
                self.show_image(self.images[0][0])
                self.counter.setText(f"1 / {len(self.images)}")
                
        except Exception as e:
            print(f"Error loading images: {e}")
    
    def display_thumbs(self):
        """Display thumbnails"""
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        if not self.filtered_images:
            label = QLabel("No images")
            label.setStyleSheet("color: #666; padding: 20px;")
            self.grid_layout.addWidget(label, 0, 0)
            return
        
        for idx, (path,) in enumerate(self.filtered_images[:50]):
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
            
            thumb_path = Path("cache/thumbnails") / (Path(path).stem + ".jpg")
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
        
        for idx, (p,) in enumerate(self.filtered_images):
            if p == path:
                self.counter.setText(f"{idx+1} / {len(self.filtered_images)}")
                break
        
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(600, 500, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
            self.preview.setPixmap(scaled)
        
        tags = self.tagger.get_photo_tags(path)
        if tags:
            tag_text = "Tags: " + ", ".join([f"{t['name']} ({t['confidence']:.0%})" for t in tags])
            self.tags_label.setText(tag_text)
            self.face_label.setText(f"Faces: {len(tags)}")
        else:
            self.tags_label.setText("Tags: None")
            self.face_label.setText("Faces: 0")
    
    def detect_faces(self):
        """Detect faces"""
        if not self.current_path:
            QMessageBox.warning(self, "Warning", "No image selected!")
            return
        
        try:
            faces = self.detector.detect_faces(self.current_path)
            self.current_faces = faces
            self.face_label.setText(f"Faces: {len(faces)}")
            if not faces:
                QMessageBox.information(self, "No Faces", "No faces detected.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Detection failed: {e}")
    
    def add_face(self):
        """Add face name"""
        if not hasattr(self, 'current_faces') or not self.current_faces:
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
                self.person_filter.addItem(name)
    
    def auto_tag(self):
        """Auto-tag current photo"""
        if not self.current_path:
            QMessageBox.warning(self, "Warning", "No image selected!")
            return
        
        try:
            tags = self.tagger.tag_photo(self.current_path)
            if tags:
                tag_text = "Tags: " + ", ".join([f"{t['name']} ({t['confidence']:.0%})" for t in tags])
                self.tags_label.setText(tag_text)
                self.face_label.setText(f"Faces: {len(tags)}")
                QMessageBox.information(self, "Auto-Tag Complete", f"✅ Tagged {len(tags)} faces!")
            else:
                QMessageBox.information(self, "Auto-Tag", "No faces found.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Auto-tag failed: {e}")
    
    def show_timeline(self):
        """Show timeline"""
        timeline = self.timeline.get_timeline_data()
        if timeline['dates']:
            text = f"📅 Timeline:\n  Total: {timeline['total_photos']}\n  Days: {len(timeline['dates'])}\n  Average: {timeline['total_photos']/len(timeline['dates']):.1f}/day"
            self.timeline_text.setText(text)
        else:
            self.timeline_text.setText("No timeline data")
    
    def show_person_timeline(self):
        """Show person timeline"""
        name = self.person_timeline.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a name!")
            return
        timeline = self.timeline.get_person_timeline(name)
        if timeline['dates']:
            text = f"👤 {name}: {timeline['total_photos']} photos\nFirst: {timeline['dates'][-1]}\nLast: {timeline['dates'][0]}"
            self.timeline_text.setText(text)
        else:
            self.timeline_text.setText(f"No timeline for {name}")
    
    def show_analytics(self):
        """Show analytics"""
        stats = self.analytics.get_overall_stats()
        text = f"📊 Analytics:\n  Photos: {stats.get('total_photos', 0)}\n  Faces: {stats.get('total_face_tags', 0)}\n  People: {stats.get('unique_people', 0)}\n  Detection: {stats.get('face_detection_rate', 0):.1f}%"
        self.analytics_text.setText(text)
    
    def show_top_faces(self):
        """Show top faces"""
        frequency = self.analytics.get_face_frequency()
        if frequency.get('people'):
            text = "👤 Top Faces:\n"
            for i, (name, count) in enumerate(zip(frequency['people'][:10], frequency['counts'][:10]), 1):
                text += f"  {i}. {name}: {count}\n"
            self.analytics_text.setText(text)
        else:
            self.analytics_text.setText("No faces found")
    
    def list_collections(self):
        """List collections"""
        self.collections_list.clear()
        if not self.collections.collections:
            self.collections.create_predefined_collections()
        for name, data in self.collections.collections.items():
            count = data.get('count', 0)
            item = QListWidgetItem(f"📂 {name} ({count} photos)")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.collections_list.addItem(item)
    
    def view_collection(self, item):
        """View collection"""
        name = item.data(Qt.ItemDataRole.UserRole)
        photos = self.collections.get_collection(name)
        if photos:
            self.filtered_images = [(p,) for p in photos]
            self.display_thumbs()
            if self.filtered_images:
                self.show_image(self.filtered_images[0][0])
                self.counter.setText(f"1 / {len(self.filtered_images)}")
            self.status.showMessage(f"Collection '{name}': {len(photos)} photos")
    
    def create_predefined(self):
        """Create predefined collections"""
        self.collections.create_predefined_collections()
        self.list_collections()
        self.status.showMessage("✅ Predefined collections created")
    
    def check_cloud_status(self):
        """Check cloud status"""
        status = self.cloud.get_sync_status()
        text = f"☁️ Cloud Status:\n  Google Photos: {'✅' if status['google_photos'] else '❌'}\n  Dropbox: {'✅' if status['dropbox'] else '❌'}\n  Last Sync: {status['last_sync']}\n  Synced: {status['synced_photos']} photos"
        self.cloud_text.setText(text)
    
    def cloud_backup(self):
        """Backup to cloud"""
        backup_dir = self.cloud.backup_to_cloud()
        if backup_dir:
            self.cloud_text.setText(f"✅ Backup complete:\n{backup_dir}")
    
    def mobile_export(self):
        """Mobile export"""
        person, ok = QInputDialog.getText(self, "Mobile Export", "Enter person name (or leave empty for all):")
        if ok:
            export_dir = self.mobile.prepare_mobile_export(person if person else None)
            if export_dir:
                self.cloud_text.setText(f"📱 Mobile export complete:\n{export_dir}")
    
    def list_backups(self):
        """List backups"""
        self.backup_list_widget.clear()
        backups = self.backup.list_backups()
        for backup in backups:
            item = QListWidgetItem(f"📦 {backup['name']} ({backup['size_mb']:.1f} MB)")
            item.setData(Qt.ItemDataRole.UserRole, backup['name'])
            self.backup_list_widget.addItem(item)
    
    def select_backup(self, item):
        """Select backup for restore"""
        name = item.data(Qt.ItemDataRole.UserRole)
        self.selected_backup = name
        QMessageBox.information(self, "Backup Selected", f"Selected: {name}\nClick 'Restore Backup' to restore")
    
    def create_backup(self):
        """Create backup"""
        name, ok = QInputDialog.getText(self, "Create Backup", "Enter backup name (optional):")
        if ok:
            backup_path = self.backup.create_backup(name if name else None)
            if backup_path:
                self.list_backups()
                self.status.showMessage(f"✅ Backup created: {backup_path}")
    
    def restore_backup(self):
        """Restore backup"""
        if hasattr(self, 'selected_backup'):
            reply = QMessageBox.question(self, "Restore Backup", 
                                        f"Restore {self.selected_backup}? This will overwrite current data.",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                if self.backup.restore_backup(self.selected_backup):
                    QMessageBox.information(self, "Restore Complete", "✅ Backup restored successfully!")
                    self.load_images()
        else:
            QMessageBox.warning(self, "Warning", "Please select a backup from the list first.")
    
    def list_shares(self):
        """List shares"""
        self.share_list_widget.clear()
        shares = self.sharing.list_shares()
        for share in shares:
            item = QListWidgetItem(f"📤 {share['person']} ({share['photos']} photos)")
            item.setData(Qt.ItemDataRole.UserRole, share['id'])
            self.share_list_widget.addItem(item)
    
    def select_share(self, item):
        """Select share"""
        share_id = item.data(Qt.ItemDataRole.UserRole)
        self.selected_share = share_id
        link = self.sharing.get_share_link(share_id)
        QMessageBox.information(self, "Share Link", f"🔗 Share Link:\n{link}")
    
    def create_share(self):
        """Create share"""
        person, ok = QInputDialog.getText(self, "Create Share", "Enter person name:")
        if ok and person:
            share_id = self.sharing.create_share_link(person)
            if share_id:
                self.list_shares()
                self.status.showMessage(f"✅ Share created: {share_id}")
    
    def get_share_link(self):
        """Get share link"""
        if hasattr(self, 'selected_share'):
            link = self.sharing.get_share_link(self.selected_share)
            if link:
                QMessageBox.information(self, "Share Link", f"🔗 {link}")
        else:
            QMessageBox.warning(self, "Warning", "Please select a share from the list first.")
    
    def filter_by_person(self, name):
        """Filter by person"""
        if name == "All Photos":
            self.filtered_images = self.images.copy()
        elif name != "---":
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT photo_path FROM photo_tags WHERE person_name = ?", (name,))
            results = cursor.fetchall()
            conn.close()
            self.filtered_images = results
        self.display_thumbs()
        if self.filtered_images:
            self.show_image(self.filtered_images[0][0])
            self.counter.setText(f"1 / {len(self.filtered_images)}")
    
    def do_search(self):
        """Execute search"""
        query = self.search_input.text().strip()
        if not query:
            return
        results = self.filter.apply_filter(person=query)
        if results:
            self.filtered_images = [(p,) for p in results]
            self.display_thumbs()
            if self.filtered_images:
                self.show_image(self.filtered_images[0][0])
                self.counter.setText(f"1 / {len(self.filtered_images)}")
            self.status.showMessage(f"Found {len(results)} photos")
        else:
            QMessageBox.information(self, "No Results", "No photos found")
    
    def clear_search(self):
        """Clear search"""
        self.search_input.clear()
        self.filtered_images = self.images.copy()
        self.display_thumbs()
        if self.filtered_images:
            self.show_image(self.filtered_images[0][0])
            self.counter.setText(f"1 / {len(self.filtered_images)}")
    
    def load_more(self):
        """Load more images from database"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            current_count = len(self.images)
            cursor.execute("""
                SELECT path, id FROM photos
                ORDER BY id DESC
                LIMIT 50 OFFSET ?
            """, (current_count,))
            new_images = cursor.fetchall()
            conn.close()
            if not new_images:
                QMessageBox.information(self, "Info", "No more images to load!")
                self.load_more_btn.setEnabled(False)
                return
            self.images.extend(new_images)
            self.loaded_images = self.images.copy()
            self.filtered_images = self.images.copy()
            self.image_count.setText(f"{len(self.images)} images loaded")
            self.display_thumbs()
            self.status.showMessage(f"Loaded {len(new_images)} more images (Total: {len(self.images)})")
            if len(new_images) < 50:
                self.load_more_btn.setEnabled(False)
        except Exception as e:
            self.status.showMessage(f"Error loading more: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load more images: {e}")
    def prev_image(self):
        """Go to previous image"""
        if not self.filtered_images:
            return
        for idx, (path,) in enumerate(self.filtered_images):
            if path == self.current_path and idx > 0:
                self.show_image(self.filtered_images[idx-1][0])
                break
    
    def next_image(self):
        """Go to next image"""
        if not self.filtered_images:
            return
        for idx, (path,) in enumerate(self.filtered_images):
            if path == self.current_path and idx < len(self.filtered_images) - 1:
                self.show_image(self.filtered_images[idx+1][0])
                break


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    viewer = FaceViewerV09()
    viewer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
