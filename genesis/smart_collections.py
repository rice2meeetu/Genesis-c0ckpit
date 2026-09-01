#!/usr/bin/env python3
"""
GENESIS Smart Collections Module v0.8
Auto-created collections based on rules
"""

import os
import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.append('.')
from genesis.advanced_filtering import AdvancedFilter


class SmartCollection:
    """Smart collections with rule-based grouping"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.filter = AdvancedFilter(db_path)
        self.collections_file = Path("cache/collections.json")
        self.collections_file.parent.mkdir(parents=True, exist_ok=True)
        self.collections = self.load_collections()
    
    def load_collections(self) -> dict:
        if self.collections_file.exists():
            try:
                with open(self.collections_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_collections(self):
        with open(self.collections_file, 'w') as f:
            json.dump(self.collections, f, indent=2)
    
    def create_collection(self, name: str, rules: dict, auto_update: bool = True) -> bool:
        self.collections[name] = {
            'rules': rules,
            'auto_update': auto_update,
            'created': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'photos': []
        }
        if auto_update:
            self.update_collection(name)
        self.save_collections()
        return True
    
    def update_collection(self, name: str) -> list:
        if name not in self.collections:
            print(f"Collection '{name}' not found")
            return []
        rules = self.collections[name]['rules']
        photos = self.filter.apply_filter(**rules)
        self.collections[name]['photos'] = photos
        self.collections[name]['last_updated'] = datetime.now().isoformat()
        self.collections[name]['count'] = len(photos)
        self.save_collections()
        return photos
    
    def update_all_collections(self):
        for name in self.collections.keys():
            if self.collections[name].get('auto_update', True):
                self.update_collection(name)
    
    def get_collection(self, name: str) -> list:
        if name not in self.collections:
            print(f"Collection '{name}' not found")
            return []
        if self.collections[name].get('auto_update', True):
            return self.update_collection(name)
        return self.collections[name].get('photos', [])
    
    def delete_collection(self, name: str) -> bool:
        if name in self.collections:
            del self.collections[name]
            self.save_collections()
            return True
        return False
    
    def list_collections(self) -> dict:
        return {name: data.get('count', 0) for name, data in self.collections.items()}
    
    def get_predefined_collections(self) -> dict:
        return {
            'Recent Photos': {
                'date_from': (datetime.now() - timedelta(days=30)).isoformat()
            },
            'Group Photos': {
                'min_faces': 2
            },
            'Frequent People': {
                'min_confidence': 0.8
            },
            'All People': {},
            'Last Year': {
                'date_from': (datetime.now() - timedelta(days=365)).isoformat()
            }
        }
    
    def create_predefined_collections(self):
        predefined = self.get_predefined_collections()
        for name, rules in predefined.items():
            if name not in self.collections:
                self.create_collection(name, rules)
        print(f"✅ Created {len(predefined)} predefined collections")
    
    def get_collection_stats(self) -> dict:
        stats = {
            'total_collections': len(self.collections),
            'total_photos': 0,
            'collections': []
        }
        for name, data in self.collections.items():
            count = data.get('count', 0)
            stats['total_photos'] += count
            stats['collections'].append({
                'name': name,
                'count': count,
                'auto_update': data.get('auto_update', True)
            })
        return stats
    
    def print_collections(self):
        stats = self.get_collection_stats()
        print("=" * 60)
        print("📂 SMART COLLECTIONS")
        print("=" * 60)
        print(f"📁 Total collections: {stats['total_collections']}")
        print(f"📸 Total photos: {stats['total_photos']}")
        print("\n📋 Collections:")
        for col in stats['collections']:
            update_status = "🔄 auto" if col['auto_update'] else "📌 manual"
            print(f"  {col['name']}: {col['count']} photos ({update_status})")


def main():
    import argparse
    from datetime import timedelta
    
    parser = argparse.ArgumentParser(description="GENESIS Smart Collections")
    parser.add_argument("--list", action="store_true", help="List all collections")
    parser.add_argument("--create", type=str, help="Create a new collection")
    parser.add_argument("--update", type=str, help="Update a collection")
    parser.add_argument("--update-all", action="store_true", help="Update all collections")
    parser.add_argument("--delete", type=str, help="Delete a collection")
    parser.add_argument("--predefined", action="store_true", help="Create predefined collections")
    parser.add_argument("--view", type=str, help="View photos in a collection")
    
    args = parser.parse_args()
    collections = SmartCollection()
    
    if args.predefined:
        collections.create_predefined_collections()
    if args.list:
        collections.print_collections()
    if args.create:
        print(f"\n📁 Creating collection: {args.create}")
        rules = {}
        print("Enter rules (key=value, one per line, empty to finish):")
        while True:
            line = input("> ").strip()
            if not line:
                break
            if '=' in line:
                key, value = line.split('=', 1)
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except:
                    pass
                rules[key] = value
        if rules:
            collections.create_collection(args.create, rules)
            print(f"✅ Collection '{args.create}' created")
        else:
            print("❌ No rules provided")
    if args.update:
        photos = collections.update_collection(args.update)
        print(f"🔄 Updated '{args.update}': {len(photos)} photos")
    if args.update_all:
        collections.update_all_collections()
        print("🔄 All collections updated")
    if args.delete:
        if collections.delete_collection(args.delete):
            print(f"✅ Collection '{args.delete}' deleted")
        else:
            print(f"❌ Collection '{args.delete}' not found")
    if args.view:
        photos = collections.get_collection(args.view)
        if photos:
            print(f"📸 Collection '{args.view}' ({len(photos)} photos):")
            for path in photos[:10]:
                print(f"  {os.path.basename(path)}")
            if len(photos) > 10:
                print(f"  ... and {len(photos) - 10} more")
        else:
            print(f"❌ Collection '{args.view}' is empty")
    if not any([args.list, args.create, args.update, args.update_all, args.delete, args.predefined, args.view]):
        collections.print_collections()


if __name__ == "__main__":
    main()
