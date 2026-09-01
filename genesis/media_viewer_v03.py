#!/usr/bin/env python3
"""
GENESIS Media Viewer v0.3 - Face Detection
"""

import os
import sys
import sqlite3
import datetime
from pathlib import Path
from PIL import Image, ImageTk, ImageFile
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext

sys.path.append('.')
from genesis.face_detection.detector import FaceDetector, FaceUI

ImageFile.LOAD_TRUNCATED_IMAGES = True

DB = Path("database/genesis.db")
CACHE = Path("cache/thumbnails")


class MediaViewerV03:
    """Media Viewer with face detection"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("📷 GENESIS v0.3 - Face Detection Media Viewer")
        self.root.geometry("1400x900")
        
        self.images = []
        self.thumbnails = {}
        self.current_path = None
        
        # Initialize face detector
        self.detector = FaceDetector()
        self.face_ui = FaceUI(self, self.detector)
        
        self.build_ui()
        self.load_database()
        
    def build_ui(self):
        """Build the user interface"""
        # Main container
        main_paned = ttk.PanedWindow(self.root, orient='horizontal')
        main_paned.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Left: Gallery
        gallery_frame = ttk.Frame(main_paned)
        main_paned.add(gallery_frame, weight=1)
        
        # Gallery controls
        gallery_controls = ttk.Frame(gallery_frame)
        gallery_controls.pack(fill='x', pady=(0,5))
        
        ttk.Label(gallery_controls, text="📷 Media Gallery", font=('', 12, 'bold')).pack(side='left')
        ttk.Button(gallery_controls, text="🔄 Refresh", command=self.load_database).pack(side='right')
        
        # Gallery grid with scroll
        gallery_scroll = ttk.Frame(gallery_frame)
        gallery_scroll.pack(fill='both', expand=True)
        
        self.canvas = tk.Canvas(gallery_scroll, bg='#1a1a1a')
        scrollbar = ttk.Scrollbar(gallery_scroll, orient='vertical', command=self.canvas.yview)
        
        self.thumb_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0,0), window=self.thumb_frame, anchor='nw')
        self.thumb_frame.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Right: Preview
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)
        
        # Preview
        preview_frame = ttk.LabelFrame(right_frame, text="🖼️ Preview", padding=5)
        preview_frame.pack(fill='both', expand=True)
        
        self.preview_label = ttk.Label(preview_frame, text="Select an image to preview", 
                                       background='#2a2a2a', foreground='#888')
        self.preview_label.pack(fill='both', expand=True)
        
        # Metadata
        meta_frame = ttk.LabelFrame(right_frame, text="📋 Metadata", padding=5)
        meta_frame.pack(fill='x', pady=(5,0))
        
        self.meta_text = scrolledtext.ScrolledText(meta_frame, height=6, width=40, 
                                                   background='#1e1e1e', foreground='#ddd',
                                                   insertbackground='white')
        self.meta_text.pack(fill='x')
        
        # Face Detection
        face_frame = ttk.LabelFrame(right_frame, text="👤 Face Detection", padding=5)
        face_frame.pack(fill='x', pady=(5,0))
        
        face_controls = ttk.Frame(face_frame)
        face_controls.pack(fill='x')
        
        self.detect_btn = ttk.Button(face_controls, text="🔍 Detect Faces", 
                                     command=self.detect_faces)
        self.detect_btn.pack(side='left', padx=2)
        
        self.add_face_btn = ttk.Button(face_controls, text="➕ Add Face", 
                                       command=self.add_face_name)
        self.add_face_btn.pack(side='left', padx=2)
        
        self.face_count_label = ttk.Label(face_controls, text="Faces: 0")
        self.face_count_label.pack(side='right', padx=5)
        
        # Navigation
        nav_frame = ttk.LabelFrame(right_frame, text="📋 Navigation", padding=5)
        nav_frame.pack(fill='x', pady=(5,0))
        
        nav_controls = ttk.Frame(nav_frame)
        nav_controls.pack(fill='x')
        
        ttk.Button(nav_controls, text="◀ Previous", command=self.prev_image).pack(side='left', padx=2)
        ttk.Button(nav_controls, text="Next ▶", command=self.next_image).pack(side='left', padx=2)
        
        self.image_counter = ttk.Label(nav_controls, text="0 / 0")
        self.image_counter.pack(side='right', padx=5)
        
        # Style
        self.apply_style()
        
    def apply_style(self):
        """Apply custom styling"""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TLabelframe.Label', font=('', 10, 'bold'))
        style.configure('TLabel', background='#1e1e1e', foreground='#ddd')
        style.configure('TFrame', background='#1e1e1e')
        
    def load_database(self):
        """Load images from database"""
        try:
            con = sqlite3.connect(DB)
            cur = con.cursor()
            
            cur.execute("""
                SELECT path, id, width, height, file_size, modified_date 
                FROM photos 
                ORDER BY modified_date DESC
            """)
            self.images = cur.fetchall()
            
            con.close()
            
            print(f"📸 Loaded {len(self.images)} images")
            self.show_thumbnails()
            
            if self.images:
                self.image_counter.config(text=f"1 / {len(self.images)}")
                self.show_preview(self.images[0][0])
            
        except Exception as e:
            print(f"Error loading database: {e}")
            messagebox.showerror("Error", f"Failed to load database: {e}")
    
    def show_thumbnails(self):
        """Display thumbnails in grid"""
        # Clear existing thumbnails
        for widget in self.thumb_frame.winfo_children():
            widget.destroy()
        
        columns = 6
        self.thumbnails = {}
        
        for i, (path, img_id, width, height, file_size, modified) in enumerate(self.images):
            if not path or not os.path.exists(path):
                continue
                
            thumb = CACHE / (Path(path).stem + ".jpg")
            
            if not thumb.exists():
                continue
                
            try:
                img = Image.open(thumb)
                img.thumbnail((120, 120))
                
                if img.width < 1 or img.height < 1:
                    continue
                    
                photo = ImageTk.PhotoImage(img)
                
                btn = ttk.Button(
                    self.thumb_frame,
                    image=photo,
                    command=lambda p=path: self.show_preview(p)
                )
                btn.image = photo
                
                row = i // columns
                col = i % columns
                btn.grid(row=row, column=col, padx=4, pady=4, sticky='nsew')
                self.thumbnails[path] = btn
                
            except Exception as e:
                print(f"Error loading thumbnail: {e}")
        
        # Configure grid
        for col in range(columns):
            self.thumb_frame.grid_columnconfigure(col, weight=1)
    
    def show_preview(self, path):
        """Show image preview with metadata"""
        self.current_path = path
        
        # Update counter
        for i, (p, id_, w, h, fs, md) in enumerate(self.images):
            if p == path:
                self.image_counter.config(text=f"{i+1} / {len(self.images)}")
                break
        
        # Load and display image
        try:
            img = Image.open(path)
            
            # Resize for preview
            max_size = (600, 500)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            photo = ImageTk.PhotoImage(img)
            self.preview_label.config(image=photo)
            self.preview_label.image = photo
            
            # Show metadata
            stats = os.stat(path) if os.path.exists(path) else None
            meta = f"""📄 Filename: {os.path.basename(path)}
