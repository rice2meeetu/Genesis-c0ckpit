"""Native, read-only pose-library browser for the GENESIS cockpit."""

from __future__ import annotations

import json
import math
import tkinter as tk
from pathlib import Path
from tkinter import ttk, font as tkfont

from PIL import Image, ImageOps, ImageTk

from genesis.send_to import SendDestination, build_send_to_menu

BG, PANEL, GOLD, TEXT, MUTED = "#080808", "#181818", "#d4af37", "#f4efe6", "#a0a0a0"

POSE_SEND_DESTINATIONS = (
    SendDestination("pose_reference", "Send as Pose Reference"),
    SendDestination("source_image", "Send as Source Image"),
    SendDestination("viewer_editor", "Open in Viewer / Editor"),
)


def read_library(root: Path) -> list[dict]:
    root = root.resolve()
    data = json.loads((root / "index.json").read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("The pose index must contain a list.")
    result, seen = [], set()
    for item in data:
        if not isinstance(item, dict) or not item.get("path"):
            continue
        relative = Path(str(item["path"]))
        full = (root / relative).resolve()
        if relative.is_absolute() or not full.is_relative_to(root) or full in seen:
            continue
        seen.add(full)
        result.append({**item, "file": full, "name": str(item.get("name", full.stem)),
                       "category": str(item.get("category", "Uncategorised"))})
    return result


class NativePoseLibrary(tk.Frame):
    PAGE_SIZE = 24

    def __init__(self, parent, library_root: Path, on_select=None, on_open=None,
                 on_workbench=None, on_send=None):
        super().__init__(parent, bg=BG)
        # Match physical text height even when desktop font configuration scales fonts.
        probe = tkfont.Font(self, family="Sans", size=-14)
        ratio = 20 / max(1, probe.metrics("linespace"))
        def pose_font(size=14, bold=False):
            return ("Sans", -max(7, round(size * ratio)), "bold" if bold else "normal")
        self._font = pose_font
        style = ttk.Style(self)
        style.configure("Pose.TButton", font=self._font(), padding=(12, 9))
        style.configure("Pose.TCombobox", font=self._font())
        style.configure("Pose.TEntry", font=self._font())
        self.library_root = Path(library_root)
        self.on_select, self.on_open, self.on_send = on_select, on_open, on_send
        self.items, self.filtered = [], []
        self.page, self.columns = 0, 4
        self.selected = None
        self._photos, self._tiles = [], []
        self._render_job = self._search_job = self._preview_job = None
        self._preview_photo = None
        self._generation = 0
        self.category = tk.StringVar(value="All categories")
        self.search = tk.StringVar()
        self.message = tk.StringVar(value="Choose a pose to inspect its reference image.")

        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=24, pady=(22, 14))
        tk.Label(header, text="POSE LIBRARY", bg=BG, fg=GOLD,
                 font=self._font(28, True)).pack(anchor="w")
        tk.Label(header, text="Local references · built into GENESIS · no browser required",
                 bg=BG, fg=MUTED, font=self._font()).pack(anchor="w", pady=(6, 0))
        if on_workbench:
            ttk.Button(style="Pose.TButton", master=header, text="Open existing stage workbench",
                       command=on_workbench).pack(anchor="w", pady=(12, 0))

        filters = tk.Frame(self, bg=BG)
        filters.pack(fill="x", padx=24, pady=(0, 16))
        filters.columnconfigure(1, weight=1)
        self.category_menu = ttk.Combobox(filters, textvariable=self.category,
                                         state="readonly", width=24, font=self._font(), style="Pose.TCombobox")
        self.category_menu.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        search_box = ttk.Entry(filters, textvariable=self.search, font=self._font(), style="Pose.TEntry")
        search_box.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        ttk.Button(style="Pose.TButton", master=filters, text="Clear search", command=lambda: self.search.set("")).grid(row=0, column=2)
        ttk.Button(style="Pose.TButton", master=filters, text="Reload library", command=self.reload).grid(row=0, column=3, padx=(12, 0))
        tk.Label(filters, text="Search name, category or resolution", bg=BG, fg=MUTED, font=self._font()).grid(
            row=1, column=1, sticky="w", pady=(5, 0))

        body = tk.PanedWindow(self, orient="horizontal", bg=BG, sashwidth=10,
                              borderwidth=0, showhandle=False)

        gallery = tk.Frame(body, bg=BG)
        detail = tk.Frame(body, bg=PANEL, width=340)
        body.add(gallery, minsize=280, stretch="always")
        body.add(detail, minsize=240, stretch="never")
        self.gallery_canvas = tk.Canvas(gallery, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(gallery, orient="vertical", command=self.gallery_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.gallery_canvas.pack(side="left", fill="both", expand=True)
        self.gallery_canvas.configure(yscrollcommand=scrollbar.set)
        self.grid_frame = tk.Frame(self.gallery_canvas, bg=BG)
        self._window = self.gallery_canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.grid_frame.bind("<Configure>", lambda _: self.gallery_canvas.configure(
            scrollregion=self.gallery_canvas.bbox("all")))
        self.gallery_canvas.bind("<Configure>", self._resize_gallery)
        self._bind_scroll(self.gallery_canvas)

        self.selection_label = tk.Label(detail, text="No pose selected", bg=PANEL, fg=GOLD,
                                        font=self._font(18, True), wraplength=300, justify="left")
        self.selection_label.pack(fill="x", padx=16, pady=16)
        self.preview = tk.Canvas(detail, bg="#101010", height=320, width=320, highlightthickness=0)

        self.preview.bind("<Configure>", self._queue_preview)
        self.metadata = tk.Label(detail, text="", bg=PANEL, fg=MUTED, font=self._font(13), wraplength=300, justify="left")
        self.metadata.pack(fill="x", padx=16, pady=12)
        self.select_button = ttk.Button(style="Pose.TButton", master=detail, text="Select reference", command=self.use_selection, state="disabled")
        self.select_button.pack(fill="x", padx=16, pady=4)
        self.send_button = ttk.Button(style="Pose.TButton", master=detail, text="Send To…", command=self.show_send_menu, state="disabled")
        self.send_button.pack(fill="x", padx=16, pady=4)
        self.send_menu = build_send_to_menu(
            self,
            POSE_SEND_DESTINATIONS,
            self.send_selection,
        )
        self.open_button = ttk.Button(style="Pose.TButton", master=detail, text="Open in Viewer / Editor", command=self.open_selection, state="disabled")
        self.open_button.pack(fill="x", padx=16, pady=4)
        self.copy_button = ttk.Button(style="Pose.TButton", master=detail, text="Copy reference path", command=self.copy_path, state="disabled")
        self.copy_button.pack(fill="x", padx=16, pady=(4, 16))

        footer = tk.Frame(self, bg=BG)
        footer.pack(side="bottom", fill="x", padx=24, pady=(10, 18))
        self.previous_button = ttk.Button(style="Pose.TButton", master=footer, text="Previous", command=lambda: self.change_page(-1))
        self.previous_button.pack(side="left")
        self.page_label = tk.Label(footer, bg=BG, fg=TEXT, font=self._font())
        self.page_label.pack(side="left", padx=16)
        self.next_button = ttk.Button(style="Pose.TButton", master=footer, text="Next", command=lambda: self.change_page(1))
        self.next_button.pack(side="left")
        tk.Label(self, textvariable=self.message, bg=BG, fg=MUTED, anchor="w",
                 wraplength=900, font=self._font()).pack(side="bottom", fill="x", padx=24, pady=(0, 18))
        self.preview.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        body.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        self.category_menu.bind("<<ComboboxSelected>>", lambda _: self.filter_items())
        self.search.trace_add("write", self._queue_search)
        self.reload()

    def _bind_scroll(self, widget):
        def scroll(event):
            step = -1 if event.num == 4 or getattr(event, "delta", 0) > 0 else 1
            self.gallery_canvas.yview_scroll(step, "units")
            return "break"
        for sequence in ("<Button-4>", "<Button-5>", "<MouseWheel>"):
            widget.bind(sequence, scroll)

    def reload(self):
        try:
            self.items = read_library(self.library_root)
            self.message.set(f"{len(self.items)} local pose references. Original files and workflows remain unchanged.")
        except (OSError, ValueError) as exc:
            self.items = []
            self.message.set(f"Could not load the pose library: {exc}")
        categories = ["All categories"] + sorted({item["category"] for item in self.items})
        self.category_menu.configure(values=categories)
        if self.category.get() not in categories:
            self.category.set(categories[0])
        self.filter_items()

    def _queue_search(self, *_):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(180, self.filter_items)

    def filter_items(self):
        if self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = None
        query, category = self.search.get().strip().casefold(), self.category.get()
        self.filtered = [item for item in self.items
                         if (category == "All categories" or item["category"] == category)
                         and (not query or query in " ".join(str(item.get(k, ""))
                              for k in ("name", "category", "resolution", "path")).casefold())]
        self.page = 0
        self.render_page()

    def _resize_gallery(self, event):
        self.gallery_canvas.itemconfigure(self._window, width=event.width)
        columns = max(1, min(6, event.width // 190))
        if columns != self.columns:
            self.columns = columns
            self._layout_tiles()

    def _layout_tiles(self):
        for column in range(6):
            self.grid_frame.columnconfigure(column, weight=1 if column < self.columns else 0,
                                             uniform="poses" if column < self.columns else "")
        for i, tile in enumerate(self._tiles):
            tile.grid(row=i // self.columns, column=i % self.columns, sticky="nsew", padx=6, pady=6)

    def change_page(self, delta):
        pages = max(1, math.ceil(len(self.filtered) / self.PAGE_SIZE))
        self.page = min(pages - 1, max(0, self.page + delta))
        self.render_page()

    def render_page(self):
        self._generation += 1
        generation = self._generation
        if self._render_job:
            self.after_cancel(self._render_job)
            self._render_job = None
        for child in self.grid_frame.winfo_children():
            child.destroy()
        self._tiles, self._photos = [], []
        start = self.page * self.PAGE_SIZE
        current = self.filtered[start:start + self.PAGE_SIZE]
        pages = max(1, math.ceil(len(self.filtered) / self.PAGE_SIZE))
        self.page_label.configure(text=f"{len(self.filtered)} poses · Page {self.page + 1} of {pages}")
        self.previous_button.configure(state="normal" if self.page else "disabled")
        self.next_button.configure(state="normal" if self.page + 1 < pages else "disabled")
        self.gallery_canvas.yview_moveto(0)
        if not current:
            tk.Label(self.grid_frame, text="No poses match this search.", bg=BG, fg=MUTED,
                     padx=20, pady=36, font=self._font()).grid(row=0, column=0, sticky="w")
            return
        for item in current:
            tile = tk.Frame(self.grid_frame, bg=PANEL, highlightthickness=1, highlightbackground="#3a3a3a")
            thumb = tk.Canvas(tile, width=170, height=160, bg="#101010", highlightthickness=0, cursor="hand2")
            thumb.pack(fill="x", padx=8, pady=8)
            label = tk.Label(tile, text=item["name"], bg=PANEL, fg=TEXT, wraplength=170,
                             pady=6, cursor="hand2", font=self._font())
            label.pack(fill="x", padx=8)
            for widget in (tile, thumb, label):
                widget.bind("<Button-1>", lambda _, value=item: self.select(value))
                self._bind_scroll(widget)
            tile._thumbnail = thumb
            self._tiles.append(tile)
        self._layout_tiles()

        def load_one(i=0):
            self._render_job = None
            if generation != self._generation or i >= len(current):
                return
            canvas = self._tiles[i]._thumbnail
            try:
                with Image.open(current[i]["file"]) as original:
                    image = ImageOps.contain(original.convert("RGB"), (160, 152))
                photo = ImageTk.PhotoImage(image, master=self)
                self._photos.append(photo)
                canvas.create_image(max(170, canvas.winfo_width()) // 2, 80, image=photo)
            except (OSError, ValueError):
                canvas.create_text(85, 80, text="Reference unavailable", width=150, fill=MUTED)
            self._render_job = self.after(1, lambda: load_one(i + 1))
        load_one()

    def select(self, item):
        self.selected = item
        self.selection_label.configure(text=item["name"])
        self.metadata.configure(text=f"{item['category']}\n{item.get('resolution', '')}\n{item['path']}")
        available = item["file"].is_file()
        for button in (self.select_button, self.send_button, self.open_button, self.copy_button):
            button.configure(state="normal" if available else "disabled")
        self.message.set("Preview only. Choose Select reference to keep this pose in GENESIS." if available
                         else "This reference file is missing; no selection was applied.")
        self._draw_preview()

    def _queue_preview(self, _=None):
        if self._preview_job:
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(100, self._draw_preview)

    def _draw_preview(self):
        self._preview_job = None
        self.preview.delete("all")
        if not self.selected:
            return
        width, height = max(20, self.preview.winfo_width()), max(20, self.preview.winfo_height())
        try:
            with Image.open(self.selected["file"]) as original:
                image = ImageOps.contain(original.convert("RGB"), (width - 16, height - 16))
            self._preview_photo = ImageTk.PhotoImage(image, master=self)
            self.preview.create_image(width // 2, height // 2, image=self._preview_photo)
        except (OSError, ValueError):
            self.preview.create_text(width // 2, height // 2, text="Reference unavailable", fill=MUTED)

    def use_selection(self):
        if self.selected and self.selected["file"].is_file():
            if self.on_select:
                self.on_select(self.selected)
            self.message.set(f"Selected {self.selected['name']} · reference only; no generation was started.")

    def show_send_menu(self):
        if not self.selected or not self.selected["file"].is_file():
            return
        self.send_menu.tk_popup(
            self.send_button.winfo_rootx(),
            self.send_button.winfo_rooty() + self.send_button.winfo_height(),
        )

    def send_selection(self, destination):
        if not self.selected or not self.selected["file"].is_file():
            return
        if self.on_send:
            self.on_send(self.selected, destination)
            self.message.set(
                f"Sent {self.selected['name']} to {destination.replace('_', ' ')}. "
                "No generation was started."
            )

    def open_selection(self):
        if self.selected and self.selected["file"].is_file() and self.on_open:
            self.on_open(self.selected["file"])

    def copy_path(self):
        if self.selected:
            self.clipboard_clear()
            self.clipboard_append(str(self.selected["file"]))
            self.message.set("Reference path copied.")

    def destroy(self):
        self._generation += 1
        for job in (self._search_job, self._render_job, self._preview_job):
            if job:
                self.after_cancel(job)
        super().destroy()
