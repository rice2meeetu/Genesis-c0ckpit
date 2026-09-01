#!/usr/bin/env python3
"""
GENESIS Status - Quick project state checker
"""

import os
import sys
import subprocess
import sqlite3
from datetime import datetime

def get_git_status():
    try:
        branch = subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip()
        status = subprocess.check_output(['git', 'status', '--porcelain'], text=True)
        clean = len(status.strip()) == 0
        return {'branch': branch, 'clean': clean}
    except:
        return {'branch': 'unknown', 'clean': False}

def get_db_stats(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM photos")
        photos = cursor.fetchone()[0]
        try:
            cursor.execute("SELECT COUNT(*) FROM photo_tags")
            faces = cursor.fetchone()[0]
        except:
            faces = 0
        conn.close()
        return {'photos': photos, 'faces': faces}
    except:
        return {'photos': 0, 'faces': 0}

def get_version():
    try:
        tags = subprocess.check_output(['git', 'tag', '--sort=-v:refname'], text=True).strip().split('\n')
        if tags and tags[0]:
            return tags[0]
    except:
        pass
    return 'unknown'

print("=" * 50)
print("📊 GENESIS STATUS")
print("=" * 50)

git = get_git_status()
print(f"Branch: {git['branch']}")
print(f"Clean: {'✅' if git['clean'] else '❌'}")

version = get_version()
print(f"Version: {version}")

db_path = os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
stats = get_db_stats(db_path)
print(f"Photos: {stats['photos']}")
print(f"Face tags: {stats['faces']}")

print(f"\nChecked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 50)

print("\n🎯 Next Steps:")
print("  🚀 Launch: python3 genesis/media_viewer_v10.py")
print("  📸 Scan: python3 genesis/auto_import.py --path ~/Pictures --auto-tag")
print("  📊 Status: python3 genesis_status.py")
print("=" * 50)
