"""Advanced visual layout editor for the GENESIS Cockpit home cards."""

from __future__ import annotations

import copy
import json
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk


SIZE_NAMES = {1: "Small", 2: "Medium", 3: "Large", 4: "Full"}
SIZE_VALUES = {value: key for key, value in SIZE_NAMES.items()}


class LayoutDesigner(tk.Toplevel):
    def __init__(self, parent, layout, defaults, validate, preview, save_settings):
        super().__init__(parent)
        self.title("GENESIS · Maximum Layout Editor")
        self.geometry("1120x760")
        self.minsize(900, 650)
        self.configure(bg="#080a0f")
        self.transient(parent)
        self.parent = parent
        self.validate_layout = validate
        self.preview_callback = preview
        self.save_settings_callback = save_settings
        self.defaults = copy.deepcopy(defaults)
        self.working = copy.deepcopy(layout)
        self.history = [copy.deepcopy(self.working)]
        self.history_index = 0
        self.drag_index = None
        self.live_preview = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Select a card to edit it.")
        self._build()
        self._refresh()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _build(self):
        header = tk.Frame(self, bg="#080a0f")
        header.pack(fill="x", padx=22, pady=(18, 10))
        tk.Label(header, text="MAXIMUM LAYOUT EDITOR", bg="#080a0f", fg="#f4ead5",
                 font=("Noto Sans Display", 19, "bold")).pack(side="left")
        ttk.Checkbutton(header, text="Live preview", variable=self.live_preview).pack(
            side="right")

        body = tk.PanedWindow(self, orient="horizontal", bg="#080a0f",
                              sashwidth=6, bd=0)
        body.pack(fill="both", expand=True, padx=22)
        left = tk.Frame(body, bg="#10141c", highlightthickness=1,
                        highlightbackground="#283142")
        right = tk.Frame(body, bg="#10141c", highlightthickness=1,
                         highlightbackground="#283142")
        body.add(left, minsize=430, stretch="always")
        body.add(right, minsize=390, stretch="always")

        columns = ("section", "width", "height", "shown")
        self.tree = ttk.Treeview(left, columns=columns, show="tree headings",
                                 selectmode="browse")
        for column, label, width in (("#0", "CARD", 220), ("section", "SECTION", 120),
                                     ("width", "WIDTH", 70), ("height", "HEIGHT", 65),
                                     ("shown", "ON", 45)):
            self.tree.heading(column, text=label)
            self.tree.column(column, width=width, anchor="center" if column != "#0" else "w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree.bind("<<TreeviewSelect>>", self._load_selection)
        self.tree.bind("<ButtonPress-1>", self._drag_start)
        self.tree.bind("<ButtonRelease-1>", self._drag_end)

        row = tk.Frame(left, bg="#10141c")
        row.pack(fill="x", padx=8, pady=(0, 8))
        for label, command in (("↑", lambda: self._move(-1)), ("↓", lambda: self._move(1)),
                               ("UNDO", self._undo), ("REDO", self._redo)):
            tk.Button(row, text=label, command=command, bg="#171d28", fg="#f4ead5",
                      relief="flat", padx=12, pady=7).pack(side="left", padx=(0, 5))

        notebook = ttk.Notebook(right)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)
        card_tab = tk.Frame(notebook, bg="#10141c")
        preset_tab = tk.Frame(notebook, bg="#10141c")
        notebook.add(card_tab, text="Card & Section")
        notebook.add(preset_tab, text="Presets & Files")

        self.vars = {
            "title": tk.StringVar(), "section": tk.StringVar(),
            "width": tk.StringVar(value="Small"), "height": tk.IntVar(value=220),
            "visible": tk.BooleanVar(value=True), "background": tk.StringVar(),
            "border": tk.StringVar(), "accent": tk.StringVar(),
        }
        self._field(card_tab, "CARD TITLE", ttk.Entry(card_tab, textvariable=self.vars["title"]))
        self.section_box = ttk.Combobox(card_tab, textvariable=self.vars["section"])
        self._field(card_tab, "SECTION (type a new name to create one)",
                    self.section_box)
        self._field(card_tab, "WIDTH", ttk.Combobox(
            card_tab, textvariable=self.vars["width"], state="readonly",
            values=tuple(SIZE_VALUES)))
        self._field(card_tab, "HEIGHT · 140–420", ttk.Spinbox(
            card_tab, textvariable=self.vars["height"], from_=140, to=420, increment=10))

        tk.Label(card_tab, text="DESCRIPTION", bg="#10141c", fg="#9da9b8",
                 font=("DejaVu Sans", 8, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
        self.description = tk.Text(card_tab, height=5, bg="#0b0e14", fg="#f4ead5",
                                   insertbackground="#d4af37", relief="flat", wrap="word")
        self.description.pack(fill="x", padx=14)
        ttk.Checkbutton(card_tab, text="Show this card",
                        variable=self.vars["visible"]).pack(anchor="w", padx=14, pady=12)

        colors = tk.Frame(card_tab, bg="#10141c")
        colors.pack(fill="x", padx=10)
        for key, label in (("background", "Background"), ("border", "Border"),
                           ("accent", "Accent")):
            tk.Button(colors, text=label, command=lambda k=key: self._pick_color(k),
                      bg="#171d28", fg="#f4ead5", relief="flat", padx=10,
                      pady=7).pack(side="left", padx=4)
        tk.Button(card_tab, text="APPLY CARD CHANGES", command=self._apply_fields,
                  bg="#d4af37", fg="#050505", relief="flat", padx=16, pady=9,
                  font=("DejaVu Sans", 9, "bold")).pack(anchor="e", padx=14, pady=16)

        tk.Label(preset_tab, text="NAMED LAYOUTS", bg="#10141c", fg="#d4af37",
                 font=("DejaVu Sans", 10, "bold")).pack(anchor="w", padx=14, pady=(16, 6))
        self.preset_name = tk.StringVar()
        ttk.Entry(preset_tab, textvariable=self.preset_name).pack(fill="x", padx=14, pady=4)
        preset_buttons = tk.Frame(preset_tab, bg="#10141c")
        preset_buttons.pack(fill="x", padx=10, pady=6)
        for label, command in (("SAVE PRESET", self._save_preset),
                               ("LOAD PRESET", self._load_preset),
                               ("DELETE", self._delete_preset)):
            tk.Button(preset_buttons, text=label, command=command, bg="#171d28",
                      fg="#f4ead5", relief="flat", padx=10, pady=7).pack(
                          side="left", padx=4)
        self.preset_list = tk.Listbox(preset_tab, height=8, bg="#0b0e14", fg="#f4ead5",
                                      selectbackground="#283142", relief="flat")
        self.preset_list.pack(fill="x", padx=14, pady=(0, 14))
        files = tk.Frame(preset_tab, bg="#10141c")
        files.pack(fill="x", padx=10)
        for label, command in (("IMPORT JSON", self._import_json),
                               ("EXPORT JSON", self._export_json),
                               ("RESTORE TEMPLATE 1", self._restore)):
            tk.Button(files, text=label, command=command, bg="#171d28", fg="#f4ead5",
                      relief="flat", padx=10, pady=8).pack(side="left", padx=4)
        self._refresh_presets()

        footer = tk.Frame(self, bg="#080a0f")
        footer.pack(fill="x", padx=22, pady=(10, 18))
        tk.Label(footer, textvariable=self.status, bg="#080a0f", fg="#8f9bad",
                 font=("DejaVu Sans", 8)).pack(side="left")
        tk.Button(footer, text="CANCEL", command=self._cancel, bg="#171d28",
                  fg="#f4ead5", relief="flat", padx=16, pady=9).pack(side="right")
        tk.Button(footer, text="SAVE & APPLY", command=self._save, bg="#d4af37",
                  fg="#050505", relief="flat", padx=18, pady=9,
                  font=("DejaVu Sans", 9, "bold")).pack(side="right", padx=(0, 8))
        self.bind("<Control-z>", lambda _e: self._undo())
        self.bind("<Control-y>", lambda _e: self._redo())

    def _field(self, parent, label, widget):
        tk.Label(parent, text=label, bg="#10141c", fg="#9da9b8",
                 font=("DejaVu Sans", 8, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
        widget.pack(fill="x", padx=14)

    def _selected(self):
        selected = self.tree.selection()
        return int(selected[0].split("-", 1)[1]) if selected else None

    def _refresh(self, selected_key=None):
        self.tree.delete(*self.tree.get_children())
        sections = list(dict.fromkeys(item["section"] for item in self.working))
        self.section_box.configure(values=sections)
        target = None
        for index, item in enumerate(self.working):
            iid = f"card-{index}"
            self.tree.insert("", "end", iid=iid, text=item["title"], values=(
                item["section"], SIZE_NAMES[item["span"]], item["height"],
                "✓" if item["visible"] else "—"))
            if item["key"] == selected_key:
                target = iid
        if target:
            self.tree.selection_set(target)
            self.tree.focus(target)
            self.tree.see(target)

    def _load_selection(self, _event=None):
        index = self._selected()
        if index is None:
            return
        item = self.working[index]
        for key in ("title", "section", "height", "visible", "background", "border", "accent"):
            self.vars[key].set(item[key])
        self.vars["width"].set(SIZE_NAMES[item["span"]])
        self.description.delete("1.0", "end")
        self.description.insert("1.0", item["description"])
        self.status.set(f"Editing {item['title']} · drag rows to reorder")

    def _record(self):
        self.history = self.history[:self.history_index + 1]
        self.history.append(copy.deepcopy(self.working))
        self.history_index += 1
        if self.live_preview.get():
            self.preview_callback(copy.deepcopy(self.working))

    def _apply_fields(self):
        index = self._selected()
        if index is None:
            return
        item = self.working[index]
        item.update({
            "title": self.vars["title"].get(),
            "description": self.description.get("1.0", "end").strip(),
            "section": self.vars["section"].get(),
            "span": SIZE_VALUES[self.vars["width"].get()],
            "height": self.vars["height"].get(),
            "visible": self.vars["visible"].get(),
            "background": self.vars["background"].get(),
            "border": self.vars["border"].get(),
            "accent": self.vars["accent"].get(),
        })
        self.working = self.validate_layout(self.working)
        key = item["key"]
        self._record()
        self._refresh(key)

    def _move(self, delta):
        index = self._selected()
        if index is None or not 0 <= index + delta < len(self.working):
            return
        key = self.working[index]["key"]
        self.working[index], self.working[index + delta] = (
            self.working[index + delta], self.working[index])
        self._record()
        self._refresh(key)

    def _drag_start(self, event):
        row = self.tree.identify_row(event.y)
        self.drag_index = int(row.split("-", 1)[1]) if row else None

    def _drag_end(self, event):
        row = self.tree.identify_row(event.y)
        if self.drag_index is None or not row:
            return
        target = int(row.split("-", 1)[1])
        item = self.working.pop(self.drag_index)
        self.working.insert(target, item)
        self.drag_index = None
        self._record()
        self._refresh(item["key"])

    def _pick_color(self, key):
        color = colorchooser.askcolor(self.vars[key].get(), parent=self)[1]
        if color:
            self.vars[key].set(color)

    def _undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.working = copy.deepcopy(self.history[self.history_index])
            self._refresh()
            if self.live_preview.get():
                self.preview_callback(copy.deepcopy(self.working))

    def _redo(self):
        if self.history_index + 1 < len(self.history):
            self.history_index += 1
            self.working = copy.deepcopy(self.history[self.history_index])
            self._refresh()
            if self.live_preview.get():
                self.preview_callback(copy.deepcopy(self.working))

    def _refresh_presets(self):
        self.preset_list.delete(0, "end")
        for name in sorted(self.parent.settings.get("home_layout_presets", {}), key=str.casefold):
            self.preset_list.insert("end", name)

    def _preset_selection(self):
        selected = self.preset_list.curselection()
        return self.preset_list.get(selected[0]) if selected else self.preset_name.get().strip()

    def _save_preset(self):
        name = self.preset_name.get().strip()[:40]
        if not name:
            messagebox.showinfo("GENESIS", "Enter a preset name.", parent=self)
            return
        presets = self.parent.settings.setdefault("home_layout_presets", {})
        presets[name] = self.validate_layout(self.working)
        self.save_settings_callback(self.parent.settings)
        self._refresh_presets()
        self.status.set(f"Saved preset: {name}")

    def _load_preset(self):
        name = self._preset_selection()
        layout = self.parent.settings.get("home_layout_presets", {}).get(name)
        if layout:
            self.working = self.validate_layout(copy.deepcopy(layout))
            self._record()
            self._refresh()

    def _delete_preset(self):
        name = self._preset_selection()
        presets = self.parent.settings.get("home_layout_presets", {})
        if name in presets:
            del presets[name]
            self.save_settings_callback(self.parent.settings)
            self._refresh_presets()

    def _export_json(self):
        path = filedialog.asksaveasfilename(parent=self, title="Export GENESIS layout",
                                            defaultextension=".json",
                                            filetypes=[("JSON", "*.json")])
        if path:
            Path(path).write_text(json.dumps({"version": 1, "layout": self.working}, indent=2),
                                  encoding="utf-8")

    def _import_json(self):
        path = filedialog.askopenfilename(parent=self, title="Import GENESIS layout",
                                          filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            self.working = self.validate_layout(payload.get("layout", payload))
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror("GENESIS", f"Could not import layout:\n{exc}", parent=self)
            return
        self._record()
        self._refresh()

    def _restore(self):
        self.working = self.validate_layout(copy.deepcopy(self.defaults))
        self._record()
        self._refresh()

    def _save(self):
        self.parent.settings["home_card_layout"] = self.validate_layout(self.working)
        self.save_settings_callback(self.parent.settings)
        self.preview_callback(self.parent.settings["home_card_layout"])
        self.destroy()

    def _cancel(self):
        self.preview_callback(self.parent.settings.get("home_card_layout", self.defaults))
        self.destroy()


def open_layout_designer(parent, layout, defaults, validate, preview, save_settings):
    return LayoutDesigner(parent, layout, defaults, validate, preview, save_settings)