📐 Dimensions: {img.width} × {img.height}
💾 Filesize: {stats.st_size / 1024:.1f} KB" if stats else "N/A"
📅 Modified: {datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S') if stats else 'N/A'}
🔗 Path: {path}"""
            
            self.meta_text.delete(1.0, tk.END)
            self.meta_text.insert(1.0, meta)
            
            # Check for existing face data
            face_meta = self.detector.get_face_metadata(path)
            self.face_count_label.config(text=f"Faces: {face_meta['count']}")
            
        except Exception as e:
            print(f"Error showing preview: {e}")
    
    def detect_faces(self):
        """Detect faces in current image"""
        if not self.current_path or not os.path.exists(self.current_path):
            messagebox.showwarning("Warning", "No image selected!")
            return
        
        self.detect_btn.config(text="⏳ Detecting...", state='disabled')
        self.root.update()
        
        try:
            # Detect faces
            pil_image, faces = self.face_ui.detect_and_display(self.current_path)
            
            if pil_image:
                # Convert PIL to PhotoImage
                photo = ImageTk.PhotoImage(pil_image)
                self.preview_label.config(image=photo)
                self.preview_label.image = photo
            
            # Update count
            count = len(faces) if faces else 0
            self.face_count_label.config(text=f"Faces: {count}")
            
            if count == 0:
                messagebox.showinfo("No Faces", "No faces detected in this image.")
            else:
                # Show face details
                details = [f"Face {i+1}: {face['name']} (confidence: {face['confidence']:.0%})" 
                          for i, face in enumerate(faces)]
                details.insert(0, f"Found {count} faces:")
                
                messagebox.showinfo(
                    f"Faces Found ({count})", 
                    "\n".join(details)
                )
                
        except Exception as e:
            messagebox.showerror("Error", f"Face detection failed: {e}")
        
        self.detect_btn.config(text="🔍 Detect Faces", state='normal')
    
    def add_face_name(self):
        """Add a name to detected face"""
        if not self.face_ui.face_rectangles:
            messagebox.showwarning("Warning", "No faces detected! Click 'Detect Faces' first.")
            return
        
        # Get face index
        face_index = simpledialog.askinteger(
            "Face Index",
            f"Which face to name? (1-{len(self.face_ui.face_rectangles)})",
            minvalue=1,
            maxvalue=len(self.face_ui.face_rectangles)
        )
        
        if not face_index:
            return
        
        # Get name
        name = simpledialog.askstring("Face Name", "Enter name for this face:")
        
        if not name or name.strip() == "":
            return
        
        # Save face
        success = self.face_ui.add_face_name(face_index - 1, name.strip())
        
        if success:
            messagebox.showinfo("Success", f"✅ Face saved as '{name.strip()}'!")
            self.face_count_label.config(text=f"Faces: {len(self.face_ui.face_rectangles)}")
            # Refresh preview with names
            self.detect_faces()
        else:
            messagebox.showerror("Error", "❌ Failed to save face.")
    
    def prev_image(self):
        """Go to previous image"""
        if not self.images or not self.current_path:
            return
        
        for i, (path, id_, w, h, fs, md) in enumerate(self.images):
            if path == self.current_path and i > 0:
                self.show_preview(self.images[i-1][0])
                break
    
    def next_image(self):
        """Go to next image"""
        if not self.images or not self.current_path:
            return
        
        for i, (path, id_, w, h, fs, md) in enumerate(self.images):
            if path == self.current_path and i < len(self.images) - 1:
                self.show_preview(self.images[i+1][0])
                break


def main():
    root = tk.Tk()
    app = MediaViewerV03(root)
    root.mainloop()


if __name__ == "__main__":
    main()
