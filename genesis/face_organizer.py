"""Native GENESIS face organiser backed by the existing face database modules."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import face_recognition
from PIL import Image, ImageTk

from genesis.face_detection.detector import FaceDetector
from genesis.face_groups import FaceGroups
from genesis.face_search import FaceSearch


SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
BG = "#07090c"
PANEL = "#10141b"
PANEL_2 = "#171d26"
GOLD = "#d4af37"
TEXT = "#f3efe6"
MUTED = "#9da7b3"
BORDER = "#3d3520"


def default_face_db() -> Path:
    override = os.environ.get("GENESIS_FACE_DB", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / "GENESIS-Photo-Studio" / "database" / "genesis.db"


def ensure_face_schema(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS face_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                encoding BLOB NOT NULL,
                image_path TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """
        )


def index_folder(db_path: Path, folder: Path) -> int:
    files = [
        path for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGES
    ]
    ensure_face_schema(db_path)
    with sqlite3.connect(db_path) as conn:
        before = conn.total_changes
        conn.executemany(
            "INSERT OR IGNORE INTO photos(path) VALUES (?)",
            ((str(path.resolve()),) for path in files),
        )
        return conn.total_changes - before


def list_people(db_path: Path) -> list[str]:
    ensure_face_schema(db_path)
    with sqlite3.connect(db_path) as conn:
        return [
            row[0] for row in conn.execute(
                "SELECT DISTINCT name FROM face_data WHERE name <> '' ORDER BY name COLLATE NOCASE"
            ).fetchall()
        ]


def rename_person(db_path: Path, old_name: str, new_name: str) -> int:
    ensure_face_schema(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "UPDATE face_data SET name = ? WHERE name = ?",
            (new_name.strip(), old_name),
        )
        return cursor.rowcount


