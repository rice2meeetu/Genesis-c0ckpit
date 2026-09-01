#!/usr/bin/env python3
"""
Ultra-Fast Face Detection - Uses HOG model for speed
"""

import os
import sys
import sqlite3
import time
import face_recognition

db_path = os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")

print("⚡ Ultra-Fast Face Detection")
print("=" * 40)

# Get photos
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT path FROM photos")
photos = cursor.fetchall()
conn.close()

print(f"📸 Scanning {len(photos)} photos...")
print("=" * 40)

total_faces = 0
start_time = time.time()

for i, (path,) in enumerate(photos, 1):
    if not os.path.exists(path):
        continue
    
    try:
        image = face_recognition.load_image_file(path)
        # HOG model = faster
        face_locations = face_recognition.face_locations(image, model='hog')
        
        if face_locations:
            total_faces += len(face_locations)
            if i % 100 == 0:
                print(f"  📊 {i}/{len(photos)}: {total_faces} faces found")
    except:
        pass

elapsed = time.time() - start_time

print("\n" + "=" * 40)
print(f"✅ Complete!")
print(f"👤 Total faces found: {total_faces}")
print(f"⏱️ Time: {elapsed:.1f}s")
print(f"🚀 Speed: {len(photos)/elapsed:.1f} images/sec")
