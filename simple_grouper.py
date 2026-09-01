#!/usr/bin/env python3
"""
Simple Face Grouper - ACDSee Ultimate Style
With Organize & Delete features
"""

import os
import sys
import sqlite3
import shutil
import json
from pathlib import Path
from datetime import datetime
import face_recognition
import numpy as np

sys.path.append('.')
from genesis.face_detection.detector import FaceDetector


class SimpleGrouper:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.detector = FaceDetector(db_path)
        self.groups = []
        self.kept_groups = []
        self.deleted_groups = []
    
    def scan_and_group(self, limit: int = None):
        """Simple scan and group - just like ACDSee"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if limit:
            cursor.execute("SELECT path FROM photos LIMIT ?", (limit,))
        else:
            cursor.execute("SELECT path FROM photos")
        
        photos = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        print(f"🔍 Scanning {len(photos)} photos...")
        
        # Detect all faces
        all_faces = []
        for i, path in enumerate(photos):
            if not os.path.exists(path):
                continue
            faces = self.detector.detect_faces(path)
            for face in faces:
                all_faces.append({
                    'path': path,
                    'encoding': face['encoding'],
                    'name': face['name']
                })
            if (i+1) % 50 == 0:
                print(f"  ⏳ Processed {i+1}/{len(photos)}")
        
        print(f"\n👤 Found {len(all_faces)} faces")
        
        # Group them
        if not all_faces:
            return []
        
        print("\n🔗 Grouping faces...")
        groups = []
        used = [False] * len(all_faces)
        threshold = 0.5
        
        for i in range(len(all_faces)):
            if used[i]:
                continue
            
            group = [i]
            used[i] = True
            enc_i = all_faces[i]['encoding']
            
            for j in range(i+1, len(all_faces)):
                if used[j]:
                    continue
                dist = np.linalg.norm(enc_i - all_faces[j]['encoding'])
                if dist < threshold:
                    group.append(j)
                    used[j] = True
            
            groups.append(group)
        
        # Build group data
        result = []
        for g in groups:
            # Skip single faces
            if len(g) > 1:
                # Try to name the group
                names = [all_faces[i]['name'] for i in g if all_faces[i]['name'] != 'Unknown']
                group_name = max(set(names), key=names.count) if names else f"Person_{len(result)+1}"
                
                result.append({
                    'name': group_name,
                    'faces': [all_faces[i] for i in g],
                    'count': len(g)
                })
        
        print(f"✅ Found {len(result)} face groups")
        self.groups = result
        return result
    
    def show_groups(self):
        """Show all groups with status"""
        print("\n" + "=" * 60)
        print("👤 FACE GROUPS")
        print("=" * 60)
        
        if not self.groups:
            print("No groups found. Run scan first.")
            return
        
        for i, group in enumerate(self.groups, 1):
            status = "✅" if i in self.kept_groups else "⏳"
            print(f"\n{status} Group {i}: {group['name']} ({group['count']} photos)")
            # Show first 3 files
            for face in group['faces'][:3]:
                print(f"      📸 {os.path.basename(face['path'])}")
            if group['count'] > 3:
                print(f"      ... and {group['count']-3} more")
        
        print("\n" + "=" * 60)
        print(f"📊 Total: {len(self.groups)} groups")
        print(f"✅ Kept: {len(self.kept_groups)}")
        print(f"🗑️ Deleted: {len(self.deleted_groups)}")
    
    def organize_group(self, group_num, new_name):
        """Rename/organize a group"""
        if group_num < 1 or group_num > len(self.groups):
            print(f"❌ Group {group_num} not found")
            return
        
        group = self.groups[group_num - 1]
        old_name = group['name']
        group['name'] = new_name
        
        print(f"✅ Group {group_num} renamed: {old_name} → {new_name}")
        
        # If group is exported, rename the folder too
        export_base = os.path.expanduser("~/GENESIS-Groups")
        old_folder = Path(export_base) / old_name
        new_folder = Path(export_base) / new_name
        if old_folder.exists():
            shutil.move(str(old_folder), str(new_folder))
            print(f"   📁 Folder renamed: {old_folder.name} → {new_folder.name}")
    
    def keep_group(self, group_num):
        """Mark a group as kept (protected from deletion)"""
        if group_num < 1 or group_num > len(self.groups):
            print(f"❌ Group {group_num} not found")
            return
        
        if group_num not in self.kept_groups:
            self.kept_groups.append(group_num)
            print(f"✅ Group {group_num} marked as KEPT")
        else:
            print(f"ℹ️ Group {group_num} is already kept")
    
    def delete_group(self, group_num, confirm=True):
        """Delete a group"""
        if group_num < 1 or group_num > len(self.groups):
            print(f"❌ Group {group_num} not found")
            return
        
        if group_num in self.kept_groups:
            print(f"⚠️ Group {group_num} is KEPT. Unkeep it first to delete.")
            return
        
        group = self.groups[group_num - 1]
        
        if confirm:
            print(f"\n⚠️ Delete group {group_num}: {group['name']} ({group['count']} photos)")
            choice = input("Are you sure? (y/n): ").strip()
            if choice.lower() != 'y':
                print("  Cancelled")
                return
        
        # Delete exported folder if exists
        export_base = os.path.expanduser("~/GENESIS-Groups")
        group_folder = Path(export_base) / group['name']
        if group_folder.exists():
            shutil.rmtree(group_folder)
            print(f"   🗑️ Deleted folder: {group_folder}")
        
        # Remove from groups
        self.deleted_groups.append(group_num)
        
        print(f"✅ Group {group_num} deleted")
    
    def export_group(self, group_num, output_dir=None):
        """Export a specific group"""
        if group_num < 1 or group_num > len(self.groups):
            print(f"❌ Group {group_num} not found")
            return
        
        group = self.groups[group_num - 1]
        
        if output_dir is None:
            export_base = os.path.expanduser("~/GENESIS-Groups")
            # Use group name if available, otherwise use number
            name = group['name'].replace(" ", "_")
            output_dir = str(Path(export_base) / name)
        
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\n📤 Exporting group {group_num}: {group['name']} ({group['count']} photos)...")
        
        for i, face in enumerate(group['faces'], 1):
            src = face['path']
            if os.path.exists(src):
                ext = Path(src).suffix
                dst = Path(output_dir) / f"{group['name']}_{i:03d}{ext}"
                shutil.copy2(src, dst)
                print(f"  ✅ {dst.name}")
        
        # Save info
        info = {
            'group_num': group_num,
            'name': group['name'],
            'count': group['count'],
            'exported': datetime.now().isoformat()
        }
        with open(Path(output_dir) / "_group_info.json", 'w') as f:
            json.dump(info, f, indent=2)
        
        print(f"\n✅ Exported to: {output_dir}")
        return output_dir
    
    def export_all_groups(self):
        """Export all groups"""
        print("\n📦 Exporting ALL groups...")
        exported = []
        
        for i in range(1, len(self.groups) + 1):
            if i not in self.deleted_groups:
                output = self.export_group(i)
                exported.append(output)
        
        print(f"\n✅ Exported {len(exported)} groups to ~/GENESIS-Groups/")
        return exported


def main():
    print("👤 Simple Face Grouper (ACDSee Style)")
    print("=" * 50)
    print("Scan, Group, Organize, and Delete!")
    print("")
    
    grouper = SimpleGrouper()
    
    while True:
        print("\n📋 Options:")
        print("  ─────────────────────────────")
        print("  1 - Scan photos & group faces")
        print("  2 - Show groups")
        print("  3 - Rename/Organize a group")
        print("  4 - Keep a group (protect)")
        print("  5 - Delete a group")
        print("  6 - Export a group")
        print("  7 - Export ALL groups")
        print("  8 - Exit")
        print("  ─────────────────────────────")
        
        choice = input("\nChoice: ").strip()
        
        if choice == '1':
            limit = input("Scan limit? (press Enter for all): ").strip()
            limit = int(limit) if limit else None
            grouper.scan_and_group(limit)
            grouper.show_groups()
            print("\n💡 Tip: Use option 4 to keep groups, option 5 to delete")
        
        elif choice == '2':
            grouper.show_groups()
        
        elif choice == '3':
            if not grouper.groups:
                print("❌ No groups found. Scan first.")
                continue
            
            grouper.show_groups()
            num = int(input("\nGroup number to rename: ").strip())
            new_name = input("New name: ").strip()
            if new_name:
                grouper.organize_group(num, new_name)
        
        elif choice == '4':
            if not grouper.groups:
                print("❌ No groups found. Scan first.")
                continue
            
            grouper.show_groups()
            nums = input("\nGroup number(s) to keep (e.g., 1,3,5): ").strip()
            for num in nums.split(','):
                try:
                    grouper.keep_group(int(num.strip()))
                except:
                    pass
        
        elif choice == '5':
            if not grouper.groups:
                print("❌ No groups found. Scan first.")
                continue
            
            grouper.show_groups()
            nums = input("\nGroup number(s) to delete (e.g., 2,4,6): ").strip()
            for num in nums.split(','):
                try:
                    grouper.delete_group(int(num.strip()))
                except:
                    pass
        
        elif choice == '6':
            if not grouper.groups:
                print("❌ No groups found. Scan first.")
                continue
            
            grouper.show_groups()
            num = int(input("\nGroup number to export: ").strip())
            output = input("Output folder (press Enter for default): ").strip()
            if not output:
                output = None
            else:
                output = os.path.expanduser(output)
            grouper.export_group(num, output)
        
        elif choice == '7':
            if not grouper.groups:
                print("❌ No groups found. Scan first.")
                continue
            grouper.export_all_groups()
        
        elif choice == '8':
            print("\n👋 Bye!")
            print("\n📁 Groups saved to: ~/GENESIS-Groups/")
            print("✅ Kept groups: ", grouper.kept_groups)
            print("🗑️ Deleted groups: ", grouper.deleted_groups)
            break
        
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()
