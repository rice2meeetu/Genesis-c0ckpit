#!/usr/bin/env python3
"""
GENESIS Timeline Module v0.8
View photos by date and track person appearances over time
"""

import os
import sys
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict
import json

sys.path.append('.')
from genesis.face_detection.detector import FaceDetector


class TimelineAnalyzer:
    """Analyze photo timeline and person appearances"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.detector = FaceDetector(self.db_path)
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
    
    def get_photos_by_date(self, date_start: str = None, date_end: str = None) -> list:
        """Get photos within date range"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            query = "SELECT path, modified_date FROM photos WHERE 1=1"
            params = []
            
            if date_start:
                query += " AND modified_date >= ?"
                params.append(date_start)
            if date_end:
                query += " AND modified_date <= ?"
                params.append(date_end)
            
            query += " ORDER BY modified_date DESC"
            
            cursor.execute(query, params)
            return cursor.fetchall()
            
        except Exception as e:
            print(f"Error getting photos by date: {e}")
            return []
    
    def get_timeline_data(self) -> dict:
        """Get timeline data grouped by date"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT DATE(modified_date) as date, COUNT(*) as count
                FROM photos
                WHERE modified_date IS NOT NULL
                GROUP BY DATE(modified_date)
                ORDER BY date DESC
                LIMIT 365
            """)
            
            results = cursor.fetchall()
            
            timeline = {
                'dates': [],
                'counts': [],
                'total_photos': 0
            }
            
            for date, count in results:
                timeline['dates'].append(date)
                timeline['counts'].append(count)
                timeline['total_photos'] += count
            
            return timeline
            
        except Exception as e:
            print(f"Error getting timeline: {e}")
            return {'dates': [], 'counts': [], 'total_photos': 0}
    
    def get_person_timeline(self, person_name: str) -> dict:
        """Get timeline for a specific person"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT DATE(pt.created_at) as date, COUNT(*) as count
                FROM photo_tags pt
                WHERE pt.person_name = ?
                GROUP BY DATE(pt.created_at)
                ORDER BY date DESC
                LIMIT 365
            """, (person_name,))
            
            results = cursor.fetchall()
            
            timeline = {
                'person': person_name,
                'dates': [],
                'counts': [],
                'total_photos': 0
            }
            
            for date, count in results:
                timeline['dates'].append(date)
                timeline['counts'].append(count)
                timeline['total_photos'] += count
            
            return timeline
            
        except Exception as e:
            print(f"Error getting person timeline: {e}")
            return {'person': person_name, 'dates': [], 'counts': [], 'total_photos': 0}
    
    def get_date_range_stats(self, days: int = 30) -> dict:
        """Get statistics for a date range"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT photo_path) as unique_photos,
                    COUNT(DISTINCT person_name) as unique_people
                FROM photo_tags
                WHERE created_at >= ?
            """, (cutoff,))
            
            result = cursor.fetchone()
            
            return {
                'days': days,
                'total_faces': result[0] or 0,
                'unique_photos': result[1] or 0,
                'unique_people': result[2] or 0
            }
            
        except Exception as e:
            print(f"Error getting date range stats: {e}")
            return {'days': days, 'total_faces': 0, 'unique_photos': 0, 'unique_people': 0}
    
    def get_monthly_summary(self) -> dict:
        """Get monthly photo summary"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    strftime('%Y-%m', modified_date) as month,
                    COUNT(*) as count
                FROM photos
                WHERE modified_date IS NOT NULL
                GROUP BY strftime('%Y-%m', modified_date)
                ORDER BY month DESC
                LIMIT 12
            """)
            
            results = cursor.fetchall()
            
            return {
                'months': [row[0] for row in results],
                'counts': [row[1] for row in results]
            }
            
        except Exception as e:
            print(f"Error getting monthly summary: {e}")
            return {'months': [], 'counts': []}
    
    def print_timeline_summary(self):
        """Print timeline summary"""
        timeline = self.get_timeline_data()
        monthly = self.get_monthly_summary()
        
        print("=" * 60)
        print("📅 PHOTO TIMELINE")
        print("=" * 60)
        print(f"📸 Total photos: {timeline['total_photos']}")
        
        if timeline['dates']:
            print(f"📅 Date range: {timeline['dates'][-1]} to {timeline['dates'][0]}")
            print(f"📊 Photos per day (avg): {timeline['total_photos'] / len(timeline['dates']):.1f}")
        
        if monthly['months']:
            print("\n📊 Monthly summary (last 12 months):")
            for month, count in zip(monthly['months'][:6], monthly['counts'][:6]):
                print(f"  {month}: {count} photos")
            if len(monthly['months']) > 6:
                print(f"  ... and {len(monthly['months']) - 6} more months")


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GENESIS Timeline Analysis")
    parser.add_argument("--timeline", action="store_true", help="Show timeline")
    parser.add_argument("--person", type=str, help="Show timeline for a person")
    parser.add_argument("--stats", type=int, nargs='?', const=30, 
                       help="Show stats for last N days")
    parser.add_argument("--monthly", action="store_true", help="Show monthly summary")
    
    args = parser.parse_args()
    
    analyzer = TimelineAnalyzer()
    
    if args.timeline:
        analyzer.print_timeline_summary()
    
    if args.person:
        timeline = analyzer.get_person_timeline(args.person)
        print(f"\n👤 Timeline for {args.person}:")
        print(f"  📸 Total photos: {timeline['total_photos']}")
        if timeline['dates']:
            print(f"  📅 First appearance: {timeline['dates'][-1]}")
            print(f"  📅 Last appearance: {timeline['dates'][0]}")
    
    if args.stats is not None:
        stats = analyzer.get_date_range_stats(args.stats)
        print(f"\n📊 Last {stats['days']} days:")
        print(f"  👤 Unique people: {stats['unique_people']}")
        print(f"  📸 Unique photos: {stats['unique_photos']}")
        print(f"  🏷️ Total face tags: {stats['total_faces']}")
    
    if args.monthly:
        monthly = analyzer.get_monthly_summary()
        print("\n📊 Monthly summary:")
        for month, count in zip(monthly['months'], monthly['counts']):
            print(f"  {month}: {count} photos")
    
    if not any([args.timeline, args.person, args.stats, args.monthly]):
        analyzer.print_timeline_summary()
    
    analyzer.close()


if __name__ == "__main__":
    main()
