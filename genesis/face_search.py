#!/usr/bin/env python3
"""
GENESIS Face Search - Find all photos of a specific person
"""

import os
import sys
import sqlite3
import pickle
import face_recognition
from pathlib import Path

sys.path.append('.')
from genesis.face_detection.detector import FaceDetector


class FaceSearch:
    """Search for faces in the database"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.detector = FaceDetector(self.db_path)
    
    def search_person(self, name: str, limit: int = 100) -> list:
        """Find all photos containing a specific person"""
        results = []
        
        # Check if we know this face
        if name not in self.detector.known_names:
            print(f"❌ Unknown person: {name}")
            print(f"Known faces: {', '.join(self.detector.known_names)}")
            return results
        
        # Get the encoding for this person
        idx = self.detector.known_names.index(name)
        target_encoding = self.detector.known_encodings[idx]
        
        # Get images from database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT path FROM photos ORDER BY id DESC LIMIT ?", (limit,))
            images = cursor.fetchall()
            conn.close()
            
            print(f"🔍 Searching for '{name}' in {len(images)} images...")
            
            found_count = 0
            for img_path in images:
                img_path = img_path[0]
                if not os.path.exists(img_path):
                    continue
                
                try:
                    # Load image and detect faces
                    image = face_recognition.load_image_file(img_path)
                    face_encodings = face_recognition.face_encodings(image)
                    
                    # Check if the person is in this image
                    for encoding in face_encodings:
                        matches = face_recognition.compare_faces([target_encoding], encoding, 0.6)
                        if matches[0]:
                            results.append(img_path)
                            found_count += 1
                            break
                            
                except Exception as e:
                    # Skip images that can't be processed
                    pass
            
            print(f"✅ Found {len(results)} photos with '{name}'")
            return results
            
        except Exception as e:
            print(f"Error searching: {e}")
            return results
    
    def list_known_faces(self):
        """List all known faces"""
        if not self.detector.known_names:
            print("No faces in database yet. Add some faces first!")
        else:
            print(f"Known faces ({len(self.detector.known_names)}):")
            for name in sorted(self.detector.known_names):
                print(f"  👤 {name}")
    
    def get_face_count(self, name: str) -> int:
        """Get count of photos with a specific person"""
        return len(self.search_person(name, limit=50))


def main():
    """Face search CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GENESIS Face Search")
    parser.add_argument("--list", action="store_true", help="List all known faces")
    parser.add_argument("--search", type=str, help="Search for a person by name")
    parser.add_argument("--limit", type=int, default=100, help="Limit number of images to search")
    
    args = parser.parse_args()
    
    searcher = FaceSearch()
    
    if args.list:
        searcher.list_known_faces()
    elif args.search:
        results = searcher.search_person(args.search, limit=args.limit)
        if results:
            print("\n📸 Photos:")
            for i, path in enumerate(results[:10], 1):
                print(f"  {i}. {os.path.basename(path)}")
            if len(results) > 10:
                print(f"  ... and {len(results) - 10} more")
        else:
            print("No results found")
    else:
        searcher.list_known_faces()


if __name__ == "__main__":
    main()
