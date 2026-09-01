#!/usr/bin/env python3
"""
GENESIS Face Detection Module v0.3
Face detection and recognition for photo gallery
"""

import os
import sys
import sqlite3
import json
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import hashlib
import datetime

try:
    import cv2
    import face_recognition
    import numpy as np
    from PIL import Image, ImageDraw, ImageTk
except ImportError as e:
    print(f"ERROR: Required packages not installed: {e}")
    print("Run: pip install opencv-python face-recognition numpy Pillow")
    sys.exit(1)


class FaceDetector:
    """Face detection and recognition engine"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.known_faces = {}
        self.known_encodings = []
        self.known_names = []
        self.load_known_faces()
        
    def load_known_faces(self):
        """Load known faces from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if face_data table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='face_data'
            """)
            
            if cursor.fetchone():
                cursor.execute("""
                    SELECT name, encoding, id, image_path 
                    FROM face_data
                """)
                
                for row in cursor.fetchall():
                    name, encoding_blob, face_id, image_path = row
                    if encoding_blob:
                        encoding = pickle.loads(encoding_blob)
                        self.known_faces[name] = {
                            'encoding': encoding,
                            'id': face_id,
                            'image_path': image_path
                        }
                        self.known_encodings.append(encoding)
                        self.known_names.append(name)
            
            conn.close()
            print(f"✅ Loaded {len(self.known_faces)} known faces")
        except Exception as e:
            print(f"Error loading known faces: {e}")
    
    def detect_faces(self, image_path: str) -> List[Dict]:
        """Detect faces in an image"""
        try:
            # Load image
            image = face_recognition.load_image_file(image_path)
            
            # Find face locations
            face_locations = face_recognition.face_locations(image)
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            results = []
            
            for i, (location, encoding) in enumerate(zip(face_locations, face_encodings)):
                # Compare with known faces
                matches = face_recognition.compare_faces(self.known_encodings, encoding, tolerance=0.6)
                name = "Unknown"
                
                # If match found, get name
                if True in matches:
                    match_index = matches.index(True)
                    name = self.known_names[match_index]
                
                # Get confidence
                if self.known_encodings:
                    distances = face_recognition.face_distance(self.known_encodings, encoding)
                    confidence = 1.0 - min(distances) if len(distances) > 0 else 0.0
                else:
                    confidence = 0.0
                
                # Extract face crop
                top, right, bottom, left = location
                
                results.append({
                    'location': {
                        'top': top,
                        'right': right,
                        'bottom': bottom,
                        'left': left
                    },
                    'encoding': encoding,
                    'name': name,
                    'confidence': confidence,
                    'index': i
                })
            
            return results
            
        except Exception as e:
            print(f"Error detecting faces in {image_path}: {e}")
            return []
    
    def save_face(self, name: str, encoding: np.ndarray, image_path: str, face_id: int = None):
        """Save a known face to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS face_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    encoding BLOB NOT NULL,
                    image_path TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # Check if face already exists
            cursor.execute(
                "SELECT id FROM face_data WHERE name = ? AND image_path = ?",
                (name, image_path)
            )
            existing = cursor.fetchone()
            
            now = datetime.datetime.now().isoformat()
            encoding_blob = pickle.dumps(encoding)
            
            if existing:
                cursor.execute("""
                    UPDATE face_data 
                    SET encoding = ?, updated_at = ?
                    WHERE name = ? AND image_path = ?
                """, (encoding_blob, now, name, image_path))
                face_id = existing[0]
            else:
                cursor.execute("""
                    INSERT INTO face_data (name, encoding, image_path, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, encoding_blob, image_path, now, now))
                face_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            
            # Update memory
            self.known_faces[name] = {
                'encoding': encoding,
                'id': face_id,
                'image_path': image_path
            }
            
            # Update encodings list
            if name in self.known_names:
                idx = self.known_names.index(name)
                self.known_encodings[idx] = encoding
            else:
                self.known_encodings.append(encoding)
                self.known_names.append(name)
            
            print(f"✅ Saved face: {name} (ID: {face_id})")
            return True
            
        except Exception as e:
            print(f"Error saving face: {e}")
            return False
    
    def delete_face(self, face_id: int):
        """Delete a face from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM face_data WHERE id = ?", (face_id,))
            conn.commit()
            conn.close()
            print(f"✅ Deleted face ID: {face_id}")
            return True
        except Exception as e:
            print(f"Error deleting face: {e}")
            return False
    
    def get_face_metadata(self, image_path: str) -> Dict:
        """Get face metadata for an image"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT face_data.name, face_data.id 
                FROM face_data
                JOIN face_assignments ON face_data.id = face_assignments.face_id
                WHERE face_assignments.image_path = ?
            """, (image_path,))
            
            results = cursor.fetchall()
            conn.close()
            
            return {
                'faces': [{'name': row[0], 'id': row[1]} for row in results],
                'count': len(results)
            }
        except Exception as e:
            return {'faces': [], 'count': 0}
    
    def get_all_face_names(self) -> List[str]:
        """Get all unique face names"""
        return list(self.known_faces.keys())


