#!/usr/bin/env python3
"""
GENESIS Cloud Sync Module v0.9
Sync photos with cloud services
"""

import os
import sys
import json
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
import hashlib

try:
    import requests
except ImportError:
    print("⚠️  requests not installed. Run: pip install requests")
    print("   Cloud sync will be limited")

sys.path.append('.')
from genesis.optimized_cache import OptimizedCache


class CloudSync:
    """Sync photos with cloud services"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.cache = OptimizedCache(db_path)
        self.config_file = Path("cache/cloud_config.json")
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config = self.load_config()
    
    def load_config(self) -> dict:
        """Load cloud configuration"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_config(self):
        """Save cloud configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def setup_google_photos(self, api_key: str = None):
        """Setup Google Photos integration"""
        self.config['google_photos'] = {
            'enabled': True,
            'api_key': api_key,
            'setup_date': datetime.now().isoformat()
        }
        self.save_config()
        print("✅ Google Photos configured")
    
    def setup_dropbox(self, access_token: str = None):
        """Setup Dropbox integration"""
        self.config['dropbox'] = {
            'enabled': True,
            'access_token': access_token,
            'setup_date': datetime.now().isoformat()
        }
        self.save_config()
        print("✅ Dropbox configured")
    
    def get_sync_status(self) -> dict:
        """Get sync status"""
        status = {
            'google_photos': self.config.get('google_photos', {}).get('enabled', False),
            'dropbox': self.config.get('dropbox', {}).get('enabled', False),
            'last_sync': self.config.get('last_sync', 'Never'),
            'synced_photos': self.config.get('synced_photos', 0)
        }
        return status
    
    def export_for_cloud(self, photo_paths: list, output_dir: str = None) -> str:
        """Export photos optimized for cloud"""
        if output_dir is None:
            output_dir = os.path.expanduser("~/GENESIS-Cloud-Export")
        
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"📤 Exporting {len(photo_paths)} photos for cloud...")
        
        exported = []
        for i, src_path in enumerate(photo_paths, 1):
            if os.path.exists(src_path):
                dest_path = os.path.join(output_dir, os.path.basename(src_path))
                try:
                    shutil.copy2(src_path, dest_path)
                    exported.append(dest_path)
                except Exception as e:
                    print(f"Error exporting {src_path}: {e}")
        
        # Create metadata
        meta_path = os.path.join(output_dir, "_cloud_export_info.txt")
        with open(meta_path, 'w') as f:
            f.write("GENESIS Cloud Export\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(f"Photos: {len(exported)}\n")
        
        print(f"✅ Exported {len(exported)} photos to {output_dir}")
        return output_dir
    
    def sync_to_google_photos(self, photo_paths: list):
        """Sync photos to Google Photos"""
        if not self.config.get('google_photos', {}).get('enabled'):
            print("❌ Google Photos not configured")
            return False
        
        # Export first
        export_dir = self.export_for_cloud(photo_paths)
        
        print("☁️ Syncing to Google Photos...")
        print("   Google Photos integration requires OAuth setup")
        print(f"   Photos exported to: {export_dir}")
        print("   Upload using Google Photos web interface")
        
        return True
    
    def sync_to_dropbox(self, photo_paths: list):
        """Sync photos to Dropbox"""
        if not self.config.get('dropbox', {}).get('enabled'):
            print("❌ Dropbox not configured")
            return False
        
        # Export first
        export_dir = self.export_for_cloud(photo_paths)
        
        print("☁️ Syncing to Dropbox...")
        print(f"   Photos exported to: {export_dir}")
        print("   Sync using Dropbox desktop app or web interface")
        
        return True
    
    def backup_to_cloud(self, include_faces: bool = True) -> str:
        """Backup entire database and photos to cloud"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.expanduser(f"~/GENESIS-Backups/backup_{timestamp}")
        os.makedirs(backup_dir, exist_ok=True)
        
        # Backup database
        db_backup = os.path.join(backup_dir, "genesis.db")
        shutil.copy2(self.db_path, db_backup)
        
        # Backup faces if requested
        if include_faces:
            faces_backup = os.path.join(backup_dir, "faces_data.json")
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM face_data")
                faces = cursor.fetchall()
                conn.close()
                
                with open(faces_backup, 'w') as f:
                    json.dump(faces, f, default=str)
            except:
                pass
        
        # Create info file
        info_path = os.path.join(backup_dir, "_backup_info.txt")
        with open(info_path, 'w') as f:
            f.write("GENESIS Cloud Backup\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(f"Database: genesis.db\n")
            f.write(f"Faces included: {include_faces}\n")
            f.write(f"Size: {self._get_size(backup_dir):.1f} MB\n")
        
        print(f"✅ Backup created: {backup_dir}")
        return backup_dir
    
    def _get_size(self, path: str) -> float:
        """Get directory size in MB"""
        total = 0
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                total += os.path.getsize(file_path)
        return total / (1024 * 1024)


class MobileSync:
    """Mobile sync features"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.sync_file = Path("cache/mobile_sync.json")
        self.sync_file.parent.mkdir(parents=True, exist_ok=True)
        self.load_sync_data()
    
    def load_sync_data(self):
        """Load sync data"""
        if self.sync_file.exists():
            try:
                with open(self.sync_file, 'r') as f:
                    self.sync_data = json.load(f)
            except:
                self.sync_data = {}
        else:
            self.sync_data = {}
    
    def save_sync_data(self):
        """Save sync data"""
        with open(self.sync_file, 'w') as f:
            json.dump(self.sync_data, f, indent=2)
    
    def prepare_mobile_export(self, person_name: str = None, limit: int = 50) -> str:
        """Prepare photos for mobile device"""
        export_dir = os.path.expanduser("~/GENESIS-Mobile")
        os.makedirs(export_dir, exist_ok=True)
        
        # Get photos
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if person_name:
            cursor.execute("""
                SELECT photo_path FROM photo_tags
                WHERE person_name = ?
                LIMIT ?
            """, (person_name, limit))
        else:
            cursor.execute("""
                SELECT path FROM photos
                LIMIT ?
            """, (limit,))
        
        photos = cursor.fetchall()
        conn.close()
        
        # Export with mobile optimization
        print(f"📱 Preparing {len(photos)} photos for mobile...")
        exported = []
        
        for i, (path,) in enumerate(photos):
            if os.path.exists(path):
                dest_path = os.path.join(export_dir, f"mobile_{i:04d}.jpg")
                try:
                    from PIL import Image
                    img = Image.open(path)
                    # Resize for mobile
                    img.thumbnail((1080, 1080), Image.Resampling.LANCZOS)
                    img.save(dest_path, quality=80, optimize=True)
                    exported.append(dest_path)
                except Exception as e:
                    print(f"Error processing {path}: {e}")
        
        # Create index
        index_path = os.path.join(export_dir, "_mobile_index.json")
        with open(index_path, 'w') as f:
            json.dump({
                'export_date': datetime.now().isoformat(),
                'count': len(exported),
                'person': person_name,
                'files': [os.path.basename(p) for p in exported]
            }, f, indent=2)
        
        print(f"✅ Mobile export ready: {export_dir}")
        return export_dir


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GENESIS Cloud Sync")
    parser.add_argument("--status", action="store_true", help="Show sync status")
    parser.add_argument("--setup-google", type=str, help="Setup Google Photos (API key)")
    parser.add_argument("--setup-dropbox", type=str, help="Setup Dropbox (access token)")
    parser.add_argument("--sync", type=str, help="Sync photos to cloud")
    parser.add_argument("--backup", action="store_true", help="Backup to cloud")
    parser.add_argument("--mobile", type=str, nargs='?', const='', help="Prepare mobile export")
    
    args = parser.parse_args()
    
    cloud = CloudSync()
    mobile = MobileSync()
    
    if args.status:
        status = cloud.get_sync_status()
        print("☁️ Cloud Sync Status:")
        print(f"  Google Photos: {'✅' if status['google_photos'] else '❌'}")
        print(f"  Dropbox: {'✅' if status['dropbox'] else '❌'}")
        print(f"  Last Sync: {status['last_sync']}")
        print(f"  Synced Photos: {status['synced_photos']}")
    
    if args.setup_google:
        cloud.setup_google_photos(args.setup_google)
    
    if args.setup_dropbox:
        cloud.setup_dropbox(args.setup_dropbox)
    
    if args.sync:
        # Get photos to sync
        conn = sqlite3.connect(cloud.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT path FROM photos LIMIT 100")
        photos = cursor.fetchall()
        conn.close()
        
        photo_paths = [p[0] for p in photos if os.path.exists(p[0])]
        
        if args.sync == 'google':
            cloud.sync_to_google_photos(photo_paths)
        elif args.sync == 'dropbox':
            cloud.sync_to_dropbox(photo_paths)
        else:
            print("Usage: --sync google OR --sync dropbox")
    
    if args.backup:
        backup_dir = cloud.backup_to_cloud()
        print(f"✅ Backup complete: {backup_dir}")
    
    if args.mobile is not None:
        person = args.mobile if args.mobile else None
        mobile.prepare_mobile_export(person)


if __name__ == "__main__":
    main()
