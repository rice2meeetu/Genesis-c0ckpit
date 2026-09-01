"""Local prompt preset manager for GENESIS image generation."""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox


BG = "#050505"
PANEL = "#0c0c0d"
PANEL_2 = "#151515"
BORDER = "#4a4028"
GOLD = "#d4af37"
TEXT = "#f4efe6"
MUTED = "#aaa39a"
BLUE = "#211b0d"
RED = "#d16a6a"
STORE_PATH = Path.home() / ".config" / "genesis-photo-studio" / "prompts.json"


def load_prompts(path: Path = STORE_PATH) -> list[dict[str, str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict) and item.get("name")]


def save_prompts(prompts: list[dict[str, str]], path: Path = STORE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(prompts, indent=2, ensure_ascii=False), encoding="utf-8")


class PromptManager(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        on_use=None,
        current_prompt: str = "",
        on_close=None,
        embedded: bool = True,
    ):
        super().__init__(parent, bg=BG)
        self.on_use = on_use
        self.on_close = on_close
        self.embedded = embedded
        self.prompts = load_prompts()
        self._build()
        self._refresh_list()
        if current_prompt:
            self.name_var.set("New prompt")
            self.prompt_text.insert("1.0", current_prompt)

    def _build(self) -> None:
        header = tk.Frame(self, bg=PANEL, highlightthickness=1,
                          highlightbackground=BORDER)
        header.pack(fill="x", padx=12, pady=(12, 8))
        title = tk.Frame(header, bg=PANEL)
        title.pack(side="left", padx=14, pady=10)
        tk.Label(title, text="PROMPT MANAGER", bg=PANEL, fg=GOLD,
                 font=("Sans", 16, "bold")).pack(anchor="w")
        tk.Label(title, text="Local presets · no cloud sync · explicit save only",
                 bg=PANEL, fg=MUTED, font=("Sans", 9)).pack(anchor="w", pady=(2, 0))

        if self.on_close:
            self._button(
                header,
                "← BACK TO IMAGE / AI",
                self.on_close
            ).pack(side="right", padx=12, pady=10)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        library = tk.Frame(body, bg=PANEL, width=275, highlightthickness=1,
                           highlightbackground=BORDER)
        library.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        library.grid_propagate(False)
        tk.Label(library, text="SAVED PROMPTS", bg=PANEL, fg=GOLD,
                 font=("Sans", 9, "bold"), anchor="w").pack(fill="x", padx=10, pady=9)
        self.prompt_list = tk.Listbox(library, bg=PANEL_2, fg=TEXT,
                                      selectbackground=BLUE, selectforeground="#ffffff",
                                      relief="flat", bd=0, font=("Sans", 10))
        self.prompt_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.prompt_list.bind("<<ListboxSelect>>", self._select)

        editor = tk.Frame(body, bg=PANEL, highlightthickness=1,
                          highlightbackground=BORDER)
        editor.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        tk.Label(editor, text="NAME", bg=PANEL, fg=MUTED,
                 font=("Sans", 8, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        self.name_var = tk.StringVar()
        tk.Entry(editor, textvariable=self.name_var, bg=PANEL_2, fg=TEXT,
                 insertbackground=TEXT, relief="flat", bd=0,
                 font=("Sans", 11)).pack(fill="x", padx=12, ipady=7)
        tk.Label(editor, text="PROMPT", bg=PANEL, fg=MUTED,
                 font=("Sans", 8, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        self.prompt_text = tk.Text(editor, bg=PANEL_2, fg=TEXT,
                                   insertbackground=TEXT, wrap="word", relief="flat",
                                   bd=0, padx=10, pady=8, font=("Sans", 10))
        self.prompt_text.pack(fill="both", expand=True, padx=12)
        tk.Label(editor, text="TAGS / NOTES", bg=PANEL, fg=MUTED,
                 font=("Sans", 8, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        self.notes_var = tk.StringVar()
        tk.Entry(editor, textvariable=self.notes_var, bg=PANEL_2, fg=TEXT,
                 insertbackground=TEXT, relief="flat", bd=0).pack(
                     fill="x", padx=12, pady=(0, 12), ipady=6)

        actions = tk.Frame(self, bg=PANEL, highlightthickness=1,
                           highlightbackground=BORDER)
        actions.pack(fill="x", padx=12, pady=(0, 12))
        self._button(actions, "NEW", self.clear).pack(side="left", padx=8, pady=8)
        self._button(actions, "SAVE PRESET", self.save).pack(side="left", pady=8)
        tk.Button(actions, text="DELETE", command=self.delete, bg="#2a1518", fg=RED,
                  activebackground=RED, activeforeground="#ffffff", relief="flat",
                  bd=0, padx=11, pady=7, font=("Sans", 8, "bold")).pack(
                      side="left", padx=6, pady=8)
        self._button(actions, "USE IN IMAGE GENERATE", self.use).pack(
            side="right", padx=8, pady=8)

    @staticmethod
    def _button(parent: tk.Misc, label: str, command) -> tk.Button:
        return tk.Button(
            parent,
            text=label,
            command=command,
            bg="#17130a",
            fg=GOLD,
            activebackground=GOLD,
            activeforeground="#050505",
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground="#57471f",
            highlightcolor=GOLD,
            padx=13,
            pady=8,
            font=("Sans", 8, "bold"),
            cursor="hand2",
        )

    def _refresh_list(self) -> None:
        self.prompt_list.delete(0, "end")
        for item in self.prompts:
            self.prompt_list.insert("end", item["name"])

    def _select(self, _event=None) -> None:
        selected = self.prompt_list.curselection()
        if not selected:
            return
        item = self.prompts[selected[0]]
        self.name_var.set(item.get("name", ""))
        self.notes_var.set(item.get("notes", ""))
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", item.get("prompt", ""))

    def clear(self) -> None:
        self.prompt_list.selection_clear(0, "end")
        self.name_var.set("")
        self.notes_var.set("")
        self.prompt_text.delete("1.0", "end")
        self.name_var.set("New prompt")
        self.prompt_text.focus_set()

    def save(self) -> None:
        name = self.name_var.get().strip()
        prompt = self.prompt_text.get("1.0", "end").strip()
        if not name or not prompt:
            messagebox.showinfo("GENESIS", "Enter both a name and prompt.", parent=self)
            return
        item = {"name": name, "prompt": prompt, "notes": self.notes_var.get().strip()}
        existing = next((index for index, value in enumerate(self.prompts)
                         if value.get("name", "").lower() == name.lower()), None)
        if existing is None:
            self.prompts.append(item)
        else:
            self.prompts[existing] = item
        self.prompts.sort(key=lambda value: value["name"].lower())
        try:
            save_prompts(self.prompts)
        except OSError as exc:
            messagebox.showerror("GENESIS", f"Could not save prompts:\n{exc}", parent=self)
            return
        self._refresh_list()

    def delete(self) -> None:
        selected = self.prompt_list.curselection()
        if not selected:
            return
        item = self.prompts[selected[0]]
        if not messagebox.askyesno("GENESIS", f"Delete prompt preset “{item['name']}”?",
                                   parent=self):
            return
        self.prompts.pop(selected[0])
        try:
            save_prompts(self.prompts)
        except OSError as exc:
            messagebox.showerror("GENESIS", f"Could not save prompts:\n{exc}", parent=self)
            return
        self._refresh_list()
        self.clear()

    def use(self) -> None:
        prompt = self.prompt_text.get("1.0", "end").strip()
        if not prompt:
            messagebox.showinfo(
                "GENESIS",
                "Enter or select a prompt first.",
                parent=self,
            )
            return

        if self.on_use:
            self.on_use(prompt)

        if self.embedded:
            if self.on_close:
                self.on_close()
        else:
            self.winfo_toplevel().destroy()


def build_prompt_manager(
    parent: tk.Misc,
    on_use=None,
    current_prompt: str = "",
    on_close=None,
) -> PromptManager:
    """Build Prompt Manager directly inside a GENESIS workspace."""
    panel = PromptManager(
        parent,
        on_use=on_use,
        current_prompt=current_prompt,
        on_close=on_close,
        embedded=True,
    )
    panel.pack(fill="both", expand=True)
    return panel


def open_prompt_manager(
    parent: tk.Misc,
    on_use=None,
    current_prompt: str = "",
) -> tk.Toplevel:
    """Compatibility popup launcher."""
    win = tk.Toplevel(parent)
    win.title("GENESIS · Prompt Manager")
    win.geometry("1000x650")
    win.minsize(780, 520)
    win.configure(bg=BG)

    panel = PromptManager(
        win,
        on_use=on_use,
        current_prompt=current_prompt,
        embedded=False,
    )
    panel.pack(fill="both", expand=True)
    win.prompt_panel = panel
    return win
