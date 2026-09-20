
import hashlib, os, shutil, threading, json, subprocess, sys, time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import json
import shutil
import subprocess
from PIL import Image, ImageTk, ImageEnhance, ImageFilter, ImageOps
import imagehash
from genesis import integrations
from genesis import workflow_lab

try:
    import cv2
except Exception:
    cv2 = None

APP_NAME = "GENESIS COCKPIT"
DISPLAY_FONT = "Noto Sans Display"
BODY_FONT = "DejaVu Sans"
CONFIG_DIR = Path.home() / ".config" / "genesis-photo-studio"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = CONFIG_DIR / "settings.json"
POSE_WORKBENCH_HANDOFF_FILE = CONFIG_DIR / "pose-workbench-handoff.json"

SUPPORTED = {".jpg",".jpeg",".png",".webp",".bmp",".tif",".tiff"}

# Bundled placeholders are deliberately keyed by module. A user's saved artwork
# always wins, so replacing any panel remains a double-click operation.
PANEL_ART_PLACEHOLDERS = {
    "banner": "genesis-cockpit-banner.mp4",
    "flux_generation": "panel-01-image-generate.jpg",
    "pose_library": "panel-02-pose-lab.jpg",
    "reactor_face_swap": "panel-03-face-studio.jpg",
    "prompt_manager": "panel-04-prompt-manager.jpg",
    "photo_organiser": "panel-05-photo-organiser.jpg",
    "duplicate_lab": "panel-06-duplicate-lab.jpg",
    "photo_viewer": "panel-07-photo-viewer.png",
    "camera_hub": "panel-08-camera-hub.png",
    "workspace_photo_organizer": "panel-05-photo-organiser.jpg",
    "workspace_enhance_/_upscale": "panel-06-duplicate-lab.jpg",
    "workspace_background_tools": "panel-03-face-studio.jpg",
    "workspace_wallpaper_studio": "panel-04-prompt-manager.jpg",
    "workspace_camera_hub": "panel-08-camera-hub.png",
    "workspace_image_/_ai": "panel-01-image-generate.jpg",
}

def load_settings():
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except Exception:
            pass
    return {"comfy_url":"http://127.0.0.1:8188"}

def save_settings(s):
    SETTINGS_FILE.write_text(json.dumps(s, indent=2))


def queue_pose_workbench_handoff(path, role, handoff_file=POSE_WORKBENCH_HANDOFF_FILE):
    """Atomically queue one explicit image role for the separate workbench."""
    path = Path(path).expanduser().resolve()
    if role not in {"pose_reference", "source_image"}:
        raise ValueError(f"Unsupported Pose workbench role: {role}")
    if not path.is_file():
        raise ValueError("The selected Pose reference is unavailable.")
    handoff_file = Path(handoff_file)
    handoff_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = handoff_file.with_suffix(handoff_file.suffix + ".tmp")
    temporary.write_text(
        json.dumps({"version": 1, "role": role, "path": str(path)}, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, handoff_file)
    return handoff_file




# ============================================================
# GENESIS Linux Native Picker + Remember Last Folder
# ============================================================

GENESIS_PREFS = os.path.expanduser(
    "~/.config/genesis-photo-studio/paths.json"
)

def _load_genesis_paths():
    try:
        with open(GENESIS_PREFS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_genesis_path(key, path):
    if not path:
        return

    # If a file was selected, remember its parent folder
    if os.path.isfile(path):
        path = os.path.dirname(path)

    try:
        os.makedirs(os.path.dirname(GENESIS_PREFS), exist_ok=True)

        data = _load_genesis_paths()
        data[key] = os.path.abspath(path)

        with open(GENESIS_PREFS, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def _genesis_last_folder(key, fallback=None):
    data = _load_genesis_paths()
    path = data.get(key)

    if path and os.path.isdir(path):
        return path

    if fallback and os.path.isdir(fallback):
        return fallback

    return os.path.expanduser("~")

def genesis_pick_folder(
    title="Choose folder",
    initialdir=None,
    remember_key="folder"
):
    initialdir = _genesis_last_folder(
        remember_key,
        initialdir
    )

    if shutil.which("zenity"):
        cmd = [
            "zenity",
            "--file-selection",
            "--directory",
            "--title=" + title,
            "--width=1100",
            "--height=750",
            "--filename=" + os.path.abspath(initialdir) + "/",
        ]

        try:
            r = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True
            )

            if r.returncode == 0:
                selected = r.stdout.strip()

                if selected:
                    _save_genesis_path(
                        remember_key,
                        selected
                    )

                return selected

            return ""

        except Exception:
            pass

    selected = filedialog.askdirectory(
        title=title,
        initialdir=initialdir
    )

    if selected:
        _save_genesis_path(
            remember_key,
            selected
        )

    return selected


def genesis_pick_files(
    title="Choose images",
    initialdir=None,
    remember_key="image_input",
    visual_parent=None,
):
    initialdir = _genesis_last_folder(
        remember_key,
        initialdir
    )

    if visual_parent is not None:
        from genesis.visual_browser import pick_images
        files = pick_images(visual_parent, initial_folder=initialdir, multiple=True)
        if files:
            _save_genesis_path(remember_key, files[0])
        return tuple(files or ())

    if shutil.which("zenity"):
        cmd = [
            "zenity",
            "--file-selection",
            "--multiple",
            "--separator=\n",
            "--title=" + title,
            "--width=1100",
            "--height=750",
            "--filename=" + os.path.abspath(initialdir) + "/",
            "--file-filter=Images | *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff",
            "--file-filter=All files | *",
        ]

        try:
            r = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True
            )

            if r.returncode == 0:
                files = tuple(
                    x for x in r.stdout.splitlines()
                    if x.strip()
                )

                if files:
                    _save_genesis_path(
                        remember_key,
                        files[0]
                    )

                return files

            return ()

        except Exception:
            pass

    files = filedialog.askopenfilenames(
        title=title,
        initialdir=initialdir,
        filetypes=[
            (
                "Images",
                "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff"
            ),
            ("All files", "*.*")
        ]
    )

    if files:
        _save_genesis_path(
            remember_key,
            files[0]
        )

    return files


def genesis_pick_file(
    title="Choose image",
    initialdir=None,
    remember_key="single_image",
    allow_video=False,
    visual_parent=None,
):
    initialdir = _genesis_last_folder(
        remember_key,
        initialdir
    )

    if visual_parent is not None and not allow_video:
        from genesis.visual_browser import pick_images
        selected = pick_images(visual_parent, initial_folder=initialdir, multiple=False)
        if selected:
            _save_genesis_path(remember_key, selected[0])
            return selected[0]
        return ""

    if shutil.which("zenity"):
        media_filter = (
            "--file-filter=Artwork | *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.mp4 *.mov *.m4v *.webm"
            if allow_video else
            "--file-filter=Images | *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff"
        )
        cmd = [
            "zenity",
            "--file-selection",
            "--title=" + title,
            "--width=1100",
            "--height=750",
            "--filename=" + os.path.abspath(initialdir) + "/",
            media_filter,
            "--file-filter=All files | *",
        ]

        try:
            r = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True
            )

            if r.returncode == 0:
                selected = r.stdout.strip()

                if selected:
                    _save_genesis_path(
                        remember_key,
                        selected
                    )

                return selected

            return ""

        except Exception:
            pass

    selected = filedialog.askopenfilename(
        title=title,
        initialdir=initialdir,
        filetypes=(
            [("Artwork", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.mp4 *.mov *.m4v *.webm"),
             ("All files", "*.*")]
            if allow_video else
            [("Images", "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff"),
             ("All files", "*.*")]
        ),
    )

    if selected:
        _save_genesis_path(
            remember_key,
            selected
        )

    return selected


def genesis_save_image(
    title="Save image",
    initialdir=None,
    remember_key="save_image"
):
    initialdir = _genesis_last_folder(
        remember_key,
        initialdir
    )

    if shutil.which("zenity"):
        cmd = [
            "zenity",
            "--file-selection",
            "--save",
            "--confirm-overwrite",
            "--title=" + title,
            "--width=1100",
            "--height=750",
            "--filename=" + os.path.abspath(initialdir) + "/output.png",
            "--file-filter=PNG | *.png",
            "--file-filter=JPEG | *.jpg *.jpeg",
        ]

        try:
            r = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True
            )

            if r.returncode == 0:
                selected = r.stdout.strip()

                if selected and not os.path.splitext(selected)[1]:
                    selected += ".png"

                if selected:
                    _save_genesis_path(
                        remember_key,
                        selected
                    )

                return selected

            return ""

        except Exception:
            pass

    selected = filedialog.asksaveasfilename(
        title=title,
        initialdir=initialdir,
        defaultextension=".png",
        filetypes=[
            ("PNG", "*.png"),
            ("JPEG", "*.jpg")
        ]
    )

    if selected:
        _save_genesis_path(
            remember_key,
            selected
        )

    return selected