def delete_person(db_path: Path, name: str) -> int:
    ensure_face_schema(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("DELETE FROM face_data WHERE name = ?", (name,))
        return cursor.rowcount


def register_face_reference(db_path: Path, image_path: Path, name: str) -> bool:
    ensure_face_schema(db_path)
    image = face_recognition.load_image_file(str(image_path))
    locations = face_recognition.face_locations(image)
    if not locations:
        raise ValueError("No face was detected in that image.")
    encodings = face_recognition.face_encodings(image, locations)
    if not encodings:
        raise ValueError("The detected face could not be encoded.")

    # Prefer the largest detected face when a reference photo contains several.
    areas = [max(0, bottom - top) * max(0, right - left) for top, right, bottom, left in locations]
    index = max(range(len(areas)), key=areas.__getitem__)
    detector = FaceDetector(str(db_path))
    return bool(detector.save_face(name.strip(), encodings[index], str(image_path.resolve())))


class FaceOrganizerApp(tk.Tk):
    """ACDSee-style lightweight people browser over GENESIS face backends."""

    def __init__(self, db_path: Path | None = None) -> None:
        super().__init__()
        self.db_path = Path(db_path or default_face_db())
        ensure_face_schema(self.db_path)
        self.title("GENESIS · Face Organiser")
        self.geometry("1420x860")
        self.minsize(1050, 650)
        self.configure(bg=BG)
        self._preview_image: ImageTk.PhotoImage | None = None
        self._selected_person = ""
        self._result_paths: list[str] = []
        self._busy = False
        self._build_style()
        self._build_ui()
        self.refresh_people()

    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=BG, foreground=TEXT, fieldbackground=PANEL)
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED)
        style.configure("Gold.TLabel", background=BG, foreground=GOLD, font=("Segoe UI", 14, "bold"))
        style.configure("TButton", background=PANEL_2, foreground=TEXT, bordercolor=BORDER, padding=8)
        style.map("TButton", background=[("active", "#252c36")])
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT, rowheight=30)
        style.configure("Treeview.Heading", background=PANEL_2, foreground=GOLD)

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x", padx=14, pady=(14, 8))
        ttk.Label(header, text="FACE ORGANISER", style="Gold.TLabel").pack(side="left")
        ttk.Label(
            header,
            text="Named face references · person groups · photo search · albums",
            style="Muted.TLabel",
        ).pack(side="left", padx=18)
        ttk.Button(header, text="Add photo folder", command=self.add_folder).pack(side="right", padx=4)
        ttk.Button(header, text="Add face reference", command=self.add_face_reference).pack(side="right", padx=4)
        ttk.Button(header, text="Refresh", command=self.refresh_people).pack(side="right", padx=4)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        left = ttk.Frame(body, style="Panel.TFrame")
        left.pack(side="left", fill="y", padx=(0, 8))
        ttk.Label(left, text="PEOPLE", style="Gold.TLabel").pack(anchor="w", padx=10, pady=(10, 6))
        self.people = ttk.Treeview(left, columns=("count",), show="tree headings", height=24)
        self.people.heading("#0", text="Name")
        self.people.heading("count", text="Photos")
        self.people.column("#0", width=190, stretch=True)
        self.people.column("count", width=70, anchor="center", stretch=False)
        self.people.pack(fill="y", expand=True, padx=8, pady=(0, 8))
        self.people.bind("<<TreeviewSelect>>", self._person_selected)
        actions = ttk.Frame(left, style="Panel.TFrame")
        actions.pack(fill="x", padx=8, pady=(0, 10))
        ttk.Button(actions, text="Rename", command=self.rename_selected).pack(side="left", padx=2)
        ttk.Button(actions, text="Remove", command=self.delete_selected).pack(side="left", padx=2)
        ttk.Button(actions, text="Album", command=self.export_album).pack(side="left", padx=2)

        center = ttk.Frame(body, style="Panel.TFrame")
        center.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.group_title = ttk.Label(center, text="Select a person", style="Gold.TLabel")
        self.group_title.pack(anchor="w", padx=10, pady=(10, 6))
        self.results = tk.Listbox(
            center,
            bg="#0b0f14",
            fg=TEXT,
            selectbackground="#5b4919",
            selectforeground="white",
            highlightthickness=1,
            highlightbackground=BORDER,
            activestyle="none",
        )
        self.results.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.results.bind("<<ListboxSelect>>", self._photo_selected)
        self.results.bind("<Double-Button-1>", lambda _event: self.open_selected_photo())
        row = ttk.Frame(center, style="Panel.TFrame")
        row.pack(fill="x", padx=8, pady=(0, 10))
        ttk.Button(row, text="Open photo", command=self.open_selected_photo).pack(side="left", padx=2)
        ttk.Button(row, text="Open folder", command=self.open_selected_folder).pack(side="left", padx=2)

        right = ttk.Frame(body, style="Panel.TFrame")
        right.pack(side="left", fill="both", ipadx=4)
        ttk.Label(right, text="PREVIEW", style="Gold.TLabel").pack(anchor="w", padx=10, pady=(10, 6))
        self.preview = tk.Label(right, bg="#05080b", fg=MUTED, text="Select a photo", width=46, height=28)
        self.preview.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.preview_path = ttk.Label(right, text="", style="Muted.TLabel", wraplength=380)
        self.preview_path.pack(fill="x", padx=10, pady=(0, 10))

        self.status = ttk.Label(self, text=f"Database: {self.db_path}", style="Muted.TLabel")
        self.status.pack(fill="x", padx=16, pady=(0, 12))

    def _set_status(self, text: str) -> None:
        self.status.configure(text=text)

    def refresh_people(self) -> None:
        for item in self.people.get_children():
            self.people.delete(item)
        try:
            names = list_people(self.db_path)
        except Exception as exc:
            messagebox.showerror("GENESIS Face Organiser", str(exc), parent=self)
            return
        for name in names:
            self.people.insert("", "end", iid=name, text=name, values=("—",))
        self._set_status(f"{len(names)} named people · Database: {self.db_path}")

    def add_folder(self) -> None:
        folder = filedialog.askdirectory(title="Add photo folder", parent=self)
        if not folder:
            return
        self._set_status("Indexing image paths…")

        def worker() -> None:
            try:
                count = index_folder(self.db_path, Path(folder))
                self.after(0, lambda: self._set_status(f"Indexed {count} new photos from {folder}"))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("GENESIS Face Organiser", str(exc), parent=self))

        threading.Thread(target=worker, daemon=True).start()

    def add_face_reference(self) -> None:
        filename = filedialog.askopenfilename(
            title="Choose a clear face reference",
            parent=self,
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff"), ("All files", "*.*")],
        )
        if not filename:
            return
        name = simpledialog.askstring("Name this person", "Person name:", parent=self)
        if not name or not name.strip():
            return
        self._set_status(f"Encoding reference for {name.strip()}…")

        def worker() -> None:
            try:
                ok = register_face_reference(self.db_path, Path(filename), name)
                if not ok:
                    raise RuntimeError("Face reference could not be saved.")
                self.after(0, self.refresh_people)
                self.after(0, lambda: self._set_status(f"Saved face reference: {name.strip()}"))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("GENESIS Face Organiser", str(exc), parent=self))

        threading.Thread(target=worker, daemon=True).start()

    def _person_selected(self, _event=None) -> None:
        selected = self.people.selection()
        if not selected or self._busy:
            return
        self._selected_person = selected[0]
        self.group_title.configure(text=self._selected_person)
        self.results.delete(0, "end")
        self.results.insert("end", "Searching indexed photos…")
        self._busy = True

        def worker() -> None:
            try:
                paths = FaceSearch(str(self.db_path)).search_person(self._selected_person, limit=2000)
                self.after(0, lambda: self._show_results(self._selected_person, paths))
            except Exception as exc:
                self.after(0, lambda: self._search_failed(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _show_results(self, name: str, paths: list[str]) -> None:
        self._busy = False
        self._result_paths = list(paths)
        self.results.delete(0, "end")
        for path in paths:
            self.results.insert("end", path)
        if not paths:
            self.results.insert("end", "No indexed matches yet. Add a photo folder, then select this person again.")
        if self.people.exists(name):
            self.people.set(name, "count", str(len(paths)))
        self._set_status(f"{name}: {len(paths)} matching photos")

    def _search_failed(self, exc: Exception) -> None:
        self._busy = False
        self.results.delete(0, "end")
        self._set_status(f"Face search failed: {exc}")
        messagebox.showerror("GENESIS Face Organiser", str(exc), parent=self)

    def _selected_result_path(self) -> Path | None:
        selected = self.results.curselection()
        if not selected:
            return None
        index = selected[0]
        if index >= len(self._result_paths):
            return None
        path = Path(self._result_paths[index])
        return path if path.is_file() else None

    def _photo_selected(self, _event=None) -> None:
        path = self._selected_result_path()
        if path is None:
            return
        try:
            image = Image.open(path).convert("RGB")
            image.thumbnail((430, 560), Image.Resampling.LANCZOS)
            self._preview_image = ImageTk.PhotoImage(image)
            self.preview.configure(image=self._preview_image, text="")
            self.preview_path.configure(text=str(path))
        except Exception as exc:
            self.preview.configure(image="", text=f"Preview failed\n{exc}")

    def open_selected_photo(self) -> None:
        path = self._selected_result_path()
        if path is not None:
            self._open_path(path)

    def open_selected_folder(self) -> None:
        path = self._selected_result_path()
        if path is not None:
            self._open_path(path.parent)

    @staticmethod
    def _open_path(path: Path) -> None:
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def rename_selected(self) -> None:
        if not self._selected_person:
            return
        new_name = simpledialog.askstring(
            "Rename person",
            f"Rename {self._selected_person} to:",
            initialvalue=self._selected_person,
            parent=self,
        )
        if not new_name or not new_name.strip() or new_name.strip() == self._selected_person:
            return
        count = rename_person(self.db_path, self._selected_person, new_name.strip())
        self._selected_person = ""
        self.refresh_people()
        self._set_status(f"Renamed {count} face reference(s) to {new_name.strip()}")

    def delete_selected(self) -> None:
        if not self._selected_person:
            return
        if not messagebox.askyesno(
            "Remove named face",
            f"Remove face references for {self._selected_person}?\n\nPhotos will not be deleted.",
            parent=self,
        ):
            return
        count = delete_person(self.db_path, self._selected_person)
        self._selected_person = ""
        self._result_paths = []
        self.results.delete(0, "end")
        self.refresh_people()
        self._set_status(f"Removed {count} face reference(s); original photos were untouched")

    def export_album(self) -> None:
        if not self._selected_person:
            return
        destination = filedialog.askdirectory(title="Choose album destination", parent=self)
        if not destination:
            return
        target = Path(destination) / self._selected_person
        self._set_status(f"Creating album for {self._selected_person}…")

        def worker() -> None:
            try:
                result = FaceGroups(str(self.db_path)).create_person_album(self._selected_person, str(target))
                if not result:
                    raise RuntimeError("No matching photos were found for this person.")
                self.after(0, lambda: self._set_status(f"Album created: {result}"))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("GENESIS Face Organiser", str(exc), parent=self))

        threading.Thread(target=worker, daemon=True).start()


def smoke() -> bool:
    """Import/runtime check used by Windows packaging CI without creating a GUI."""
    ensure_face_schema(default_face_db())
    return callable(face_recognition.face_locations) and FaceDetector is not None and FaceSearch is not None


def main() -> int:
    app = FaceOrganizerApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
