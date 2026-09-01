#!/usr/bin/env python3
"""
GENESIS Analytics Dashboard Module v0.8
Visual statistics and analytics for photo collection
"""

import os
import sys
import sqlite3
from collections import defaultdict
from datetime import datetime

sys.path.append('.')
from genesis.face_detection.detector import FaceDetector
from genesis.timeline import TimelineAnalyzer


class AnalyticsDashboard:
    """Analytics dashboard for photo collection"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.detector = FaceDetector(self.db_path)
        self.timeline = TimelineAnalyzer(db_path)
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
    
    def get_overall_stats(self) -> dict:
        """Get overall collection statistics"""
        conn = self.connect()
        cursor = conn.cursor()
        
        stats = {}
        
        try:
            # Total photos
            cursor.execute("SELECT COUNT(*) FROM photos")
            stats['total_photos'] = cursor.fetchone()[0] or 0
            
            # Total face tags
            cursor.execute("SELECT COUNT(*) FROM photo_tags")
            stats['total_face_tags'] = cursor.fetchone()[0] or 0
            
            # Unique people
            cursor.execute("SELECT COUNT(DISTINCT person_name) FROM photo_tags")
            stats['unique_people'] = cursor.fetchone()[0] or 0
            
            # Photos with faces
            cursor.execute("SELECT COUNT(DISTINCT photo_path) FROM photo_tags")
            stats['photos_with_faces'] = cursor.fetchone()[0] or 0
            
            # Face detection rate
            if stats['total_photos'] > 0:
                stats['face_detection_rate'] = (
                    stats['photos_with_faces'] / stats['total_photos'] * 100
                )
            else:
                stats['face_detection_rate'] = 0
            
            # Average faces per photo
            if stats['photos_with_faces'] > 0:
                stats['avg_faces_per_photo'] = (
                    stats['total_face_tags'] / stats['photos_with_faces']
                )
            else:
                stats['avg_faces_per_photo'] = 0
            
            return stats
            
        except Exception as e:
            print(f"Error getting overall stats: {e}")
            return {}
    
    def get_face_frequency(self) -> dict:
        """Get face frequency distribution"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT person_name, COUNT(*) as count
                FROM photo_tags
                WHERE person_name != 'Unknown'
                GROUP BY person_name
                ORDER BY count DESC
            """)
            
            results = cursor.fetchall()
            
            return {
                'people': [row[0] for row in results],
                'counts': [row[1] for row in results]
            }
            
        except Exception as e:
            print(f"Error getting face frequency: {e}")
            return {'people': [], 'counts': []}
    
    def get_person_appearance_patterns(self) -> dict:
        """Get person appearance patterns"""
        conn = self.connect()
        cursor = conn.cursor()
        
        patterns = {}
        
        try:
            cursor.execute("""
                SELECT 
                    person_name,
                    COUNT(*) as total,
                    COUNT(DISTINCT DATE(created_at)) as days_active,
                    MIN(DATE(created_at)) as first_seen,
                    MAX(DATE(created_at)) as last_seen
                FROM photo_tags
                WHERE person_name != 'Unknown'
                GROUP BY person_name
            """)
            
            results = cursor.fetchall()
            
            for name, total, days, first, last in results:
                patterns[name] = {
                    'total_photos': total,
                    'days_active': days,
                    'first_seen': first,
                    'last_seen': last,
                    'avg_per_day': total / days if days > 0 else 0
                }
            
            return patterns
            
        except Exception as e:
            print(f"Error getting person patterns: {e}")
            return {}
    
    def get_photo_growth(self) -> dict:
        """Get photo growth over time"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as count
                FROM photos
                WHERE created_at IS NOT NULL
                GROUP BY DATE(created_at)
                ORDER BY date
            """)
            
            results = cursor.fetchall()
            
            cumulative = []
            total = 0
            for date, count in results:
                total += count
                cumulative.append({'date': date, 'daily': count, 'cumulative': total})
            
            return {
                'daily': [row[1] for row in results],
                'cumulative': cumulative,
                'total': total if results else 0
            }
            
        except Exception as e:
            print(f"Error getting photo growth: {e}")
            return {'daily': [], 'cumulative': [], 'total': 0}
    
    def print_dashboard(self):
        """Print analytics dashboard"""
        stats = self.get_overall_stats()
        frequency = self.get_face_frequency()
        patterns = self.get_person_appearance_patterns()
        growth = self.get_photo_growth()
        
        print("=" * 60)
        print("📊 GENESIS ANALYTICS DASHBOARD")
        print("=" * 60)
        
        print("\n📸 COLLECTION OVERVIEW:")
        print(f"  Total photos: {stats.get('total_photos', 0)}")
        print(f"  Photos with faces: {stats.get('photos_with_faces', 0)}")
        print(f"  Face detection rate: {stats.get('face_detection_rate', 0):.1f}%")
        print(f"  Average faces per photo: {stats.get('avg_faces_per_photo', 0):.1f}")
        print(f"  Unique people: {stats.get('unique_people', 0)}")
        print(f"  Total face tags: {stats.get('total_face_tags', 0)}")
        
        print("\n👤 TOP FACES:")
        if frequency.get('people'):
            for i, (name, count) in enumerate(zip(frequency['people'][:5], frequency['counts'][:5]), 1):
                print(f"  {i}. {name}: {count} photos")
            if len(frequency['people']) > 5:
                print(f"  ... and {len(frequency['people']) - 5} more people")
        else:
            print("  No faces detected yet")
        
        print("\n📈 PHOTO GROWTH:")
        if growth.get('cumulative'):
            latest = growth['cumulative'][-1]
            earliest = growth['cumulative'][0]
            print(f"  Total growth: {latest['cumulative']} photos")
            print(f"  Date range: {earliest['date']} to {latest['date']}")
            if len(growth['cumulative']) > 1:
                avg = growth['cumulative'][-1]['cumulative'] / len(growth['cumulative'])
                print(f"  Average: {avg:.1f} photos/day")
        
        print("\n👥 PERSON INSIGHTS:")
        if patterns:
            # Most active
            active = sorted(patterns.items(), key=lambda x: x[1]['total_photos'], reverse=True)
            for name, data in active[:3]:
                print(f"  {name}: {data['total_photos']} photos, {data['days_active']} days active")
        else:
            print("  No person data available")


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GENESIS Analytics Dashboard")
    parser.add_argument("--dashboard", action="store_true", help="Show dashboard")
    parser.add_argument("--top-faces", type=int, default=5, help="Show top faces")
    parser.add_argument("--patterns", action="store_true", help="Show person patterns")
    parser.add_argument("--growth", action="store_true", help="Show photo growth")
    
    args = parser.parse_args()
    
    dashboard = AnalyticsDashboard()
    
    if args.dashboard or not any([args.top_faces, args.patterns, args.growth]):
        dashboard.print_dashboard()
    
    if args.patterns:
        patterns = dashboard.get_person_appearance_patterns()
        print("\n👥 Person Appearance Patterns:")
        for name, data in patterns.items():
            print(f"\n  {name}:")
            print(f"    Total: {data['total_photos']} photos")
            print(f"    Days active: {data['days_active']}")
            print(f"    First seen: {data['first_seen']}")
            print(f"    Last seen: {data['last_seen']}")
    
    if args.growth:
        growth = dashboard.get_photo_growth()
        print("\n📈 Photo Growth:")
        if growth.get('cumulative'):
            for entry in growth['cumulative'][-10:]:
                print(f"  {entry['date']}: +{entry['daily']} ({entry['cumulative']} total)")
    
    dashboard.close()


if __name__ == "__main__":
    main()
