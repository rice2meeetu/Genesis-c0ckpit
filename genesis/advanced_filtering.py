#!/usr/bin/env python3
"""
GENESIS Advanced Filtering Module v0.8
Multi-filter search with saved queries
"""

import os
import sys
import sqlite3
import json
from datetime import datetime
from pathlib import Path

sys.path.append('.')
from genesis.auto_tag import AutoTagger


class AdvancedFilter:
    """Advanced filtering with multiple criteria"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.tagger = AutoTagger(db_path)
        self.conn = None
        self.saved_filters_file = Path("cache/saved_filters.json")
        self.saved_filters_file.parent.mkdir(parents=True, exist_ok=True)
        self.saved_filters = self.load_saved_filters()
    
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
    
    def load_saved_filters(self) -> dict:
        """Load saved filters from file"""
        if self.saved_filters_file.exists():
            try:
                with open(self.saved_filters_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_filters(self):
        """Save filters to file"""
        with open(self.saved_filters_file, 'w') as f:
            json.dump(self.saved_filters, f, indent=2)
    
    def save_filter(self, name: str, filter_criteria: dict):
        """Save a filter for later use"""
        self.saved_filters[name] = {
            'criteria': filter_criteria,
            'created': datetime.now().isoformat()
        }
        self.save_filters()
        return True
    
    def delete_filter(self, name: str):
        """Delete a saved filter"""
        if name in self.saved_filters:
            del self.saved_filters[name]
            self.save_filters()
            return True
        return False
    
    def get_saved_filters(self) -> dict:
        """Get all saved filters"""
        return self.saved_filters
    
    def apply_filter(self, **kwargs) -> list:
        """Apply multiple filters"""
        conn = self.connect()
        cursor = conn.cursor()
        
        query = "SELECT DISTINCT photo_path FROM photos WHERE 1=1"
        params = []
        
        # Person filter
        if kwargs.get('person'):
            query += " AND photo_path IN (SELECT photo_path FROM photo_tags WHERE person_name = ?)"
            params.append(kwargs['person'])
        
        # Date range filter
        if kwargs.get('date_from'):
            query += " AND modified_date >= ?"
            params.append(kwargs['date_from'])
        if kwargs.get('date_to'):
            query += " AND modified_date <= ?"
            params.append(kwargs['date_to'])
        
        # Face count filter
        if kwargs.get('min_faces'):
            query += " AND photo_path IN (SELECT photo_path FROM photo_tags GROUP BY photo_path HAVING COUNT(*) >= ?)"
            params.append(kwargs['min_faces'])
        
        # Tag filter
        if kwargs.get('tags'):
            tags = kwargs['tags']
            if isinstance(tags, list):
                for tag in tags:
                    query += " AND photo_path IN (SELECT photo_path FROM photo_tags WHERE person_name = ?)"
                    params.append(tag)
        
        # File type filter
        if kwargs.get('file_types'):
            file_types = kwargs['file_types']
            if isinstance(file_types, list):
                type_conditions = []
                for ft in file_types:
                    type_conditions.append("photo_path LIKE ?")
                    params.append(f"%.{ft}")
                if type_conditions:
                    query += f" AND ({' OR '.join(type_conditions)})"
        
        # Minimum confidence
        if kwargs.get('min_confidence'):
            query += " AND photo_path IN (SELECT photo_path FROM photo_tags WHERE confidence >= ?)"
            params.append(kwargs['min_confidence'])
        
        # Limit
        limit = kwargs.get('limit', 100)
        query += f" LIMIT {limit}"
        
        try:
            cursor.execute(query, params)
            results = [row[0] for row in cursor.fetchall()]
            return results
            
        except Exception as e:
            print(f"Error applying filter: {e}")
            return []
    
    def search_with_filter(self, filter_name: str) -> list:
        """Apply a saved filter"""
        if filter_name not in self.saved_filters:
            print(f"Filter '{filter_name}' not found")
            return []
        
        criteria = self.saved_filters[filter_name]['criteria']
        return self.apply_filter(**criteria)
    
    def get_filter_options(self) -> dict:
        """Get available filter options"""
        conn = self.connect()
        cursor = conn.cursor()
        
        options = {}
        
        try:
            # Get unique people
            cursor.execute("SELECT DISTINCT person_name FROM photo_tags WHERE person_name != 'Unknown'")
            options['people'] = [row[0] for row in cursor.fetchall()]
            
            # Get date range
            cursor.execute("SELECT MIN(modified_date), MAX(modified_date) FROM photos")
            min_date, max_date = cursor.fetchone()
            options['date_range'] = {'min': min_date, 'max': max_date}
            
            # Get file types
            cursor.execute("SELECT DISTINCT UPPER(SUBSTR(photo_path, -4)) FROM photos")
            options['file_types'] = [row[0] for row in cursor.fetchall() if row[0]]
            
            return options
            
        except Exception as e:
            print(f"Error getting filter options: {e}")
            return {}
    
    def print_filter_help(self):
        """Print filter usage help"""
        print("=" * 60)
        print("🔍 ADVANCED FILTER HELP")
        print("=" * 60)
        print("\nAvailable filter options:")
        print("  person: str          - Filter by person name")
        print("  date_from: str       - Start date (YYYY-MM-DD)")
        print("  date_to: str         - End date (YYYY-MM-DD)")
        print("  min_faces: int       - Minimum number of faces")
        print("  tags: list[str]      - List of person names (AND)")
        print("  file_types: list     - File extensions (e.g., ['jpg','png'])")
        print("  min_confidence: float - Minimum confidence (0-1)")
        print("  limit: int           - Max results")
        print("\nExamples:")
        print("  filter.apply_filter(person='John', min_faces=2)")
        print("  filter.apply_filter(date_from='2024-01-01', date_to='2024-12-31')")
        print("  filter.apply_filter(tags=['John','Mary'])")
        print("\nSave filters:")
        print("  filter.save_filter('family_photos', {'person':'John', 'min_faces':2})")
        print("  results = filter.search_with_filter('family_photos')")


def main():
    """CLI interface"""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="GENESIS Advanced Filtering")
    parser.add_argument("--list-filters", action="store_true", help="List saved filters")
    parser.add_argument("--search", type=str, help="Search with saved filter")
    parser.add_argument("--save", type=str, help="Save current filter")
    parser.add_argument("--delete", type=str, help="Delete saved filter")
    parser.add_argument("--help-filters", action="store_true", help="Show filter help")
    
    args = parser.parse_args()
    
    filter_obj = AdvancedFilter()
    
    if args.list_filters:
        filters = filter_obj.get_saved_filters()
        if filters:
            print("📂 Saved filters:")
            for name, data in filters.items():
                print(f"  {name}: {data['criteria']}")
        else:
            print("No saved filters")
    
    if args.search:
        results = filter_obj.search_with_filter(args.search)
        if results:
            print(f"📸 Found {len(results)} photos:")
            for path in results[:10]:
                print(f"  {os.path.basename(path)}")
            if len(results) > 10:
                print(f"  ... and {len(results) - 10} more")
        else:
            print("No results found")
    
    if args.save:
        # Save example filter
        filter_obj.save_filter(args.save, {'person': 'lozz'})
        print(f"✅ Filter saved as: {args.save}")
    
    if args.delete:
        if filter_obj.delete_filter(args.delete):
            print(f"✅ Filter deleted: {args.delete}")
        else:
            print(f"❌ Filter not found: {args.delete}")
    
    if args.help_filters or not any([args.list_filters, args.search, args.save, args.delete]):
        filter_obj.print_filter_help()
    
    filter_obj.close()


if __name__ == "__main__":
    main()
