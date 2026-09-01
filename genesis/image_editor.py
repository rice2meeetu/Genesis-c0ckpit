"""Lightweight native image viewer and annotation editor for GENESIS."""

from __future__ import annotations

import math
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk


BG = "#050505"
PANEL = "#0c0c0c"
PANEL_2 = "#151515"
BORDER = "#4a4028"
GOLD = "#d4af37"
TEXT = "#f4efe6"
MUTED = "#aaa39a"
BLUE = "#211b0d"


class GenesisImageEditor(tk.Frame):
    """Useful non-destructive viewer/editor built only on Tk and Pillow."""

    def __init__(self, parent: tk.Misc, path: str | Path | None = None):
        super().__init__(parent, bg=BG)

        self.image: Image.Image | None = None
        self.tk_image: ImageTk.PhotoImage | None = None
        self.current_path: Path | None = None
        self.undo_stack: list[Image.Image] = []
        self.redo_stack: list[Image.Image] = []
        self.zoom = 1.0
        self.pan = [0.0, 0.0]
        self.display = (0.0, 0.0, 1.0, 0, 0)
        self.tool = tk.StringVar(value="pan")
        self.drag_start: tuple[float, float] | None = None
        self.pan_start: tuple[float, float] | None = None
        self.dirty = False

        self._build()
        if path:
            self.after(50, lambda: self.load_image(path))

    def _build(self) -> None:
        header = tk.Frame(self, bg=PANEL, highlightthickness=1,
                          highlightbackground=BORDER)
        header.pack(fill="x", padx=10, pady=(10, 6))
        tk.Label(header, text="PHOTO VIEWER / EDITOR", bg=PANEL, fg=GOLD,
                 font=("Sans", 15, "bold")).pack(side="left", padx=12, pady=9)
        self.file_label = tk.Label(header, text="No image loaded", bg=PANEL,
                                   fg=MUTED, font=("Sans", 9))
        self.file_label.pack(side="left", padx=12)

        actions = tk.Frame(self, bg=BG)
        actions.pack(fill="x", padx=10, pady=4)
        for label, command in (
            ("OPEN", self.open_image), ("SAVE AS", self.save_as),
            ("UNDO", self.undo), ("REDO", self.redo),
            ("ROTATE LEFT", lambda: self.rotate(90)),
            ("ROTATE RIGHT", lambda: self.rotate(-90)),
            ("SET WALLPAPER", self.set_wallpaper),
        ):
            self._button(actions, label, command).pack(side="left", padx=(0, 5))

        tools = tk.Frame(self, bg=BG)
        tools.pack(fill="x", padx=10, pady=(2, 6))
        tk.Label(tools, text="TOOLS", bg=BG, fg=MUTED,
                 font=("Sans", 8, "bold")).pack(side="left", padx=(0, 8))
        for value, label in (
            ("pan", "PAN"), ("crop", "CROP"), ("arrow", "ARROW"),
            ("ellipse", "CIRCLE"), ("rectangle", "RECTANGLE"),
            ("text", "TEXT"),
        ):
            self._button(tools, label, lambda v=value: self._set_tool(v)).pack(
                side="left", padx=(0, 4)
            )
        tk.Label(tools, text="ZOOM", bg=BG, fg=MUTED,
                 font=("Sans", 8, "bold")).pack(side="left", padx=(16, 6))
        self._button(tools, "−", lambda: self.change_zoom(0.8)).pack(side="left")
        self.zoom_label = tk.Label(tools, text="100%", width=7, bg=BG, fg=TEXT)
        self.zoom_label.pack(side="left")
        self._button(tools, "+", lambda: self.change_zoom(1.25)).pack(side="left")
        self._button(tools, "FIT", self.fit_image).pack(side="left", padx=(5, 0))

        self.canvas = tk.Canvas(self, bg="#181818", highlightthickness=1,
                                highlightbackground=BORDER, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self.canvas.bind("<Configure>", lambda _event: self.render())
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._motion)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<MouseWheel>", self._wheel)
        self.canvas.bind("<Button-4>", lambda _event: self.change_zoom(1.1))
        self.canvas.bind("<Button-5>", lambda _event: self.change_zoom(0.9))

        self.status = tk.Label(self, text="Open an image to begin", bg=PANEL,
                               fg=MUTED, anchor="w", padx=10, pady=5)
        self.status.pack(fill="x", padx=10, pady=(0, 10))

    @staticmethod
    def _button(parent: tk.Misc, label: str, command) -> tk.Button:
        return tk.Button(parent, text=label, command=command, bg=PANEL_2,
                         fg=TEXT, activebackground=BLUE,
                         activeforeground="#ffffff", relief="flat", bd=0,
                         padx=10, pady=6, font=("Sans", 8, "bold"),
                         cursor="hand2")

    def _set_tool(self, value: str) -> None:
        self.tool.set(value)
        self.canvas.configure(cursor="fleur" if value == "pan" else "crosshair")
        self.status.configure(text=f"{value.replace('_', ' ').title()} tool selected")

    def open_image(self) -> None:
        from genesis.visual_browser import pick_images
        selected = pick_images(
            self, initial_folder=self.current_path.parent if self.current_path else None,
            multiple=False,
        )
        if selected:
            self.load_image(selected[0])

    def load_image(self, path: str | Path) -> None:
        if self.dirty and not messagebox.askyesno(
            "GENESIS", "Discard unsaved edits and open another image?",
            parent=self,
        ):
            return
        try:
            with Image.open(path) as source:
                image = ImageOps.exif_transpose(source).convert("RGBA")
        except Exception as exc:
            messagebox.showerror("GENESIS", f"Could not open image:\n{exc}", parent=self)
            return
        self.image = image
        self.current_path = Path(path)
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.dirty = False
        self.file_label.configure(text=self.current_path.name)
        self.fit_image()
        self.status.configure(text=f"Loaded {self.image.width} × {self.image.height}")

    def fit_image(self) -> None:
        self.zoom = 1.0
        self.pan = [0.0, 0.0]
        self.render()

    def change_zoom(self, multiplier: float) -> None:
        if self.image is None:
            return
        self.zoom = max(0.1, min(8.0, self.zoom * multiplier))
        self.render()

    def render(self) -> None:
        self.canvas.delete("all")
        if self.image is None:
            self.canvas.create_text(
                max(1, self.canvas.winfo_width()) / 2,
                max(1, self.canvas.winfo_height()) / 2,
                text="DROP INTO YOUR WORKFLOW\nOPEN AN IMAGE TO VIEW OR EDIT",
                fill="#999999", justify="center", font=("Sans", 14, "bold")
            )
            return
        cw = max(40, self.canvas.winfo_width())
        ch = max(40, self.canvas.winfo_height())
        fit = min((cw - 30) / self.image.width, (ch - 30) / self.image.height)
        scale = max(0.01, fit * self.zoom)
        width = max(1, int(self.image.width * scale))
        height = max(1, int(self.image.height * scale))
        preview = self.image.resize((width, height), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(preview)
        x = (cw - width) / 2 + self.pan[0]
        y = (ch - height) / 2 + self.pan[1]
        self.canvas.create_image(x, y, image=self.tk_image, anchor="nw")
        self.canvas.create_rectangle(x, y, x + width, y + height,
                                     outline=BORDER, width=1)
        self.display = (x, y, scale, width, height)
        self.zoom_label.configure(text=f"{self.zoom * 100:.0f}%")

    def _canvas_to_image(self, x: float, y: float) -> tuple[int, int]:
        if self.image is None:
            return 0, 0
        dx, dy, scale, _width, _height = self.display
        ix = int((x - dx) / scale)
        iy = int((y - dy) / scale)
        return (max(0, min(self.image.width, ix)),
                max(0, min(self.image.height, iy)))

    def _press(self, event) -> None:
        if self.image is None:
            return
        self.drag_start = (event.x, event.y)
        if self.tool.get() == "pan":
            self.pan_start = (event.x - self.pan[0], event.y - self.pan[1])

    def _motion(self, event) -> None:
        if self.image is None or self.drag_start is None:
            return
        if self.tool.get() == "pan" and self.pan_start:
            self.pan = [event.x - self.pan_start[0], event.y - self.pan_start[1]]
            self.render()
            return
        self.canvas.delete("tool-preview")
        x0, y0 = self.drag_start
        tool = self.tool.get()
        if tool in {"crop", "rectangle"}:
            self.canvas.create_rectangle(x0, y0, event.x, event.y, outline=GOLD,
                                         width=2, dash=(5, 3), tags="tool-preview")
        elif tool == "ellipse":
            self.canvas.create_oval(x0, y0, event.x, event.y, outline=GOLD,
                                    width=2, dash=(5, 3), tags="tool-preview")
        elif tool == "arrow":
            self.canvas.create_line(x0, y0, event.x, event.y, fill=GOLD,
                                    width=3, arrow="last", tags="tool-preview")

    def _release(self, event) -> None:
        if self.image is None or self.drag_start is None:
            return
        start = self._canvas_to_image(*self.drag_start)
        end = self._canvas_to_image(event.x, event.y)
        tool = self.tool.get()
        self.canvas.delete("tool-preview")
        self.drag_start = None
        self.pan_start = None
        if tool == "pan" or start == end:
            return
        if tool == "crop":
            left, right = sorted((start[0], end[0]))
            top, bottom = sorted((start[1], end[1]))
            if right - left < 2 or bottom - top < 2:
                return
            self._remember()
            self.image = self.image.crop((left, top, right, bottom))
            self.fit_image()
            self._changed("Image cropped")
            return
        self._remember()
        draw = ImageDraw.Draw(self.image)
        width = max(3, round(min(self.image.size) / 260))
        color = (214, 168, 75, 255)
        box = (*start, *end)
        if tool == "rectangle":
            draw.rectangle(box, outline=color, width=width)
        elif tool == "ellipse":
            draw.ellipse(box, outline=color, width=width)
        elif tool == "arrow":
            self._draw_arrow(draw, start, end, color, width)
        elif tool == "text":
            value = simpledialog.askstring("GENESIS", "Annotation text:", parent=self)
            if not value:
                self.image = self.undo_stack.pop()
                return
            font = ImageFont.load_default(size=max(14, round(min(self.image.size) / 35)))
            draw.text(start, value, fill=color, font=font, stroke_width=1,
                      stroke_fill=(0, 0, 0, 255))
        else:
            self.image = self.undo_stack.pop()
            return
        self._changed(f"{tool.title()} annotation added")

    @staticmethod
    def _draw_arrow(draw: ImageDraw.ImageDraw, start, end, color, width) -> None:
        draw.line((start, end), fill=color, width=width)
        angle = math.atan2(end[1] - start[1], end[0] - start[0])
        size = max(12, width * 5)
        left = (end[0] - size * math.cos(angle - math.pi / 6),
                end[1] - size * math.sin(angle - math.pi / 6))
        right = (end[0] - size * math.cos(angle + math.pi / 6),
                 end[1] - size * math.sin(angle + math.pi / 6))
        draw.polygon((end, left, right), fill=color)

    def _remember(self) -> None:
        if self.image is None:
            return
        self.undo_stack.append(self.image.copy())
        if len(self.undo_stack) > 30:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def _changed(self, message: str) -> None:
        self.dirty = True
        self.render()
        self.status.configure(text=message)

    def rotate(self, degrees: int) -> None:
        if self.image is None:
            return
        self._remember()
        self.image = self.image.rotate(degrees, expand=True)
        self.fit_image()
        self._changed("Image rotated")

    def undo(self) -> None:
        if self.image is None or not self.undo_stack:
            return
        self.redo_stack.append(self.image.copy())
        self.image = self.undo_stack.pop()
        self.dirty = True
        self.render()
        self.status.configure(text="Undo")

    def redo(self) -> None:
        if self.image is None or not self.redo_stack:
            return
        self.undo_stack.append(self.image.copy())
        self.image = self.redo_stack.pop()
        self.dirty = True
        self.render()
        self.status.configure(text="Redo")

    def save_as(self) -> Path | None:
        if self.image is None:
            messagebox.showinfo("GENESIS", "Open an image first.", parent=self)
            return None
        initial = self.current_path.name if self.current_path else "genesis-edit.png"
        selected = filedialog.asksaveasfilename(
            parent=self, title="Save edited image", initialfile=initial,
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg"),
                       ("WebP", "*.webp")],
        )
        if not selected:
            return None
        target = Path(selected)
        try:
            output = self.image
            if target.suffix.lower() in {".jpg", ".jpeg"}:
                output = output.convert("RGB")
            output.save(target)
        except Exception as exc:
            messagebox.showerror("GENESIS", f"Could not save image:\n{exc}", parent=self)
            return None
        self.current_path = target
        self.dirty = False
        self.file_label.configure(text=target.name)
        self.status.configure(text=f"Saved {target}")
        return target

    def set_wallpaper(self) -> None:
        if self.image is None:
            messagebox.showinfo("GENESIS", "Open an image first.", parent=self)
            return
        target = self.current_path
        if target is None or self.dirty:
            target = self.save_as()
        if target is None:
            return
        uri = target.resolve().as_uri()
        try:
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri],
                check=True, capture_output=True, text=True, timeout=8,
            )
            subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri],
                check=False, capture_output=True, text=True, timeout=8,
            )
        except Exception as exc:
            messagebox.showerror("GENESIS", f"Could not set wallpaper:\n{exc}", parent=self)
            return
        self.status.configure(text="Desktop wallpaper updated")
        messagebox.showinfo("GENESIS", "Desktop wallpaper updated.", parent=self)

    def _wheel(self, event) -> None:
        self.change_zoom(1.1 if event.delta > 0 else 0.9)


def build_editor_panel(
    parent: tk.Misc,
    path: str | Path | None = None
) -> GenesisImageEditor:
    """Create the editor as an embedded GENESIS workspace panel."""
    panel = GenesisImageEditor(parent, path)
    panel.pack(fill="both", expand=True)
    return panel


def open_editor(parent: tk.Misc, path: str | Path | None = None) -> tk.Toplevel:
    """Compatibility popup launcher for callers outside the integrated workspace."""
    win = tk.Toplevel(parent)
    win.title("GENESIS · Photo Viewer / Editor")
    win.geometry("1280x820")
    win.minsize(900, 620)
    win.configure(bg=BG)

    panel = GenesisImageEditor(win, path)
    panel.pack(fill="both", expand=True)

    win.editor_panel = panel
    return win