class PhotoStudio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title(APP_NAME)
        self.geometry("1600x960")
        self.minsize(1280,760)
        self.settings = load_settings()
        self.files = []
        self.thumb_cache = {}
        self.current_image = None
        self.current_path = None
        self.canvas_subject = None
        self.canvas_bg = None
        self.subject_pos = [300,200]
        self.subject_scale = 1.0
        self.drag_start = None

        # GENESIS configurable cockpit artwork
        self.art_canvases = {}
        self.art_images = {}
        self.art_render_jobs = {}
        self.workspace_backdrop_images = {}
        self.workspace_backdrop_jobs = {}
        self.banner_video_capture = None
        self.banner_secondary_capture = None
        self.banner_video_job = None
        self.banner_video_path = None
        self.splash_video_capture = None
        self.splash_secondary_capture = None
        self.splash_video_job = None

        bundled_banner = (
            Path(__file__).resolve().parent
            / "genesis"
            / "assets"
            / "panel_backgrounds"
            / PANEL_ART_PLACEHOLDERS["banner"]
        )
        if (
            bundled_banner.is_file()
            and self.settings.get("cockpit_banner_asset_version") != 1
        ):
            self.settings[self._cockpit_art_setting_key("banner")] = str(bundled_banner)
            self.settings["cockpit_banner_asset_version"] = 1
            try:
                save_settings(self.settings)
            except OSError as exc:
                print("GENESIS BANNER: could not save default selection", exc)

        self._setup_cockpit_theme()

        # Show the animated GENESIS splash immediately, before constructing
        # the heavier cockpit UI.
        self.withdraw()
        self.after_idle(self._begin_genesis_startup)

    def _setup_cockpit_theme(self):
        self.configure(bg="#050505")

        try:
            asset_dir = Path(__file__).resolve().parent / "genesis"
            icon_candidates = (
                asset_dir / "genesis_cockpit_icon.png",
                Path.home() / "Downloads" / "64e55b26-32fd-4060-9ae5-f45a3f526d07.jpg",
                asset_dir / "icon.png",
            )
            icon_path = next((path for path in icon_candidates if path.exists()), None)
            if icon_path and icon_path.exists():
                icon_image = Image.open(icon_path).convert("RGBA")
                icon_image.thumbnail((256, 256), Image.Resampling.LANCZOS)
                self._genesis_window_icon = ImageTk.PhotoImage(icon_image)
                self.iconphoto(True, self._genesis_window_icon)
        except Exception:
            pass

        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except Exception:
            pass

        BG = "#080a0f"
        PANEL = "#10141c"
        PANEL2 = "#171d28"
        BORDER = "#283142"
        TEXT = "#f6f7fb"
        MUTED = "#8f9bad"
        ACCENT = "#d4af37"
        ACCENT2 = "#8a6d1d"
        SELECT = "#202938"

        style.configure(
            ".",
            background=BG,
            foreground=TEXT,
            fieldbackground=PANEL,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            font=("DejaVu Sans", 10)
        )

        style.configure(
            "TFrame",
            background=BG
        )

        style.configure(
            "Cockpit.TFrame",
            background=PANEL
        )

        style.configure(
            "TLabel",
            background=BG,
            foreground=TEXT
        )

        style.configure(
            "Muted.TLabel",
            background=BG,
            foreground=MUTED
        )

        style.configure(
            "Header.TLabel",
            background=BG,
            foreground=TEXT,
            font=("DejaVu Sans", 20, "bold")
        )

        style.configure(
            "Status.TLabel",
            background=PANEL,
            foreground=ACCENT,
            font=("DejaVu Sans", 10, "bold"),
            padding=(10, 5)
        )

        style.configure(
            "TButton",
            background=PANEL2,
            foreground=TEXT,
            borderwidth=1,
            relief="flat",
            padding=(10, 7)
        )

        style.map(
            "TButton",
            background=[
                ("active", SELECT),
                ("pressed", ACCENT2)
            ],
            foreground=[
                ("active", "#ffffff"),
                ("pressed", "#ffffff")
            ]
        )

        style.configure(
            "Accent.TButton",
            background=ACCENT2,
            foreground="#ffffff",
            font=("DejaVu Sans", 10, "bold")
        )

        style.map(
            "Accent.TButton",
            background=[
                ("active", ACCENT),
                ("pressed", "#8f6824")
            ]
        )

        style.configure(
            "TNotebook",
            background=BG,
            borderwidth=0,
            tabmargins=(0, 0, 0, 0)
        )

        style.configure(
            "TNotebook.Tab",
            background=PANEL,
            foreground=MUTED,
            padding=(18, 10),
            borderwidth=0,
            font=("DejaVu Sans", 10, "bold")
        )

        style.map(
            "TNotebook.Tab",
            background=[
                ("selected", SELECT),
                ("active", PANEL2)
            ],
            foreground=[
                ("selected", ACCENT),
                ("active", TEXT)
            ]
        )

        style.configure(
            "TLabelframe",
            background=BG,
            foreground=TEXT,
            bordercolor=BORDER
        )

        style.configure(
            "TLabelframe.Label",
            background=BG,
            foreground=ACCENT,
            font=("DejaVu Sans", 10, "bold")
        )

        style.configure(
            "TEntry",
            fieldbackground=PANEL,
            foreground=TEXT,
            insertcolor=TEXT
        )

        style.configure(
            "TSpinbox",
            fieldbackground=PANEL,
            background=PANEL2,
            foreground=TEXT,
            arrowcolor=ACCENT,
            bordercolor=BORDER
        )

        style.configure(
            "TCombobox",
            fieldbackground=PANEL,
            background=PANEL,
            foreground=TEXT,
            arrowcolor=ACCENT
        )

        style.configure(
            "Treeview",
            background=PANEL,
            fieldbackground=PANEL,
            foreground=TEXT,
            rowheight=28,
            bordercolor=BORDER
        )

        style.map(
            "Treeview",
            background=[("selected", SELECT)],
            foreground=[("selected", "#ffffff")]
        )

        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=PANEL,
            background=ACCENT,
            bordercolor=BORDER,
            lightcolor=ACCENT,
            darkcolor=ACCENT2,
            thickness=10
        )

        style.configure(
            "Vertical.TScrollbar",
            troughcolor=BG,
            background=PANEL2,
            arrowcolor=ACCENT,
            bordercolor=BORDER
        )

        self.option_add("*Listbox.background", PANEL)
        self.option_add("*Listbox.foreground", TEXT)
        self.option_add("*Listbox.selectBackground", SELECT)
        self.option_add("*Listbox.selectForeground", "#ffffff")
        self.option_add("*Text.background", PANEL)
        self.option_add("*Text.foreground", TEXT)
        self.option_add("*Text.insertBackground", TEXT)
        self.option_add("*Canvas.background", BG)

    def _build(self):
        # ============================================================
        # TOP COCKPIT HEADER
        # ============================================================
        top = ttk.Frame(self, style="Cockpit.TFrame")
        top.pack(fill="x", padx=18, pady=(16, 10))

        title_wrap = ttk.Frame(top, style="Cockpit.TFrame")
        title_wrap.pack(side="left", padx=12, pady=8)

        ttk.Label(
            title_wrap,
            text="GENESIS",
            font=(DISPLAY_FONT, 28, "bold"),
            foreground="#d4af37",
            background="#101010"
        ).pack(side="left")

        ttk.Label(
            title_wrap,
            text="  CREATIVE STUDIO",
            font=(DISPLAY_FONT, 17, "bold"),
            foreground="#f4ead5",
            background="#101010"
        ).pack(side="left")

        ttk.Label(
            title_wrap,
            text="   LOCAL WORKSPACE  /  LINUX ROCm",
            font=("DejaVu Sans", 9, "bold"),
            foreground="#9da9b8",
            background="#101010"
        ).pack(side="left", padx=(12, 0))

        self.status = ttk.Label(
            top,
            text="SYSTEM READY",
            style="Status.TLabel"
        )
        self.status.pack(side="right", padx=12, pady=8)

        # ============================================================
        # MASTER COCKPIT BODY
        #
        # [ LEFT NAVIGATION ] [ ACTIVE WORKSPACE ]
        # ============================================================
        shell = ttk.Frame(self)
        shell.pack(
            fill="both",
            expand=True,
            padx=18,
            pady=(0, 18)
        )

        nav_shell = tk.Frame(shell, bg="#0c1017")
        nav_shell.pack(side="left", fill="y", padx=(0, 14))
        nav_canvas = tk.Canvas(nav_shell, bg="#0c1017", width=286,
                               highlightthickness=0)
        nav_scroll = ttk.Scrollbar(nav_shell, orient="vertical", command=nav_canvas.yview)
        nav_scroll.pack(side="right", fill="y")
        nav_canvas.pack(side="left", fill="both", expand=True)
        nav_canvas.configure(yscrollcommand=nav_scroll.set)
        self.nav_rail = tk.Frame(nav_canvas, bg="#0c1017", highlightthickness=1,
                                 highlightbackground="#283142")
        nav_window = nav_canvas.create_window((0, 0), window=self.nav_rail, anchor="nw")
        self.nav_rail.bind("<Configure>", lambda _e: nav_canvas.configure(
            scrollregion=nav_canvas.bbox("all")))
        nav_canvas.bind("<Configure>", lambda e: nav_canvas.itemconfigure(
            nav_window, width=e.width))

        self.workspace = tk.Frame(
            shell,
            bg="#080a0f",
            highlightthickness=1,
            highlightbackground="#283142"
        )
        self.workspace.pack(
            side="left",
            fill="both",
            expand=True
        )

        # ============================================================
        # PAGES
        # ============================================================
        self.pages = {}

        self.tab_home = ttk.Frame(self.workspace)
        self.tab_org = ttk.Frame(self.workspace)
        self.tab_tools = ttk.Frame(self.workspace)
        self.tab_bg = ttk.Frame(self.workspace)
        self.tab_canvas = ttk.Frame(self.workspace)
        self.tab_cameras = ttk.Frame(self.workspace)
        self.tab_ai = ttk.Frame(self.workspace)
        self.tab_pose = ttk.Frame(self.workspace)

        self.pages = {
            "home": self.tab_home,
            "photos": self.tab_org,
            "enhance": self.tab_tools,
            "background": self.tab_tools,
            "canvas": self.tab_canvas,
            "cameras": self.tab_cameras,
            "ai": self.tab_ai,
            "poses": self.tab_pose,
        }

        # ============================================================
        # LEFT NAVIGATION
        # ============================================================
        tk.Label(
            self.nav_rail,
            text="WORKSPACES",
            bg="#0c1017",
            fg="#9da9b8",
            font=("DejaVu Sans", 9, "bold"),
            anchor="w"
        ).pack(
            fill="x",
            padx=16,
            pady=(18, 8)
        )

        self.nav_buttons = {}

        nav_items = [
            ("home", "Overview", "home"),
            (None, "AI IMAGE STUDIO", None),
            ("ai", "Generate", "ai"),
            ("poses", "Pose Library", "poses"),
            ("model-manager", "Models & LoRAs", "model-manager"),
            ("prompt-manager", "Prompt Builder", "prompt-manager"),
            (None, "PHOTO STUDIO", None),
            ("photos", "Library & Faces", "photos"),
            ("enhance", "Photo Tools", "enhance"),
            ("canvas", "Create / Wallpaper", "canvas"),
            (None, "CONNECTED", None),
            ("cameras", "Camera Hub", "cameras"),
            ("media", "Media / Jellyfin", "media"),
        ]

        for key, label, target in nav_items:
            if key is None:
                tk.Label(
                    self.nav_rail,
                    text=label,
                    bg="#0c1017",
                    fg="#667387",
                    font=("DejaVu Sans", 8, "bold"),
                    anchor="w",
                ).pack(fill="x", padx=18, pady=(16, 5))
                continue
            btn = tk.Button(
                self.nav_rail,
                text=label,
                command=lambda k=target: (
                    self._open_cockpit_target(k)
                    if k in {"editor", "duplicates", "media", "model-manager", "prompt-manager"}
                    else self._show_page(k)
                ),
                bg="#111722",
                fg="#e8edf5",
                activebackground="#202938",
                activeforeground="#ffffff",
                relief="flat",
                bd=0,
                highlightthickness=0,
                anchor="w",
                padx=14,
                pady=10,
                font=("DejaVu Sans", 9, "bold"),
                cursor="hand2"
            )
            btn.pack(
                fill="x",
                padx=10,
                pady=2
            )
            self.nav_buttons[key] = btn

        tk.Frame(
            self.nav_rail,
            bg="#3a3a3a",
            height=1
        ).pack(
            fill="x",
            padx=12,
            pady=(18, 14)
        )

        tk.Label(
            self.nav_rail,
            text="SYSTEMS",
            bg="#0b0b0b",
            fg="#9da9b8",
            font=("DejaVu Sans", 9, "bold"),
            anchor="w"
        ).pack(
            fill="x",
            padx=16,
            pady=(0, 8)
        )

        self.nav_camera_status = tk.Label(
            self.nav_rail,
            text="● Cameras: checking",
            bg="#0b0b0b",
            fg="#9da9b8",
            anchor="w",
            font=("DejaVu Sans", 9)
        )
        self.nav_camera_status.pack(
            fill="x",
            padx=16,
            pady=3
        )

        self.nav_comfy_status = tk.Label(
            self.nav_rail,
            text="● ComfyUI: not checked",
            bg="#0b0b0b",
            fg="#9da9b8",
            anchor="w",
            font=("DejaVu Sans", 9)
        )
        self.nav_comfy_status.pack(
            fill="x",
            padx=16,
            pady=3
        )

        self.nav_llama_status = tk.Label(
            self.nav_rail,
            text="● LLM: not checked",
            bg="#0b0b0b",
            fg="#9da9b8",
            anchor="w",
            font=("DejaVu Sans", 9)
        )
        self.nav_llama_status.pack(fill="x", padx=16, pady=3)

        self.nav_silly_status = tk.Label(
            self.nav_rail,
            bg="#0b0b0b",
            fg="#9da9b8",
            anchor="w",
            font=("DejaVu Sans", 9)
        )
        self.nav_silly_status.pack(fill="x", padx=16, pady=3)

        self.nav_media_status = tk.Label(
            self.nav_rail,
            text="● Media: not checked",
            bg="#0b0b0b",
            fg="#9da9b8",
            anchor="w",
            font=("DejaVu Sans", 9)
        )
        self.nav_media_status.pack(fill="x", padx=16, pady=3)

        tk.Button(
            self.nav_rail,
            text="Refresh status",
            command=self.refresh_system_statuses,
            bg="#111722",
            fg="#9da9b8",
            activebackground="#202938",
            activeforeground="#d4af37",
            relief="flat",
            bd=0,
            font=("DejaVu Sans", 8, "bold"),
            pady=8,
            cursor="hand2"
        ).pack(
            fill="x",
            padx=10,
            pady=(14, 8)
        )

        # Bottom cockpit identifier anchors the rail visually.
        tk.Label(
            self.nav_rail,
            text="LOCAL  /  ROCm",
            bg="#0c1017",
            fg="#574729",
            font=("DejaVu Sans", 8, "bold"),
            anchor="center"
        ).pack(
            side="bottom",
            fill="x",
            padx=10,
            pady=12
        )

        # ------------------------------------------------------------
        # USER-SELECTABLE SYSTEM / IDENTITY ART
        # ------------------------------------------------------------
        self.system_art_wrap = tk.Frame(
            self.nav_rail,
            bg="#0c1017"
        )
        self.system_art_wrap.pack(
            side="top",
            fill="x",
            padx=10,
            pady=(10, 14),
            before=self.nav_buttons["home"]
        )

        tk.Label(
            self.system_art_wrap,
            text="GENESIS",
            bg="#0c1017",
            fg="#9da9b8",
            font=("DejaVu Sans", 8, "bold")
        ).pack(
            anchor="w",
            padx=4,
            pady=(0, 4)
        )

        self.system_art_canvas = tk.Canvas(
            self.system_art_wrap,
            bg="#101010",
            height=96,
            highlightthickness=1,
            highlightbackground="#3a3a3a",
            cursor="hand2"
        )
        self.system_art_canvas.pack(
            fill="x"
        )

        self.system_art_canvas.bind(
            "<Button-3>",
            lambda e: self._open_art_controls(
                "system_logo",
                self.system_art_canvas
            )
        )

        self.system_art_canvas.bind(
            "<Double-Button-1>",
            lambda e: self._choose_cockpit_art(
                "system_logo",
                self.system_art_canvas
            )
        )

        self.system_art_canvas.bind(
            "<Configure>",
            lambda e: self._schedule_art_render(
                "system_logo",
                self.system_art_canvas
            )
        )


        # Keep the rail wide enough for its labels at the active font/DPI size.
        self.nav_rail.update_idletasks()
        nav_canvas.configure(width=max(
            286,
            max(child.winfo_reqwidth() for child in self.nav_rail.winfo_children()) + 36,
        ))

        def scroll_navigation(event):
            step = -1 if getattr(event, "num", None) == 4 or event.delta > 0 else 1
            nav_canvas.yview_scroll(step, "units")
            return "break"

        def bind_navigation_scroll(widget):
            for event_name in ("<Button-4>", "<Button-5>", "<MouseWheel>"):
                widget.bind(event_name, scroll_navigation, add="+")
            for child in widget.winfo_children():
                bind_navigation_scroll(child)
        bind_navigation_scroll(self.nav_rail)

        # ============================================================
        # BUILD EXISTING MODULES
        # ============================================================
        self._home_ui()
        self._organiser_ui()
        self._tools_ui()
        self._bg_ui()
        self._canvas_ui()
        self._camera_ui()
        self._ai_ui()
        self._install_workspace_backdrops()

        self._show_page("home")
        self.after(900, self.refresh_system_statuses)

    def _show_page(self, page_key):
        if page_key == "poses":
            self._ensure_native_pose_library()
        page = self.pages.get(page_key)

        if page is None:
            return

        for frame in self.pages.values():
            frame.pack_forget()

        page.pack(
            fill="both",
            expand=True
        )

        for key, button in self.nav_buttons.items():
            if key == page_key:
                button.configure(
                    bg="#202938",
                    fg="#d4af37"
                )
            else:
                button.configure(
                    bg="#111722",
                    fg="#e8edf5"
                )

    def _workspace_heading(self, parent, kicker, title, detail):
        art_key = "workspace_" + "_".join(title.lower().split())
        canvas = tk.Canvas(
            parent, bg="#101010", height=132, highlightthickness=1,
            highlightbackground="#3a3a3a", cursor="hand2",
        )
        canvas.pack(fill="x", padx=10, pady=(10, 6))
        self.workspace_art_canvases = getattr(self, "workspace_art_canvases", {})
        self.workspace_art_metadata = getattr(self, "workspace_art_metadata", {})
        self.workspace_art_canvases[art_key] = canvas
        self.workspace_art_metadata[art_key] = {
            "kicker": kicker.upper(), "title": title, "detail": detail,
        }
        canvas.bind(
            "<Button-3>",
            lambda _event, k=art_key, c=canvas: self._open_art_controls(k, c),
        )
        canvas.bind(
            "<Double-Button-1>",
            lambda _event, k=art_key, c=canvas: self._choose_cockpit_art(k, c),
        )
        canvas.bind(
            "<Configure>",
            lambda _event, k=art_key, c=canvas: self._schedule_art_render(k, c),
        )
        self.after(120, lambda k=art_key, c=canvas: self._render_art_canvas(k, c))

    def _draw_workspace_backdrop_overlay(self, art_key, canvas, width, height):
        metadata = getattr(self, "workspace_art_metadata", {}).get(art_key)
        if not metadata:
            return
        canvas.create_rectangle(0, 0, width, height, fill="#050505",
                                outline="", stipple="gray50")
        canvas.create_rectangle(18, 20, 21, height - 20,
                                fill="#d4af37", outline="")
        canvas.create_text(34, 24, text=metadata["kicker"], anchor="nw",
                           fill="#d4af37", font=(BODY_FONT, 8, "bold"))
        canvas.create_text(34, 43, text=metadata["title"], anchor="nw",
                           fill="#f4ead5", font=(DISPLAY_FONT, 20, "bold"))
        canvas.create_text(34, 84, text=metadata["detail"], anchor="nw",
                           fill="#b5bdc8", font=(BODY_FONT, 9))
        canvas.create_text(width - 16, height - 14,
                           text="RIGHT-CLICK TO CUSTOMISE BACKGROUND",
                           anchor="se", fill="#9a8965",
                           font=(BODY_FONT, 7, "bold"))

    def _install_workspace_backdrops(self):
        """Place a dimmed supplied image behind each major workspace."""
        page_art = {
            "photos": "photo_organiser",
            "enhance": "duplicate_lab",
            "background": "reactor_face_swap",
            "canvas": "prompt_manager",
            "cameras": "camera_hub",
            "ai": "flux_generation",
        }
        for page_key, art_key in page_art.items():
            parent = getattr(
                self,
                f"{page_key}_backdrop_host",
                self.pages.get(page_key),
            )
            if parent is None:
                continue
            backdrop = tk.Label(parent, bg="#050505", bd=0)
            backdrop.place(x=0, y=0, relwidth=1, relheight=1)
            backdrop.lower()
            parent.bind(
                "<Configure>",
                lambda _event, key=art_key, widget=backdrop:
                self._schedule_workspace_backdrop(key, widget),
                add="+",
            )
            self.after(
                180,
                lambda key=art_key, widget=backdrop:
                self._render_workspace_backdrop(key, widget),
            )

    def _schedule_workspace_backdrop(self, art_key, widget):
        previous = self.workspace_backdrop_jobs.get(art_key)
        if previous:
            try:
                self.after_cancel(previous)
            except Exception:
                pass
        self.workspace_backdrop_jobs[art_key] = self.after(
            120,
            lambda: self._render_workspace_backdrop(art_key, widget),
        )

    def _render_workspace_backdrop(self, art_key, widget):
        if not widget.winfo_exists():
            return
        width = max(40, widget.winfo_width())
        height = max(40, widget.winfo_height())
        name = PANEL_ART_PLACEHOLDERS.get(art_key)
        if not name:
            return
        path = (
            Path(__file__).resolve().parent
            / "genesis" / "assets" / "panel_backgrounds" / name
        )
        if not path.is_file():
            return
        try:
            source = Image.open(path).convert("RGB")
            scale = max(width / source.width, height / source.height)
            resized = source.resize(
                (
                    max(1, int(source.width * scale)),
                    max(1, int(source.height * scale)),
                ),
                Image.Resampling.LANCZOS,
            )
            left = max(0, (resized.width - width) // 2)
            top = max(0, int((resized.height - height) * 0.38))
            background = resized.crop(
                (left, top, left + width, top + height)
            )
            background = background.filter(
                ImageFilter.GaussianBlur(radius=1.4)
            )
            background = ImageEnhance.Contrast(background).enhance(0.88)
            background = Image.blend(
                background,
                Image.new("RGB", background.size, "#050505"),
                0.72,
            )
            tkimg = ImageTk.PhotoImage(background)
            widget.configure(image=tkimg)
            self.workspace_backdrop_images[art_key] = tkimg
        except Exception as exc:
            print("GENESIS BACKDROP ERROR", art_key, exc)

    def _recent_project_text(self):
        path = self.settings.get("recent_photo_project")
        return path if path and Path(path).is_dir() else "No photo folder opened yet"

    def _open_latest_project(self):
        path = self.settings.get("recent_photo_project")
        if path and Path(path).is_dir():
            self._show_page("photos")
            self.scan_folder_again(path)
            return
        self._show_page("photos")
        self.after(80, self.scan_folder)

    def _open_cockpit_target(self, target):
        if target == "background":
            self._show_page("enhance")
            self.after(
                30,
                lambda: self._show_photo_tools_mode("background")
            )
            return

        launchers = {
            "media": self.launch_media,
            "editor": self.open_image_editor,
            "duplicates": self.open_duplicate_lab,
            "model-manager": self.open_model_manager,
            "prompt-manager": self.open_prompt_manager,
            "comfyui": self.launch_comfyui,
        }
        if target in launchers:
            launchers[target]()
            return
        if not target.startswith("ai:"):
            self._show_page(target)
            return
        mode = target.split(":", 1)[1]
        self._show_page("ai")
        if mode == "pose":
            self.after(80, self.open_pose_studio)
        elif mode == "status":
            self.after(80, self.run_workflow_preflight)
        elif mode == "prompt":
            self.after(80, self.open_prompt_manager)
        elif mode == "reactor":
            # ReActor workflows are discovered asynchronously.
            # Remember what Face Studio requested, refresh the list,
            # then select it when discovery has completed.
            self._pending_generation_mode = "reactor"
            self.gen_status_label.config(
                text="FACE STUDIO · loading ReActor workflow..."
            )
            self.refresh_generation_options()
        else:
            self.after(100, lambda: self._select_generation_workflow(mode))

    def _select_generation_workflow(self, mode):
        workflow_words = {
            "reactor": ("reactor", "face", "swap"),
            "9b": ("9b_kv", "9b-kv", "klein_9b", "klein-9b"),
            "fluxup": ("fluxup", "fluxedup"),
            "phroot": ("phroot", "phr00t"),
        }
        words = workflow_words.get(mode, ("flux", "klein"))
        match = next((name for name in self.gen_workflow_paths
                      if any(word in name.lower() for word in words)), None)
        if match:
            self.gen_workflow_var.set(match)
            label = {
                "reactor": "ReActor", "9b": "Klein 9B",
                "fluxup": "FluxUp", "phroot": "Phr00t",
            }.get(mode, "FLUX")
            self.gen_status_label.config(
                text=f"{label} workflow selected · review inputs, then Generate"
            )
        else:
            label = {
                "reactor": "ReActor / face-swap", "9b": "Klein 9B",
                "fluxup": "FluxUp", "phroot": "Phr00t",
            }.get(mode, "FLUX / Klein")
            self.gen_status_label.config(
                text=f"No indexed {label} workflow yet · use Refresh or Inspect Workflow JSON"
            )

    def _home_ui(self):
        home_canvas = tk.Canvas(
            self.tab_home,
            bg="#050505",
            highlightthickness=0,
        )
        home_scroll = ttk.Scrollbar(
            self.tab_home,
            orient="vertical",
            command=home_canvas.yview,
        )
        home_canvas.configure(yscrollcommand=home_scroll.set)
        home_scroll.pack(side="right", fill="y")
        home_canvas.pack(side="left", fill="both", expand=True)

        outer = tk.Frame(
            home_canvas,
            bg="#050505"
        )
        home_window = home_canvas.create_window(
            (0, 0),
            window=outer,
            anchor="nw",
        )
        outer.configure(padx=28, pady=24)
        outer.bind(
            "<Configure>",
            lambda _event: home_canvas.configure(
                scrollregion=home_canvas.bbox("all")
            ),
        )
        home_canvas.bind(
            "<Configure>",
            lambda event: home_canvas.itemconfigure(
                home_window,
                width=event.width,
            ),
        )
        home_canvas.bind(
            "<MouseWheel>",
            lambda event: home_canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units",
            ),
        )

        # ============================================================
        # TOP GENESIS BANNER
        # ============================================================
        banner_wrap = tk.Frame(
            outer,
            bg="#101010",
            highlightthickness=1,
            highlightbackground="#3a3a3a"
        )
        banner_wrap.pack(
            fill="x",
            pady=(0, 12)
        )

        self.home_banner_canvas = tk.Canvas(
            banner_wrap,
            bg="#101010",
            height=420,
            highlightthickness=0,
            cursor="hand2"
        )
        self.home_banner_canvas.pack(
            fill="x",
            expand=True
        )

        self.home_banner_canvas.bind(
            "<Button-3>",
            lambda e: self._open_art_controls(
                "banner",
                self.home_banner_canvas
            )
        )

        self.home_banner_canvas.bind(
            "<Double-Button-1>",
            lambda e: self._choose_cockpit_art(
                "banner",
                self.home_banner_canvas
            )
        )

        self.home_banner_canvas.bind(
            "<Configure>",
            lambda e: self._schedule_art_render(
                "banner",
                self.home_banner_canvas
            )
        )

        # ============================================================
        # COMMAND CENTRE TITLE
        # ============================================================
        heading = tk.Frame(
            outer,
            bg="#050505"
        )
        heading.pack(
            fill="x",
            pady=(8, 20)
        )

        tk.Label(
            heading,
            text="GENESIS COMMAND CENTRE",
            bg="#050505",
            fg="#f4ead5",
            font=(DISPLAY_FONT, 20, "bold"),
            anchor="w"
        ).pack(
            anchor="w"
        )

        tk.Label(
            heading,
            text="Right-click artwork to customise",
            bg="#050505",
            fg="#9da9b8",
            font=("DejaVu Sans", 9),
            anchor="e"
        ).pack(
            anchor="w", pady=(6, 0)
        )

        # ============================================================
        # PRIMARY STUDIO MODULES
        # ============================================================
        studio_sections = tk.Frame(
            outer,
            bg="#050505"
        )
        studio_sections.pack(
            fill="both",
            expand=True
        )

        # Home cockpit uses a 4-column layout.
        # Card span controls visual priority without changing card actions.
        section_data = [
            (
                "IMAGE / AI",
                "Local generation, identity and prompt tools",
                [
                    ("flux_generation", "IMAGE GENERATE",
                     "Create with local FLUX and Klein workflows.", "ai:flux", 2),
                    ("pose_library", "POSE LAB",
                     "Browse poses and hand off to generation.", "ai:pose", 1),
                    ("reactor_face_swap", "FACE STUDIO",
                     "Use optional local ReActor face workflows.", "ai:reactor", 1),
                ],
            ),
            (
                "PHOTO STUDIO",
                "Organising, viewing and duplicate review in one workspace",
                [
                    ("photo_organiser", "PHOTO ORGANIZER",
                     "Library, viewer / editor, duplicates and people in one workspace.",
                     "photos", 3),
                    ("prompt_manager", "PROMPT STUDIO",
                     "Build, save, organize and reuse local prompts.",
                     "prompt-manager", 1),
                ],
            ),
            (
                "SYSTEMS / INTEGRATIONS",
                "Capture, connected local tools and system readiness",
                [
                    ("comfyui", "COMFYUI",
                     "Open the configured local generation service.", "comfyui", 1),
                    ("model_status", "WORKFLOW / MODEL MANAGER",
                     "Inspect installed models, LoRAs, VAEs and workflows.",
                     "model-manager", 2),
                ],
            ),
        ]

        self.home_card_canvases = {}
        self.home_card_metadata = {}

        for section_index, (section_title, section_note, card_data) in enumerate(section_data):
            section = tk.Frame(studio_sections, bg="#050505")
            section.pack(fill="x", pady=(0, 24))

            section_heading = tk.Frame(section, bg="#050505")
            section_heading.pack(fill="x", padx=10, pady=(0, 14))

            tk.Label(
                section_heading,
                text=section_title,
                bg="#050505",
                fg="#d4af37",
                font=(DISPLAY_FONT, 13, "bold"),
            ).pack(anchor="w")

            tk.Label(
                section_heading,
                text=section_note,
                wraplength=650,
                justify="left",
                bg="#050505",
                fg="#9da9b8",
                font=("DejaVu Sans", 8),
            ).pack(anchor="w")

            card_row = tk.Frame(section, bg="#050505")
            card_row.pack(fill="x")

            # Fixed four-column cockpit grid.
            for grid_col in range(4):
                card_row.grid_columnconfigure(
                    grid_col,
                    weight=1,
                    uniform=f"section{section_index}",
                )

            grid_col = 0
            responsive_cards = []

            for art_key, title, description, target, span in card_data:
                card = tk.Frame(
                    card_row,
                    bg="#101010",
                    highlightthickness=1,
                    highlightbackground="#3a3a3a"
                )
                card.grid(
                    row=0,
                    column=grid_col,
                    columnspan=span,
                    sticky="nsew",
                    padx=10,
                    pady=4,
                )

                art = tk.Canvas(
                    card,
                    bg="#101010",
                    height=220,
                    highlightthickness=0,
                    cursor="hand2"
                )
                art.pack(fill="both", expand=True)

                self.home_card_canvases[art_key] = art
                self.home_card_metadata[art_key] = {
                    "title": title,
                    "description": description,
                    "target": target,
                }

                art.bind(
                    "<Button-3>",
                    lambda e, k=art_key, c=art: self._open_art_controls(k, c)
                )

                art.bind(
                    "<Button-1>",
                    lambda e, k=art_key, c=art, t=target:
                    self._home_card_click(e, k, c, t)
                )

                art.bind(
                    "<Configure>",
                    lambda e, k=art_key, c=art: self._schedule_art_render(k, c)
                )

                responsive_cards.append((card, span))
                grid_col += span

            def arrange_cards(event, cards=responsive_cards, row=card_row):
                columns = 4 if event.width >= 1600 else 2 if event.width >= 760 else 1
                if getattr(row, "_layout_columns", None) == columns:
                    return
                row._layout_columns = columns
                for col in range(4):
                    row.grid_columnconfigure(col, weight=1 if col < columns else 0,
                                             uniform="cards" if col < columns else "")
                r, col = 0, 0
                for card, requested_span in cards:
                    span = min(requested_span, columns)
                    if col + span > columns:
                        r, col = r + 1, 0
                    card.grid_configure(row=r, column=col, columnspan=span, pady=8)
                    col += span
            card_row.bind("<Configure>", arrange_cards)

        # Initial artwork render
        self.after(
            250,
            self._refresh_all_cockpit_art
        )

    # ================================================================
    # COCKPIT ARTWORK SYSTEM
    # ================================================================

    def _cockpit_art_setting_key(self, art_key):
        return f"cockpit_art_{art_key}"

    def _home_card_click(self, event, art_key, canvas, target):
        current = canvas.find_withtag("current")
        tags = canvas.gettags(current[0]) if current else ()
        if "frame_control" in tags:
            self._open_art_controls(art_key, canvas)
            return "break"
        self._open_cockpit_target(target)
        return "break"

    def _draw_home_card_overlay(self, art_key, canvas, width, height):
        metadata = getattr(self, "home_card_metadata", {}).get(art_key)
        if not metadata:
            return

        hero_card = art_key in {"flux_generation", "photo_organiser"}

        if art_key in PANEL_ART_PLACEHOLDERS:
            canvas.create_rectangle(
                0, int(height * 0.30), width, height,
                fill="#070707", outline="", stipple="gray50",
            )

        # Warm cockpit frame instead of the old blue-grey border.
        canvas.create_rectangle(
            0, 0, width - 1, height - 1,
            outline="#6b5730" if hero_card else "#4b4028",
            width=2 if hero_card else 1,
        )

        # Small gold accent gives the hero cards more visual priority.
        if hero_card:
            canvas.create_rectangle(
                0, int(height * 0.43), 4, height,
                fill="#d4af37", outline="",
            )

        title_item = canvas.create_text(
            20,
            20,
            text=metadata["title"],
            anchor="nw",
            width=max(80, width - 40),
            fill="#d4af37" if hero_card else "#f4ead5",
            font=(
                DISPLAY_FONT,
                16 if hero_card and width >= 280 else
                15 if width >= 280 else 13,
                "bold",
            ),
        )

        title_bounds = canvas.bbox(title_item)
        description_item = canvas.create_text(
            20,
            title_bounds[3] + 10,
            text=metadata["description"],
            anchor="nw",
            width=max(80, width - 40),
            fill="#c8c1b5",
            font=("DejaVu Sans", 8),
        )


        # Keep title and wrapped description together with a bottom inset.
        text_bottom = canvas.bbox(description_item)[3]
        text_offset = max(0, height - 20 - text_bottom)
        canvas.move(title_item, 0, text_offset)
        canvas.move(description_item, 0, text_offset)

    def _cockpit_art_option_key(self, art_key, option):
        return f"cockpit_art_{art_key}_{option}"

    def _art_defaults(self, art_key):
        if art_key == "banner":
            return {
                "fit": "Cover",
                "zoom": 1.0,
                "x": 50.0,
                "y": 30.0,
            }

        if art_key == "system_logo":
            return {
                "fit": "Contain",
                "zoom": 1.0,
                "x": 50.0,
                "y": 50.0,
            }

        return {
            "fit": "Cover",
            "zoom": 1.0,
            "x": 50.0,
            "y": 50.0,
        }

    def _get_art_options(self, art_key):
        defaults = self._art_defaults(art_key)

        try:
            zoom = float(
                self.settings.get(
                    self._cockpit_art_option_key(art_key, "zoom"),
                    defaults["zoom"]
                )
            )
        except Exception:
            zoom = defaults["zoom"]

        try:
            xpos = float(
                self.settings.get(
                    self._cockpit_art_option_key(art_key, "x"),
                    defaults["x"]
                )
            )
        except Exception:
            xpos = defaults["x"]

        try:
            ypos = float(
                self.settings.get(
                    self._cockpit_art_option_key(art_key, "y"),
                    defaults["y"]
                )
            )
        except Exception:
            ypos = defaults["y"]

        return {
            "fit": self.settings.get(
                self._cockpit_art_option_key(art_key, "fit"),
                defaults["fit"]
            ),
            "zoom": max(0.5, min(3.0, zoom)),
            "x": max(0.0, min(100.0, xpos)),
            "y": max(0.0, min(100.0, ypos)),
        }

    def _choose_cockpit_art(self, art_key, canvas):
        selected = genesis_pick_file(
            title="Choose GENESIS artwork",
            remember_key="cockpit_art",
            allow_video=(art_key == "banner"),
        )

        if not selected:
            return

        self.settings[
            self._cockpit_art_setting_key(art_key)
        ] = selected

        save_settings(self.settings)

        self._render_art_canvas(
            art_key,
            canvas
        )

    def _open_art_controls(self, art_key, canvas):
        options = self._get_art_options(art_key)
        original_options = dict(options)

        win = tk.Toplevel(self)
        win.title(
            f"GENESIS Artwork · {art_key.replace('_', ' ').title()}"
        )
        win.geometry("500x500")
        win.resizable(False, False)
        win.configure(bg="#050505")

        outer = tk.Frame(
            win,
            bg="#050505"
        )
        outer.pack(
            fill="both",
            expand=True,
            padx=18,
            pady=16
        )

        tk.Label(
            outer,
            text="ARTWORK FRAMING",
            bg="#050505",
            fg="#d4af37",
            font=("DejaVu Sans", 15, "bold")
        ).pack(
            anchor="w",
            pady=(0, 3)
        )

        tk.Label(
            outer,
            text=art_key.replace("_", " ").upper(),
            bg="#050505",
            fg="#9da9b8",
            font=("DejaVu Sans", 9, "bold")
        ).pack(
            anchor="w",
            pady=(0, 14)
        )

        fit_var = tk.StringVar(
            value=options["fit"]
        )

        zoom_var = tk.DoubleVar(
            value=options["zoom"]
        )

        x_var = tk.DoubleVar(
            value=options["x"]
        )

        y_var = tk.DoubleVar(
            value=options["y"]
        )

        form = tk.Frame(
            outer,
            bg="#050505"
        )
        form.pack(
            fill="x"
        )

        tk.Label(
            form,
            text="Fit Mode",
            bg="#050505",
            fg="#f4ead5",
            anchor="w"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 8)
        )

        fit_combo = ttk.Combobox(
            form,
            textvariable=fit_var,
            values=["Cover", "Contain"],
            state="readonly",
            width=18
        )
        fit_combo.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(16, 0),
            pady=(0, 8)
        )

        form.columnconfigure(
            1,
            weight=1
        )

        tk.Label(
            outer,
            text="ZOOM",
            bg="#050505",
            fg="#f4ead5",
            font=("DejaVu Sans", 9, "bold"),
            anchor="w"
        ).pack(
            fill="x",
            pady=(8, 0)
        )

        zoom_scale = tk.Scale(
            outer,
            from_=0.5,
            to=3.0,
            resolution=0.05,
            orient="horizontal",
            variable=zoom_var,
            bg="#050505",
            fg="#f4ead5",
            troughcolor="#181818",
            activebackground="#d4af37",
            highlightthickness=0,
            length=440
        )
        zoom_scale.pack(
            fill="x"
        )

        tk.Label(
            outer,
            text="HORIZONTAL POSITION",
            bg="#050505",
            fg="#f4ead5",
            font=("DejaVu Sans", 9, "bold"),
            anchor="w"
        ).pack(
            fill="x",
            pady=(8, 0)
        )

        x_scale = tk.Scale(
            outer,
            from_=0,
            to=100,
            resolution=1,
            orient="horizontal",
            variable=x_var,
            bg="#050505",
            fg="#f4ead5",
            troughcolor="#181818",
            activebackground="#d4af37",
            highlightthickness=0,
            length=440
        )
        x_scale.pack(
            fill="x"
        )

        tk.Label(
            outer,
            text="VERTICAL POSITION",
            bg="#050505",
            fg="#f4ead5",
            font=("DejaVu Sans", 9, "bold"),
            anchor="w"
        ).pack(
            fill="x",
            pady=(8, 0)
        )

        y_scale = tk.Scale(
            outer,
            from_=0,
            to=100,
            resolution=1,
            orient="horizontal",
            variable=y_var,
            bg="#050505",
            fg="#f4ead5",
            troughcolor="#181818",
            activebackground="#d4af37",
            highlightthickness=0,
            length=440
        )
        y_scale.pack(
            fill="x"
        )

        tk.Label(
            outer,
            text=(
                "0 = left/top   •   50 = centre   •   100 = right/bottom\n"
                "Cover fills the slot. Contain starts with the whole image."
            ),
            bg="#050505",
            fg="#9da9b8",
            justify="left",
            anchor="w"
        ).pack(
            fill="x",
            pady=(10, 12)
        )

        def preview(*_):
            self.settings[
                self._cockpit_art_option_key(
                    art_key,
                    "fit"
                )
            ] = fit_var.get()

            self.settings[
                self._cockpit_art_option_key(
                    art_key,
                    "zoom"
                )
            ] = float(zoom_var.get())

            self.settings[
                self._cockpit_art_option_key(
                    art_key,
                    "x"
                )
            ] = float(x_var.get())

            self.settings[
                self._cockpit_art_option_key(
                    art_key,
                    "y"
                )
            ] = float(y_var.get())

            self._render_art_canvas(
                art_key,
                canvas
            )

        fit_combo.bind(
            "<<ComboboxSelected>>",
            preview
        )

        zoom_scale.configure(
            command=preview
        )

        x_scale.configure(
            command=preview
        )

        y_scale.configure(
            command=preview
        )

        buttons = tk.Frame(
            outer,
            bg="#050505"
        )
        buttons.pack(
            fill="x",
            side="bottom"
        )

        def save_and_close():
            preview()
            save_settings(
                self.settings
            )
            win.destroy()

        def cancel_and_close():
            for option, value in original_options.items():
                self.settings[
                    self._cockpit_art_option_key(
                        art_key,
                        option
                    )
                ] = value

            self._render_art_canvas(
                art_key,
                canvas
            )
            win.destroy()

        def reset():
            defaults = self._art_defaults(
                art_key
            )

            fit_var.set(
                defaults["fit"]
            )
            zoom_var.set(
                defaults["zoom"]
            )
            x_var.set(
                defaults["x"]
            )
            y_var.set(
                defaults["y"]
            )

            preview()

        tk.Button(
            buttons,
            text="CHANGE IMAGE",
            command=lambda:
            self._choose_cockpit_art(
                art_key,
                canvas
            ),
            bg="#181818",
            fg="#f4ead5",
            activebackground="#292929",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=10,
            pady=7
        ).pack(
            side="left"
        )

        tk.Button(
            buttons,
            text="RESET",
            command=reset,
            bg="#181818",
            fg="#9da9b8",
            activebackground="#292929",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=10,
            pady=7
        ).pack(
            side="left",
            padx=6
        )

        tk.Button(
            buttons,
            text="CANCEL",
            command=cancel_and_close,
            bg="#181818",
            fg="#9da9b8",
            activebackground="#292929",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=10,
            pady=7
        ).pack(
            side="right",
            padx=(6, 0)
        )

        tk.Button(
            buttons,
            text="SAVE",
            command=save_and_close,
            bg="#292929",
            fg="#ffffff",
            activebackground="#8a6d1d",
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=16,
            pady=7,
            font=("DejaVu Sans", 9, "bold")
        ).pack(
            side="right"
        )

        win.protocol(
            "WM_DELETE_WINDOW",
            cancel_and_close
        )

    def _schedule_art_render(self, art_key, canvas):
        previous = self.art_render_jobs.get(art_key)

        if previous:
            try:
                self.after_cancel(previous)
            except Exception:
                pass

        self.art_render_jobs[art_key] = self.after(
            100,
            lambda:
            self._render_art_canvas(
                art_key,
                canvas
            )
        )

    def _render_art_canvas(self, art_key, canvas):
        if not canvas.winfo_exists():
            return

        width = max(
            20,
            canvas.winfo_width()
        )

        height = max(
            20,
            canvas.winfo_height()
        )

        canvas.delete("all")

        art_path = self.settings.get(
            self._cockpit_art_setting_key(art_key),
            ""
        )

        if not (art_path and Path(art_path).is_file()):
            placeholder_name = PANEL_ART_PLACEHOLDERS.get(art_key)
            if placeholder_name:
                placeholder_path = (
                    Path(__file__).resolve().parent
                    / "genesis"
                    / "assets"
                    / "panel_backgrounds"
                    / placeholder_name
                )
                if placeholder_path.is_file():
                    art_path = str(placeholder_path)

        if (
            art_key == "banner"
            and art_path
            and Path(art_path).suffix.lower() in {".mp4", ".mov", ".m4v", ".webm"}
        ):
            if self._start_banner_video(art_path, canvas):
                return

        if art_key == "banner":
            self._stop_banner_video()

        if art_key == "system_logo" and not (
            art_path and Path(art_path).is_file()
        ):
            default_logo = (
                Path(__file__).resolve().parent
                / "genesis"
                / "genesis_cockpit_icon.png"
            )
            if default_logo.is_file():
                art_path = str(default_logo)

        if (
            art_path
            and Path(art_path).is_file()
        ):
            try:
                source = Image.open(
                    art_path
                ).convert("RGB")

                options = self._get_art_options(
                    art_key
                )

                image_w = max(
                    1,
                    source.width
                )

                image_h = max(
                    1,
                    source.height
                )

                if options["fit"] == "Contain":
                    base_scale = min(
                        width / image_w,
                        height / image_h
                    )
                else:
                    base_scale = max(
                        width / image_w,
                        height / image_h
                    )

                final_scale = (
                    base_scale
                    * options["zoom"]
                )

                new_w = max(
                    1,
                    int(
                        image_w
                        * final_scale
                    )
                )

                new_h = max(
                    1,
                    int(
                        image_h
                        * final_scale
                    )
                )

                resized = source.resize(
                    (new_w, new_h),
                    Image.Resampling.LANCZOS
                )

                xpos = (
                    options["x"]
                    / 100.0
                )

                ypos = (
                    options["y"]
                    / 100.0
                )

                if new_w >= width:
                    x = -int(
                        (new_w - width)
                        * xpos
                    )
                else:
                    x = int(
                        (width - new_w)
                        * xpos
                    )

                if new_h >= height:
                    y = -int(
                        (new_h - height)
                        * ypos
                    )
                else:
                    y = int(
                        (height - new_h)
                        * ypos
                    )

                background = Image.new(
                    "RGB",
                    (width, height),
                    "#05070b"
                )

                background.paste(
                    resized,
                    (x, y)
                )

                # Keep controls and labels legible over every placeholder while
                # retaining enough artwork detail to identify each workspace.
                overlay_strength = (
                    0.66 if art_key == "banner"
                    else 0.20 if art_key == "system_logo"
                    else 0.64
                )
                background = Image.blend(
                    background,
                    Image.new("RGB", background.size, "#050505"),
                    overlay_strength
                )

                tkimg = ImageTk.PhotoImage(
                    background
                )

                canvas.create_image(
                    0,
                    0,
                    image=tkimg,
                    anchor="nw"
                )

                self.art_images[
                    art_key
                ] = tkimg

                if art_key == "banner":
                    self._draw_banner_title(canvas, width, height)
                elif art_key.startswith("workspace_"):
                    self._draw_workspace_backdrop_overlay(
                        art_key, canvas, width, height
                    )
                else:
                    self._draw_home_card_overlay(
                        art_key, canvas, width, height
                    )

                return

            except Exception as e:
                print(
                    "GENESIS ART ERROR",
                    art_key,
                    e
                )

        canvas.configure(
            bg="#101010"
        )

        is_home_card = art_key in getattr(self, "home_card_metadata", {})

        # Generic border / art placeholder belongs to editing surfaces,
        # not the finished Cockpit Home cards.
        if not is_home_card:
            canvas.create_rectangle(
                1,
                1,
                width - 2,
                height - 2,
                outline="#3a3a3a"
            )

            placeholder_y = height // 2 - 8

            canvas.create_text(
                width // 2,
                placeholder_y,
                text="GENESIS",
                fill="#574729",
                font=("DejaVu Sans", 14, "bold")
            )

            canvas.create_text(
                width // 2,
                placeholder_y + 24,
                text="DOUBLE-CLICK TO SET ART",
                fill="#8a7445",
                font=("DejaVu Sans", 7, "bold")
            )

        if art_key.startswith("workspace_"):
            self._draw_workspace_backdrop_overlay(
                art_key, canvas, width, height
            )
        else:
            self._draw_home_card_overlay(
                art_key, canvas, width, height
            )

    def _stop_banner_video(self):
        if self.banner_video_job:
            try:
                self.after_cancel(self.banner_video_job)
            except Exception:
                pass
            self.banner_video_job = None
        if self.banner_video_capture is not None:
            try:
                self.banner_video_capture.release()
            except Exception:
                pass
            self.banner_video_capture = None
        if self.banner_secondary_capture is not None:
            try:
                self.banner_secondary_capture.release()
            except Exception:
                pass
            self.banner_secondary_capture = None
        self.banner_video_path = None

    def destroy(self):
        self._stop_banner_video()
        if self.splash_video_job:
            try:
                self.after_cancel(self.splash_video_job)
            except Exception:
                pass
            self.splash_video_job = None
        if self.splash_video_capture is not None:
            try:
                self.splash_video_capture.release()
            except Exception:
                pass
            self.splash_video_capture = None
        if self.splash_secondary_capture is not None:
            try:
                self.splash_secondary_capture.release()
            except Exception:
                pass
            self.splash_secondary_capture = None
        super().destroy()

    def _secondary_banner_video_path(self):
        return (
            Path(__file__).resolve().parent
            / "genesis"
            / "assets"
            / "panel_backgrounds"
            / "genesis-cockpit-banner-secondary.mp4"
        )

    def _start_banner_video(self, video_path, canvas):
        if cv2 is None:
            print("GENESIS BANNER VIDEO: OpenCV unavailable; using placeholder")
            return False
        if (
            self.banner_video_capture is not None
            and self.banner_video_path == str(video_path)
            and self.banner_video_job
        ):
            return True

        self._stop_banner_video()
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            capture.release()
            print("GENESIS BANNER VIDEO: could not open", video_path)
            return False

        self.banner_video_capture = capture
        secondary_path = self._secondary_banner_video_path()
        secondary_capture = cv2.VideoCapture(str(secondary_path))
        if secondary_path.is_file() and secondary_capture.isOpened():
            self.banner_secondary_capture = secondary_capture
        else:
            secondary_capture.release()
        self.banner_video_path = str(video_path)
        source_fps = capture.get(cv2.CAP_PROP_FPS) or 24.0
        frame_step = max(1, int(round(source_fps / 24.0)))
        self._banner_video_tick(canvas, frame_step)
        return True

    def _banner_video_tick(self, canvas, frame_step):
        capture = self.banner_video_capture
        if capture is None or not canvas.winfo_exists():
            self._stop_banner_video()
            return

        ok, frame = capture.read()
        if not ok:
            capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = capture.read()
        if not ok:
            self._stop_banner_video()
            return

        for _ in range(frame_step - 1):
            if not capture.grab():
                capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                break

        width = max(20, canvas.winfo_width())
        height = max(20, canvas.winfo_height())
        source = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        secondary = None
        if self.banner_secondary_capture is not None:
            ok_secondary, secondary_frame = self.banner_secondary_capture.read()
            if not ok_secondary:
                self.banner_secondary_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok_secondary, secondary_frame = self.banner_secondary_capture.read()
            if ok_secondary:
                for _ in range(frame_step - 1):
                    if not self.banner_secondary_capture.grab():
                        self.banner_secondary_capture.set(
                            cv2.CAP_PROP_POS_FRAMES, 0
                        )
                        break
                secondary = Image.fromarray(
                    cv2.cvtColor(secondary_frame, cv2.COLOR_BGR2RGB)
                )
        composed = self._compose_video_banner(
            source, width, height, secondary
        )
        tkimg = ImageTk.PhotoImage(composed)

        canvas.delete("all")
        canvas.create_image(0, 0, image=tkimg, anchor="nw")
        self.art_images["banner"] = tkimg
        self._draw_banner_title(canvas, width, height)
        self.banner_video_job = self.after(
            83,
            lambda: self._banner_video_tick(canvas, frame_step)
        )

    def _compose_video_banner(self, source, width, height, secondary=None):
        sources = [source]
        if secondary is not None:
            sources.append(secondary)

        # Each clip contributes to the soft, dark widescreen backdrop.
        background = Image.new("RGB", (width, height), "#050505")
        segment_width = max(1, width // len(sources))
        for index, frame in enumerate(sources):
            cover_scale = max(segment_width / frame.width, height / frame.height)
            cover = frame.resize(
                (max(1, int(frame.width * cover_scale)),
                 max(1, int(frame.height * cover_scale))),
                Image.Resampling.LANCZOS,
            )
            left = max(0, (cover.width - segment_width) // 2)
            top = max(0, int((cover.height - height) * 0.22))
            panel = cover.crop(
                (left, top, left + segment_width, top + height)
            )
            background.paste(panel, (index * segment_width, 0))

        background = background.filter(ImageFilter.GaussianBlur(radius=18))
        background = Image.blend(
            background,
            Image.new("RGB", background.size, "#050505"),
            0.58,
        )

        # Keep both portrait videos uncropped and visibly separate on the right.
        portrait_height = height if width / height >= 4.0 else int(height * 0.86)
        centres = (0.13, 0.87) if len(sources) > 1 else (0.73,)
        if width / height < 4.0:
            centres = (0.20, 0.80) if len(sources) > 1 else (0.72,)
        for frame, centre in zip(sources, centres):
            scale = portrait_height / frame.height
            portrait = frame.resize(
                (max(1, int(frame.width * scale)), portrait_height),
                Image.Resampling.LANCZOS,
            )
            portrait_x = max(0, int(width * centre - portrait.width / 2))
            portrait_y = max(0, (height - portrait.height) // 2)
            mask = Image.new("L", portrait.size, 255)
            mask = mask.filter(ImageFilter.GaussianBlur(radius=5))
            background.paste(portrait, (portrait_x, portrait_y), mask)

        # Preserve strong readability for the title area without hiding video.
        shade = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        alpha_strip = Image.new("L", (width, 1))
        alpha_strip.putdata([
            int(max(0, 150 * (1.0 - x / max(1, width * 0.62))))
            for x in range(width)
        ])
        shade.putalpha(alpha_strip.resize((width, height)))
        composed = background.convert("RGBA")
        composed.alpha_composite(shade)
        return composed.convert("RGB")

    def _draw_banner_title(self, canvas, width, height):
        x = int(width * 0.50)
        y = int(height * 0.43)

        # Strong dark shadow behind the GENESIS wordmark.
        canvas.create_text(
            x + 3, y + 3,
            text="GENESIS",
            anchor="center",
            fill="#000000",
            font=(DISPLAY_FONT, 42, "bold"),
        )

        # Subtle warm-gold halo/outline.
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            canvas.create_text(
                x + dx, y + dy,
                text="GENESIS",
                anchor="center",
                fill="#8f711e",
                font=(DISPLAY_FONT, 42, "bold"),
            )

        # Main bright gold wordmark.
        canvas.create_text(
            x, y,
            text="GENESIS",
            anchor="center",
            fill="#f2c94c",
            font=(DISPLAY_FONT, 42, "bold"),
        )

        # Stronger ivory subtitle.
        canvas.create_text(
            x + 1, y + 41,
            text="COCKPIT",
            anchor="center",
            fill="#000000",
            font=(DISPLAY_FONT, 20, "bold"),
        )
        canvas.create_text(
            x, y + 40,
            text="COCKPIT",
            anchor="center",
            fill="#fff4df",
            font=(DISPLAY_FONT, 20, "bold"),
        )

        # Brighter signature line.
        canvas.create_text(
            x, y + 70,
            text="Keep walking, Allan.",
            anchor="center",
            fill="#e6cc8a",
            font=("Z003", 16, "italic"),
        )

    def _begin_genesis_startup(self):
        """Launch splash independently so cockpit construction cannot freeze it."""
        self._startup_splash_process = None

        try:
            root = Path(__file__).resolve().parent

            video_path = (
                root
                / "genesis"
                / "assets"
                / "panel_backgrounds"
                / PANEL_ART_PLACEHOLDERS["banner"]
            )

            splash_script = root / "genesis_startup_splash.py"
            splash_python = root / ".venv" / "bin" / "python"

            args = [
                str(splash_python),
                str(splash_script),
                str(video_path),
            ]

            try:
                secondary_path = self._secondary_banner_video_path()
                if secondary_path and Path(secondary_path).is_file():
                    args.append(str(secondary_path))
            except Exception:
                pass

            self._startup_splash_process = subprocess.Popen(
                args,
                cwd=str(root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

        except Exception as exc:
            print("GENESIS SPLASH:", exc)

        # Give the independent splash just enough time to map its window.
        self.after(120, self._build_genesis_after_splash)

    def _finish_external_splash(self):
        process = getattr(
            self,
            "_startup_splash_process",
            None,
        )

        if process is None:
            return

        self._startup_splash_process = None

        try:
            if process.poll() is None:
                process.terminate()

                try:
                    process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    process.kill()
        except Exception:
            pass

    def _build_genesis_after_splash(self):
        try:
            self._build()

        except Exception:
            self._finish_external_splash()
            self.deiconify()
            raise

        # Draw Genesis underneath the still-running splash first.
        self.deiconify()
        self.lift()
        self.focus_force()

        # Then remove splash once cockpit has had a chance to paint.
        self.after(
            180,
            self._finish_external_splash,
        )

        self.after(
            220,
            self._refresh_all_cockpit_art,
        )

    def _show_startup_splash(self):
        video_path = (
            Path(__file__).resolve().parent
            / "genesis"
            / "assets"
            / "panel_backgrounds"
            / PANEL_ART_PLACEHOLDERS["banner"]
        )

        splash = tk.Toplevel(self)
        splash.overrideredirect(True)
        splash.configure(bg="#050505")
        splash.attributes("-topmost", True)

        screen_w = splash.winfo_screenwidth()
        screen_h = splash.winfo_screenheight()
        # Smaller splash = substantially cheaper video scaling/compositing.
        width = min(820, max(680, int(screen_w * 0.52)))
        height = min(480, max(400, int(screen_h * 0.48)))
        left = max(0, (screen_w - width) // 2)
        top = max(0, (screen_h - height) // 2)
        splash.geometry(f"{width}x{height}+{left}+{top}")

        canvas = tk.Canvas(
            splash,
            width=width,
            height=height,
            bg="#050505",
            highlightthickness=1,
            highlightbackground="#8a6d1d",
        )
        canvas.pack(fill="both", expand=True)

        started = time.monotonic()

        def finish(_event=None):
            if not splash.winfo_exists():
                return
            if self.splash_video_job:
                try:
                    self.after_cancel(self.splash_video_job)
                except Exception:
                    pass
                self.splash_video_job = None
            if self.splash_video_capture is not None:
                try:
                    self.splash_video_capture.release()
                except Exception:
                    pass
                self.splash_video_capture = None
            if self.splash_secondary_capture is not None:
                try:
                    self.splash_secondary_capture.release()
                except Exception:
                    pass
                self.splash_secondary_capture = None
            splash.destroy()
            self.deiconify()
            self.lift()
            self.focus_force()
            self.after(80, self._refresh_all_cockpit_art)

        splash.bind("<Escape>", finish)
        splash.bind("<Button-1>", finish)

        if cv2 is not None and video_path.is_file():
            capture = cv2.VideoCapture(str(video_path))
            if capture.isOpened():
                self.splash_video_capture = capture
                secondary_path = self._secondary_banner_video_path()
                secondary_capture = cv2.VideoCapture(str(secondary_path))
                if secondary_path.is_file() and secondary_capture.isOpened():
                    self.splash_secondary_capture = secondary_capture
                else:
                    secondary_capture.release()
                source_fps = capture.get(cv2.CAP_PROP_FPS) or 24.0
                frame_step = max(1, int(round(source_fps / 12.0)))

                def tick():
                    if not splash.winfo_exists():
                        return
                    if time.monotonic() - started >= 6.0:
                        finish()
                        return

                    ok, frame = capture.read()
                    if not ok:
                        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ok, frame = capture.read()
                    if not ok:
                        finish()
                        return

                    for _ in range(frame_step - 1):
                        if not capture.grab():
                            capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            break

                    source = Image.fromarray(
                        cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    )
                    secondary = None
                    if self.splash_secondary_capture is not None:
                        ok_secondary, secondary_frame = (
                            self.splash_secondary_capture.read()
                        )
                        if not ok_secondary:
                            self.splash_secondary_capture.set(
                                cv2.CAP_PROP_POS_FRAMES, 0
                            )
                            ok_secondary, secondary_frame = (
                                self.splash_secondary_capture.read()
                            )
                        if ok_secondary:
                            for _ in range(frame_step - 1):
                                if not self.splash_secondary_capture.grab():
                                    self.splash_secondary_capture.set(
                                        cv2.CAP_PROP_POS_FRAMES, 0
                                    )
                                    break
                            secondary = Image.fromarray(
                                cv2.cvtColor(
                                    secondary_frame, cv2.COLOR_BGR2RGB
                                )
                            )
                    composed = self._compose_video_banner(
                        source, width, height, secondary
                    )
                    tkimg = ImageTk.PhotoImage(composed)
                    canvas.delete("all")
                    canvas.create_image(0, 0, image=tkimg, anchor="nw")
                    canvas.image = tkimg
                    self._draw_splash_title(canvas, width, height)

                    elapsed = min(1.0, (time.monotonic() - started) / 6.0)
                    canvas.create_rectangle(
                        0, height - 4, int(width * elapsed), height,
                        fill="#d4af37", outline="",
                    )
                    self.splash_video_job = self.after(42, tick)

                tick()
                return
            capture.release()

        self._draw_splash_title(canvas, width, height)
        self.splash_video_job = self.after(1800, finish)

    def _draw_splash_title(self, canvas, width, height):
        x = int(width * 0.50)
        y = int(height * 0.42)
        canvas.create_text(
            x + 3, y + 3,
            text="GENESIS",
            anchor="center",
            fill="#000000",
            font=(DISPLAY_FONT, 52, "bold"),
        )
        canvas.create_text(
            x, y,
            text="GENESIS",
            anchor="center",
            fill="#d4af37",
            font=(DISPLAY_FONT, 52, "bold"),
        )
        canvas.create_text(
            x, y + 58,
            text="COCKPIT",
            anchor="center",
            fill="#f4ead5",
            font=(DISPLAY_FONT, 25, "bold"),
        )
        canvas.create_text(
            x, y + 100,
            text="Keep walking, Allan.",
            anchor="center",
            fill="#d8c49a",
            font=("Z003", 21, "italic"),
        )
        canvas.create_text(
            width - 26, height - 20,
            text="CLICK TO ENTER",
            anchor="e",
            fill="#8d826e",
            font=("DejaVu Sans", 8, "bold"),
        )

    def _refresh_all_cockpit_art(self):
        if hasattr(
            self,
            "home_banner_canvas"
        ):
            self._render_art_canvas(
                "banner",
                self.home_banner_canvas
            )

        if hasattr(
            self,
            "system_art_canvas"
        ):
            self._render_art_canvas(
                "system_logo",
                self.system_art_canvas
            )

        for art_key, canvas in getattr(
            self,
            "home_card_canvases",
            {}
        ).items():
            self._render_art_canvas(
                art_key,
                canvas
            )

        for art_key, canvas in getattr(
            self, "workspace_art_canvases", {}
        ).items():
            self._render_art_canvas(art_key, canvas)


    def _organiser_ui(self):
        # ============================================================
        # INTEGRATED PHOTO ORGANIZER MODE BAR
        # ============================================================
        self.organizer_mode_buttons = {}

        mode_bar = tk.Frame(
            self.tab_org,
            bg="#090909",
            highlightthickness=1,
            highlightbackground="#4a4028"
        )
        mode_bar.pack(fill="x", padx=8, pady=(6, 6))

        tk.Label(
            mode_bar,
            text="PHOTO ORGANIZER",
            bg="#090909",
            fg="#d4af37",
            font=("DejaVu Sans", 10, "bold")
        ).pack(side="left", padx=(12, 18), pady=9)

        modes = (
            ("library", "▣  LIBRARY"),
            ("editor", "✎  VIEWER / EDITOR"),
            ("duplicates", "≋  DUPLICATES"),
            ("people", "◎  PEOPLE / FACES"),
        )

        for key, label in modes:
            btn = tk.Button(
                mode_bar,
                text=label,
                command=lambda k=key: self._show_organizer_mode(k),
                bg="#17130a",
                fg="#d4af37",
                activebackground="#d4af37",
                activeforeground="#050505",
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground="#57471f",
                highlightcolor="#d4af37",
                padx=14,
                pady=8,
                font=("DejaVu Sans Condensed", 9, "bold"),
                cursor="hand2"
            )
            btn.pack(side="left", padx=4, pady=7)
            self.organizer_mode_buttons[key] = btn

        self.org_mode_host = ttk.Frame(self.tab_org)
        self.org_mode_host.pack(fill="both", expand=True)

        self.org_library_frame = ttk.Frame(self.org_mode_host)
        self.org_editor_frame = tk.Frame(self.org_mode_host, bg="#050505")
        self.org_duplicates_frame = tk.Frame(self.org_mode_host, bg="#050505")
        self.org_people_frame = tk.Frame(self.org_mode_host, bg="#050505")

        self._workspace_heading(
            self.org_library_frame,
            "Asset workspace",
            "PHOTO ORGANIZER",
            "Review, select, compare and hand images to the Genesis editing tools.",
        )
        # ====================================================
        # TOP ACTION BAR
        # ====================================================
        bar = ttk.Frame(self.org_library_frame)
        bar.pack(fill="x", pady=(6, 2))

        ttk.Button(
            bar,
            text="Scan Folder",
            command=self.scan_folder
        ).pack(side="left", padx=4)

        ttk.Button(
            bar,
            text="Open in Viewer / Editor",
            command=self.open_current_in_editor
        ).pack(side="left", padx=4)

        ttk.Button(
            bar,
            text="Duplicate Lab",
            command=self.open_duplicate_lab
        ).pack(side="left", padx=4)

        ttk.Button(
            bar,
            text="Find Exact Duplicates",
            command=self.find_exact
        ).pack(side="left", padx=4)

        ttk.Button(
            bar,
            text="Find Near Duplicates",
            command=self.find_near
        ).pack(side="left", padx=4)

        ttk.Button(
            bar,
            text="Rename Selected",
            command=self.rename_selected
        ).pack(side="left", padx=4)

        ttk.Button(
            bar,
            text="Copy Selected to Group Folder",
            command=self.copy_selected
        ).pack(side="left", padx=4)

        # ====================================================
        # SELECTION / ART BAR
        # ====================================================
        selectbar = ttk.Frame(self.org_library_frame)
        selectbar.pack(fill="x", pady=(2, 6))

        ttk.Button(
            selectbar,
            text="Browse Images",
            command=self.browse_photo_images
        ).pack(side="left", padx=4)

        ttk.Button(
            selectbar,
            text="✓ Select All",
            command=self._select_all_files
        ).pack(side="left", padx=4)

        ttk.Button(
            selectbar,
            text="✕ Clear Selection",
            command=self._clear_all_files
        ).pack(side="left", padx=4)

        self.selected_count_label = ttk.Label(
            selectbar,
            text="0 selected"
        )
        self.selected_count_label.pack(side="left", padx=12)

        ttk.Button(
            selectbar,
            text="Set Left Art",
            command=lambda: self._set_organiser_art("left")
        ).pack(side="right", padx=4)

        ttk.Button(
            selectbar,
            text="Set Right Art",
            command=lambda: self._set_organiser_art("right")
        ).pack(side="right", padx=4)

        # ====================================================
        # THREE-COLUMN MASTER LAYOUT
        #
        # [ LEFT ART ] [ WORKSPACE ] [ RIGHT ART ]
        # ====================================================
        body = ttk.Frame(self.org_library_frame)
        body.pack(fill="both", expand=True)

        self.organiser_left_panel = tk.Frame(
            body,
            width=180,
            bg="#101010"
        )
        self.organiser_left_panel.pack(
            side="left",
            fill="y",
            padx=(4, 4),
            pady=4
        )
        self.organiser_left_panel.pack_propagate(False)

        workspace = ttk.Frame(body)
        workspace.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.organiser_right_panel = tk.Frame(
            body,
            width=180,
            bg="#101010"
        )
        self.organiser_right_panel.pack(
            side="right",
            fill="y",
            padx=(4, 4),
            pady=4
        )
        self.organiser_right_panel.pack_propagate(False)

        self.organiser_left_art = tk.Label(
            self.organiser_left_panel,
            text="LEFT ART",
            fg="white",
            bg="#101010",
            anchor="center"
        )
        self.organiser_left_art.pack(
            fill="both",
            expand=True
        )

        self.organiser_right_art = tk.Label(
            self.organiser_right_panel,
            text="RIGHT ART",
            fg="white",
            bg="#101010",
            anchor="center"
        )
        self.organiser_right_art.pack(
            fill="both",
            expand=True
        )

        # ====================================================
        # WORKSPACE
        #
        # [ CHECKBOX LIST ] | [ LARGE PREVIEW ]
        # ====================================================
        pw = ttk.Panedwindow(
            workspace,
            orient="horizontal"
        )
        pw.pack(fill="both", expand=True)

        left = ttk.Frame(pw)
        right = ttk.Frame(pw)

        pw.add(left, weight=1)
        pw.add(right, weight=2)

        # ====================================================
        # CHECKBOX FILE LIST
        # ====================================================
        ttk.Label(
            left,
            text="Photos",
            font=("DejaVu Sans", 11, "bold")
        ).pack(
            anchor="w",
            padx=6,
            pady=(4, 2)
        )

        list_holder = ttk.Frame(left)
        list_holder.pack(
            fill="both",
            expand=True,
            padx=4,
            pady=4
        )

        self.file_canvas = tk.Canvas(
            list_holder,
            highlightthickness=0
        )

        file_scroll = ttk.Scrollbar(
            list_holder,
            orient="vertical",
            command=self.file_canvas.yview
        )

        self.file_canvas.configure(
            yscrollcommand=file_scroll.set
        )

        file_scroll.pack(
            side="right",
            fill="y"
        )

        self.file_canvas.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.file_check_frame = ttk.Frame(
            self.file_canvas
        )

        self.file_check_window = self.file_canvas.create_window(
            (0, 0),
            window=self.file_check_frame,
            anchor="nw"
        )

        def update_scrollregion(_event=None):
            self.file_canvas.configure(
                scrollregion=self.file_canvas.bbox("all")
            )

        def resize_check_frame(event):
            self.file_canvas.itemconfigure(
                self.file_check_window,
                width=event.width
            )

        self.file_check_frame.bind(
            "<Configure>",
            update_scrollregion
        )

        self.file_canvas.bind(
            "<Configure>",
            resize_check_frame
        )

        # Mouse wheel scrolling
        self.file_canvas.bind(
            "<Enter>",
            lambda _e: self.bind_all(
                "<MouseWheel>",
                self._organiser_mousewheel
            )
        )

        self.file_canvas.bind(
            "<Leave>",
            lambda _e: self.unbind_all(
                "<MouseWheel>"
            )
        )

        self.file_vars = {}
        self.file_checks = {}

        # ====================================================
        # PREVIEW
        # ====================================================
        self.preview = ttk.Label(
            right,
            anchor="center"
        )
        self.preview.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        self.info = ttk.Label(
            right,
            text="",
            justify="left",
            wraplength=760
        )
        self.info.pack(
            fill="x",
            padx=10,
            pady=4
        )

        # ====================================================
        # LOAD SAVED SIDE ART
        # ====================================================
        self.after(
            150,
            self._load_organiser_art
        )




        # ------------------------------------------------------------
        # Embedded Viewer / Editor
        # ------------------------------------------------------------
        try:
            from genesis.image_editor import build_editor_panel
            self.embedded_image_editor = build_editor_panel(
                self.org_editor_frame
            )
        except Exception as exc:
            self.embedded_image_editor = None
            tk.Label(
                self.org_editor_frame,
                text=f"Viewer / Editor could not load\n\n{exc}",
                bg="#050505",
                fg="#d16a6a",
                font=("DejaVu Sans", 11, "bold")
            ).pack(expand=True)

        # ------------------------------------------------------------
        # Embedded Duplicate Lab
        # ------------------------------------------------------------
        try:
            from genesis.duplicate_lab import build_duplicate_lab
            initial = self.settings.get("recent_photo_project")
            self.embedded_duplicate_lab = build_duplicate_lab(
                self.org_duplicates_frame,
                initial
            )
        except Exception as exc:
            self.embedded_duplicate_lab = None
            tk.Label(
                self.org_duplicates_frame,
                text=f"Duplicate Lab could not load\n\n{exc}",
                bg="#050505",
                fg="#d16a6a",
                font=("DejaVu Sans", 11, "bold")
            ).pack(expand=True)

        # ------------------------------------------------------------
        # People / Faces foundation
        # ------------------------------------------------------------
        people_header = tk.Frame(
            self.org_people_frame,
            bg="#0c0c0d",
            highlightthickness=1,
            highlightbackground="#4a4028"
        )
        people_header.pack(fill="x", padx=12, pady=(12, 8))

        tk.Label(
            people_header,
            text="PEOPLE / FACES",
            bg="#0c0c0d",
            fg="#d4af37",
            font=("DejaVu Sans", 16, "bold")
        ).pack(anchor="w", padx=14, pady=(12, 3))

        tk.Label(
            people_header,
            text="Face grouping and people organization workspace.",
            bg="#0c0c0d",
            fg="#aaa39a",
            font=("DejaVu Sans", 9)
        ).pack(anchor="w", padx=14, pady=(0, 12))

        tk.Label(
            self.org_people_frame,
            text=(
                "PEOPLE / FACES\n\n"
                "This workspace is ready for the face-indexing stage.\n"
                "Photo organization stays separate from generation face-swap tools."
            ),
            bg="#050505",
            fg="#aaa39a",
            justify="center",
            font=("DejaVu Sans", 11, "bold")
        ).pack(expand=True)

        self._show_organizer_mode("library")


    def _show_organizer_mode(self, mode):
        frames = {
            "library": self.org_library_frame,
            "editor": self.org_editor_frame,
            "duplicates": self.org_duplicates_frame,
            "people": self.org_people_frame,
        }

        if mode not in frames:
            mode = "library"

        for frame in frames.values():
            frame.pack_forget()

        frames[mode].pack(fill="both", expand=True)

        for key, button in self.organizer_mode_buttons.items():
            if key == mode:
                button.configure(
                    bg="#d4af37",
                    fg="#050505",
                    activebackground="#e4c45a",
                    activeforeground="#050505",
                    highlightbackground="#d4af37"
                )
            else:
                button.configure(
                    bg="#17130a",
                    fg="#d4af37",
                    activebackground="#2a210d",
                    activeforeground="#f4efe6",
                    highlightbackground="#57471f"
                )

        labels = {
            "library": "Photo Organizer · Library",
            "editor": "Photo Organizer · Viewer / Editor",
            "duplicates": "Photo Organizer · Duplicate Review",
            "people": "Photo Organizer · People / Faces",
        }

        try:
            self.status.config(text=labels[mode])
        except Exception:
            pass


    def _organiser_mousewheel(self, event):
        if event.delta:
            self.file_canvas.yview_scroll(
                int(-1 * (event.delta / 120)),
                "units"
            )


    def _organiser_assets_dir(self):
        assets = Path(__file__).resolve().parent / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        return assets


    def _set_organiser_art(self, side):
        src = genesis_pick_file(
            f"Choose {side} organiser artwork",
            remember_key=f"organiser_{side}_art"
        )

        if not src:
            return

        try:
            im = Image.open(src).convert("RGB")

            assets = self._organiser_assets_dir()

            if side == "left":
                dest = assets / "organiser_left.png"
            else:
                dest = assets / "organiser_right.png"

            im.save(dest, "PNG", quality=95)

            self._load_organiser_art()

            self.status.config(
                text=f"{side.title()} artwork updated"
            )

        except Exception as e:
            messagebox.showerror(
                APP_NAME,
                f"Could not load artwork:\n{e}"
            )


    def _render_side_art(self, path, label):
        if not path.exists():
            label.configure(
                image="",
                text="No artwork set"
            )
            return

        try:
            im = Image.open(path).convert("RGB")

            # Portrait-style side panel.
            target_w = 176
            target_h = max(
                self.winfo_height() - 190,
                500
            )

            ratio = min(
                target_w / im.width,
                target_h / im.height
            )

            new_w = max(1, int(im.width * ratio))
            new_h = max(1, int(im.height * ratio))

            im = im.resize(
                (new_w, new_h),
                Image.LANCZOS
            )

            tkimg = ImageTk.PhotoImage(im)

            label.configure(
                image=tkimg,
                text=""
            )

            label.image = tkimg

        except Exception as e:
            label.configure(
                image="",
                text=f"Artwork error\n{e}"
            )


    def _load_organiser_art(self):
        assets = self._organiser_assets_dir()

        self._render_side_art(
            assets / "organiser_left.png",
            self.organiser_left_art
        )

        self._render_side_art(
            assets / "organiser_right.png",
            self.organiser_right_art
        )


    def _populate_file_checks(self):
        for child in self.file_check_frame.winfo_children():
            child.destroy()

        self.file_vars = {}
        self.file_checks = {}

        for index, p in enumerate(self.files):
            var = tk.BooleanVar(value=False)

            self.file_vars[str(p)] = var

            row = tk.Frame(
                self.file_check_frame,
                bd=0,
                highlightthickness=0
            )

            row.pack(
                fill="x",
                padx=2,
                pady=1
            )

            cb = tk.Checkbutton(
                row,
                variable=var,
                anchor="w",
                padx=4,
                command=lambda path=p: self._file_check_clicked(path)
            )

            cb.pack(
                side="left",
                padx=(2, 0)
            )

            filename = tk.Label(
                row,
                text=p.name,
                anchor="w",
                justify="left",
                cursor="hand2"
            )

            filename.pack(
                side="left",
                fill="x",
                expand=True,
                padx=(3, 6),
                pady=3
            )

            filename.bind(
                "<Button-1>",
                lambda _e, path=p: self._preview_path(path)
            )

            filename.bind(
                "<Double-Button-1>",
                lambda _e, path=p: self._toggle_file_from_name(path)
            )

            self.file_checks[str(p)] = cb

        self._update_selected_count()

        if self.files:
            self._preview_path(self.files[0])


    def _toggle_file_from_name(self, path):
        key = str(path)

        if key not in self.file_vars:
            return

        self.file_vars[key].set(
            not self.file_vars[key].get()
        )

        self._file_check_clicked(path)


    def _file_check_clicked(self, path):
        self._preview_path(path)
        self._update_selected_count()


    def _select_all_files(self):
        for var in self.file_vars.values():
            var.set(True)

        self._update_selected_count()


    def _clear_all_files(self):
        for var in self.file_vars.values():
            var.set(False)

        self._update_selected_count()


    def _update_selected_count(self):
        count = sum(
            1
            for var in self.file_vars.values()
            if var.get()
        )

        if hasattr(self, "selected_count_label"):
            self.selected_count_label.configure(
                text=f"{count} selected"
            )


    def _preview_path(self, p):
        p = Path(p)

        try:
            im = Image.open(p).convert("RGB")

            w, h = im.size

            im.thumbnail(
                (850, 650),
                Image.LANCZOS
            )

            tkimg = ImageTk.PhotoImage(im)

            self.preview.configure(
                image=tkimg
            )

            self.preview.image = tkimg

            self.info.config(
                text=(
                    f"{p.name}\n"
                    f"{w} × {h}\n"
                    f"{p}"
                )
            )

            self.current_path = p

        except Exception as e:
            self.info.config(
                text=str(e)
            )

    def browse_photo_images(self):
        """Explicit visual selection; cancelling leaves the current workspace alone."""
        from genesis.visual_browser import pick_images
        folder = self.settings.get("recent_photo_project")
        selected = pick_images(self, initial_folder=folder, multiple=False)
        if selected:
            self.open_image_editor(selected[0])

    def open_current_in_editor(self):
        if not self.current_path or not Path(self.current_path).is_file():
            messagebox.showinfo(APP_NAME, "Select a photo first.")
            return
        self.open_image_editor(self.current_path)


    def scan_folder(self):
        d = genesis_pick_folder(
            "Choose photo folder",
            remember_key="photo_input"
        )

        if not d:
            return

        self._remember_photo_project(d)

        self.status.config(
            text="Scanning..."
        )

        self.update_idletasks()

        self.files = [
            p for p in Path(d).rglob("*")
            if p.is_file()
            and p.suffix.lower() in SUPPORTED
        ]

        self.files.sort(
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        self._populate_file_checks()

        self.status.config(
            text=f"{len(self.files)} photos loaded"
        )


    def preview_selected(self, *_):
        paths = self._selected_paths()

        if paths:
            self._preview_path(paths[0])
        elif self.files:
            self._preview_path(self.files[0])


    def _selected_paths(self):
        selected = []

        for p in self.files:
            var = self.file_vars.get(str(p))

            if var is not None and var.get():
                selected.append(Path(p))

        return selected


    def rename_selected(self):
        paths = self._selected_paths()
        if not paths:
            messagebox.showinfo(APP_NAME, "Select one or more photos first."); return
        base = simpledialog.askstring(APP_NAME, "Base name (example: Lorraine):")
        if not base: return
        if not messagebox.askyesno(APP_NAME, f"Rename {len(paths)} selected files to {base}_001 etc?"):
            return
        for n,p in enumerate(paths,1):
            new = p.with_name(f"{base}_{n:03d}{p.suffix.lower()}")
            k=1
            while new.exists() and new != p:
                new = p.with_name(f"{base}_{n:03d}_{k}{p.suffix.lower()}"); k+=1
            p.rename(new)
        self.scan_folder_again(self.settings.get("recent_photo_project") or paths[0].parent)

    def scan_folder_again(self, d):
        self._remember_photo_project(d)
        self.files = [
            p for p in Path(d).rglob("*")
            if p.is_file()
            and p.suffix.lower() in SUPPORTED
        ]

        self.files.sort(
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        self._populate_file_checks()

        self.status.config(
            text=f"{len(self.files)} photos loaded"
        )

    def _remember_photo_project(self, path):
        self.settings["recent_photo_project"] = str(path)
        save_settings(self.settings)
        if hasattr(self, "home_recent_label"):
            self.home_recent_label.config(text=self._recent_project_text())


    def copy_selected(self):
        paths = self._selected_paths()
        if not paths:
            messagebox.showinfo(APP_NAME, "Select photos first."); return
        dest = genesis_pick_folder("Choose destination root folder", remember_key="destination")
        if not dest: return
        group = simpledialog.askstring(APP_NAME, "Group folder name:", initialvalue="Person_01")
        if not group: return
        out = Path(dest)/group; out.mkdir(parents=True, exist_ok=True)
        for p in paths:
            target = out/p.name
            if target.exists():
                stem, suf = p.stem, p.suffix
                i=1
                while (out/f"{stem}_{i}{suf}").exists(): i+=1
                target = out/f"{stem}_{i}{suf}"
            shutil.copy2(p,target)
        messagebox.showinfo(APP_NAME, f"Copied {len(paths)} photos to:\n{out}")

    def find_exact(self):
        if not self.files:
            messagebox.showinfo(APP_NAME, "Scan a photo folder first.")
            return
        self.status.config(text="Hashing exact duplicates...")
        def work():
            groups={}
            for p in self.files:
                try:
                    h=hashlib.sha256(p.read_bytes()).hexdigest()
                    groups.setdefault(h,[]).append(p)
                except: pass
            dup=[g for g in groups.values() if len(g)>1]
            self.after(0, lambda: self.show_dup_results("Exact duplicates", dup))
        threading.Thread(target=work,daemon=True).start()

    def find_near(self):
        if not self.files:
            messagebox.showinfo(APP_NAME, "Scan a photo folder first.")
            return
        threshold = simpledialog.askinteger(APP_NAME, "Perceptual hash distance (lower=stricter):", initialvalue=6, minvalue=1,maxvalue=20)
        if threshold is None: return
        self.status.config(text="Finding near duplicates...")
        def work():
            hashes=[]
            for p in self.files:
                try: hashes.append((p,imagehash.phash(Image.open(p).convert("RGB"))))
                except: pass
            groups=[]; used=set()
            for i,(p,h) in enumerate(hashes):
                if i in used: continue
                g=[p]
                for j in range(i+1,len(hashes)):
                    if j in used: continue
                    if h-hashes[j][1] <= threshold:
                        g.append(hashes[j][0]); used.add(j)
                if len(g)>1: groups.append(g)
            self.after(0, lambda: self.show_dup_results("Near duplicates", groups))
        threading.Thread(target=work,daemon=True).start()

    def show_dup_results(self, title, groups):
        self.status.config(text=f"{title}: {len(groups)} groups")
        win=tk.Toplevel(self); win.title(title); win.geometry("950x600")
        txt=tk.Text(win, wrap="none"); txt.pack(fill="both",expand=True)
        if not groups: txt.insert("end","No duplicate groups found.")
        for i,g in enumerate(groups,1):
            txt.insert("end",f"\nGROUP {i}\n")
            for p in g: txt.insert("end",f"  {p}\n")

    def _tools_ui(self):
        self.photo_tools_mode_buttons = {}

        mode_bar = tk.Frame(
            self.tab_tools,
            bg="#090909",
            highlightthickness=1,
            highlightbackground="#4a4028"
        )
        mode_bar.pack(fill="x", padx=8, pady=(6, 6))

        tk.Label(
            mode_bar,
            text="PHOTO TOOLS",
            bg="#090909",
            fg="#d4af37",
            font=("DejaVu Sans", 10, "bold")
        ).pack(side="left", padx=(12, 18), pady=9)

        modes = (
            ("enhance", "✦  ENHANCE / UPSCALE"),
            ("background", "◐  REMOVE BACKGROUND"),
            ("batch", "▤  BATCH PROCESS"),
        )

        for key, label in modes:
            btn = tk.Button(
                mode_bar,
                text=label,
                command=lambda k=key: self._show_photo_tools_mode(k),
                bg="#17130a",
                fg="#d4af37",
                activebackground="#d4af37",
                activeforeground="#050505",
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground="#57471f",
                padx=14,
                pady=8,
                font=("DejaVu Sans Condensed", 9, "bold"),
                cursor="hand2"
            )
            btn.pack(side="left", padx=4, pady=7)
            self.photo_tools_mode_buttons[key] = btn

        self.photo_tools_host = ttk.Frame(self.tab_tools)
        self.photo_tools_host.pack(fill="both", expand=True)

        self.tools_enhance_frame = ttk.Frame(self.photo_tools_host)
        self.tools_bg_frame = ttk.Frame(self.photo_tools_host)
        self.tools_batch_frame = tk.Frame(
            self.photo_tools_host,
            bg="#050505"
        )

        self._workspace_heading(
            self.tools_enhance_frame,
            "Batch processing",
            "ENHANCE / UPSCALE",
            "Apply local resizing and enhancement presets without overwriting originals.",
        )
        top=ttk.Frame(self.tools_enhance_frame); top.pack(fill="x", pady=8)
        ttk.Button(top,text="Choose Images",command=self.choose_tool_files).pack(side="left",padx=4)
        ttk.Label(top,text="Upscale:").pack(side="left",padx=(18,4))
        self.scale_var=tk.StringVar(value="2x")
        ttk.Combobox(top,textvariable=self.scale_var,values=["1x","2x","4x"],width=6,state="readonly").pack(side="left")
        ttk.Label(top,text="Enhance:").pack(side="left",padx=(18,4))
        self.enhance_var=tk.StringVar(value="Balanced")
        ttk.Combobox(top,textvariable=self.enhance_var,values=["None","Balanced","Sharpen","Strong"],width=10,state="readonly").pack(side="left")
        ttk.Button(top,text="Process Batch",command=self.process_batch).pack(side="left",padx=12)
        self.tool_list=tk.Listbox(self.tools_enhance_frame,selectmode="extended"); self.tool_list.pack(fill="both",expand=True,padx=8,pady=8)



        batch_panel = tk.Frame(
            self.tools_batch_frame,
            bg="#0c0c0d",
            highlightthickness=1,
            highlightbackground="#4a4028"
        )
        batch_panel.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20
        )

        tk.Label(
            batch_panel,
            text="BATCH PROCESS",
            bg="#0c0c0d",
            fg="#d4af37",
            font=("DejaVu Sans", 18, "bold")
        ).pack(pady=(35, 8))

        tk.Label(
            batch_panel,
            text=(
                "Choose the batch pipeline you want to run.\n"
                "Original source images remain untouched."
            ),
            bg="#0c0c0d",
            fg="#aaa39a",
            justify="center",
            font=("DejaVu Sans", 10)
        ).pack(pady=(0, 24))

        batch_buttons = tk.Frame(batch_panel, bg="#0c0c0d")
        batch_buttons.pack()

        for label, mode in (
            ("ENHANCE / UPSCALE BATCH", "enhance"),
            ("BACKGROUND REMOVAL BATCH", "background"),
        ):
            tk.Button(
                batch_buttons,
                text=label,
                command=lambda m=mode: self._show_photo_tools_mode(m),
                bg="#17130a",
                fg="#d4af37",
                activebackground="#d4af37",
                activeforeground="#050505",
                relief="flat",
                bd=0,
                highlightthickness=1,
                highlightbackground="#57471f",
                padx=22,
                pady=12,
                font=("DejaVu Sans Condensed", 10, "bold"),
                cursor="hand2"
            ).pack(side="left", padx=8)

        self._show_photo_tools_mode("enhance")


    def _show_photo_tools_mode(self, mode):
        frames = {
            "enhance": self.tools_enhance_frame,
            "background": self.tools_bg_frame,
            "batch": self.tools_batch_frame,
        }

        if mode not in frames:
            mode = "enhance"

        for frame in frames.values():
            frame.pack_forget()

        frames[mode].pack(fill="both", expand=True)

        for key, button in self.photo_tools_mode_buttons.items():
            if key == mode:
                button.configure(
                    bg="#d4af37",
                    fg="#050505",
                    activebackground="#e4c45a",
                    activeforeground="#050505",
                    highlightbackground="#d4af37"
                )
            else:
                button.configure(
                    bg="#17130a",
                    fg="#d4af37",
                    activebackground="#2a210d",
                    activeforeground="#f4efe6",
                    highlightbackground="#57471f"
                )

        labels = {
            "enhance": "Photo Tools · Enhance / Upscale",
            "background": "Photo Tools · Remove Background",
            "batch": "Photo Tools · Batch Process",
        }

        try:
            self.status.config(text=labels[mode])
        except Exception:
            pass


    def choose_tool_files(self):
        files=genesis_pick_files("Choose images", remember_key="image_input", visual_parent=self)
        self.tool_list.delete(0,"end")
        for f in files:self.tool_list.insert("end",f)

    def process_batch(self):
        files=[Path(self.tool_list.get(i)) for i in range(self.tool_list.size())]
        if not files:
            messagebox.showinfo(APP_NAME,"Choose one or more images first.")
            return
        out=genesis_pick_folder("Output folder", remember_key="output")
        if not out:return
        factor={"1x":1,"2x":2,"4x":4}[self.scale_var.get()]
        mode=self.enhance_var.get()
        for p in files:
            try:
                im=Image.open(p).convert("RGB")
                if mode!="None":
                    if mode=="Balanced":
                        im=ImageEnhance.Contrast(im).enhance(1.08)
                        im=ImageEnhance.Sharpness(im).enhance(1.25)
                    elif mode=="Sharpen":
                        im=im.filter(ImageFilter.UnsharpMask(radius=1.5,percent=130,threshold=3))
                    elif mode=="Strong":
                        im=ImageEnhance.Contrast(im).enhance(1.15)
                        im=ImageEnhance.Color(im).enhance(1.08)
                        im=im.filter(ImageFilter.UnsharpMask(radius=2,percent=160,threshold=2))
                if factor>1:
                    im=im.resize((im.width*factor,im.height*factor),Image.Resampling.LANCZOS)
                im.save(Path(out)/(p.stem+"_processed.jpg"),quality=95)
            except Exception as e:
                print("PROCESS ERROR",p,e)
        messagebox.showinfo(APP_NAME,"Batch complete.")

    def _bg_ui(self):
        self._workspace_heading(
            self.tools_bg_frame,
            "Local cutout pipeline",
            "BACKGROUND TOOLS",
            "Create transparent PNG cutouts in batches while preserving source files.",
        )
        fr=ttk.Frame(self.tools_bg_frame); fr.pack(fill="x",pady=10)
        ttk.Button(fr,text="Select Images",command=self.choose_bg_files).pack(side="left",padx=4)
        ttk.Button(fr,text="Remove Background Batch",command=self.remove_bg_batch).pack(side="left",padx=4)
        ttk.Label(fr,text="Uses isolated rembg backend if installed. Originals are never overwritten.").pack(side="left",padx=12)
        self.bg_list=tk.Listbox(self.tools_bg_frame); self.bg_list.pack(fill="both",expand=True,padx=8,pady=8)

    def choose_bg_files(self):
        files=genesis_pick_files("Choose images", remember_key="image_input", visual_parent=self)
        self.bg_list.delete(0,"end")
        for f in files:self.bg_list.insert("end",f)

    def remove_bg_batch(self):
        try:
            from rembg import remove
        except Exception:
            messagebox.showwarning(APP_NAME, "Background backend is not installed yet.\n\nRun the optional installer:\n~/GENESIS-Photo-Studio/install-rembg.sh")
            return
        files=[Path(self.bg_list.get(i)) for i in range(self.bg_list.size())]
        if not files:
            messagebox.showinfo(APP_NAME,"Select one or more images first.")
            return
        out=genesis_pick_folder("Output folder", remember_key="output")
        if not out:return
        for p in files:
            try:
                inp=p.read_bytes(); result=remove(inp)
                (Path(out)/(p.stem+"_cutout.png")).write_bytes(result)
            except Exception as e:
                print("REMBG ERROR",p,e)
        messagebox.showinfo(APP_NAME,"Background removal finished.")

    def _canvas_ui(self):
        self._workspace_heading(
            self.tab_canvas,
            "Composition workspace",
            "WALLPAPER STUDIO",
            "Layer, position and export a cutout over a widescreen background.",
        )
        top=ttk.Frame(self.tab_canvas);top.pack(fill="x",pady=6)
        ttk.Button(top,text="Load Background",command=self.load_canvas_bg).pack(side="left",padx=4)
        ttk.Button(top,text="Load Cutout PNG",command=self.load_canvas_subject).pack(side="left",padx=4)
        ttk.Button(top,text="Scale +",command=lambda:self.change_scale(1.1)).pack(side="left",padx=4)
        ttk.Button(top,text="Scale -",command=lambda:self.change_scale(0.9)).pack(side="left",padx=4)
        ttk.Button(top,text="Export Composite",command=self.export_canvas).pack(side="left",padx=10)
        self.cv=tk.Canvas(self.tab_canvas,bg="#222",width=1000,height=650)
        self.cv.pack(fill="both",expand=True,padx=8,pady=8)
        self.cv.bind("<ButtonPress-1>",self.drag_begin)
        self.cv.bind("<B1-Motion>",self.drag_move)

    def load_canvas_bg(self):
        f=genesis_pick_file("Choose image", remember_key="single_image", visual_parent=self)
        if not f:return
        self.canvas_bg=Image.open(f).convert("RGBA")
        self.redraw_canvas()

    def load_canvas_subject(self):
        f=genesis_pick_file("Choose PNG/WebP", remember_key="single_image", visual_parent=self)
        if not f:return
        self.canvas_subject=Image.open(f).convert("RGBA")
        self.subject_scale=1.0
        self.redraw_canvas()

    def change_scale(self,m):
        if self.canvas_subject is None:
            self.status.config(text="Load a cutout PNG before changing its scale")
            return
        self.subject_scale=max(.1,min(5,self.subject_scale*m));self.redraw_canvas()

    def drag_begin(self,e): self.drag_start=(e.x,e.y)
    def drag_move(self,e):
        if not self.drag_start:return
        dx=e.x-self.drag_start[0];dy=e.y-self.drag_start[1]
        self.subject_pos[0]+=dx;self.subject_pos[1]+=dy
        self.drag_start=(e.x,e.y);self.redraw_canvas()

    def make_composite(self):
        if self.canvas_bg is None:
            bg=Image.new("RGBA",(1280,720),(30,30,30,255))
        else:
            bg=ImageOps.contain(self.canvas_bg,(1280,720))
            canvas=Image.new("RGBA",(1280,720),(0,0,0,255))
            canvas.alpha_composite(bg,((1280-bg.width)//2,(720-bg.height)//2))
            bg=canvas
        if self.canvas_subject is not None:
            s=self.canvas_subject
            s=s.resize((max(1,int(s.width*self.subject_scale)),max(1,int(s.height*self.subject_scale))),Image.Resampling.LANCZOS)
            bg.alpha_composite(s,(int(self.subject_pos[0]),int(self.subject_pos[1])))
        return bg

    def redraw_canvas(self):
        im=self.make_composite().copy()
        cw=max(1,self.cv.winfo_width()); ch=max(1,self.cv.winfo_height())
        im.thumbnail((cw,ch))
        tkimg=ImageTk.PhotoImage(im)
        self.cv.delete("all")
        self.cv.create_image(cw//2,ch//2,image=tkimg)
        self.cv.image=tkimg

    def export_canvas(self):
        f=genesis_save_image("Save image", remember_key="save_image")
        if not f:return
        im=self.make_composite()
        if f.lower().endswith(".jpg"):
            im.convert("RGB").save(f,quality=95)
        else: im.save(f)
        messagebox.showinfo(APP_NAME,"Composite exported.")


    def _camera_ui(self):
        self.cameras_enabled = False
        self.camera_preview_labels = {}
        self.camera_preview_images = {}
        self.camera_popup = None
        self.camera_popup_label = None
        self.camera_popup_cam = None
        self.camera_popup_image = None

        self._workspace_heading(
            self.tab_cameras,
            "Live monitoring",
            "CAMERA HUB",
            "View and manage the configured local camera feeds.",
        )

        top = ttk.Frame(self.tab_cameras)
        top.pack(fill="x", padx=10, pady=(8, 4))

        ttk.Label(
            top,
            text="GENESIS CAMERA HUB",
            font=("DejaVu Sans", 16, "bold")
        ).pack(side="left")

        self.camera_status = ttk.Label(
            top,
            text="Checking go2rtc..."
        )
        self.camera_status.pack(side="right")

        controls = ttk.Frame(self.tab_cameras)
        controls.pack(fill="x", padx=10, pady=(0, 6))

        ttk.Button(
            controls,
            text="CAMERAS ON",
            command=self.start_cameras
        ).pack(side="left", padx=(0, 5))

        ttk.Button(
            controls,
            text="CAMERAS OFF",
            command=self.stop_cameras
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            controls,
            text="Refresh All",
            command=self.refresh_all_cameras
        ).pack(side="left", padx=3)

        ttk.Button(
            controls,
            text="Open Live WebRTC Grid",
            command=self.open_camera_grid
        ).pack(side="left", padx=3)

        ttk.Button(
            controls,
            text="Check Backend",
            command=self.check_go2rtc
        ).pack(side="left", padx=3)

        ttk.Button(
            controls,
            text="Restart go2rtc",
            command=self.restart_go2rtc
        ).pack(side="left", padx=3)

        grid = ttk.Frame(self.tab_cameras)
        grid.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        for col in range(3):
            grid.columnconfigure(col, weight=1)

        for row in range(2):
            grid.rowconfigure(row, weight=1)

        for i in range(6):
            cam = i + 1
            row = i // 3
            col = i % 3

            tile = ttk.LabelFrame(
                grid,
                text=f"CAM {cam}"
            )
            tile.grid(
                row=row,
                column=col,
                sticky="nsew",
                padx=4,
                pady=4
            )

            preview = tk.Label(
                tile,
                text="Loading...",
                bg="#111111",
                fg="#dddddd",
                cursor="hand2"
            )
            preview.pack(
                fill="both",
                expand=True,
                padx=3,
                pady=3
            )

            preview.bind(
                "<Button-1>",
                lambda e, n=cam: self.enlarge_camera(n)
            )

            preview.bind(
                "<Double-Button-1>",
                lambda e, n=cam: self.open_camera(n)
            )

            self.camera_preview_labels[cam] = preview

            buttons = ttk.Frame(tile)
            buttons.pack(fill="x", padx=3, pady=(0, 3))

            ttk.Button(
                buttons,
                text="Enlarge",
                command=lambda n=cam: self.enlarge_camera(n)
            ).pack(side="left", padx=2)

            ttk.Button(
                buttons,
                text="Live",
                command=lambda n=cam: self.open_camera(n)
            ).pack(side="right", padx=2)

        ttk.Label(
            self.tab_cameras,
            text=(
                "Click a camera to enlarge. Double-click or press Live for full WebRTC. "
                "Overview uses lightweight 640×360 go2rtc snapshots."
            )
        ).pack(anchor="w", padx=12, pady=(0, 6))

        # Preview state is local; service changes require a camera action.
        self.camera_status.config(text="Camera previews OFF · service unchanged")

    def _fetch_camera_frame(self, cam_number, width=640):
        import io
        import urllib.request

        url = (
            f"http://127.0.0.1:1984/api/frame.jpeg"
            f"?src=cam{cam_number}&width={width}"
        )

        with urllib.request.urlopen(url, timeout=4) as r:
            data = r.read()

        return Image.open(io.BytesIO(data)).convert("RGB")

    def refresh_all_cameras(self):
        if not getattr(self, "cameras_enabled", False):
            return
        for cam in range(1, 7):
            self._refresh_camera_async(cam)

    def _refresh_camera_async(self, cam_number):
        if not getattr(self, "cameras_enabled", False):
            return

        def worker():
            try:
                image = self._fetch_camera_frame(
                    cam_number,
                    width=640
                )

                self.after(
                    0,
                    lambda img=image, n=cam_number:
                    self._apply_camera_frame(n, img)
                )

            except Exception as e:
                self.after(
                    0,
                    lambda err=str(e), n=cam_number:
                    self._camera_error(n, err)
                )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def _apply_camera_frame(self, cam_number, image):
        label = self.camera_preview_labels.get(cam_number)

        if label is None:
            return

        max_w = label.winfo_width()
        max_h = label.winfo_height()

        if max_w < 200:
            max_w = 480

        if max_h < 120:
            max_h = 270

        display = image.copy()
        display.thumbnail(
            (max_w, max_h),
            Image.Resampling.LANCZOS
        )

        tkimg = ImageTk.PhotoImage(display)

        label.configure(
            image=tkimg,
            text=""
        )

        self.camera_preview_images[cam_number] = tkimg

        if (
            self.camera_popup is not None
            and self.camera_popup.winfo_exists()
            and self.camera_popup_cam == cam_number
        ):
            self._refresh_camera_popup(cam_number)

        if getattr(self, "cameras_enabled", False):
            self.after(
                2000,
                lambda n=cam_number:
                self._refresh_camera_async(n)
            )

    def _camera_error(self, cam_number, error):
        label = self.camera_preview_labels.get(cam_number)

        if label is not None:
            label.configure(
                image="",
                text=f"CAM {cam_number}\nUnavailable"
            )

        if getattr(self, "cameras_enabled", False):
            self.after(
                3500,
                lambda n=cam_number:
                self._refresh_camera_async(n)
            )

    def enlarge_camera(self, cam_number):
        if (
            self.camera_popup is not None
            and self.camera_popup.winfo_exists()
        ):
            self.camera_popup.destroy()

        win = tk.Toplevel(self)
        win.title(f"GENESIS · CAM {cam_number}")
        win.geometry("1280x780")
        win.minsize(720, 440)

        self.camera_popup = win
        self.camera_popup_cam = cam_number

        top = ttk.Frame(win)
        top.pack(fill="x", padx=8, pady=8)

        ttk.Label(
            top,
            text=f"CAM {cam_number}",
            font=("DejaVu Sans", 16, "bold")
        ).pack(side="left")

        ttk.Button(
            top,
            text="Open Live WebRTC",
            command=lambda:
            self.open_camera(cam_number)
        ).pack(side="right", padx=4)

        ttk.Button(
            top,
            text="Close",
            command=win.destroy
        ).pack(side="right", padx=4)

        self.camera_popup_label = tk.Label(
            win,
            bg="#000000",
            fg="#dddddd",
            text="Loading..."
        )

        self.camera_popup_label.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=(0, 8)
        )

        self._refresh_camera_popup(cam_number)

    def _refresh_camera_popup(self, cam_number):
        if (
            self.camera_popup is None
            or not self.camera_popup.winfo_exists()
            or self.camera_popup_cam != cam_number
        ):
            return

        def worker():
            try:
                image = self._fetch_camera_frame(
                    cam_number,
                    width=1280
                )

                self.after(
                    0,
                    lambda img=image, n=cam_number:
                    self._apply_popup_frame(n, img)
                )

            except Exception:
                self.after(
                    0,
                    lambda n=cam_number:
                    self._camera_popup_error(n)
                )

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def _camera_popup_error(self, cam_number):
        if (
            self.camera_popup is not None
            and self.camera_popup.winfo_exists()
            and self.camera_popup_cam == cam_number
        ):
            self.camera_popup_label.configure(
                image="",
                text=f"CAM {cam_number}\nBackend unavailable"
            )

    def _apply_popup_frame(self, cam_number, image):
        if (
            self.camera_popup is None
            or not self.camera_popup.winfo_exists()
            or self.camera_popup_cam != cam_number
        ):
            return

        label = self.camera_popup_label

        max_w = max(640, label.winfo_width())
        max_h = max(360, label.winfo_height())

        display = image.copy()
        display.thumbnail(
            (max_w, max_h),
            Image.Resampling.LANCZOS
        )

        tkimg = ImageTk.PhotoImage(display)

        label.configure(
            image=tkimg,
            text=""
        )

        self.camera_popup_image = tkimg

    def open_camera_grid(self):
        if not integrations.endpoint_online(
            integrations.GO2RTC_URL,
            "/api/streams"
        ):
            messagebox.showwarning(
                APP_NAME,
                "go2rtc is offline. Start or restart the camera backend first."
            )
            return
        integrations.open_url(
            "http://127.0.0.1:1984/#mesh=cam1,cam2,cam3,cam4,cam5,cam6"
        )

    def open_camera(self, cam_number):
        cam = f"cam{cam_number}"
        if not integrations.endpoint_online(
            integrations.GO2RTC_URL,
            "/api/streams"
        ):
            messagebox.showwarning(
                APP_NAME,
                "go2rtc is offline. This live camera cannot be opened."
            )
            return
        integrations.open_url(
            f"http://127.0.0.1:1984/stream.html"
            f"?src={cam}&mode=webrtc,mse,hls,mjpeg"
        )

    def check_go2rtc(self):
        import urllib.request

        try:
            with urllib.request.urlopen(
                "http://127.0.0.1:1984/api/streams",
                timeout=2
            ) as r:
                data = r.read().decode(
                    "utf-8",
                    "ignore"
                )

            found = sum(
                1
                for i in range(1, 7)
                if f'"cam{i}"' in data
            )

            self.camera_status.config(
                text=f"go2rtc ONLINE · {found}/6 streams"
            )

            self.status.config(
                text=f"Camera gateway online · {found}/6 streams"
            )

        except Exception:
            self.camera_status.config(
                text="go2rtc OFFLINE"
            )

            self.status.config(
                text="Camera gateway not reachable"
            )

    def start_cameras(self):
        try:
            result = subprocess.run(
                ["systemctl", "--user", "start", "go2rtc"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "systemctl start failed")

            self.cameras_enabled = True
            self.camera_status.config(text="CAMERAS STARTING...")
            self.nav_camera_status.config(
                text="● Cameras: STARTING",
                fg="#e0a84f"
            )

            self.after(1000, self.check_go2rtc)
            self.after(1300, self.refresh_all_cameras)
            self.after(1500, self.refresh_system_statuses)

        except Exception as e:
            messagebox.showerror(APP_NAME, f"Could not start cameras:\n{e}")

    def stop_cameras(self):
        self.cameras_enabled = False

        for cam, label in self.camera_preview_labels.items():
            label.configure(
                image="",
                text=f"CAM {cam}\nOFF"
            )

        try:
            subprocess.run(
                ["systemctl", "--user", "stop", "go2rtc"],
                capture_output=True,
                text=True,
                timeout=10
            )
        except Exception:
            pass

        self.camera_status.config(text="CAMERAS OFF")
        self.nav_camera_status.config(
            text="● Cameras: OFF",
            fg="#9da9b8"
        )

    def restart_go2rtc(self):
        try:
            result = subprocess.run(
                [
                    "systemctl",
                    "--user",
                    "restart",
                    "go2rtc"
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                raise RuntimeError(
                    result.stderr.strip()
                    or "systemctl restart failed"
                )

            self.after(
                1200,
                self.check_go2rtc
            )

            self.after(
                1800,
                self.refresh_all_cameras
            )

        except Exception as e:
            messagebox.showwarning(
                APP_NAME,
                f"Could not restart go2rtc:\n{e}"
            )


    def _ai_ui(self):
        ai_canvas = tk.Canvas(self.tab_ai, bg="#050505", highlightthickness=0)
        self.ai_backdrop_host = ai_canvas
        ai_scroll = ttk.Scrollbar(
            self.tab_ai, orient="vertical", command=ai_canvas.yview
        )
        ai_canvas.configure(yscrollcommand=ai_scroll.set)
        ai_scroll.pack(side="right", fill="y")
        ai_canvas.pack(side="left", fill="both", expand=True)

        outer = ttk.Frame(ai_canvas)
        self.ai_main_container = outer
        self.ai_canvas = ai_canvas
        ai_window = ai_canvas.create_window((0, 0), window=outer, anchor="n")
        outer.configure(padding=(14, 12))
        outer.bind(
            "<Configure>",
            lambda _event: ai_canvas.configure(scrollregion=ai_canvas.bbox("all")),
        )
        ai_canvas.bind(
            "<Configure>",
            lambda event: (
                ai_canvas.coords(ai_window, event.width / 2, 0),
                ai_canvas.itemconfigure(
                    ai_window,
                    width=max(760, int(event.width * 0.88)),
                ),
            ),
        )
        ai_canvas.bind(
            "<MouseWheel>",
            lambda event: ai_canvas.yview_scroll(
                int(-1 * (event.delta / 120)), "units"
            ),
        )

        self._workspace_heading(
            outer,
            "Local creation",
            "IMAGE / AI",
            "Generate, pose, prompt and inspect local AI workflows.",
        )

        heading = ttk.Frame(outer)
        heading.pack(fill="x", pady=(0, 10))
        ttk.Label(
            heading,
            text="LOCAL AI / WORKFLOW CONTROL",
            font=("DejaVu Sans", 16, "bold")
        ).pack(side="left")
        ttk.Button(
            heading,
            text="Refresh All Status",
            command=self.refresh_system_statuses
        ).pack(side="right")

        toolstrip = ttk.Frame(outer)
        toolstrip.pack(fill="x", pady=(0, 8))
        ttk.Label(toolstrip, text="CREATE", style="Muted.TLabel").pack(side="left", padx=(0, 8))
        for label, mode in (("FLUX / Klein", "flux"), ("ReActor Face Swap", "reactor")):
            ttk.Button(toolstrip, text=label,
                       command=lambda value=mode: self._select_generation_workflow(value)).pack(side="left", padx=3)
        ttk.Button(toolstrip, text="Pose Library", command=self.open_pose_studio).pack(side="left", padx=3)
        ttk.Button(
            toolstrip,
            text="Prompt Manager",
            command=self.open_prompt_manager
        ).pack(side="left", padx=3)
        ttk.Button(toolstrip, text="Model / Workflow Check", command=self.run_workflow_preflight).pack(side="left", padx=3)

        # ============================================================
        # EMBEDDED PROMPT STUDIO
        # ============================================================
        self.ai_prompt_host = tk.Frame(
            outer,
            bg="#050505",
            highlightthickness=1,
            highlightbackground="#4a4028"
        )

        self.embedded_prompt_manager = None

        llama = ttk.LabelFrame(outer, text="LOCAL LLM · llama.cpp ROCm")
        llama.pack(fill="x", pady=5)
        llama_info = ttk.Frame(llama)
        llama_info.pack(side="left", fill="both", expand=True, padx=10, pady=8)
        self.llama_status_label = ttk.Label(
            llama_info,
            text="Checking...",
            font=("DejaVu Sans", 11, "bold")
        )
        self.llama_status_label.pack(anchor="w")
        self.llama_detail_label = ttk.Label(
            llama_info,
            text=(
                "Rocinante-X-12B Q5_K_M · context 12,288 · "
                "http://127.0.0.1:8081"
            )
        )
        self.llama_detail_label.pack(anchor="w", pady=(3, 0))
        llama_actions = ttk.Frame(llama)
        llama_actions.pack(side="right", padx=8, pady=8)
        ttk.Button(
            llama_actions,
            text="Start Server",
            command=self.start_llama
        ).pack(side="left", padx=3)
        ttk.Button(
            llama_actions,
            text="Open API",
            command=lambda: integrations.open_url(integrations.LLAMA_URL)
        ).pack(side="left", padx=3)

        comfy = ttk.LabelFrame(outer, text="COMFYUI · existing ROCm image backend")
        comfy.pack(fill="x", pady=5)
        comfy_info = ttk.Frame(comfy)
        comfy_info.pack(side="left", fill="both", expand=True, padx=10, pady=8)
        self.comfy_status_label = ttk.Label(
            comfy_info,
            text="Checking...",
            font=("DejaVu Sans", 11, "bold")
        )
        self.comfy_status_label.pack(anchor="w")
        self.comfy_detail_label = ttk.Label(
            comfy_info,
            text="comfyui-reactor-rocm · http://127.0.0.1:8188"
        )
        self.comfy_detail_label.pack(anchor="w", pady=(3, 0))
        comfy_actions = ttk.Frame(comfy)
        comfy_actions.pack(side="right", padx=8, pady=8)
        ttk.Button(
            comfy_actions,
            text="Start",
            command=self.start_comfyui
        ).pack(side="left", padx=3)
        ttk.Button(
            comfy_actions,
            text="Open",
            command=self.launch_comfyui
        ).pack(side="left", padx=3)

        self._generation_ui(outer)

        media = ttk.LabelFrame(outer, text="MEDIA · Jellyfin Desktop + MPV / ModernZ")
        media.pack(fill="x", pady=5)
        media_info = ttk.Frame(media)
        media_info.pack(side="left", fill="both", expand=True, padx=10, pady=8)
        self.media_status_label = ttk.Label(
            media_info,
            text="Checking...",
            font=("DejaVu Sans", 11, "bold")
        )
        self.media_status_label.pack(anchor="w")
        ttk.Label(
            media_info,
            text="Uses the completed integrated library/player configuration unchanged."
        ).pack(anchor="w", pady=(3, 0))
        ttk.Button(
            media,
            text="Open Media Library",
            command=self.launch_media
        ).pack(side="right", padx=11, pady=8)

        workflow_lab_frame = ttk.LabelFrame(
            outer,
            text="GENESIS WORKFLOW LAB · poses / ComfyUI / custom workflows"
        )
        workflow_lab_frame.pack(fill="x", pady=(7, 5))

        workflow_summary = ttk.Frame(workflow_lab_frame)
        workflow_summary.pack(fill="x", padx=10, pady=(8, 4))

        self.workflow_lab_summary = ttk.Label(
            workflow_summary,
            text=(
                f"{len(workflow_lab.pose_library_index())} poses indexed · "
                f"{max(0, len(workflow_lab.pose_library_categories()) - 1)} categories · "
                f"{len(workflow_lab.built_in_workflows())} built-in workflows"
            ),
            font=("DejaVu Sans", 10, "bold")
        )
        self.workflow_lab_summary.pack(side="left")

        workflow_actions = ttk.Frame(workflow_lab_frame)
        workflow_actions.pack(fill="x", padx=8, pady=(3, 8))

        ttk.Button(
            workflow_actions,
            text="Pose Studio",
            command=self.open_pose_studio
        ).pack(side="left", padx=3)

        ttk.Button(
            workflow_actions,
            text="Run Preflight",
            command=self.run_workflow_preflight
        ).pack(side="left", padx=3)

        ttk.Button(
            workflow_actions,
            text="Inspect Workflow JSON",
            command=self.inspect_custom_workflow
        ).pack(side="left", padx=3)

        ttk.Button(
            workflow_actions,
            text="Open ComfyUI",
            command=self.launch_comfyui
        ).pack(side="left", padx=3)

        self.workflow_lab_status = tk.Text(
            workflow_lab_frame,
            height=8,
            wrap="word",
            background="#101010",
            foreground="#f4ead5",
            insertbackground="#f4ead5",
            relief="flat",
            padx=8,
            pady=6
        )
        self.workflow_lab_status.pack(
            fill="x",
            padx=10,
            pady=(0, 10)
        )
        self.workflow_lab_status.insert(
            "1.0",
            "Workflow Lab ready.\n"
            "Run Preflight to check the current ComfyUI GPU/node/model state, "
            "or inspect any downloaded ComfyUI workflow JSON."
        )
        self.workflow_lab_status.configure(state="disabled")

    def _generation_ui(self, parent):
        frame = ttk.LabelFrame(parent, text="IMAGE GENERATION · existing ComfyUI workflows")
        frame.pack(fill="x", pady=(7, 5))
        self.gen_workflow_var = tk.StringVar()
        self.gen_model_var = tk.StringVar(value="Use workflow default")
        self.gen_lora_var = tk.StringVar(value="Use workflow default")
        self.gen_source_var = tk.StringVar(value="No source image selected")
        self.gen_workflow_paths = {}

        presets = ttk.Frame(frame)
        presets.pack(fill="x", padx=10, pady=(9, 2))
        ttk.Label(presets, text="TESTED BUILDS", style="Muted.TLabel").pack(side="left", padx=(0, 8))
        for label, mode in (("KLEIN 9B", "9b"), ("FLUXUP", "fluxup"), ("PHR00T", "phroot")):
            ttk.Button(
                presets, text=label,
                command=lambda value=mode: self._select_generation_workflow(value),
            ).pack(side="left", padx=(0, 5))

        form = ttk.Frame(frame)
        form.pack(fill="x", padx=10, pady=(8, 4))
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)
        ttk.Label(form, text="Workflow").grid(row=0, column=0, sticky="w", padx=(0, 7), pady=3)
        self.gen_workflow_combo = ttk.Combobox(form, textvariable=self.gen_workflow_var, state="readonly")
        self.gen_workflow_combo.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=3)
        ttk.Label(form, text="Model").grid(row=0, column=2, sticky="w", padx=(0, 7), pady=3)
        self.gen_model_combo = ttk.Combobox(form, textvariable=self.gen_model_var, state="readonly")
        self.gen_model_combo.grid(row=0, column=3, sticky="ew", pady=3)
        ttk.Label(form, text="LoRA").grid(row=1, column=0, sticky="w", padx=(0, 7), pady=3)
        self.gen_lora_combo = ttk.Combobox(form, textvariable=self.gen_lora_var, state="readonly")
        self.gen_lora_combo.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=3)

        ttk.Label(form, text="CFG").grid(row=2, column=0, sticky="w", padx=(0,7), pady=3)
        self.gen_cfg_var = tk.DoubleVar(value=3.5)
        ttk.Spinbox(form, from_=1.0, to=30.0, increment=0.5,
                    textvariable=self.gen_cfg_var,
                    width=8).grid(row=2, column=1, sticky="w", pady=3)

        ttk.Label(form, text="Steps").grid(row=2, column=2, sticky="w", padx=(0,7), pady=3)
        self.gen_steps_var = tk.IntVar(value=20)
        ttk.Spinbox(form, from_=1, to=100,
                    textvariable=self.gen_steps_var,
                    width=8).grid(row=2, column=3, sticky="w", pady=3)

        ttk.Label(form, text="Seed").grid(row=3, column=0, sticky="w", padx=(0,7), pady=3)
        self.gen_seed_var = tk.StringVar(value="-1")
        ttk.Entry(form,
                  textvariable=self.gen_seed_var,
                  width=18).grid(row=3, column=1, sticky="ew", pady=3)

        ttk.Label(form, text="Width").grid(row=3, column=2, sticky="w", padx=(0,7), pady=3)
        self.gen_width_var = tk.IntVar(value=768)
        ttk.Spinbox(form, from_=256, to=4096, increment=64,
                    textvariable=self.gen_width_var,
                    width=8).grid(row=3, column=3, sticky="w", pady=3)

        ttk.Label(form, text="Height").grid(row=4, column=0, sticky="w", padx=(0,7), pady=3)
        self.gen_height_var = tk.IntVar(value=768)
        ttk.Spinbox(form, from_=256, to=4096, increment=64,
                    textvariable=self.gen_height_var,
                    width=8).grid(row=4, column=1, sticky="w", pady=3)

        ttk.Label(form, text="Denoise").grid(row=4, column=2, sticky="w", padx=(0,7), pady=3)
        self.gen_denoise_var = tk.DoubleVar(value=0.8)
        ttk.Spinbox(form, from_=0.0, to=1.0, increment=0.05,
                    textvariable=self.gen_denoise_var,
                    width=8).grid(row=4, column=3, sticky="w", pady=3)
        source = ttk.Frame(form)
        source.grid(row=1, column=2, columnspan=2, sticky="ew", pady=3)
        ttk.Button(source, text="Load Source Image", command=self.choose_generation_source).pack(side="left")
        ttk.Label(source, textvariable=self.gen_source_var).pack(side="left", padx=8)

        ttk.Label(frame, text="Prompt").pack(anchor="w", padx=10)
        self.gen_prompt_text = tk.Text(frame, height=3, wrap="word", relief="flat", padx=7, pady=5)
        self.gen_prompt_text.pack(fill="x", padx=10, pady=(2, 4))

        ttk.Label(
            frame,
            text="Negative Prompt"
        ).pack(anchor="w", padx=10, pady=(4, 0))

        self.gen_negative_text = tk.Text(
            frame,
            height=2,
            wrap="word",
            relief="flat",
            padx=7,
            pady=5
        )
        self.gen_negative_text.pack(fill="x", padx=10, pady=(2, 5))

        actions = ttk.Frame(frame)
        actions.pack(fill="x", padx=10, pady=(0, 9))
        self.gen_button = ttk.Button(actions, text="GENERATE", style="Accent.TButton", command=self.generate_image)
        self.gen_button.pack(side="left")
        ttk.Button(actions, text="Refresh Models / Workflows", command=self.refresh_generation_options).pack(side="left", padx=7)
        ttk.Button(
            actions,
            text="Models & LoRAs",
            command=self.open_model_asset_inventory,
        ).pack(side="left", padx=3)
        self.gen_status_label = ttk.Label(
            actions,
            text="GENESIS submits a copy; your saved ComfyUI workflow is not changed.",
            style="Muted.TLabel"
        )
        self.gen_status_label.pack(side="left", padx=8)

        # ===== GENESIS GENERATION PROGRESS =====
        progress_frame = ttk.Frame(frame)
        progress_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.gen_progress = ttk.Progressbar(
            progress_frame,
            orient="horizontal",
            mode="determinate",
            maximum=100,
            length=500
        )
        self.gen_progress.pack(side="left", fill="x", expand=True)

        self.gen_percent_label = ttk.Label(
            progress_frame,
            text="0%",
            width=6,
            anchor="e"
        )
        self.gen_percent_label.pack(side="right", padx=(8, 0))

        self.gen_progress["value"] = 0

        from genesis.job_queue import JobQueueView, JobStore
        self.job_store = JobStore()
        self.gen_job_queue = JobQueueView(frame, self.job_store)
        self.gen_job_queue.pack(fill="x", padx=10, pady=(0, 10))

        self.after(300, self.refresh_generation_options)

    def choose_generation_source(self):
        path = genesis_pick_file(title="Choose source image for generation", remember_key="generation_source")
        if path:
            self.gen_source_path = path
            self.gen_source_var.set(Path(path).name)

    def refresh_generation_options(self):
        self.gen_status_label.config(text="Reading existing workflows and model inventory...")

        def worker():
            try:
                workflows = [item for item in workflow_lab.workflow_browser() if item.get("valid")]
                info = workflow_lab.object_info() if workflow_lab.comfy_alive() else {}
                inventory = workflow_lab.model_inventory(info) if info else {}
                error = None
            except Exception as exc:
                workflows, inventory, error = [], {}, str(exc)
            self.after(0, lambda: self._apply_generation_options(workflows, inventory, error))

        threading.Thread(target=worker, daemon=True).start()

    def open_model_asset_inventory(self):
        from genesis.asset_inventory import open_asset_inventory
        open_asset_inventory(self, getattr(self, "asset_inventory_data", {}))

    def _apply_generation_options(self, workflows, inventory, error=None):
        self.asset_inventory_data = dict(inventory or {})
        self.gen_workflow_paths = {
            f"{item['name']} · {Path(item['path']).parent.name}": item["path"] for item in workflows
        }
        names = list(self.gen_workflow_paths)
        self.gen_workflow_combo.configure(values=names)
        prior = self.settings.get("generation_workflow")
        selected = next((name for name, path in self.gen_workflow_paths.items() if path == prior), names[0] if names else "")
        self.gen_workflow_var.set(selected)
        models = sorted(set(inventory.get("diffusion_models", []) + inventory.get("checkpoints", [])), key=str.lower)
        loras = inventory.get("loras", [])
        self.gen_model_combo.configure(values=["Use workflow default"] + models)
        self.gen_lora_combo.configure(values=["Use workflow default"] + loras)
        self.gen_model_var.set(self.settings.get("generation_model", "Use workflow default"))
        self.gen_lora_var.set(self.settings.get("generation_lora", "Use workflow default"))
        status = f"ComfyUI inventory unavailable: {error}" if error else f"Ready · {len(names)} workflows · {len(models)} models · {len(loras)} LoRAs"
        self.gen_status_label.config(text=status)

        pending_mode = getattr(self, "_pending_generation_mode", None)
        if pending_mode:
            self._pending_generation_mode = None
            self.after(
                50,
                lambda mode=pending_mode: self._select_generation_workflow(mode)
            )

    def _generation_overrides(self, prompt, uploaded, prompt_text, model, lora):
        model_slots = [(str(n), key) for n, node in prompt.items()
                       for key in ("unet_name", "model_name", "ckpt_name")
                       if isinstance((node.get("inputs") or {}).get(key), str)]
        lora_slots = [(str(n), "lora_name") for n, node in prompt.items()
                      if "lora" in str(node.get("class_type", "")).lower()
                      and isinstance((node.get("inputs") or {}).get("lora_name"), str)]
        for label, selection, slots in (("Model", model, model_slots), ("LoRA", lora, lora_slots)):
            if selection and selection != "Use workflow default" and len(slots) != 1:
                raise ValueError(
                    f"{label} selection needs exactly one workflow slot; found {len(slots)}. "
                    "Choose 'Use workflow default' to preserve per-stage mappings, "
                    "or configure the slots in the existing workbench."
                )
        overrides = {}
        sources = []
        for node_id, node in prompt.items():
            node_type = str(node.get("class_type") or "")
            title = str((node.get("_meta") or {}).get("title") or node_type).lower()
            inputs = node.get("inputs") or {}
            values = {}

            # Global numeric controls are safe only for a unique input slot.
            for control, keys, convert in (
                ("cfg", ("cfg",), float), ("steps", ("steps",), int),
                ("seed", ("seed", "noise_seed"), int),
                ("width", ("width",), int), ("height", ("height",), int),
                ("denoise", ("denoise",), float),
            ):
                variable = getattr(self, f"gen_{control}_var", None)
                hits = [(str(n), k) for n, item in prompt.items()
                        for k in keys if k in (item.get("inputs") or {})]
                if variable is not None and len(hits) == 1 and hits[0][0] == str(node_id):
                    key = hits[0][1]
                    if not isinstance(inputs[key], list):
                        values[key] = convert(variable.get())

            if uploaded and node_type == "LoadImage" and "mask" not in title:
                rank = 0 if any(word in title for word in ("source", "input", "reference")) else 1
                sources.append((rank, str(node_id)))
            if prompt_text and "negative" not in title:
                for key in ("prompt", "text", "positive"):
                    if key in inputs and isinstance(inputs[key], str):
                        values[key] = prompt_text
                        break
            for selection, hits in ((model, model_slots), (lora, lora_slots)):
                if selection and selection != "Use workflow default" and hits[0][0] == str(node_id):
                    values[hits[0][1]] = selection
            if values:
                overrides[str(node_id)] = values
        if uploaded and sources:
            sources.sort()
            image_name = "/".join(value for value in (uploaded.get("subfolder"), uploaded.get("name")) if value)
            overrides.setdefault(sources[0][1], {})["image"] = image_name
        return overrides

    def generate_image(self):
        workflow_path = self.gen_workflow_paths.get(self.gen_workflow_var.get())
        if not workflow_path:
            messagebox.showwarning(APP_NAME, "Choose a workflow first.")
            return
        if not workflow_lab.comfy_alive():
            messagebox.showwarning(APP_NAME, "ComfyUI is offline. Start it, then press Generate again.")
            return
        prompt_text = self.gen_prompt_text.get("1.0", "end").strip()
        source_path = getattr(self, "gen_source_path", None)
        model, lora = self.gen_model_var.get(), self.gen_lora_var.get()

        import random

        try:
            if hasattr(self, "gen_seed_var"):
                if str(self.gen_seed_var.get()).strip() == "-1":
                    self.gen_seed_var.set(str(random.randint(0, 2**63 - 1)))
        except Exception:
            pass

        self.settings.update({"generation_workflow": workflow_path, "generation_model": model, "generation_lora": lora})
        save_settings(self.settings)
        self.gen_button.configure(state="disabled")
        if hasattr(self, "gen_progress"):
            self.gen_progress["value"] = 0
        if hasattr(self, "gen_percent_label"):
            self.gen_percent_label.config(text="0%")
        self.gen_status_label.config(text="Preparing workflow... · 0%")

        try:
            self.current_generation_job_id = self.job_store.create(
                "Image generation",
                detail="Preparing workflow",
                workflow=str(workflow_path),
            )
            self.job_store.update(
                self.current_generation_job_id,
                status="running",
            )
            self.gen_job_queue.refresh()
        except Exception:
            self.current_generation_job_id = None

        def progress(value):
            state = value.get("status", "working")
            elapsed = int(value.get("elapsed", 0))
            percent = value.get("percent", value.get("progress", 0))

            try:
                percent = float(percent)
                if percent <= 1:
                    percent *= 100
                percent = max(0, min(100, percent))
            except Exception:
                percent = 0

            def update_progress():
                if hasattr(self, "gen_progress"):
                    self.gen_progress["value"] = percent
                if hasattr(self, "gen_percent_label"):
                    self.gen_percent_label.config(text=f"{percent:.0f}%")
                self.gen_status_label.config(
                    text=f"Generation {state} · {elapsed}s"
                )

            self.after(0, update_progress)
            job_id = getattr(self, "current_generation_job_id", None)
            if job_id is not None:
                try:
                    self.job_store.update(
                        job_id,
                        status="running",
                        progress=percent,
                        detail=f"Generation {state} · {elapsed}s",
                    )
                except Exception:
                    pass

        def worker():
            try:
                client = workflow_lab.ComfyClient(self.settings.get("comfy_url", workflow_lab.COMFY_URL))
                stats = client.system_stats()
                if not workflow_lab.gpu_acceleration_available(stats):
                    raise workflow_lab.ComfyError(
                        "GPU acceleration is required. Restart ComfyUI with ROCm/CUDA enabled "
                        "and without --cpu, then try again."
                    )
                info = client.object_info()
                base = workflow_lab.workflow_to_prompt(workflow_path, info)

                # Reject ambiguous overrides before uploading any source image.
                self._generation_overrides(base, None, prompt_text, model, lora)

                uploaded = client.upload_image(source_path) if source_path else None

                overrides = self._generation_overrides(
                    base,
                    uploaded,
                    prompt_text,
                    model,
                    lora,
                )

                # ===== GENESIS KLEIN 4B MODEL MAPPING =====
                # Workflow node IDs are not stable between saved ComfyUI
                # templates. Target the loader types and their real inputs so
                # the 4B override cannot accidentally land on a sampler, LoRA,
                # or VAE node from another workflow revision.
                is_klein_4b = any(token in Path(workflow_path).stem.lower()
                                  for token in ("klein_4b", "klein-4b", "klein_img", "klein-img"))
                loader_types = ("UNETLoader", "CLIPLoader", "DualCLIPLoader", "VAELoader")
                single_model = sum(
                    isinstance((node.get("inputs") or {}).get(key), str)
                    for node in base.values() for key in ("unet_name", "model_name", "ckpt_name")
                ) == 1
                unique_loaders = all(sum(node.get("class_type") == kind for node in base.values()) <= 1
                                     for kind in loader_types)
                use_klein_defaults = (is_klein_4b and single_model and unique_loaders
                                      and model in ("", "Use workflow default", None))
                for node_id, node in base.items() if use_klein_defaults else ():
                    node_type = str(node.get("class_type") or "")
                    inputs = node.get("inputs") or {}
                    target = overrides.setdefault(str(node_id), {})
                    if node_type == "UNETLoader" and "unet_name" in inputs:
                        target["unet_name"] = "flux-2-klein-4b.safetensors"
                    elif node_type == "CLIPLoader" and "clip_name" in inputs:
                        target["clip_name"] = "qwen_3_4b_fp4_flux2.safetensors"
                        if "type" in inputs:
                            target["type"] = "flux2"
                    elif node_type == "DualCLIPLoader":
                        for key in ("clip_name1", "clip_name2"):
                            if key in inputs:
                                target[key] = "qwen_3_4b_fp4_flux2.safetensors"
                        if "type" in inputs:
                            target["type"] = "flux2"
                    elif node_type == "VAELoader" and "vae_name" in inputs:
                        target["vae_name"] = "flux2-vae.safetensors"
                    elif node_type == "SaveImage" and "filename_prefix" in inputs:
                        target["filename_prefix"] = "GENESIS-Klein4B"
                    if not target:
                        overrides.pop(str(node_id), None)

                prompt = workflow_lab.workflow_to_prompt(
                    workflow_path,
                    info,
                    overrides,
                )

                # Apply Genesis Negative Prompt after the final prompt exists.
                negative_text = ""
                if hasattr(self, "gen_negative_text"):
                    negative_text = self.gen_negative_text.get("1.0", "end").strip()
                workflow_lab.apply_negative_prompt(prompt, negative_text)

                validation = workflow_lab.validate_prompt(prompt, info)
                if not validation["valid"]:
                    raise workflow_lab.ComfyError("Workflow is not runnable: " + ", ".join(validation["missing_nodes"] + validation["missing_inputs"]))
                result = client.wait(client.submit(prompt), timeout=3600, progress=progress)
                if result.status != "completed":
                    raise workflow_lab.ComfyError(result.error or f"Generation ended: {result.status}")
                output_dir = Path.home() / "GENESIS-Exports"
                output_dir.mkdir(parents=True, exist_ok=True)
                stamp, saved = time.strftime("%Y%m%d-%H%M%S"), []
                for index, output in enumerate(result.outputs, 1):
                    if output.get("kind") != "images":
                        continue
                    suffix = Path(output.get("filename", "image.png")).suffix or ".png"
                    destination = output_dir / f"GENESIS-{stamp}-{index:02d}{suffix}"
                    destination.write_bytes(client.view(output))
                    saved.append(destination)
                if not saved:
                    raise workflow_lab.ComfyError("Workflow completed but returned no images.")
                self.after(0, lambda: self._generation_finished(saved))
            except Exception as exc:
                detail = str(exc)
                self.after(0, lambda value=detail: self._generation_failed(value))

        threading.Thread(target=worker, daemon=True).start()

    def _generation_finished(self, paths):
        if hasattr(self, "gen_progress"):
            self.gen_progress["value"] = 100
        if hasattr(self, "gen_percent_label"):
            self.gen_percent_label.config(text="100%")

        self.gen_button.configure(state="normal")
        self.gen_status_label.config(text=f"Generation complete · {len(paths)} image(s) saved")
        self.status.config(text="IMAGE GENERATION COMPLETE")
        job_id = getattr(self, "current_generation_job_id", None)
        if job_id is not None:
            try:
                self.job_store.update(
                    job_id,
                    status="completed",
                    progress=100,
                    detail=f"{len(paths)} image(s) saved",
                    outputs=paths,
                )
                self.gen_job_queue.refresh()
            except Exception:
                pass
            self.current_generation_job_id = None

        # ===== GENERATION RESULT ACTIONS =====
        result_path = Path(paths[0])
        result_frame = getattr(self, "gen_result_frame", None)

        if result_frame is not None:
            for child in result_frame.winfo_children():
                child.destroy()
        else:
            result_frame = ttk.Frame(self.gen_status_label.master)
            self.gen_result_frame = result_frame

        result_frame.pack(fill="x", padx=10, pady=(0, 8))

        ttk.Label(
            result_frame,
            text=f"✓ Ready: {result_path.name}"
        ).pack(side="left", padx=(0, 10))

        ttk.Button(
            result_frame,
            text="OPEN IMAGE",
            command=lambda p=result_path: __import__("subprocess").Popen(
                ["xdg-open", str(p)]
            )
        ).pack(side="left", padx=3)

        ttk.Button(
            result_frame,
            text="EDIT IMAGE",
            command=lambda p=result_path: self.open_image_editor(p)
        ).pack(side="left", padx=3)

        ttk.Button(
            result_frame,
            text="OPEN FOLDER",
            command=lambda p=result_path: __import__("subprocess").Popen(
                ["xdg-open", str(p.parent)]
            )
        ).pack(side="left", padx=3)

        self._preview_path(result_path)

    def _generation_failed(self, detail):
        self.gen_button.configure(state="normal")
        self.gen_status_label.config(text="Generation failed — see message")
        job_id = getattr(self, "current_generation_job_id", None)
        if job_id is not None:
            try:
                self.job_store.update(
                    job_id,
                    status="failed",
                    detail="Generation failed",
                    error=detail,
                )
                self.gen_job_queue.refresh()
            except Exception:
                pass
            self.current_generation_job_id = None
        messagebox.showwarning(APP_NAME, f"Generation failed:\n{detail}")

    def _set_workflow_lab_text(self, value):
        if not hasattr(self, "workflow_lab_status"):
            return
        self.workflow_lab_status.configure(state="normal")
        self.workflow_lab_status.delete("1.0", "end")
        self.workflow_lab_status.insert("1.0", str(value))
        self.workflow_lab_status.configure(state="disabled")


    def run_workflow_preflight(self):
        self._set_workflow_lab_text("Checking ComfyUI, GPU, nodes and models...")

        def worker():
            try:
                result = workflow_lab.health_report_text()
            except Exception as e:
                result = f"Workflow Lab preflight failed:\n{e}"

            self.after(
                0,
                lambda value=result: self._set_workflow_lab_text(value)
            )

        threading.Thread(target=worker, daemon=True).start()


    def inspect_custom_workflow(self):
        try:
            path = filedialog.askopenfilename(
                parent=self,
                title="Choose ComfyUI workflow JSON",
                filetypes=[
                    ("ComfyUI workflow", "*.json"),
                    ("JSON files", "*.json"),
                    ("All files", "*.*"),
                ],
            )
        except Exception as e:
            messagebox.showwarning(
                APP_NAME,
                f"Could not open workflow picker:\n{e}"
            )
            return

        if not path:
            return

        self._set_workflow_lab_text(
            f"Inspecting workflow:\n{path}\n"
        )

        def worker():
            try:
                result = workflow_lab.inspect_workflow(path)

                if not result["valid"]:
                    report = (
                        f"WORKFLOW INSPECTION FAILED\n\n"
                        f"File: {path}\n"
                        f"Error: {result['error'] or 'Unknown JSON error'}"
                    )
                else:
                    nodes = result["node_types"]
                    missing = result["missing_nodes"]

                    lines = [
                        "GENESIS WORKFLOW INSPECTOR",
                        "",
                        f"File: {path}",
                        f"Node types detected: {len(nodes)}",
                        "",
                        "NODES:",
                    ]

                    lines.extend(
                        f"  - {node}"
                        for node in nodes
                    )

                    lines.append("")

                    if workflow_lab.comfy_alive():
                        if missing:
                            lines.append("MISSING FROM CURRENT COMFYUI:")
                            lines.extend(
                                f"  - {node}"
                                for node in missing
                            )
                        else:
                            lines.append(
                                "NODE CHECK: PASS · all detected node types are installed"
                            )
                    else:
                        lines.append(
                            "COMFYUI OFFLINE · node availability could not be verified"
                        )

                    if result["error"]:
                        lines.extend([
                            "",
                            f"Inspection note: {result['error']}"
                        ])

                    report = "\n".join(lines)

            except Exception as e:
                report = f"Workflow inspection failed:\n{e}"

            self.after(
                0,
                lambda value=report: self._set_workflow_lab_text(value)
            )

        threading.Thread(target=worker, daemon=True).start()


    def _ensure_native_pose_library(self):
        if getattr(self, "native_pose_library", None) is not None:
            return
        from genesis.pose_library import NativePoseLibrary
        self.native_pose_library = NativePoseLibrary(
            self.tab_pose,
            Path.home() / "AI" / "GENESIS_POSE_MAKER" / "assets" / "pose_library",
            on_select=self._select_native_pose_reference,
            on_open=self.open_image_editor,
            on_workbench=self.open_legacy_pose_workbench,
            on_send=self._send_native_pose_reference,
        )
        self.native_pose_library.pack(fill="both", expand=True)

    def _select_native_pose_reference(self, item):
        self.selected_pose_reference = dict(item)
        self.status.configure(text=f"POSE REFERENCE · {item['name']}")

    def _send_native_pose_reference(self, item, destination):
        path = Path(item["file"])
        if not path.is_file():
            raise ValueError("The selected Pose reference is unavailable.")
        if destination in {"pose_reference", "source_image"}:
            queue_pose_workbench_handoff(path, destination)
            self.open_legacy_pose_workbench()
            label = "Pose Reference" if destination == "pose_reference" else "Source Image"
            self.status.configure(text=f"POSE WORKBENCH · {label} handoff queued")
            return
        if destination == "viewer_editor":
            self.open_image_editor(path)
            return
        raise ValueError(f"Unsupported Pose handoff destination: {destination}")

    def open_pose_studio(self):
        self._show_page("poses")
        self.status.configure(text="POSE LIBRARY · Native GENESIS workspace")

    def open_legacy_pose_workbench(self):
        launcher = Path(__file__).resolve().parent / "pose_webview.py"

        if not launcher.is_file():
            messagebox.showwarning(
                APP_NAME,
                f"Pose Library launcher was not found:\n{launcher}"
            )
            return

        try:
            subprocess.Popen(
                [
                    str(Path(__file__).resolve().parent / ".venv" / "bin" / "python"),
                    str(launcher),
                ],
                cwd=str(Path(__file__).resolve().parent),
                start_new_session=True
            )

            self._set_workflow_lab_text(
                "Existing stage workbench opened in its separate window."
            )

        except Exception as e:
            messagebox.showwarning(
                APP_NAME,
                f"Could not open Pose Library:\n{e}"
            )


    def _start_service_async(self, service, online_check, label):
        def worker():
            online = online_check()
            ok, detail = integrations.start_user_service(
                service,
                already_online=online
            )
            self.after(
                0,
                lambda: self._service_start_result(label, ok, detail)
            )

        self.status.config(text=f"Starting {label}...")
        threading.Thread(target=worker, daemon=True).start()

    def _service_start_result(self, label, ok, detail):
        self.status.config(text=f"{label}: {detail}")
        if not ok:
            messagebox.showwarning(APP_NAME, f"{label} could not start:\n{detail}")
        self.after(1800, self.refresh_system_statuses)

    def start_llama(self):
        if not (
            integrations.LLAMA_BINARY.is_file()
            and integrations.LLAMA_MODEL.is_file()
        ):
            messagebox.showwarning(
                APP_NAME,
                "The existing llama.cpp binary or Rocinante model is unavailable."
            )
            return
        self._start_service_async(
            integrations.LLAMA_SERVICE,
            lambda: integrations.endpoint_online(
                integrations.LLAMA_URL,
                "/health"
            ),
            "llama.cpp"
        )

    def start_comfyui(self):
        if not (
            integrations.COMFYUI_PYTHON.is_file()
            and (integrations.COMFYUI_ROOT / "main.py").is_file()
        ):
            messagebox.showwarning(
                APP_NAME,
                "The existing ComfyUI ROCm environment is unavailable."
            )
            return
        self._start_service_async(
            integrations.COMFYUI_SERVICE,
            lambda: integrations.endpoint_online(
                integrations.COMFYUI_URL,
                "/system_stats"
            ),
            "ComfyUI"
        )

    def launch_comfyui(self):
        if integrations.endpoint_online(
            integrations.COMFYUI_URL,
            "/system_stats"
        ):
            integrations.open_url(integrations.COMFYUI_URL)
            return
        self.start_comfyui()
        self._wait_for_endpoint_and_open(
            integrations.COMFYUI_URL,
            "/system_stats",
            "ComfyUI"
        )

    def _wait_for_endpoint_and_open(self, url, path, label, attempt=0):
        if integrations.endpoint_online(url, path, timeout=0.5):
            integrations.open_url(url)
            self.status.config(text=f"{label} ONLINE")
            self.refresh_system_statuses()
            return
        if attempt >= 40:
            self.status.config(
                text=f"{label} did not become ready; check its service log"
            )
            return
        self.after(
            750,
            lambda: self._wait_for_endpoint_and_open(
                url,
                path,
                label,
                attempt + 1
            )
        )

    def launch_media(self):
        ok, detail = integrations.launch_jellyfin_desktop()
        self.status.config(text=detail)
        if not ok:
            messagebox.showwarning(APP_NAME, detail)
        self.after(1200, self.refresh_system_statuses)

    def open_image_editor(self, path=None):
        """Open the integrated GENESIS Viewer / Editor workspace."""
        try:
            self._show_page("photos")
            self._show_organizer_mode("editor")

            editor = getattr(self, "embedded_image_editor", None)

            if path and editor is not None:
                editor.after(
                    40,
                    lambda p=path: editor.load_image(p)
                )

            self.status.config(
                text="Photo Organizer · Viewer / Editor"
            )

        except Exception as exc:
            messagebox.showerror(
                APP_NAME,
                f"Could not open Photo Viewer / Editor:\n{exc}"
            )


    def open_duplicate_lab(self):
        """Open integrated duplicate review inside Photo Organizer."""
        try:
            self._show_page("photos")
            self._show_organizer_mode("duplicates")

            lab = getattr(self, "embedded_duplicate_lab", None)
            initial = self.settings.get("recent_photo_project")

            if (
                lab is not None
                and initial
                and Path(initial).is_dir()
            ):
                lab._set_folder(Path(initial))

            self.status.config(
                text="Photo Organizer · Duplicate Review"
            )

        except Exception as exc:
            messagebox.showerror(
                APP_NAME,
                f"Could not open Duplicate Lab:\n{exc}"
            )


    def open_prompt_manager(self):
        """Show Prompt Studio inside the IMAGE / AI workspace."""
        try:
            self._show_page("ai")

            current = ""
            try:
                current = self.gen_prompt_text.get("1.0", "end").strip()
            except Exception:
                pass

            def use_prompt(value):
                try:
                    self.gen_prompt_text.delete("1.0", "end")
                    self.gen_prompt_text.insert("1.0", value)
                    self.gen_status_label.config(
                        text="Prompt loaded from Prompt Studio"
                    )
                except Exception:
                    pass

            self._show_ai_prompt_studio(
                current_prompt=current,
                on_use=use_prompt
            )

            self.status.config(text="Prompt Studio opened")

        except Exception as exc:
            messagebox.showerror(
                APP_NAME,
                f"Could not open Prompt Studio:\n{exc}"
            )

    def _show_ai_prompt_studio(self, current_prompt="", on_use=None):
        """Swap the IMAGE / AI content to the embedded Prompt Studio."""
        outer = self.ai_main_container

        if not hasattr(self, "_ai_saved_pack"):
            self._ai_saved_pack = []

        # Keep the original layout when Prompt Studio is entered again.

        for child in outer.winfo_children():
            if child is self.ai_prompt_host:
                continue

            manager = child.winfo_manager()

            if manager == "pack":
                info = child.pack_info().copy()
                self._ai_saved_pack.append((child, info))
                child.pack_forget()

        self.ai_prompt_host.pack(
            fill="both",
            expand=True,
            padx=4,
            pady=4
        )

        for child in self.ai_prompt_host.winfo_children():
            child.destroy()

        from genesis.prompt_manager import build_prompt_manager

        self.embedded_prompt_manager = build_prompt_manager(
            self.ai_prompt_host,
            on_use=on_use,
            current_prompt=current_prompt,
            on_close=self._show_ai_main,
        )

        try:
            self.ai_canvas.yview_moveto(0)
        except Exception:
            pass

    def _show_ai_main(self):
        """Return from Prompt Studio to the normal IMAGE / AI workspace."""
        try:
            self.ai_prompt_host.pack_forget()
        except Exception:
            pass

        saved = getattr(self, "_ai_saved_pack", [])

        for child, info in saved:
            try:
                options = dict(info)
                options.pop("in", None)
                child.pack(**options)
            except Exception:
                try:
                    child.pack(fill="x")
                except Exception:
                    pass

        self._ai_saved_pack = []

        try:
            self.ai_canvas.yview_moveto(0)
        except Exception:
            pass

        try:
            self.status.config(text="IMAGE / AI")
        except Exception:
            pass

    def open_model_manager(self):
        """Open filesystem-only local model/workflow readiness."""
        try:
            from genesis.model_registry import open_model_manager

            manager = open_model_manager(self)
            manager.transient(self)
            self.status.config(text="Workflow / Model Manager opened")
        except Exception as exc:
            messagebox.showerror(
                APP_NAME,
                f"Could not open Workflow / Model Manager:\n{exc}"
            )

    def refresh_system_statuses(self):
        if getattr(self, "_status_refreshing", False):
            return
        self._status_refreshing = True

        def worker():
            snapshot = integrations.status_snapshot()
            self.after(0, lambda: self._apply_system_statuses(snapshot))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_system_statuses(self, snapshot):
        self._status_refreshing = False

        def nav(label, name, online, installed=True, blocked=False):
            if online:
                label.config(text=f"● {name}: ONLINE", fg="#4fd18b")
            elif blocked:
                label.config(text=f"● {name}: READ-ONLY", fg="#e0a84f")
            elif installed:
                label.config(text=f"● {name}: STOPPED", fg="#9da9b8")
            else:
                label.config(text=f"● {name}: UNAVAILABLE", fg="#d16a6a")

        nav(
            self.nav_camera_status,
            "Cameras",
            snapshot["go2rtc_online"],
            installed=True
        )
        nav(
            self.nav_comfy_status,
            "ComfyUI",
            snapshot["comfy_online"],
            snapshot["comfy_installed"]
        )
        nav(
            self.nav_llama_status,
            "LLM",
            snapshot["llama_online"],
            snapshot["llama_installed"]
        )
        nav(
            self.nav_media_status,
            "Media",
            snapshot["jellyfin_server"],
            installed=True
        )

        llama_state = "ONLINE" if snapshot["llama_online"] else (
            "STOPPED" if snapshot["llama_installed"] else "UNAVAILABLE"
        )
        self.llama_status_label.config(text=f"llama.cpp {llama_state}")
        self.llama_detail_label.config(
            text=(
                f"{snapshot['llama_model']} · context "
                f"{snapshot['llama_context']:,} · {snapshot['llama_endpoint']} · "
                "RX 9060 XT / ROCm build"
            )
        )

        comfy_state = "ONLINE" if snapshot["comfy_online"] else (
            "STOPPED" if snapshot["comfy_installed"] else "UNAVAILABLE"
        )
        self.comfy_status_label.config(text=f"ComfyUI {comfy_state}")
        self.comfy_detail_label.config(
            text=f"{snapshot['comfy_gpu']} · {integrations.COMFYUI_URL}"
        )

        media_state = "ONLINE" if snapshot["jellyfin_server"] else "SERVER OFFLINE"
        desktop_state = "desktop running" if snapshot["jellyfin_desktop"] else "desktop closed"
        self.media_status_label.config(
            text=f"Jellyfin {media_state} · {desktop_state}"
        )

        self.status.config(text="SYSTEM STATUS UPDATED")

if __name__=="__main__":
    PhotoStudio().mainloop()
