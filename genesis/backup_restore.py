#!/usr/bin/env python3
"""
GENESIS Backup & Restore Module v0.9
Backup and restore functionality
"""

import os
import sys
import json
import shutil
import sqlite3
import zipfile
from pathlib import Path
from datetime import datetime
import hashlib

sys.path.append('.')
from genesis.optimized_cache import OptimizedCache


class BackupManager:
    """Manage backups of the entire system"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.backup_dir = Path(os.path.expanduser("~/GENESIS-Backups"))
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_file = self.backup_dir / "manifest.json"
        self.manifest = self.load_manifest()
    
    def load_manifest(self) -> dict:
        """Load backup manifest"""
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_manifest(self):
        """Save backup manifest"""
        with open(self.manifest_file, 'w') as f:
            json.dump(self.manifest, f, indent=2, default=str)
    
    def create_backup(self, name: str = None, include_photos: bool = True) -> str:
        """Create a full backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if name:
            backup_name = f"{name}_{timestamp}"
        else:
            backup_name = f"backup_{timestamp}"
        
        backup_path = self.backup_dir / backup_name
        backup_path.mkdir(exist_ok=True)
        
        print(f"📦 Creating backup: {backup_name}")
        
        # Backup database
        db_backup = backup_path / "genesis.db"
        shutil.copy2(self.db_path, db_backup)
        print(f"  ✅ Database backed up")
        
        # Backup cache
        if include_photos:
            cache_dir = Path("cache")
            if cache_dir.exists():
                cache_backup = backup_path / "cache"
                shutil.copytree(cache_dir, cache_backup)
                print(f"  ✅ Cache backed up")
        
        # Create metadata
        metadata = {
            'name': backup_name,
            'created': datetime.now().isoformat(),
            'version': '0.9.0',
            'database_size_mb': os.path.getsize(db_backup) / (1024 * 1024),
            'includes_photos': include_photos,
            'files': []
        }
        
        # List files
        for root, dirs, files in os.walk(backup_path):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, backup_path)
                metadata['files'].append({
                    'name': file,
                    'path': rel_path,
                    'size_mb': os.path.getsize(file_path) / (1024 * 1024)
                })
        
        # Save metadata
        meta_path = backup_path / "metadata.json"
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Update manifest
        self.manifest[backup_name] = {
            'path': str(backup_path),
            'created': metadata['created'],
            'size_mb': sum(f['size_mb'] for f in metadata['files'])
        }
        self.save_manifest()
        
        print(f"✅ Backup complete: {backup_path}")
        return str(backup_path)
    
    def list_backups(self) -> list:
        """List all backups"""
        backups = []
        for name, data in self.manifest.items():
            backups.append({
                'name': name,
                'created': data.get('created', 'Unknown'),
                'size_mb': data.get('size_mb', 0),
                'path': data.get('path', '')
            })
        return sorted(backups, key=lambda x: x['created'], reverse=True)
    
    def restore_backup(self, backup_name: str) -> bool:
        """Restore a backup"""
        if backup_name not in self.manifest:
            print(f"❌ Backup not found: {backup_name}")
            return False
        
        backup_path = Path(self.manifest[backup_name]['path'])
        
        if not backup_path.exists():
            print(f"❌ Backup path not found: {backup_path}")
            return False
        
        print(f"🔄 Restoring backup: {backup_name}")
        
        # Restore database
        db_backup = backup_path / "genesis.db"
        if db_backup.exists():
            # Create backup of current DB
            current_backup = self.backup_dir / "current_backup_before_restore.db"
            shutil.copy2(self.db_path, current_backup)
            print(f"  ✅ Current database backed up")
            
            # Restore
            shutil.copy2(db_backup, self.db_path)
            print(f"  ✅ Database restored")
        
        # Restore cache
        cache_backup = backup_path / "cache"
        if cache_backup.exists():
            cache_dir = Path("cache")
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
            shutil.copytree(cache_backup, cache_dir)
            print(f"  ✅ Cache restored")
        
        print(f"✅ Restore complete!")
        return True
    
    def delete_backup(self, backup_name: str) -> bool:
        """Delete a backup"""
        if backup_name not in self.manifest:
            print(f"❌ Backup not found: {backup_name}")
            return False
        
        backup_path = Path(self.manifest[backup_name]['path'])
        
        if backup_path.exists():
            shutil.rmtree(backup_path)
            print(f"  ✅ Backup deleted: {backup_path}")
        
        del self.manifest[backup_name]
        self.save_manifest()
        
        return True
    
    def create_zip_backup(self, name: str = None) -> str:
        """Create a ZIP backup file"""
        # First create full backup
        backup_path = self.create_backup(name)
        
        # Then zip it
        zip_path = self.backup_dir / f"{Path(backup_path).name}.zip"
        
        print(f"📦 Creating ZIP: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(backup_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, backup_path.parent)
                    zipf.write(file_path, arcname)
        
        # Clean up folder
        shutil.rmtree(backup_path)
        
        print(f"✅ ZIP backup created: {zip_path}")
        return str(zip_path)
    
    def get_backup_stats(self) -> dict:
        """Get backup statistics"""
        backups = self.list_backups()
        
        stats = {
            'total_backups': len(backups),
            'total_size_mb': sum(b['size_mb'] for b in backups),
            'latest_backup': backups[0] if backups else None,
            'oldest_backup': backups[-1] if backups else None
        }
        
        return stats


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GENESIS Backup & Restore")
    parser.add_argument("--list", action="store_true", help="List backups")
    parser.add_argument("--create", type=str, nargs='?', const='auto', help="Create backup")
    parser.add_argument("--restore", type=str, help="Restore backup")
    parser.add_argument("--delete", type=str, help="Delete backup")
    parser.add_argument("--zip", type=str, nargs='?', const='auto', help="Create ZIP backup")
    parser.add_argument("--stats", action="store_true", help="Show backup stats")
    
    args = parser.parse_args()
    
    manager = BackupManager()
    
    if args.list:
        backups = manager.list_backups()
        if backups:
            print("📦 Backups:")
            for backup in backups:
                print(f"  {backup['name']}")
                print(f"    Created: {backup['created']}")
                print(f"    Size: {backup['size_mb']:.1f} MB")
                print()
        else:
            print("No backups found")
    
    if args.create:
        name = args.create if args.create != 'auto' else None
        manager.create_backup(name)
    
    if args.restore:
        manager.restore_backup(args.restore)
    
    if args.delete:
        manager.delete_backup(args.delete)
    
    if args.zip:
        name = args.zip if args.zip != 'auto' else None
        manager.create_zip_backup(name)
    
    if args.stats:
        stats = manager.get_backup_stats()
        print("📊 Backup Statistics:")
        print(f"  Total backups: {stats['total_backups']}")
        print(f"  Total size: {stats['total_size_mb']:.1f} MB")
        if stats['latest_backup']:
            print(f"  Latest: {stats['latest_backup']['name']}")
        if stats['oldest_backup']:
            print(f"  Oldest: {stats['oldest_backup']['name']}")
    
    if not any([args.list, args.create, args.restore, args.delete, args.zip, args.stats]):
        print("Use --help for available commands")
        print("\nExamples:")
        print("  --list                 List all backups")
        print("  --create my_backup     Create a backup")
        print("  --restore backup_name  Restore a backup")
        print("  --delete backup_name   Delete a backup")
        print("  --zip                  Create ZIP backup")
        print("  --stats                Show backup statistics")


if __name__ == "__main__":
    main()
