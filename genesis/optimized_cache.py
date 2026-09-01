#!/usr/bin/env python3
"""
GENESIS Optimized Cache Module v0.7
Faster thumbnail loading, caching, and batch processing
"""

import os
import sys
import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageFile
import threading
import queue
from concurrent.futures import ThreadPoolExecutor

ImageFile.LOAD_TRUNCATED_IMAGES = True


class OptimizedCache:
    """Optimized caching system for faster loading"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.cache_dir = Path("cache/optimized")
        self.thumb_dir = Path("cache/thumbnails")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.thumb_dir.mkdir(parents=True, exist_ok=True)
        
        # Thread pool for background processing
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.queue = queue.Queue()
        self.running = True
        
        # Cache metadata
        self.cache_metadata = self.load_metadata()
    
    def load_metadata(self):
        """Load cache metadata"""
        meta_file = self.cache_dir / "metadata.json"
        if meta_file.exists():
            try:
                with open(meta_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_metadata(self):
        """Save cache metadata"""
        meta_file = self.cache_dir / "metadata.json"
        with open(meta_file, 'w') as f:
            json.dump(self.cache_metadata, f, indent=2)
    
    def get_thumbnail_path(self, image_path: str, size: int = 150) -> Path:
        """Get cached thumbnail path"""
        # Create hash from path and size
        hash_key = hashlib.md5(f"{image_path}_{size}".encode()).hexdigest()
        return self.thumb_dir / f"{hash_key}_{size}.jpg"
    
    def get_optimized_path(self, image_path: str) -> Path:
        """Get optimized image path"""
        hash_key = hashlib.md5(image_path.encode()).hexdigest()
        return self.cache_dir / f"{hash_key}_optimized.jpg"
    
    def generate_thumbnail(self, image_path: str, size: int = 150) -> bool:
        """Generate and cache thumbnail"""
        try:
            thumb_path = self.get_thumbnail_path(image_path, size)
            
            # Check if already cached
            if thumb_path.exists() and thumb_path.stat().st_mtime > os.path.getmtime(image_path):
                return True
            
            # Generate thumbnail
            with Image.open(image_path) as img:
                # Convert if needed
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Calculate thumbnail
                img.thumbnail((size, size), Image.Resampling.LANCZOS)
                
                # Save with optimization
                img.save(thumb_path, 'JPEG', quality=85, optimize=True)
                
                # Update metadata
                self.cache_metadata[str(thumb_path)] = {
                    'source': image_path,
                    'size': size,
                    'created': datetime.now().isoformat(),
                    'dimensions': f"{img.width}x{img.height}"
                }
                self.save_metadata()
                return True
                
        except Exception as e:
            print(f"Error generating thumbnail for {image_path}: {e}")
            return False
    
    def batch_generate_thumbnails(self, image_paths: list, size: int = 150):
        """Batch generate thumbnails in background"""
        def process_batch():
            for path in image_paths:
                if not self.running:
                    break
                try:
                    self.generate_thumbnail(path, size)
                except Exception as e:
                    print(f"Error in batch: {e}")
        
        # Submit to thread pool
        self.executor.submit(process_batch)
    
    def get_cached_thumbnail(self, image_path: str, size: int = 150) -> Image.Image:
        """Get cached thumbnail"""
        thumb_path = self.get_thumbnail_path(image_path, size)
        
        if thumb_path.exists():
            try:
                return Image.open(thumb_path)
            except:
                pass
        
        # Generate if not cached
        self.generate_thumbnail(image_path, size)
        
        if thumb_path.exists():
            return Image.open(thumb_path)
        return None
    
    def preload_images(self, image_paths: list, sizes: list = [150, 300, 600]):
        """Preload images at multiple sizes"""
        for size in sizes:
            self.batch_generate_thumbnails(image_paths, size)
    
    def clear_cache(self):
        """Clear cache"""
        for file in self.thumb_dir.glob("*.jpg"):
            file.unlink()
        for file in self.cache_dir.glob("*.jpg"):
            file.unlink()
        self.cache_metadata = {}
        self.save_metadata()
        print("✅ Cache cleared")
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        thumb_count = len(list(self.thumb_dir.glob("*.jpg")))
        cache_count = len(list(self.cache_dir.glob("*.jpg")))
        
        return {
            'thumbnails': thumb_count,
            'optimized': cache_count,
            'metadata_size': len(self.cache_metadata)
        }


class LazyLoader:
    """Lazy loading for large galleries"""
    
    def __init__(self, db_path: str = None, batch_size: int = 50):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.batch_size = batch_size
        self.cache = OptimizedCache(db_path)
        self.conn = None
    
    def connect(self):
        """Connect to database"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
        return self.conn
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def load_batch(self, offset: int = 0, limit: int = 50) -> list:
        """Load a batch of images"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT path, id FROM photos 
                ORDER BY id DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            results = cursor.fetchall()
            return results
            
        except Exception as e:
            print(f"Error loading batch: {e}")
            return []
    
    def get_total_count(self) -> int:
        """Get total image count"""
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM photos")
            return cursor.fetchone()[0]
        except Exception as e:
            print(f"Error getting count: {e}")
            return 0
    
    def lazy_load_gallery(self, start: int = 0, batch_size: int = None):
        """Generator for lazy loading"""
        if batch_size is None:
            batch_size = self.batch_size
        
        offset = start
        while True:
            batch = self.load_batch(offset, batch_size)
            if not batch:
                break
            for item in batch:
                yield item
            offset += batch_size
    
    def preload_thumbnails(self, paths: list, size: int = 150):
        """Preload thumbnails in background"""
        self.cache.batch_generate_thumbnails(paths, size)


# Optimized database queries
class OptimizedDB:
    """Optimized database operations"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Connect with optimizations"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute("PRAGMA cache_size = 10000")
            self.conn.execute("PRAGMA temp_store = MEMORY")
            self.conn.execute("PRAGMA journal_mode = WAL")
            self.conn.execute("PRAGMA synchronous = OFF")
            self.cursor = self.conn.cursor()
        return self.conn
    
    def close(self):
        """Close connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
    
    def query_faces_by_photo(self, photo_path: str) -> list:
        """Optimized face query"""
        self.connect()
        try:
            self.cursor.execute("""
                SELECT person_name, confidence FROM photo_tags
                WHERE photo_path = ?
                ORDER BY confidence DESC
            """, (photo_path,))
            return self.cursor.fetchall()
        except:
            return []
    
    def query_photos_by_person(self, person_name: str, limit: int = 100) -> list:
        """Optimized person query"""
        self.connect()
        try:
            self.cursor.execute("""
                SELECT photo_path FROM photo_tags
                WHERE person_name = ?
                LIMIT ?
            """, (person_name, limit))
            return self.cursor.fetchall()
        except:
            return []
    
    def get_photo_count(self) -> int:
        """Optimized count query"""
        self.connect()
        try:
            self.cursor.execute("SELECT COUNT(*) FROM photos")
            return self.cursor.fetchone()[0]
        except:
            return 0
    
    def get_face_count(self) -> int:
        """Optimized face count"""
        self.connect()
        try:
            self.cursor.execute("SELECT COUNT(*) FROM photo_tags")
            return self.cursor.fetchone()[0]
        except:
            return 0


def main():
    """Test optimized cache"""
    import argparse
    import time
    
    parser = argparse.ArgumentParser(description="GENESIS Optimized Cache")
    parser.add_argument("--stats", action="store_true", help="Show cache stats")
    parser.add_argument("--clear", action="store_true", help="Clear cache")
    parser.add_argument("--test", action="store_true", help="Run performance test")
    
    args = parser.parse_args()
    
    cache = OptimizedCache()
    
    if args.clear:
        cache.clear_cache()
    
    if args.stats:
        stats = cache.get_cache_stats()
        print(f"📊 Cache Statistics:")
        print(f"  Thumbnails: {stats['thumbnails']}")
        print(f"  Optimized: {stats['optimized']}")
        print(f"  Metadata: {stats['metadata_size']}")
    
    if args.test:
        print("🧪 Running performance test...")
        
        # Test loading
        loader = LazyLoader()
        start = time.time()
        count = loader.get_total_count()
        print(f"  📸 Total images: {count}")
        
        # Test batch loading
        start = time.time()
        batch = loader.load_batch(0, 50)
        elapsed = time.time() - start
        print(f"  ⚡ Batch load (50): {elapsed:.3f}s")
        
        # Test thumbnail generation
        if batch:
            paths = [p for p, _ in batch if os.path.exists(p)]
            start = time.time()
            cache.batch_generate_thumbnails(paths)
            elapsed = time.time() - start
            print(f"  🖼️ Thumbnail generation: {elapsed:.3f}s")
        
        loader.close()


if __name__ == "__main__":
    main()
