#!/usr/bin/env python3
"""
Test GENESIS Face Detection v0.3
"""

import sys
import os
sys.path.append('.')

from genesis.face_detection.detector import FaceDetector

def test_face_detector():
    """Test basic face detection"""
    print("🧪 Testing GENESIS Face Detection v0.3")
    print("=" * 40)
    
    db_path = "database/genesis.db"
    detector = FaceDetector(db_path)
    
    print(f"\n✅ Face detector initialized")
    print(f"📊 Database: {db_path}")
    print(f"👤 Known faces: {len(detector.known_faces)}")
    
    # Test with sample images in the gallery
    from pathlib import Path
    import sqlite3
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT path FROM photos LIMIT 5")
        sample_images = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if sample_images:
            print(f"\n📸 Testing with {len(sample_images)} images from gallery:")
            for img_path in sample_images:
                if os.path.exists(img_path):
                    faces = detector.detect_faces(img_path)
                    print(f"  {os.path.basename(img_path)}: {len(faces)} faces found")
                else:
                    print(f"  {os.path.basename(img_path)}: file not found")
    except Exception as e:
        print(f"Error testing images: {e}")
    
    print("\n✅ Face detection test complete!")
    print("\nTo run the full viewer:")
    print("  python3 genesis/media_viewer_v03.py")

if __name__ == "__main__":
    test_face_detector()
