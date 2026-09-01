#!/usr/bin/env python3
"""
GENESIS Face Groups - Optimized version
Uses database directly without scanning all images
"""

import os
import sys
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

sys.path.append('.')
from genesis.face_detection.detector import FaceDetector


class FaceGroupsOptimized:
    """Face groups using database directly"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.detector = FaceDetector(self.db_path)

    def get_person_photos_from_db(self, name: str) -> list:
        """Get photos of a person from database (no scanning)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if we have face data
            cursor.execute("""
                SELECT image_path FROM face_data WHERE name = ?
            """, (name,))

            results = cursor.fetchall()
            conn.close()

            # Return list of paths
            return [row[0] for row in results if os.path.exists(row[0])]

        except Exception as e:
            print(f"Error: {e}")
            return []

    def get_all_groups(self) -> dict:
        """Get all face groups from database"""
        groups = {}

        for name in self.detector.known_names:
            photos = self.get_person_photos_from_db(name)
            if photos:
                groups[name] = photos

        return groups

    def create_person_album(self, name: str, output_dir: str = None) -> str:
        """Create album for a person"""
        if output_dir is None:
            output_dir = os.path.expanduser(f"~/GENESIS-Albums/{name}")

        os.makedirs(output_dir, exist_ok=True)

        photos = self.get_person_photos_from_db(name)

        if not photos:
            print(f"No photos found for {name}")
            return None

        print(f"📸 Creating album for {name} with {len(photos)} photos...")

        for i, src_path in enumerate(photos, 1):
            if os.path.exists(src_path):
                ext = Path(src_path).suffix
                dest_path = os.path.join(output_dir, f"{name}_{i:04d}{ext}")
                try:
                    shutil.copy2(src_path, dest_path)
                except Exception as e:
                    print(f"Error copying {src_path}: {e}")

        # Create info file
        info_path = os.path.join(output_dir, "_album_info.txt")
        with open(info_path, 'w') as f:
            f.write(f"GENESIS Photo Album\n")
            f.write(f"Person: {name}\n")
            f.write(f"Photos: {len(photos)}\n")
            f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        print(f"✅ Album created: {output_dir}")
        return output_dir

    def get_group_stats(self) -> dict:
        """Get group statistics"""
        groups = self.get_all_groups()

        stats = {
            'total_people': len(groups),
            'total_photos': sum(len(photos) for photos in groups.values()),
            'groups': groups
        }

        if groups:
            stats['largest_group'] = max(groups.items(), key=lambda x: len(x[1]))
            stats['smallest_group'] = min(groups.items(), key=lambda x: len(x[1]))
            stats['average_size'] = sum(len(photos) for photos in groups.values()) / len(groups)

        return stats

    def print_stats(self):
        """Print statistics"""
        stats = self.get_group_stats()

        print("=" * 50)
        print("👥 Face Groups Statistics")
        print("=" * 50)
        print(f"👤 Total people: {stats['total_people']}")
        print(f"📸 Total photos in groups: {stats['total_photos']}")

        if stats.get('average_size'):
            print(f"📊 Average group size: {stats['average_size']:.1f} photos")

        if stats.get('largest_group'):
            name, count = stats['largest_group']
            print(f"🏆 Largest group: {name} ({count} photos)")

        if stats.get('groups'):
            print("\n📋 All groups:")
            for name, photos in sorted(stats['groups'].items(), key=lambda x: len(x[1]), reverse=True):
                print(f"  👤 {name}: {len(photos)} photos")


def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description="GENESIS Face Groups (Optimized)")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--create", type=str, help="Create album for person")
    parser.add_argument("--list", action="store_true", help="List all groups")

    args = parser.parse_args()

    groups = FaceGroupsOptimized()

    if args.list or args.stats:
        groups.print_stats()
    elif args.create:
        groups.create_person_album(args.create)
    else:
        groups.print_stats()


if __name__ == "__main__":
    main()
