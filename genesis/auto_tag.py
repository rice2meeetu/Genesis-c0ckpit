#!/usr/bin/env python3
"""
GENESIS Auto-Tagging Module v0.5
Automatically tags photos with person names
"""

import os
import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime

sys.path.append('.')
from genesis.face_detection.detector import FaceDetector
from genesis.face_groups_optimized import FaceGroupsOptimized


class AutoTagger:
    """Auto-tag photos with person names"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.detector = FaceDetector(self.db_path)
        self.groups = FaceGroupsOptimized(self.db_path)
    
    def tag_photo(self, photo_path: str, update_db: bool = True) -> list:
        """Detect faces and tag a photo"""
        if not os.path.exists(photo_path):
            return []
        
        # Detect faces
        faces = self.detector.detect_faces(photo_path)
        
        tags = []
        for face in faces:
            if face['name'] != "Unknown" and face['confidence'] > 0.5:
                tags.append({
                    'name': face['name'],
                    'confidence': face['confidence'],
                    'location': face['location']
                })
        
        if update_db and tags:
            self.save_tags_to_db(photo_path, tags)
        
        return tags
    
    def save_tags_to_db(self, photo_path: str, tags: list):
        """Save tags to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tags table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS photo_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    photo_path TEXT,
                    person_name TEXT,
                    confidence REAL,
                    location_top INTEGER,
                    location_right INTEGER,
                    location_bottom INTEGER,
                    location_left INTEGER,
                    created_at TEXT,
                    UNIQUE(photo_path, person_name)
                )
            """)
            
            now = datetime.now().isoformat()
            
            for tag in tags:
                cursor.execute("""
                    INSERT OR REPLACE INTO photo_tags 
                    (photo_path, person_name, confidence, location_top, location_right, 
                     location_bottom, location_left, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    photo_path,
                    tag['name'],
                    tag['confidence'],
                    tag['location']['top'],
                    tag['location']['right'],
                    tag['location']['bottom'],
                    tag['location']['left'],
                    now
                ))
            
            conn.commit()
            conn.close()
            print(f"✅ Tagged {len(tags)} faces in {os.path.basename(photo_path)}")
            
        except Exception as e:
            print(f"Error saving tags: {e}")
    
    def get_photo_tags(self, photo_path: str) -> list:
        """Get tags for a photo"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT person_name, confidence FROM photo_tags
                WHERE photo_path = ?
                ORDER BY confidence DESC
            """, (photo_path,))
            
            results = cursor.fetchall()
            conn.close()
            
            return [{'name': row[0], 'confidence': row[1]} for row in results]
            
        except Exception as e:
            print(f"Error getting tags: {e}")
            return []
    
    def search_by_tag(self, person_name: str, min_confidence: float = 0.5) -> list:
        """Search photos by person name"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT photo_path FROM photo_tags
                WHERE person_name = ? AND confidence >= ?
                ORDER BY created_at DESC
            """, (person_name, min_confidence))
            
            results = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return results
            
        except Exception as e:
            print(f"Error searching tags: {e}")
            return []
    
    def get_all_tags(self) -> dict:
        """Get all tags with counts"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT person_name, COUNT(DISTINCT photo_path) as count
                FROM photo_tags
                GROUP BY person_name
                ORDER BY count DESC
            """)
            
            results = cursor.fetchall()
            conn.close()
            
            return {row[0]: row[1] for row in results}
            
        except Exception as e:
            print(f"Error getting tags: {e}")
            return {}
    
    def tag_all_photos(self, limit: int = 100) -> dict:
        """Tag all photos in database"""
        print(f"📸 Auto-tagging up to {limit} photos...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT path FROM photos LIMIT ?", (limit,))
            photos = cursor.fetchall()
            conn.close()
            
            results = {}
            for photo_path in photos:
                photo_path = photo_path[0]
                if not os.path.exists(photo_path):
                    continue
                
                tags = self.tag_photo(photo_path)
                if tags:
                    results[photo_path] = tags
            
            print(f"✅ Tagged {len(results)} photos")
            return results
            
        except Exception as e:
            print(f"Error tagging all photos: {e}")
            return {}


class SmartSearch:
    """Smart search with filters"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.tagger = AutoTagger(db_path)
    
    def search(self, 
               person: str = None,
               date_from: str = None,
               date_to: str = None,
               min_confidence: float = 0.5,
               limit: int = 100) -> list:
        """Smart search with filters"""
        results = []
        
        # Search by person
        if person:
            results = self.tagger.search_by_tag(person, min_confidence)
        else:
            # Get all photos
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT path FROM photos LIMIT ?", (limit,))
                results = [row[0] for row in cursor.fetchall()]
                conn.close()
            except Exception as e:
                print(f"Error getting photos: {e}")
                return []
        
        # Filter by date (if implemented)
        # Could add date filtering here
        
        return results[:limit]
    
    def get_suggestions(self, query: str) -> list:
        """Get search suggestions"""
        tags = self.tagger.get_all_tags()
        suggestions = [name for name in tags.keys() if query.lower() in name.lower()]
        return suggestions[:10]


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GENESIS Auto-Tagging")
    parser.add_argument("--tag", type=str, help="Tag a specific photo")
    parser.add_argument("--tag-all", action="store_true", help="Tag all photos")
    parser.add_argument("--search", type=str, help="Search by person name")
    parser.add_argument("--list-tags", action="store_true", help="List all tags")
    parser.add_argument("--stats", action="store_true", help="Show tag statistics")
    
    args = parser.parse_args()
    
    tagger = AutoTagger()
    searcher = SmartSearch()
    
    if args.tag:
        tags = tagger.tag_photo(args.tag)
        print(f"✅ Found {len(tags)} faces:")
        for tag in tags:
            print(f"  👤 {tag['name']} ({tag['confidence']:.0%})")
    
    elif args.tag_all:
        tagger.tag_all_photos()
    
    elif args.search:
        results = searcher.search(person=args.search)
        print(f"📸 Found {len(results)} photos with '{args.search}':")
        for i, path in enumerate(results[:10], 1):
            print(f"  {i}. {os.path.basename(path)}")
        if len(results) > 10:
            print(f"  ... and {len(results) - 10} more")
    
    elif args.list_tags or args.stats:
        tags = tagger.get_all_tags()
        print(f"📊 Tags ({len(tags)} unique people):")
        for name, count in sorted(tags.items(), key=lambda x: x[1], reverse=True):
            print(f"  👤 {name}: {count} photos")
    
    else:
        print("Use --help for available commands")


if __name__ == "__main__":
    main()
