#!/usr/bin/env python3
"""
Batch Face Detection - Process all images in the background
"""

import os
import sys
import sqlite3
import time
from pathlib import Path
from multiprocessing import Pool, cpu_count
import face_recognition
import pickle

sys.path.append('.')
from genesis.face_detection.detector import FaceDetector

def process_image(args):
    """Process a single image for faces"""
    path, db_path = args

    if not os.path.exists(path):
        return None

    try:
        # Quick check if image has faces
        image = face_recognition.load_image_file(path)
        face_locations = face_recognition.face_locations(image, model='cnn')  # Use CNN for accuracy

        if not face_locations:
            return {'path': path, 'faces': 0}

        # Get encodings
        face_encodings = face_recognition.face_encodings(image, face_locations)

        return {
            'path': path,
            'faces': len(face_locations),
            'encodings': face_encodings,
            'locations': face_locations
        }

    except Exception as e:
        return {'path': path, 'faces': 0, 'error': str(e)}

class BatchFaceDetector:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.detector = FaceDetector(db_path)
        self.processed = 0
        self.found = 0

    def scan_all(self, limit: int = 100):
        """Scan all photos in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT path FROM photos LIMIT ?", (limit,))
        photos = [row[0] for row in cursor.fetchall()]
        conn.close()

        print(f"📸 Scanning {len(photos)} photos...")
        print(f"🧠 Using {cpu_count()} CPU cores")
        print("=" * 50)

        start_time = time.time()

        # Process in parallel
        with Pool(processes=cpu_count()) as pool:
            results = pool.map(process_image, [(p, self.db_path) for p in photos])

        elapsed = time.time() - start_time

        # Save results
        for result in results:
            if result and result.get('faces', 0) > 0:
                self.found += result['faces']
                self.processed += 1

        print(f"\n✅ Complete!")
        print(f"📊 Processed: {self.processed} images")
        print(f"👤 Faces found: {self.found}")
        print(f"⏱️ Time: {elapsed:.1f} seconds ({elapsed/len(photos):.1f}s per image)")
        print(f"🚀 Speed: {len(photos)/elapsed:.1f} images/second")

if __name__ == "__main__":
    print("🔍 Batch Face Detection")
    print("=" * 50)

    detector = BatchFaceDetector()

    # Ask for limit
    limit = input("How many images to scan? (default=100, 0=all): ").strip()
    limit = int(limit) if limit else 100
    if limit == 0:
        limit = None  # All images

    print("\n🚀 Starting batch detection...")
    print("   This may take a while for large collections")
    print("")

    detector.scan_all(limit)
