#!/usr/bin/env python3
"""
GENESIS Status - Quick check
"""
import os
import sqlite3

print("=" * 40)
print("📊 GENESIS STATUS")
print("=" * 40)

# Check database
db_path = "database/genesis.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM photos")
    photos = cursor.fetchone()[0]
    
    try:
        cursor.execute("SELECT COUNT(*) FROM face_data")
        faces = cursor.fetchone()[0]
    except:
        faces = 0
    
    try:
        cursor.execute("SELECT COUNT(*) FROM photo_tags")
        tags = cursor.fetchone()[0]
    except:
        tags = 0
    
    conn.close()
    
    print(f"📸 Photos: {photos}")
    print(f"👤 Faces: {faces}")
    print(f"🏷️ Tags: {tags}")
else:
    print("❌ Database not found")

# Check virtual environment
if os.path.exists("genesis_env"):
    print("✅ Virtual environment: genesis_env")
else:
    print("❌ Virtual environment not found")

# Check launch script
if os.path.exists("launch.sh"):
    print("✅ Launch script: launch.sh")
else:
    print("❌ Launch script not found")

print("=" * 40)
print("\n🚀 Launch: ./launch.sh")
