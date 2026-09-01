#!/usr/bin/env python3
"""
GENESIS Multi-Face Analysis Module v0.6
Analyzes photos with multiple faces and relationships
"""

import os
import sys
import sqlite3
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.append('.')
from genesis.face_detection.detector import FaceDetector
from genesis.face_groups_optimized import FaceGroupsOptimized


class MultiFaceAnalyzer:
    """Analyze photos with multiple faces"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.detector = FaceDetector(self.db_path)
        self.groups = FaceGroupsOptimized(self.db_path)
        self.conn = None
    
    def connect_db(self):
        """Connect to database"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
        return self.conn
    
    def close_db(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def get_photo_face_count(self, photo_path: str) -> int:
        """Get number of faces in a photo"""
        conn = self.connect_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM photo_tags
                WHERE photo_path = ?
            """, (photo_path,))
            count = cursor.fetchone()[0]
            return count
        except:
            return 0
    
    def find_group_photos(self, min_faces: int = 2) -> list:
        """Find photos with multiple faces (group photos)"""
        conn = self.connect_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT photo_path, COUNT(*) as face_count
                FROM photo_tags
                GROUP BY photo_path
                HAVING COUNT(*) >= ?
                ORDER BY face_count DESC
            """, (min_faces,))
            
            results = cursor.fetchall()
            return [{'path': row[0], 'face_count': row[1]} for row in results]
        except:
            return []
    
    def get_face_relationships(self) -> dict:
        """Get relationships between people (who appears together)"""
        conn = self.connect_db()
        cursor = conn.cursor()
        
        relationships = defaultdict(int)
        
        try:
            # Get all photos with multiple faces
            cursor.execute("""
                SELECT photo_path, GROUP_CONCAT(DISTINCT person_name) as people
                FROM photo_tags
                WHERE person_name != 'Unknown'
                GROUP BY photo_path
                HAVING COUNT(DISTINCT person_name) >= 2
            """)
            
            results = cursor.fetchall()
            
            for photo_path, people_str in results:
                people = people_str.split(',')
                # Count co-occurrences
                for i in range(len(people)):
                    for j in range(i + 1, len(people)):
                        pair = tuple(sorted([people[i], people[j]]))
                        relationships[pair] += 1
            
            # Sort by frequency
            sorted_rels = sorted(relationships.items(), key=lambda x: x[1], reverse=True)
            
            return {
                'relationships': [{
                    'people': list(pair),
                    'count': count
                } for pair, count in sorted_rels],
                'total': len(sorted_rels)
            }
            
        except Exception as e:
            print(f"Error getting relationships: {e}")
            return {'relationships': [], 'total': 0}
    
    def get_person_analysis(self, person_name: str) -> dict:
        """Get detailed analysis for a specific person"""
        conn = self.connect_db()
        cursor = conn.cursor()
        
        analysis = {
            'name': person_name,
            'total_photos': 0,
            'with_others': 0,
            'alone': 0,
            'common_companions': [],
            'first_appearance': None,
            'last_appearance': None
        }
        
        try:
            # Get total photos
            cursor.execute("""
                SELECT COUNT(DISTINCT photo_path) FROM photo_tags
                WHERE person_name = ?
            """, (person_name,))
            analysis['total_photos'] = cursor.fetchone()[0]
            
            # Get photos with others
            cursor.execute("""
                SELECT COUNT(DISTINCT pt1.photo_path)
                FROM photo_tags pt1
                JOIN photo_tags pt2 ON pt1.photo_path = pt2.photo_path
                WHERE pt1.person_name = ?
                AND pt2.person_name != ?
                AND pt2.person_name != 'Unknown'
            """, (person_name, person_name))
            analysis['with_others'] = cursor.fetchone()[0]
            
            analysis['alone'] = analysis['total_photos'] - analysis['with_others']
            
            # Get common companions
            cursor.execute("""
                SELECT pt2.person_name, COUNT(*) as count
                FROM photo_tags pt1
                JOIN photo_tags pt2 ON pt1.photo_path = pt2.photo_path
                WHERE pt1.person_name = ?
                AND pt2.person_name != ?
                AND pt2.person_name != 'Unknown'
                GROUP BY pt2.person_name
                ORDER BY count DESC
                LIMIT 5
            """, (person_name, person_name))
            
            analysis['common_companions'] = [
                {'name': row[0], 'count': row[1]} for row in cursor.fetchall()
            ]
            
            # Get first and last appearance
            cursor.execute("""
                SELECT MIN(created_at), MAX(created_at)
                FROM photo_tags
                WHERE person_name = ?
            """, (person_name,))
            
            first, last = cursor.fetchone()
            analysis['first_appearance'] = first
            analysis['last_appearance'] = last
            
        except Exception as e:
            print(f"Error analyzing person: {e}")
        
        return analysis
    
    def analyze_all_people(self) -> dict:
        """Analyze all people in the database"""
        analysis = {}
        
        for name in self.detector.known_names:
            analysis[name] = self.get_person_analysis(name)
        
        return analysis
    
    def get_statistics(self) -> dict:
        """Get comprehensive statistics"""
        conn = self.connect_db()
        cursor = conn.cursor()
        
        stats = {
            'total_photos_with_faces': 0,
            'total_face_tags': 0,
            'unique_people': len(self.detector.known_names),
            'group_photos': len(self.find_group_photos(2)),
            'average_faces_per_photo': 0,
            'most_common_face': None,
            'relationships': self.get_face_relationships()
        }
        
        try:
            cursor.execute("""
                SELECT COUNT(DISTINCT photo_path) FROM photo_tags
            """)
            stats['total_photos_with_faces'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM photo_tags")
            stats['total_face_tags'] = cursor.fetchone()[0]
            
            if stats['total_photos_with_faces'] > 0:
                stats['average_faces_per_photo'] = (
                    stats['total_face_tags'] / stats['total_photos_with_faces']
                )
            
            # Most common face
            cursor.execute("""
                SELECT person_name, COUNT(*) as count
                FROM photo_tags
                WHERE person_name != 'Unknown'
                GROUP BY person_name
                ORDER BY count DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            if result:
                stats['most_common_face'] = {'name': result[0], 'count': result[1]}
            
        except Exception as e:
            print(f"Error getting stats: {e}")
        
        return stats
    
    def print_analysis(self):
        """Print analysis results"""
        stats = self.get_statistics()
        relationships = self.get_face_relationships()
        
        print("=" * 60)
        print("👥 MULTI-FACE ANALYSIS")
        print("=" * 60)
        print(f"📸 Photos with faces: {stats['total_photos_with_faces']}")
        print(f"🏷️ Total face tags: {stats['total_face_tags']}")
        print(f"👤 Unique people: {stats['unique_people']}")
        print(f"📊 Average faces per photo: {stats['average_faces_per_photo']:.1f}")
        print(f"👥 Group photos (2+ people): {stats['group_photos']}")
        
        if stats['most_common_face']:
            print(f"🏆 Most common: {stats['most_common_face']['name']} "
                  f"({stats['most_common_face']['count']} photos)")
        
        print("\n🤝 FACE RELATIONSHIPS:")
        if relationships['relationships']:
            for i, rel in enumerate(relationships['relationships'][:10], 1):
                print(f"  {i}. {rel['people'][0]} & {rel['people'][1]}: {rel['count']} photos")
            if len(relationships['relationships']) > 10:
                print(f"  ... and {len(relationships['relationships']) - 10} more")
        else:
            print("  No relationships found yet")
        
        print("\n📋 PERSON ANALYSIS:")
        analysis = self.analyze_all_people()
        for name, data in analysis.items():
            if data['total_photos'] > 0:
                print(f"\n  👤 {name}:")
                print(f"     📸 Photos: {data['total_photos']}")
                print(f"     🤝 With others: {data['with_others']}")
                print(f"     👤 Alone: {data['alone']}")
                if data['common_companions']:
                    companions = ', '.join([f"{c['name']} ({c['count']})" 
                                          for c in data['common_companions'][:3]])
                    print(f"     👥 Often with: {companions}")


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GENESIS Multi-Face Analysis")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--analyze", type=str, help="Analyze a specific person")
    parser.add_argument("--group-photos", type=int, default=2, 
                       help="Find group photos (min faces)")
    parser.add_argument("--relationships", action="store_true", 
                       help="Show face relationships")
    
    args = parser.parse_args()
    
    analyzer = MultiFaceAnalyzer()
    
    if args.stats or (not args.analyze and not args.relationships):
        analyzer.print_analysis()
    
    if args.analyze:
        analysis = analyzer.get_person_analysis(args.analyze)
        print(f"\n📊 Analysis for {args.analyze}:")
        print(f"  📸 Total photos: {analysis['total_photos']}")
        print(f"  🤝 With others: {analysis['with_others']}")
        print(f"  👤 Alone: {analysis['alone']}")
        if analysis['common_companions']:
            print("  👥 Common companions:")
            for comp in analysis['common_companions']:
                print(f"     - {comp['name']}: {comp['count']} photos")
    
    if args.relationships:
        relationships = analyzer.get_face_relationships()
        print(f"\n🤝 Face Relationships ({relationships['total']}):")
        for rel in relationships['relationships'][:10]:
            print(f"  {rel['people'][0]} & {rel['people'][1]}: {rel['count']} photos")
    
    analyzer.close_db()


if __name__ == "__main__":
    main()