class FaceUI:
    """Face detection UI integration"""
    
    def __init__(self, parent, detector: FaceDetector):
        self.parent = parent
        self.detector = detector
        self.current_image_path = None
        self.face_rectangles = []
        self.selected_face = None
        
    def detect_and_display(self, image_path: str):
        """Detect faces and display on image"""
        self.current_image_path = image_path
        
        if not os.path.exists(image_path):
            return None, []
        
        # Detect faces
        faces = self.detector.detect_faces(image_path)
        
        # Load image for display
        image = cv2.imread(image_path)
        if image is None:
            return None, []
            
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Draw rectangles around faces
        for face in faces:
            loc = face['location']
            top, right, bottom, left = loc['top'], loc['right'], loc['bottom'], loc['left']
            
            # Draw rectangle
            cv2.rectangle(image_rgb, (left, top), (right, bottom), (0, 255, 0), 2)
            
            # Draw name label
            name = face['name']
            confidence = face['confidence']
            label = f"{name} ({confidence:.0%})"
            cv2.putText(image_rgb, label, (left, top - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Convert to PIL for display
        pil_image = Image.fromarray(image_rgb)
        self.face_rectangles = faces
        
        return pil_image, faces
    
    def add_face_name(self, face_index: int, name: str):
        """Add a name to a detected face"""
        if not self.face_rectangles or face_index >= len(self.face_rectangles):
            return False
        
        face = self.face_rectangles[face_index]
        encoding = face['encoding']
        
        # Save to database
        return self.detector.save_face(name, encoding, self.current_image_path)
    
    def get_known_names(self) -> List[str]:
        """Get list of known face names"""
        return self.detector.get_all_face_names()


def main():
    """Test face detection"""
    import tkinter as tk
    from tkinter import filedialog
    
    print("🔍 GENESIS Face Detection Test")
    print("==============================")
    
    # Initialize detector
    db_path = os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
    detector = FaceDetector(db_path)
    
    # Test on a single image
    print("\nSelect an image to test face detection...")
    
    root = tk.Tk()
    root.withdraw()
    
    file_path = filedialog.askopenfilename(
        title="Select an image",
        filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif")]
    )
    
    if file_path:
        faces = detector.detect_faces(file_path)
        print(f"\n✅ Found {len(faces)} faces in {os.path.basename(file_path)}")
        
        for i, face in enumerate(faces):
            print(f"  Face {i+1}: {face['name']} (confidence: {face['confidence']:.0%})")
        
        if faces:
            # Show the image with face rectangles
            try:
                import matplotlib.pyplot as plt
                
                image = cv2.imread(file_path)
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                for face in faces:
                    loc = face['location']
                    top, right, bottom, left = loc['top'], loc['right'], loc['bottom'], loc['left']
                    cv2.rectangle(image_rgb, (left, top), (right, bottom), (0, 255, 0), 2)
                    name = face['name']
                    confidence = face['confidence']
                    cv2.putText(image_rgb, f"{name} ({confidence:.0%})", 
                               (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                
                plt.figure(figsize=(10, 8))
                plt.imshow(image_rgb)
                plt.axis('off')
                plt.title(f"Faces Found: {len(faces)}")
                plt.show()
            except ImportError:
                print("   Install matplotlib to view: pip install matplotlib")
    
    root.destroy()


if __name__ == "__main__":
    main()
