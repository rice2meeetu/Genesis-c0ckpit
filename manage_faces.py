#!/usr/bin/env python3
"""
GENESIS Face Management CLI Tool
"""

import sys
import os
sys.path.append('.')

from genesis.face_search import FaceSearch
from genesis.face_stats import FaceStats


def print_menu():
    """Print the main menu"""
    print("\n" + "=" * 50)
    print("👤 GENESIS Face Management")
    print("=" * 50)
    print("1. List all known faces")
    print("2. Search for a person")
    print("3. Show statistics")
    print("4. Add face to database")
    print("5. Exit")
    print("=" * 50)


def add_face():
    """Add a new face to the database"""
    import face_recognition
    import pickle
    import sqlite3
    import datetime
    
    # Get image path from user
    file_path = input("Enter path to image with a face: ").strip()
    
    if not file_path or not os.path.exists(file_path):
        print("File not found or invalid path.")
        return
    
    # Detect face
    try:
        image = face_recognition.load_image_file(file_path)
        face_locations = face_recognition.face_locations(image)
        face_encodings = face_recognition.face_encodings(image, face_locations)
        
        if not face_encodings:
            print("❌ No face detected in the image.")
            return
        
        print(f"✅ Found {len(face_locations)} face(s) in the image.")
        
        if len(face_locations) > 1:
            print("Multiple faces detected. Please select one:")
            for i in range(len(face_locations)):
                print(f"  {i+1}. Face {i+1}")
            choice = input("Enter number (1-{}): ".format(len(face_locations)))
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(face_locations):
                    print("Invalid selection.")
                    return
            except:
                print("Invalid selection.")
                return
        else:
            idx = 0
        
        name = input("Enter name for this face: ").strip()
        if not name:
            print("Name cannot be empty.")
            return
        
        # Save to database
        conn = sqlite3.connect('database/genesis.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS face_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                encoding BLOB NOT NULL,
                image_path TEXT,
                created_at TEXT
            )
        """)
        
        encoding_blob = pickle.dumps(face_encodings[idx])
        now = datetime.datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO face_data (name, encoding, image_path, created_at)
            VALUES (?, ?, ?, ?)
        """, (name, encoding_blob, file_path, now))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Face saved as: {name}")
        
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Main menu"""
    searcher = FaceSearch()
    stats = FaceStats()
    
    while True:
        print_menu()
        choice = input("Enter your choice (1-5): ").strip()
        
        if choice == "1":
            searcher.list_known_faces()
        
        elif choice == "2":
            name = input("Enter name to search: ").strip()
            if name:
                print(f"Searching for '{name}'... (this may take a moment)")
                results = searcher.search_person(name)
                if results:
                    print(f"\n📸 Found {len(results)} photos with '{name}':")
                    for i, path in enumerate(results[:10], 1):
                        print(f"  {i}. {os.path.basename(path)}")
                    if len(results) > 10:
                        print(f"  ... and {len(results) - 10} more")
                else:
                    print("No results found")
        
        elif choice == "3":
            stats.print_stats()
        
        elif choice == "4":
            add_face()
        
        elif choice == "5":
            print("👋 Goodbye!")
            break
        
        else:
            print("Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
