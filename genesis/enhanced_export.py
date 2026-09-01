#!/usr/bin/env python3
"""
GENESIS Enhanced Export Module v0.6
Advanced export options for photos
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

sys.path.append('.')
from genesis.face_groups_optimized import FaceGroupsOptimized
from genesis.multi_face_analysis import MultiFaceAnalyzer


class EnhancedExporter:
    """Enhanced photo export with multiple options"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/GENESIS-Photo-Studio/database/genesis.db")
        self.groups = FaceGroupsOptimized(self.db_path)
        self.analyzer = MultiFaceAnalyzer(self.db_path)
    
    def export_album_with_options(self, 
                                  person_name: str,
                                  output_format: str = 'folder',
                                  resize: bool = False,
                                  max_size: int = 1920,
                                  add_metadata: bool = True,
                                  social_media_ready: bool = False) -> str:
        """Export album with various options"""
        
        # Get photos
        photos = self.groups.get_person_photos_from_db(person_name)
        if not photos:
            print(f"No photos found for {person_name}")
            return None
        
        # Create output directory
        base_dir = os.path.expanduser("~/GENESIS-Exports")
        os.makedirs(base_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_name = f"{person_name}_{timestamp}"
        
        if output_format == 'folder':
            output_path = os.path.join(base_dir, export_name)
            os.makedirs(output_path, exist_ok=True)
            
            print(f"📁 Exporting {len(photos)} photos to {output_path}")
            
            for i, src_path in enumerate(photos, 1):
                if os.path.exists(src_path):
                    ext = Path(src_path).suffix
                    dest_path = os.path.join(output_path, f"{person_name}_{i:04d}{ext}")
                    self._copy_with_options(src_path, dest_path, resize, max_size, social_media_ready)
            
            if add_metadata:
                self._add_metadata_file(output_path, person_name, photos)
            
        elif output_format == 'zip':
            # Create folder first
            temp_dir = os.path.join(base_dir, f"temp_{export_name}")
            os.makedirs(temp_dir, exist_ok=True)
            
            for i, src_path in enumerate(photos, 1):
                if os.path.exists(src_path):
                    ext = Path(src_path).suffix
                    dest_path = os.path.join(temp_dir, f"{person_name}_{i:04d}{ext}")
                    self._copy_with_options(src_path, dest_path, resize, max_size, social_media_ready)
            
            if add_metadata:
                self._add_metadata_file(temp_dir, person_name, photos)
            
            # Create zip
            zip_path = os.path.join(base_dir, f"{export_name}.zip")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.dirname(temp_dir))
                        zipf.write(file_path, arcname)
            
            # Cleanup temp
            shutil.rmtree(temp_dir)
            output_path = zip_path
            print(f"📦 Exported ZIP: {output_path}")
        
        return output_path
    
    def _copy_with_options(self, src_path, dest_path, resize, max_size, social_media_ready):
        """Copy photo with optional processing"""
        if resize or social_media_ready:
            try:
                img = Image.open(src_path)
                
                # Social media optimization
                if social_media_ready:
                    # Convert to RGB (for web)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Optimize for social media
                    max_dimension = max_size
                    if max(img.size) > max_dimension:
                        ratio = max_dimension / max(img.size)
                        new_size = tuple(int(dim * ratio) for dim in img.size)
                        img = img.resize(new_size, Image.Resampling.LANCZOS)
                    
                    # Save with optimization
                    img.save(dest_path, quality=85, optimize=True)
                    return
                
                # Normal resize
                if resize:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                img.save(dest_path)
                
            except Exception as e:
                print(f"Error processing {src_path}: {e}")
                # Fallback to direct copy
                shutil.copy2(src_path, dest_path)
        else:
            shutil.copy2(src_path, dest_path)
    
    def _add_metadata_file(self, directory, person_name, photos):
        """Add metadata file to export"""
        info_path = os.path.join(directory, "_export_info.txt")
        
        # Get person analysis
        analysis = self.analyzer.get_person_analysis(person_name)
        
        with open(info_path, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("GENESIS PHOTO EXPORT\n")
            f.write("=" * 60 + "\n")
            f.write(f"Person: {person_name}\n")
            f.write(f"Photos: {len(photos)}\n")
            f.write(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Photos: {analysis.get('total_photos', 0)}\n")
            f.write(f"With Others: {analysis.get('with_others', 0)}\n")
            f.write(f"Alone: {analysis.get('alone', 0)}\n")
            
            if analysis.get('common_companions'):
                f.write("\nCommon Companions:\n")
                for comp in analysis['common_companions'][:5]:
                    f.write(f"  - {comp['name']}: {comp['count']} photos\n")
            
            f.write("\n" + "=" * 60 + "\n")
            f.write("Generated by GENESIS Photo Studio v0.6\n")
            f.write("=" * 60 + "\n")
    
    def export_social_media(self, person_name: str, platform: str = 'all'):
        """Export photos optimized for social media"""
        platforms = {
            'instagram': {'size': 1080, 'format': 'jpg'},
            'facebook': {'size': 2048, 'format': 'jpg'},
            'twitter': {'size': 1200, 'format': 'jpg'},
            'linkedin': {'size': 1200, 'format': 'jpg'},
            'pinterest': {'size': 1000, 'format': 'jpg'},
            'all': {'size': 1080, 'format': 'jpg'}
        }
        
        if platform not in platforms:
            print(f"Unknown platform: {platform}")
            return
        
        target = platforms[platform]
        if platform == 'all':
            # Export for all platforms
            results = {}
            for p in ['instagram', 'facebook', 'twitter', 'linkedin']:
                print(f"\n📤 Exporting for {p.upper()}...")
                result = self.export_album_with_options(
                    person_name,
                    output_format='folder',
                    resize=True,
                    max_size=platforms[p]['size'],
                    social_media_ready=True
                )
                if result:
                    results[p] = result
            return results
        else:
            return self.export_album_with_options(
                person_name,
                output_format='folder',
                resize=True,
                max_size=target['size'],
                social_media_ready=True
            )
    
    def export_photo_collage(self, person_name: str, cols: int = 3):
        """Create a photo collage of a person"""
        photos = self.groups.get_person_photos_from_db(person_name)
        if not photos:
            print(f"No photos found for {person_name}")
            return
        
        # Select top photos (up to 9)
        photos = photos[:9]
        
        # Create collage
        from PIL import Image
        import math
        
        rows = math.ceil(len(photos) / cols)
        thumb_size = 300
        spacing = 10
        
        # Calculate collage dimensions
        width = cols * (thumb_size + spacing) - spacing
        height = rows * (thumb_size + spacing) - spacing
        
        # Create blank canvas
        collage = Image.new('RGB', (width, height), (40, 40, 40))
        
        for i, photo_path in enumerate(photos):
            if not os.path.exists(photo_path):
                continue
            
            try:
                img = Image.open(photo_path)
                img.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)
                
                # Calculate position
                row = i // cols
                col = i % cols
                x = col * (thumb_size + spacing)
                y = row * (thumb_size + spacing)
                
                # Center image
                x_offset = (thumb_size - img.width) // 2
                y_offset = (thumb_size - img.height) // 2
                
                collage.paste(img, (x + x_offset, y + y_offset))
                
            except Exception as e:
                print(f"Error processing {photo_path}: {e}")
        
        # Save collage
        output_dir = os.path.expanduser("~/GENESIS-Collages")
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, f"{person_name}_collage.jpg")
        collage.save(output_path, quality=90)
        
        print(f"✅ Collage created: {output_path}")
        return output_path


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="GENESIS Enhanced Export")
    parser.add_argument("--export", type=str, help="Export album for a person")
    parser.add_argument("--format", choices=['folder', 'zip'], default='folder',
                       help="Export format")
    parser.add_argument("--resize", action="store_true", help="Resize images")
    parser.add_argument("--max-size", type=int, default=1920,
                       help="Maximum dimension for resized images")
    parser.add_argument("--social", choices=['instagram', 'facebook', 'twitter', 
                                            'linkedin', 'pinterest', 'all'],
                       help="Export for social media platform")
    parser.add_argument("--collage", type=str, help="Create collage for a person")
    parser.add_argument("--metadata", action="store_true", default=True,
                       help="Include metadata file")
    
    args = parser.parse_args()
    
    exporter = EnhancedExporter()
    
    if args.social:
        result = exporter.export_social_media(args.social)
        if result:
            print(f"✅ Exported for {args.social}")
    
    elif args.export:
        result = exporter.export_album_with_options(
            args.export,
            output_format=args.format,
            resize=args.resize,
            max_size=args.max_size,
            add_metadata=args.metadata
        )
        if result:
            print(f"✅ Export complete: {result}")
    
    elif args.collage:
        exporter.export_photo_collage(args.collage)
    
    else:
        print("Use --help for available commands")


if __name__ == "__main__":
    main()
