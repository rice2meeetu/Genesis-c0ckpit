"""Safe side-by-side exact and near-duplicate review UI."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import imagehash
from PIL import Image, ImageOps, ImageTk


SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
BG = "#050505"
PANEL = "#0c0c0d"
PANEL_2 = "#151515"
BORDER = "#4a4028"
GOLD = "#d4af37"
TEXT = "#f4efe6"
MUTED = "#aaa39a"
GREEN = "#4fd18b"
RED = "#d16a6a"
BLUE = "#211b0d"


class DuplicateLab(tk.Frame):
    def __init__(self, parent: tk.Misc, initial_folder: str | Path | None = None):
        super().__init__(parent, bg=BG)
        self.folder = Path(initial_folder) if initial_folder else None
        self.files: list[Path] = []
        self.pairs: list[tuple[Path, Path, int]] = []
        self.index = 0
        self.marked: set[Path] = set()
        self.preview_images: list[ImageTk.PhotoImage] = []
        self.threshold = tk.IntVar(value=6)
        self._build()
        if self.folder and self.folder.is_dir():
            self._set_folder(self.folder)

    def _build(self) -> None:
        header = tk.Frame(self, bg=PANEL, highlightthickness=1,
                          highlightbackground=BORDER)
        header.pack(fill="x", padx=12, pady=(12, 7))
        title = tk.Frame(header, bg=PANEL)
        title.pack(side="left", padx=14, pady=10)
        tk.Label(title, text="DUPLICATE LAB", bg=PANEL, fg=GOLD,
                 font=("Sans", 16, "bold")).pack(anchor="w")
        self.folder_label = tk.Label(title, text="Choose a photo folder", bg=PANEL,
                                     fg=MUTED, font=("Sans", 9))
        self.folder_label.pack(anchor="w", pady=(2, 0))
        self._button(header, "CHOOSE FOLDER", self.choose_folder).pack(
            side="right", padx=12)

        controls = tk.Frame(self, bg=BG)
        controls.pack(fill="x", padx=12, pady=5)
        self._button(controls, "FIND EXACT", self.find_exact).pack(side="left", padx=(0, 5))
        self._button(controls, "FIND NEAR", self.find_near).pack(side="left", padx=(0, 12))
        tk.Label(controls, text="SIMILARITY DISTANCE", bg=BG, fg=MUTED,
                 font=("Sans", 8, "bold")).pack(side="left")
        tk.Scale(controls, from_=1, to=20, orient="horizontal",
                 variable=self.threshold, bg=BG, fg=TEXT, troughcolor=PANEL_2,
                 activebackground=GOLD, highlightthickness=0, length=190).pack(side="left")
        self.status = tk.Label(controls, text="No scan run", bg=BG, fg=MUTED,
                               anchor="e", font=("Sans", 9))
        self.status.pack(side="right")

        comparison = tk.Frame(self, bg=BG)
        comparison.pack(fill="both", expand=True, padx=12, pady=6)
        comparison.grid_columnconfigure(0, weight=1, uniform="compare")
        comparison.grid_columnconfigure(1, weight=1, uniform="compare")
        comparison.grid_rowconfigure(0, weight=1)
        self.left = self._preview_panel(comparison, "LEFT")
        self.left["frame"].grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.right = self._preview_panel(comparison, "RIGHT")
        self.right["frame"].grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        review = tk.Frame(self, bg=PANEL, highlightthickness=1,
                          highlightbackground=BORDER)
        review.pack(fill="x", padx=12, pady=(2, 12))
        self._button(review, "← PREVIOUS", lambda: self.move(-1)).pack(
            side="left", padx=10, pady=8)
        self.pair_label = tk.Label(review, text="0 / 0", bg=PANEL, fg=TEXT,
                                   font=("Sans", 9, "bold"))
        self.pair_label.pack(side="left", padx=8)
        self._button(review, "NEXT →", lambda: self.move(1)).pack(side="left", pady=8)
        tk.Button(review, text="MOVE MARKED TO TRASH", command=self.trash_marked,
                  bg="#2a1518", fg=RED, activebackground=RED,
                  activeforeground="#ffffff", relief="flat", bd=0,
                  padx=12, pady=7, font=("Sans", 8, "bold")).pack(
                      side="right", padx=10, pady=8)
        self.marked_label = tk.Label(review, text="0 marked", bg=PANEL, fg=MUTED)
        self.marked_label.pack(side="right", padx=8)

    @staticmethod
    def _button(parent: tk.Misc, label: str, command) -> tk.Button:
        return tk.Button(parent, text=label, command=command, bg=BLUE, fg=TEXT,
                         activebackground=GOLD, activeforeground="#000000",
                         relief="flat", bd=0, padx=11, pady=7,
                         font=("Sans", 8, "bold"), cursor="hand2")

    def _preview_panel(self, parent: tk.Misc, side: str) -> dict:
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                         highlightbackground=BORDER)
        top = tk.Frame(frame, bg=PANEL)
        top.pack(fill="x", padx=10, pady=8)
        tk.Label(top, text=side, bg=PANEL, fg=GOLD,
                 font=("Sans", 9, "bold")).pack(side="left")
        info = tk.Label(top, text="No result", bg=PANEL, fg=MUTED, anchor="e")
        info.pack(side="right")
        image = tk.Label(frame, text="Run an exact or near scan", bg="#05070b",
                         fg=MUTED, font=("Sans", 11, "bold"))
        image.pack(fill="both", expand=True, padx=10)
        path = tk.Label(frame, text="", bg=PANEL, fg=TEXT, anchor="w",
                        justify="left", wraplength=500, padx=10, pady=7)
        path.pack(fill="x")
        button = tk.Button(frame, text="MARK THIS COPY", bg=PANEL_2, fg=TEXT,
                           activebackground=BLUE, activeforeground="#ffffff",
                           relief="flat", bd=0, padx=10, pady=7,
                           font=("Sans", 8, "bold"))
        button.pack(anchor="w", padx=10, pady=(0, 10))
        return {"frame": frame, "info": info, "image": image,
                "path": path, "button": button}

    def choose_folder(self) -> None:
        selected = filedialog.askdirectory(parent=self, title="Choose photo folder")
        if selected:
            self._set_folder(Path(selected))

    def _set_folder(self, folder: Path) -> None:
        self.folder = folder
        self.files = sorted(path for path in folder.rglob("*")
                            if path.is_file() and path.suffix.lower() in SUPPORTED)
        self.folder_label.configure(text=str(folder))
        self.status.configure(text=f"{len(self.files)} images ready to scan")
        self.pairs.clear()
        self.index = 0
        self._show_pair()

    def find_exact(self) -> None:
        if not self.files:
            messagebox.showinfo("GENESIS", "Choose a folder containing images first.", parent=self)
            return
        self.status.configure(text="Hashing exact duplicates…")

        def work() -> None:
            groups: dict[str, list[Path]] = {}
            for path in self.files:
                try:
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
                except OSError:
                    continue
                groups.setdefault(digest, []).append(path)
            pairs = self._groups_to_pairs(group for group in groups.values() if len(group) > 1)
            self.after(0, lambda: self._set_pairs(pairs, "exact"))

        threading.Thread(target=work, daemon=True).start()

    def find_near(self) -> None:
        if not self.files:
            messagebox.showinfo("GENESIS", "Choose a folder containing images first.", parent=self)
            return
        distance = int(self.threshold.get())
        self.status.configure(text="Calculating perceptual similarity…")

        def work() -> None:
            hashes: list[tuple[Path, imagehash.ImageHash]] = []
            for path in self.files:
                try:
                    with Image.open(path) as source:
                        hashes.append((path, imagehash.phash(source.convert("RGB"))))
                except Exception:
                    continue
            pairs: list[tuple[Path, Path, int]] = []
            for index, (left, left_hash) in enumerate(hashes):
                for right, right_hash in hashes[index + 1:]:
                    score = int(left_hash - right_hash)
                    if score <= distance:
                        pairs.append((left, right, score))
            pairs.sort(key=lambda value: value[2])
            self.after(0, lambda: self._set_pairs(pairs, "near"))

        threading.Thread(target=work, daemon=True).start()

    @staticmethod
    def _groups_to_pairs(groups) -> list[tuple[Path, Path, int]]:
        pairs = []
        for group in groups:
            first = group[0]
            pairs.extend((first, other, 0) for other in group[1:])
        return pairs

    def _set_pairs(self, pairs: list[tuple[Path, Path, int]], kind: str) -> None:
        self.pairs = pairs
        self.index = 0
        self.status.configure(text=f"{len(pairs)} {kind}-duplicate comparisons")
        self._show_pair()

    def move(self, change: int) -> None:
        if not self.pairs:
            return
        self.index = max(0, min(len(self.pairs) - 1, self.index + change))
        self._show_pair()

    def _show_pair(self) -> None:
        self.preview_images.clear()
        if not self.pairs:
            self.pair_label.configure(text="0 / 0")
            for panel in (self.left, self.right):
                panel["image"].configure(image="", text="No duplicate comparison selected")
                panel["path"].configure(text="")
            return
        left_path, right_path, score = self.pairs[self.index]
        self.pair_label.configure(text=f"{self.index + 1} / {len(self.pairs)} · distance {score}")
        self._load_preview(self.left, left_path)
        self._load_preview(self.right, right_path)

    def _load_preview(self, panel: dict, path: Path) -> None:
        try:
            with Image.open(path) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                dimensions = f"{image.width} × {image.height}"
                image.thumbnail((510, 430), Image.Resampling.LANCZOS)
            preview = ImageTk.PhotoImage(image)
            self.preview_images.append(preview)
            panel["image"].configure(image=preview, text="")
            panel["info"].configure(text=dimensions)
        except Exception as exc:
            panel["image"].configure(image="", text=f"Preview unavailable\n{exc}")
        panel["path"].configure(text=str(path))
        panel["button"].configure(
            text="UNMARK" if path in self.marked else "MARK THIS COPY",
            command=lambda value=path: self.toggle_mark(value),
            bg="#2a1518" if path in self.marked else PANEL_2,
            fg=RED if path in self.marked else TEXT,
        )

    def toggle_mark(self, path: Path) -> None:
        if path in self.marked:
            self.marked.remove(path)
        else:
            self.marked.add(path)
        self.marked_label.configure(text=f"{len(self.marked)} marked")
        self._show_pair()

    def trash_marked(self) -> None:
        existing = sorted(path for path in self.marked if path.is_file())
        if not existing:
            messagebox.showinfo("GENESIS", "Mark duplicate copies first.", parent=self)
            return
        if not shutil.which("gio"):
            messagebox.showwarning("GENESIS", "Safe desktop trash is unavailable; nothing was removed.", parent=self)
            return
        if not messagebox.askyesno(
            "GENESIS · Safe duplicate review",
            f"Move {len(existing)} marked files to the desktop Trash?\n\n"
            "They will not be permanently deleted.", parent=self,
        ):
            return
        failed = []
        for path in existing:
            result = subprocess.run(["gio", "trash", str(path)], capture_output=True,
                                    text=True, timeout=15)
            if result.returncode:
                failed.append(path)
            else:
                self.marked.discard(path)
        if self.folder:
            self._set_folder(self.folder)
        if failed:
            messagebox.showwarning("GENESIS", f"Could not trash {len(failed)} files.", parent=self)
        else:
            messagebox.showinfo("GENESIS", "Marked copies moved to Trash.", parent=self)


def build_duplicate_lab(
    parent: tk.Misc,
    folder: str | Path | None = None
) -> DuplicateLab:
    """Create Duplicate Lab inside a GENESIS workspace."""
    panel = DuplicateLab(parent, folder)
    panel.pack(fill="both", expand=True)
    return panel


def open_duplicate_lab(
    parent: tk.Misc,
    folder: str | Path | None = None
) -> tk.Toplevel:
    """Compatibility popup launcher for callers outside the integrated workspace."""
    win = tk.Toplevel(parent)
    win.title("GENESIS · Duplicate Lab")
    win.geometry("1180x760")
    win.minsize(920, 640)
    win.configure(bg=BG)

    panel = DuplicateLab(win, folder)
    panel.pack(fill="both", expand=True)

    win.duplicate_panel = panel
    return win
