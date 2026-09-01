#!/usr/bin/env python3
"""
GENESIS Person Group Manager
Organize, keep, or delete person groups
"""

import os
import sys
import shutil
import json
from pathlib import Path

class PersonManager:
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or os.path.expanduser("~/GENESIS-Characters"))
        self.index_file = self.base_dir / "_character_index.json"
        self.groups = self.load_index()

    def load_index(self):
        """Load character index"""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                return json.load(f)
        return []

    def list_groups(self):
        """List all person groups"""
        print("\n👤 Your Character Groups:")
        print("=" * 50)

        if not self.groups:
            print("  No groups found. Run person_group.py first!")
            return

        for i, group in enumerate(self.groups, 1):
            print(f"  {i}. {group['name']}: {group['variants']} variants")
            print(f"     📁 {group['path']}")

        print(f"\n📊 Total: {len(self.groups)} characters")
        return self.groups

    def keep_group(self, name_or_index):
        """Keep a specific group (mark as keep)"""
        # Find the group
        group = None
        if isinstance(name_or_index, int):
            if 1 <= name_or_index <= len(self.groups):
                group = self.groups[name_or_index - 1]
        else:
            for g in self.groups:
                if g['name'].lower() == name_or_index.lower():
                    group = g
                    break

        if not group:
            print(f"❌ Group not found: {name_or_index}")
            return False

        # Mark as kept
        group['keep'] = True

        # Save index
        with open(self.index_file, 'w') as f:
            json.dump(self.groups, f, indent=2)

        print(f"✅ Kept: {group['name']} ({group['variants']} variants)")
        return True

    def delete_group(self, name_or_index, confirm=True):
        """Delete a specific group"""
        group = None
        if isinstance(name_or_index, int):
            if 1 <= name_or_index <= len(self.groups):
                group = self.groups[name_or_index - 1]
        else:
            for g in self.groups:
                if g['name'].lower() == name_or_index.lower():
                    group = g
                    break

        if not group:
            print(f"❌ Group not found: {name_or_index}")
            return False

        # Confirm deletion
        if confirm:
            print(f"\n⚠️ Delete: {group['name']} ({group['variants']} variants)")
            confirm = input(f"Delete folder {os.path.basename(group['path'])}? (y/n): ").strip()
            if confirm.lower() != 'y':
                print("  Cancelled")
                return False

        # Delete folder
        path = Path(group['path'])
        if path.exists():
            shutil.rmtree(path)
            print(f"🗑️ Deleted: {path}")

        # Remove from index
        self.groups = [g for g in self.groups if g['name'] != group['name']]
        with open(self.index_file, 'w') as f:
            json.dump(self.groups, f, indent=2)

        print(f"✅ Removed from index: {group['name']}")
        return True

    def move_group(self, name_or_index, dest_dir):
        """Move a group to another directory"""
        group = None
        if isinstance(name_or_index, int):
            if 1 <= name_or_index <= len(self.groups):
                group = self.groups[name_or_index - 1]
        else:
            for g in self.groups:
                if g['name'].lower() == name_or_index.lower():
                    group = g
                    break

        if not group:
            print(f"❌ Group not found: {name_or_index}")
            return False

        src = Path(group['path'])
        dest = Path(dest_dir) / src.name

        if not src.exists():
            print(f"❌ Source not found: {src}")
            return False

        # Move
        shutil.move(str(src), str(dest))
        group['path'] = str(dest)

        # Save index
        with open(self.index_file, 'w') as f:
            json.dump(self.groups, f, indent=2)

        print(f"✅ Moved: {group['name']} -> {dest}")
        return True

    def export_summary(self):
        """Export summary of all groups"""
        summary_file = self.base_dir / "_groups_summary.txt"

        with open(summary_file, 'w') as f:
            f.write("GENESIS Character Groups Summary\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")

            kept = [g for g in self.groups if g.get('keep', False)]
            not_kept = [g for g in self.groups if not g.get('keep', False)]

            f.write(f"Total groups: {len(self.groups)}\n")
            f.write(f"Kept: {len(kept)}\n")
            f.write(f"To review: {len(not_kept)}\n\n")

            f.write("KEPT GROUPS:\n")
            for g in kept:
                f.write(f"  ✅ {g['name']}: {g['variants']} variants\n")

            f.write("\nTO REVIEW:\n")
            for g in not_kept:
                f.write(f"  ⏳ {g['name']}: {g['variants']} variants\n")

        print(f"📄 Summary exported: {summary_file}")

def main():
    print("👤 Person Group Manager")
    print("=" * 50)

    manager = PersonManager()

    while True:
        print("\n📋 Options:")
        print("  1 - List all groups")
        print("  2 - Keep a group (protect from deletion)")
        print("  3 - Delete a group")
        print("  4 - Move a group")
        print("  5 - Export summary")
        print("  6 - Exit")

        choice = input("\nChoose (1-6): ").strip()

        if choice == '1':
            manager.list_groups()

        elif choice == '2':
            manager.list_groups()
            try:
                num = int(input("\nEnter group number to keep: ").strip())
                manager.keep_group(num)
            except:
                name = input("Enter group name: ").strip()
                manager.keep_group(name)

        elif choice == '3':
            manager.list_groups()
            try:
                num = int(input("\nEnter group number to delete: ").strip())
                manager.delete_group(num)
            except:
                name = input("Enter group name: ").strip()
                manager.delete_group(name)

        elif choice == '4':
            manager.list_groups()
            try:
                num = int(input("\nEnter group number to move: ").strip())
                dest = input("Destination directory: ").strip()
                manager.move_group(num, dest)
            except:
                print("Invalid input")

        elif choice == '5':
            manager.export_summary()

        elif choice == '6':
            print("👋 Goodbye!")
            break

        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    from datetime import datetime
    main()
