#!/usr/bin/env python3
"""
GENESIS Auto-Import Scanner v0.10
Automatic import with face detection
"""

import os
import sys
import time
import sqlite3
from pathlib import Path
from datetime import datetime
import shutil

sys.path.append('.')
from genesis.metadata_io import MetadataIO
from genesis.face_detection.detector import FaceDetector


class AutoImportScanner:
    """Automatic import with face detection"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.metadata = MetadataIO(db_path)
        self.detector = FaceDetector(db_path)
        self.watched_dirs = []
        self.running = False
    
    def scan_and_import(self, directory_path: str, auto_tag: bool = True) -> dict:
        """Scan directory and import with auto-tagging"""
        print(f"📸 Scanning: {directory_path}")
        
        results = self.metadata.import_from_directory(directory_path)
        
        if auto_tag and results['photos'] > 0:
            print("🏷️ Auto-tagging imported photos...")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT path FROM photos ORDER BY id DESC LIMIT ?", (results['photos'],))
            new_photos = cursor.fetchall()
            conn.close()
            
            for path in new_photos:
                if os.path.exists(path[0]):
                    faces = self.detector.detect_faces(path[0])
                    if faces:
                        print(f"  👤 Found {len(faces)} faces in {os.path.basename(path[0])}")
        
        return results
    
    def import_from_watched(self):
        """Import from all watched directories"""
        total = {'photos': 0, 'faces': 0, 'errors': 0}
        
        for directory in self.watched_dirs:
            if os.path.exists(directory):
                results = self.scan_and_import(directory)
                total['photos'] += results['photos']
                total['faces'] += results['faces']
                total['errors'] += results['errors']
        
        return total


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GENESIS Auto-Import")
    parser.add_argument("--path", type=str, help="Directory to scan")
    parser.add_argument("--auto-tag", action="store_true", help="Auto-tag faces")
    parser.add_argument("--watch", type=str, help="Add directory to watch")
    
    args = parser.parse_args()
    
    scanner = AutoImportScanner()
    
    if args.path:
        scanner.scan_and_import(args.path, args.auto_tag)
    
    if args.watch:
        scanner.watched_dirs.append(args.watch)
        print(f"✅ Watching: {args.watch}")
    
    if not args.path and not args.watch:
        print("Use --path to scan a directory")
        print("Use --watch to add a watched directory")


if __name__ == "__main__":
    main()
