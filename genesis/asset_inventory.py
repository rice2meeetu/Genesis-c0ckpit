"""Shared read-only model and LoRA inventory for GENESIS workflows."""

from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk


@dataclass(frozen=True)
class AssetRecord:
    kind: str
    name: str
    source: str


def inventory_records(inventory):
    """Normalize ComfyUI inventory names without opening or interpreting assets."""
    groups = (
        ("Model", "diffusion_models"),
        ("Checkpoint", "checkpoints"),
        ("LoRA", "loras"),
        ("VAE", "vaes"),
        ("Text encoder", "clip"),
    )
    records, seen = [], set()
    for kind, key in groups:
        values = inventory.get(key, []) if isinstance(inventory, dict) else []
        for value in values if isinstance(values, (list, tuple, set)) else ():
            name = str(value).strip()
            identity = (kind.casefold(), name.casefold())
            if name and identity not in seen:
                seen.add(identity)
                records.append(AssetRecord(kind, name, key))
    return sorted(records, key=lambda record: (record.kind.casefold(), record.name.casefold()))


class AssetInventoryView(ttk.Frame):
    def __init__(self, parent, inventory=None):
        super().__init__(parent)
        self.records = inventory_records(inventory or {})
        self.search = tk.StringVar()
        self.kind = tk.StringVar(value="All assets")

        controls = ttk.Frame(self)
        controls.pack(fill="x", pady=(0, 8))
        ttk.Label(controls, text="Search").pack(side="left")
        entry = ttk.Entry(controls, textvariable=self.search)
        entry.pack(side="left", fill="x", expand=True, padx=7)
        self.kind_menu = ttk.Combobox(
            controls,
            textvariable=self.kind,
            state="readonly",
            width=18,
        )
        self.kind_menu.pack(side="left")

        self.tree = ttk.Treeview(
            self,
            columns=("kind", "name"),
            show="headings",
            height=18,
        )
        self.tree.heading("kind", text="Type")
        self.tree.heading("name", text="Asset name")
        self.tree.column("kind", width=120, stretch=False)
        self.tree.column("name", width=620, stretch=True)
        self.tree.pack(fill="both", expand=True)
        self.status = ttk.Label(self)
        self.status.pack(fill="x", pady=(7, 0))

        kinds = sorted({record.kind for record in self.records}, key=str.casefold)
        self.kind_menu.configure(values=["All assets", *kinds])
        self.search.trace_add("write", lambda *_: self.refresh())
        self.kind_menu.bind("<<ComboboxSelected>>", lambda _: self.refresh())
        self.refresh()

    def refresh(self):
        query = self.search.get().strip().casefold()
        selected_kind = self.kind.get()
        visible = [
            record for record in self.records
            if (selected_kind == "All assets" or record.kind == selected_kind)
            and (not query or query in record.name.casefold())
        ]
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)
        for index, record in enumerate(visible):
            self.tree.insert("", "end", iid=str(index), values=(record.kind, record.name))
        self.status.configure(
            text=f"{len(visible)} of {len(self.records)} assets · names only · read-only"
        )


def open_asset_inventory(parent, inventory):
    win = tk.Toplevel(parent)
    win.title("GENESIS · Models & LoRAs")
    win.geometry("900x650")
    win.minsize(680, 440)
    win.transient(parent.winfo_toplevel())
    view = AssetInventoryView(win, inventory)
    view.pack(fill="both", expand=True, padx=12, pady=12)
    ttk.Button(win, text="Close", command=win.destroy).pack(pady=(0, 12))
    win.bind("<Escape>", lambda _: win.destroy())
    return win
