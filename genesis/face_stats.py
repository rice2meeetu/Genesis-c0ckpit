#!/usr/bin/env python3
"""
GENESIS Face Statistics
"""

import os
import sys
import sqlite3

sys.path.append('.')
from genesis.face_detection.detector import FaceDetector


class FaceStats:
    """Face statistics and analytics"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.detector = FaceDetector(self.db_path)
    
    def get_stats(self):
        """Get face statistics"""
        stats = {
            'total_faces': len(self.detector.known_names),
            'unique_people': len(set(self.detector.known_names)),
            'images_scanned': 0,
            'faces_detected': 0,
            'most_common': []
        }
        
        # Get image count from database
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM photos")
            stats['images_scanned'] = cursor.fetchone()[0]
            conn.close()
        except:
            pass
        
        # Count faces per person
        face_counts = {}
        for name in self.detector.known_names:
            face_counts[name] = face_counts.get(name, 0) + 1
        
        # Most common faces
        stats['most_common'] = sorted(face_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        stats['faces_detected'] = sum(face_counts.values())
        
        return stats
    
    def print_stats(self):
        """Print statistics"""
        stats = self.get_stats()
        
        print("=" * 50)
        print("📊 GENESIS Face Statistics")
        print("=" * 50)
        print(f"📸 Images in database: {stats['images_scanned']}")
        print(f"👤 Total faces detected: {stats['faces_detected']}")
        print(f"👥 Unique people: {stats['unique_people']}")
        print()
        
        if stats['most_common']:
            print("🏆 Most common faces:")
            for i, (name, count) in enumerate(stats['most_common'][:5], 1):
                print(f"  {i}. {name}: {count} photos")
        else:
            print("No faces in database yet. Add some faces first!")


def main():
    stats = FaceStats()
    stats.print_stats()


if __name__ == "__main__":
    main()
