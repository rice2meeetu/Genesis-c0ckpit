#!/usr/bin/env python3
"""
GENESIS Sharing Module v0.9
Share photos and albums
"""

import os
import sys
import json
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
import hashlib

sys.path.append('.')
from genesis.enhanced_export import EnhancedExporter


class SharingManager:
    """Share photos and albums"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.exporter = EnhancedExporter(db_path)
        self.shared_dir = Path(os.path.expanduser("~/GENESIS-Shared"))
        self.shared_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_file = self.shared_dir / "share_manifest.json"
        self.manifest = self.load_manifest()
    
    def load_manifest(self) -> dict:
        """Load share manifest"""
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_manifest(self):
        """Save share manifest"""
        with open(self.manifest_file, 'w') as f:
            json.dump(self.manifest, f, indent=2, default=str)
    
    def create_share_link(self, person_name: str, expiration_days: int = 7) -> str:
        """Create a shareable link for a person's photos"""
        share_id = hashlib.md5(f"{person_name}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]
        share_dir = self.shared_dir / share_id
        share_dir.mkdir(exist_ok=True)
        
        print(f"📤 Creating share for {person_name}")
        
        # Export photos
        album_dir = self.exporter.export_album_with_options(
            person_name,
            output_format='folder',
            resize=True,
            max_size=1920,
            add_metadata=True
        )
        
        if not album_dir:
            print("❌ Export failed")
            return None
        
        # Copy to share directory
        for file in os.listdir(album_dir):
            src = os.path.join(album_dir, file)
            dst = os.path.join(share_dir, file)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
        
        # Create share info
        share_info = {
            'id': share_id,
            'person': person_name,
            'created': datetime.now().isoformat(),
            'expires': (datetime.now() + timedelta(days=expiration_days)).isoformat(),
            'path': str(share_dir),
            'photos': len([f for f in os.listdir(share_dir) if f.endswith(('.jpg', '.png', '.gif'))])
        }
        
        self.manifest[share_id] = share_info
        self.save_manifest()
        
        print(f"✅ Share created: {share_dir}")
        print(f"   Share ID: {share_id}")
        print(f"   Expires: {share_info['expires']}")
        
        return share_id
    
    def get_share_link(self, share_id: str) -> str:
        """Get share link URL"""
        if share_id not in self.manifest:
            return None
        
        # In a real implementation, this would return a URL
        # For now, return the local path
        share_path = self.manifest[share_id]['path']
        return f"file://{share_path}"
    
    def list_shares(self) -> list:
        """List all shares"""
        shares = []
        for share_id, data in self.manifest.items():
            shares.append({
                'id': share_id,
                'person': data.get('person', 'Unknown'),
                'created': data.get('created', 'Unknown'),
                'expires': data.get('expires', 'Never'),
                'photos': data.get('photos', 0),
                'path': data.get('path', '')
            })
        return sorted(shares, key=lambda x: x['created'], reverse=True)
    
    def delete_share(self, share_id: str) -> bool:
        """Delete a share"""
        if share_id not in self.manifest:
            print(f"❌ Share not found: {share_id}")
            return False
        
        share_path = Path(self.manifest[share_id]['path'])
        if share_path.exists():
            shutil.rmtree(share_path)
            print(f"  ✅ Share deleted: {share_path}")
        
        del self.manifest[share_id]
        self.save_manifest()
        
        return True
    
    def share_family_album(self, family_name: str, members: list) -> str:
        """Create a family album share"""
        share_id = hashlib.md5(f"{family_name}_{datetime.now().isoformat()}".encode()).hexdigest()[:8]
        share_dir = self.shared_dir / share_id
        share_dir.mkdir(exist_ok=True)
        
        print(f"👨‍👩‍👧‍👦 Creating family album: {family_name}")
        
        # Get photos for all members
        all_photos = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for member in members:
            cursor.execute("""
                SELECT DISTINCT photo_path FROM photo_tags
                WHERE person_name = ?
            """, (member,))
            photos = cursor.fetchall()
            all_photos.extend([p[0] for p in photos])
        
        conn.close()
        
        # Remove duplicates
        all_photos = list(set(all_photos))
        
        print(f"  📸 Found {len(all_photos)} photos")
        
        # Export
        for i, src_path in enumerate(all_photos, 1):
            if os.path.exists(src_path):
                dest_path = share_dir / f"family_{i:04d}.jpg"
                try:
                    shutil.copy2(src_path, dest_path)
                except Exception as e:
                    print(f"Error copying {src_path}: {e}")
        
        # Create info
        share_info = {
            'id': share_id,
            'name': family_name,
            'members': members,
            'created': datetime.now().isoformat(),
            'path': str(share_dir),
            'photos': len(all_photos)
        }
        
        self.manifest[share_id] = share_info
        self.save_manifest()
        
        print(f"✅ Family album created: {share_dir}")
        return share_id


def main():
    """CLI interface"""
    import argparse
    from datetime import timedelta
    
    parser = argparse.ArgumentParser(description="GENESIS Sharing")
    parser.add_argument("--list", action="store_true", help="List shares")
    parser.add_argument("--create", type=str, help="Create share for person")
    parser.add_argument("--family", type=str, help="Create family album")
    parser.add_argument("--members", nargs='+', help="Family members")
    parser.add_argument("--expires", type=int, default=7, help="Expiration days")
    parser.add_argument("--delete", type=str, help="Delete share")
    parser.add_argument("--link", type=str, help="Get share link")
    
    args = parser.parse_args()
    
    manager = SharingManager()
    
    if args.list:
        shares = manager.list_shares()
        if shares:
            print("📤 Active Shares:")
            for share in shares:
                print(f"\n  📁 {share['id']}")
                print(f"    Person: {share['person']}")
                print(f"    Photos: {share['photos']}")
                print(f"    Created: {share['created']}")
                print(f"    Expires: {share['expires']}")
        else:
            print("No active shares")
    
    if args.create:
        share_id = manager.create_share_link(args.create, args.expires)
        if share_id:
            link = manager.get_share_link(share_id)
            print(f"\n🔗 Share Link: {link}")
    
    if args.family and args.members:
        share_id = manager.share_family_album(args.family, args.members)
        if share_id:
            link = manager.get_share_link(share_id)
            print(f"\n🔗 Family Album Link: {link}")
    
    if args.delete:
        manager.delete_share(args.delete)
    
    if args.link:
        link = manager.get_share_link(args.link)
        if link:
            print(f"🔗 {link}")
        else:
            print(f"❌ Share not found: {args.link}")
    
    if not any([args.list, args.create, args.family, args.delete, args.link]):
        print("Use --help for available commands")
        print("\nExamples:")
        print("  --list                    List all shares")
        print("  --create john --expires 7 Create share for John")
        print("  --family Smith --members John Mary Sarah")
        print("  --link share_id           Get share link")
        print("  --delete share_id         Delete share")


if __name__ == "__main__":
    main()
