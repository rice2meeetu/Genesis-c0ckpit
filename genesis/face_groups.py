#!/usr/bin/env python3
"""
GENESIS Face Groups - Group and organize photos by person
"""

import os
import sys
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.append('.')
from genesis.face_detection.detector import FaceDetector
from genesis.face_search import FaceSearch


class FaceGroups:
    """Group photos by person"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.detector = FaceDetector(self.db_path)
        self.searcher = FaceSearch(self.db_path)
    
    def get_person_photos(self, name: str, limit: int = 500) -> list:
        """Get all photos containing a specific person"""
        return self.searcher.search_person(name, limit=limit)
    
    def get_all_groups(self, limit: int = 100) -> dict:
        """Get all face groups with their photos"""
        groups = {}
        
        for name in self.detector.known_names:
            photos = self.get_person_photos(name, limit=limit)
            if photos:
                groups[name] = photos
        
        return groups
    
    def create_person_album(self, name: str, output_dir: str = None) -> str:
        """Create an album folder with all photos of a person"""
        if output_dir is None:
            output_dir = os.path.expanduser(f"~/GENESIS-Albums/{name}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        photos = self.get_person_photos(name)
        
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
        
        # Create an info file
        info_path = os.path.join(output_dir, "_album_info.txt")
        with open(info_path, 'w') as f:
            f.write(f"GENESIS Photo Album\n")
            f.write(f"Person: {name}\n")
            f.write(f"Photos: {len(photos)}\n")
            f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source: GENESIS Photo Studio v0.3\n")
        
        print(f"✅ Album created: {output_dir}")
        print(f"   📸 {len(photos)} photos copied")
        
        return output_dir
    
    def create_all_albums(self, output_base: str = None) -> dict:
        """Create albums for all known people"""
        if output_base is None:
            output_base = os.path.expanduser("~/GENESIS-Albums")
        
        results = {}
        groups = self.get_all_groups()
        
        print(f"📦 Creating albums for {len(groups)} people...")
        
        for name, photos in groups.items():
            album_dir = os.path.join(output_base, name)
            self.create_person_album(name, album_dir)
            results[name] = album_dir
        
        return results
    
    def get_group_stats(self) -> dict:
        """Get statistics about face groups"""
        groups = self.get_all_groups()
        
        stats = {
            'total_people': len(groups),
            'total_photos': sum(len(photos) for photos in groups.values()),
            'largest_group': max(groups.items(), key=lambda x: len(x[1])) if groups else None,
            'smallest_group': min(groups.items(), key=lambda x: len(x[1])) if groups else None,
            'average_size': sum(len(photos) for photos in groups.values()) / len(groups) if groups else 0
        }
        
        return stats
    
    def print_group_stats(self):
        """Print group statistics"""
        stats = self.get_group_stats()
        
        print("=" * 50)
        print("👥 Face Groups Statistics")
        print("=" * 50)
        print(f"👤 Total people: {stats['total_people']}")
        print(f"📸 Total photos in groups: {stats['total_photos']}")
        print(f"📊 Average group size: {stats['average_size']:.1f} photos")
        
        if stats['largest_group']:
            name, count = stats['largest_group']
            print(f"🏆 Largest group: {name} ({count} photos)")
        
        if stats['smallest_group']:
            name, count = stats['smallest_group']
            print(f"📉 Smallest group: {name} ({count} photos)")
        
        print("\n📋 All groups:")
        groups = self.get_all_groups()
        for name, photos in sorted(groups.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"  👤 {name}: {len(photos)} photos")


class FaceExporter:
    """Export face groups and albums"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.groups = FaceGroups(db_path)
    
    def export_album_zip(self, name: str, output_path: str = None) -> str:
        """Export a person's album as a ZIP file"""
        import zipfile
        
        if output_path is None:
            output_path = os.path.expanduser(f"~/Desktop/{name}_album.zip")
        
        # First create the album
        album_dir = self.groups.create_person_album(name)
        
        if not album_dir:
            return None
        
        # Create ZIP
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(album_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(album_dir))
                    zipf.write(file_path, arcname)
        
        print(f"✅ Album exported as ZIP: {output_path}")
        return output_path
    
    def export_all_albums(self, output_base: str = None) -> dict:
        """Export all albums as ZIP files"""
        if output_base is None:
            output_base = os.path.expanduser("~/Desktop/")
        
        results = {}
        groups = self.groups.get_all_groups()
        
        for name in groups.keys():
            zip_path = os.path.join(output_base, f"{name}_album.zip")
            self.export_album_zip(name, zip_path)
            results[name] = zip_path
        
        return results


def main():
    """Face Groups CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GENESIS Face Groups")
    parser.add_argument("--list", action="store_true", help="List all face groups")
    parser.add_argument("--stats", action="store_true", help="Show group statistics")
    parser.add_argument("--create", type=str, help="Create album for a person")
    parser.add_argument("--create-all", action="store_true", help="Create albums for all people")
    parser.add_argument("--export", type=str, help="Export person's album as ZIP")
    parser.add_argument("--export-all", action="store_true", help="Export all albums as ZIP")
    
    args = parser.parse_args()
    
    groups = FaceGroups()
    exporter = FaceExporter()
    
    if args.list:
        groups.print_group_stats()
    
    elif args.stats:
        groups.print_group_stats()
    
    elif args.create:
        groups.create_person_album(args.create)
    
    elif args.create_all:
        groups.create_all_albums()
    
    elif args.export:
        exporter.export_album_zip(args.export)
    
    elif args.export_all:
        exporter.export_all_albums()
    
    else:
        groups.print_group_stats()


if __name__ == "__main__":
    main()
