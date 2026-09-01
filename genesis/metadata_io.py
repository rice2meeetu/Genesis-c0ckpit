#!/usr/bin/env python3
"""
GENESIS Metadata Import/Export Module v0.10
Complete metadata management with CSV, JSON, and XML support
"""

import os
import sys
import sqlite3
import json
import csv
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom
from pathlib import Path
from datetime import datetime
import shutil
import pickle

sys.path.append('.')
from genesis.face_detection.detector import FaceDetector
from genesis.auto_tag import AutoTagger
from genesis.database import connect


class MetadataIO:
    """Complete metadata import/export"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.detector = FaceDetector(self.db_path)
        self.tagger = AutoTagger(self.db_path)
        self.export_dir = Path(os.path.expanduser("~/GENESIS-Exports"))
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    def export_metadata_json(self, output_file: str = None) -> str:
        """Export all metadata to JSON"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.export_dir / f"genesis_metadata_{timestamp}.json"
        
        data = self._collect_all_metadata()
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"✅ Exported to: {output_file}")
        return str(output_file)
    
    def export_metadata_csv(self, output_file: str = None) -> str:
        """Export metadata to CSV"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.export_dir / f"genesis_metadata_{timestamp}.csv"
        
        conn = connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, path, width, height, COALESCE(file_size, 0), modified_date, created_at
            FROM photos
        """)
        
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Path', 'Width', 'Height', 'File Size', 'Modified Date', 'Created At'])
            writer.writerows(cursor.fetchall())
        
        conn.close()
        print(f"✅ Exported to: {output_file}")
        return str(output_file)
    
    def export_metadata_xml(self, output_file: str = None) -> str:
        """Export metadata to XML"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.export_dir / f"genesis_metadata_{timestamp}.xml"
        
        data = self._collect_all_metadata()
        
        root = ET.Element("GENESIS_Metadata")
        ET.SubElement(root, "ExportDate").text = datetime.now().isoformat()
        ET.SubElement(root, "Version").text = "0.10.0"
        
        photos_elem = ET.SubElement(root, "Photos")
        for photo in data['photos']:
            photo_elem = ET.SubElement(photos_elem, "Photo")
            for key, value in photo.items():
                child = ET.SubElement(photo_elem, key)
                child.text = str(value) if value is not None else ""
        
        # Save with formatting
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
        with open(output_file, 'w') as f:
            f.write(xml_str)
        
        print(f"✅ Exported to: {output_file}")
        return str(output_file)
    
    def _collect_all_metadata(self) -> dict:
        """Collect all metadata from database"""
        conn = connect(self.db_path)
        cursor = conn.cursor()
        
        data = {
            'export_date': datetime.now().isoformat(),
            'version': '0.10.0',
            'photos': [],
            'face_data': [],
            'tags': []
        }
        
        # Photos
        cursor.execute("""
            SELECT id, path, width, height, COALESCE(file_size, 0), modified_date, created_at
            FROM photos
        """)
        for row in cursor.fetchall():
            data['photos'].append({
                'id': row[0],
                'path': row[1],
                'width': row[2],
                'height': row[3],
                'file_size': row[4],
                'modified_date': row[5],
                'created_at': row[6]
            })
        
        # Face data
        try:
            cursor.execute("SELECT id, name, image_path, created_at FROM face_data")
            for row in cursor.fetchall():
                data['face_data'].append({
                    'id': row[0],
                    'name': row[1],
                    'image_path': row[2],
                    'created_at': row[3]
                })
        except:
            pass
        
        # Tags
        try:
            cursor.execute("SELECT photo_path, person_name, confidence FROM photo_tags")
            for row in cursor.fetchall():
                data['tags'].append({
                    'photo_path': row[0],
                    'person_name': row[1],
                    'confidence': row[2]
                })
        except:
            pass
        
        conn.close()
        return data
    
    def import_metadata_json(self, input_file: str) -> bool:
        """Import metadata from JSON"""
        try:
            with open(input_file, 'r') as f:
                data = json.load(f)
            
            conn = connect(self.db_path)
            cursor = conn.cursor()
            
            # Import photos
            for photo in data.get('photos', []):
                cursor.execute("""
                    INSERT OR IGNORE INTO photos (id, path, width, height, file_size, modified_date, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (photo.get('id'), photo.get('path'), photo.get('width'), photo.get('height'),
                      photo.get('file_size'), photo.get('modified_date'), photo.get('created_at')))
            
            conn.commit()
            conn.close()
            
            print(f"✅ Imported from: {input_file}")
            return True
            
        except Exception as e:
            print(f"❌ Import failed: {e}")
            return False
    
    def import_from_directory(self, directory_path: str) -> dict:
        """Import all photos from a directory with auto-tagging"""
        print(f"📸 Importing from: {directory_path}")
        
        imported = {'photos': 0, 'faces': 0, 'errors': 0}
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'}
        image_files = []
        
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if Path(file).suffix.lower() in image_extensions:
                    image_files.append(os.path.join(root, file))
        
        print(f"📁 Found {len(image_files)} images")
        
        conn = connect(self.db_path)
        cursor = conn.cursor()
        
        for image_path in image_files:
            try:
                # Add to database
                stat = os.stat(image_path)
                cursor.execute("""
                    INSERT OR IGNORE INTO photos (path, file_size, modified_date, created_at)
                    VALUES (?, ?, ?, ?)
                """, (image_path, stat.st_size, 
                      datetime.fromtimestamp(stat.st_mtime).isoformat(),
                      datetime.now().isoformat()))
                
                imported['photos'] += 1
                
                # Auto-detect faces
                faces = self.detector.detect_faces(image_path)
                if faces:
                    for face in faces:
                        if face['name'] != 'Unknown':
                            self.tagger.save_tags_to_db(image_path, [face])
                            imported['faces'] += 1
                
            except Exception as e:
                imported['errors'] += 1
                print(f"❌ Error importing {image_path}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"✅ Imported {imported['photos']} photos, {imported['faces']} faces detected")
        return imported


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GENESIS Metadata Import/Export")
    parser.add_argument("--export-json", type=str, nargs='?', const='auto', help="Export to JSON")
    parser.add_argument("--export-csv", type=str, nargs='?', const='auto', help="Export to CSV")
    parser.add_argument("--export-xml", type=str, nargs='?', const='auto', help="Export to XML")
    parser.add_argument("--import-json", type=str, help="Import from JSON")
    parser.add_argument("--import-dir", type=str, help="Import directory with auto-tagging")
    
    args = parser.parse_args()
    
    io = MetadataIO()
    
    if args.export_json:
        io.export_metadata_json(None if args.export_json == 'auto' else args.export_json)
    
    if args.export_csv:
        io.export_metadata_csv(None if args.export_csv == 'auto' else args.export_csv)
    
    if args.export_xml:
        io.export_metadata_xml(None if args.export_xml == 'auto' else args.export_xml)
    
    if args.import_json:
        io.import_metadata_json(args.import_json)
    
    if args.import_dir:
        io.import_from_directory(args.import_dir)


if __name__ == "__main__":
    main()
