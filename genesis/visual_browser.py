"""Read-only thumbnail picker and viewer; no database or service dependencies."""
from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageOps, ImageTk

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}


def revision(path):
    path = Path(path)
    stat = path.stat()
    return (str(path.resolve()), stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)


def folder_entries(folder, newest=False):
    """Only enumerate the explicitly requested directory; never scan recursively."""
    folder = Path(folder).expanduser().resolve(strict=True)
    directories, files = [], []
    for path in folder.iterdir():
        try:
            if path.is_dir():
                directories.append(path)
            elif path.is_file() and path.suffix.lower() in EXTENSIONS:
                files.append((path, path.stat().st_mtime_ns))
        except OSError:
            continue
    directories.sort(key=lambda p: (p.name.casefold(), p.name))
    files.sort(key=lambda pair: (-pair[1], pair[0].name.casefold()) if newest
               else (pair[0].name.casefold(), pair[0].name))
    return folder, directories, [p for p, _ in files]


def read_preview(path, bound):
    """Decode locally for display only. Preserve source bytes and EXIF orientation."""
    before = revision(path)
    with Image.open(path) as source:
        oriented = ImageOps.exif_transpose(source)
        dimensions = oriented.size
        oriented.thumbnail((bound, bound), Image.Resampling.LANCZOS)
        display = oriented.convert('RGBA')
    if before != revision(path):
        raise OSError('Image changed while loading. Refresh to try again.')
    return display, dimensions, before


class ThumbnailCache:
    """Bounded, revision-aware memory cache. Never writes beside source images."""
    def __init__(self, limit=96):
        self.limit = limit
        self._items = OrderedDict()
        self._lock = Lock()

    def get(self, path, bound):
        key = (revision(path), bound)
        with self._lock:
            if key in self._items:
                self._items.move_to_end(key)
                return self._items[key].copy()
        image, _, version = read_preview(path, bound)
        with self._lock:
            self._items[(version, bound)] = image.copy()
            while len(self._items) > self.limit:
                self._items.popitem(last=False)
        return image


class AsyncFrame(ttk.Frame):
    """Workers do IO/Pillow only; Tk updates are polled on the UI thread."""
    def __init__(self, parent, workers=2):
        super().__init__(parent)
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix='genesis-view')
        self._pending = []
        self._closed = False
        self._poll_id = self.after(40, self._poll)

    def submit(self, fn, callback):
        future = self._pool.submit(fn)
        self._pending.append((future, callback))
        return future

    def _poll(self):
        self._poll_id = None
        if self._closed:
            return
        pending, self._pending = self._pending, []
        for future, callback in pending:
            if future.cancelled():
                continue
            if not future.done():
                self._pending.append((future, callback))
                continue
            try:
                value, error = future.result(), None
            except Exception as exc:
                value, error = None, exc
            callback(value, error)
        self._poll_id = self.after(40, self._poll)

    def destroy(self):
        if not self._closed:
            self._closed = True
            if self._poll_id:
                self.after_cancel(self._poll_id)
            for future, _ in self._pending:
                future.cancel()
            self._pending.clear()
            self._pool.shutdown(wait=False, cancel_futures=True)
        super().destroy()


class ImageViewer(AsyncFrame):
    """Reusable fit/zoom/pan preview, isolated from the editor's unsaved state."""
    def __init__(self, parent):
        super().__init__(parent, workers=1)
        self.path = None
        self.image = self.photo = None
        self.dimensions = None
        self.zoom = 1.0
        self.pan = [0, 0]
        self._request = 0
        self._loading = None
        self._drag = None
        bar = ttk.Frame(self)
        bar.pack(fill='x')
        for label, command in [('Fit', self.fit), ('−', lambda: self.change_zoom(.8)),
                               ('+', lambda: self.change_zoom(1.25))]:
            ttk.Button(bar, text=label, command=command, width=5).pack(side='left', padx=2)
        self.zoom_label = ttk.Label(bar, text='100%')
        self.zoom_label.pack(side='left', padx=8)
        self.canvas = tk.Canvas(self, bg='#1a1d1b', highlightthickness=0, width=320, height=360)
        self.canvas.pack(fill='both', expand=True, pady=8)
        self.info = ttk.Label(self, text='Click a thumbnail to preview.', wraplength=340)
        self.info.pack(fill='x')
        self.canvas.bind('<Configure>', lambda _: self.render())
        self.canvas.bind('<ButtonPress-1>', self._press)
        self.canvas.bind('<B1-Motion>', self._move)
        self.canvas.bind('<ButtonRelease-1>', lambda _: setattr(self, '_drag', None))
        self.canvas.bind('<Button-4>', lambda _: self.change_zoom(1.15))
        self.canvas.bind('<Button-5>', lambda _: self.change_zoom(1/1.15))
        self.canvas.bind('<MouseWheel>', lambda e: self.change_zoom(1.15 if e.delta > 0 else 1/1.15))

    def clear(self):
        self._request += 1
        if self._loading:
            self._loading.cancel()
        self.path = self.image = self.photo = self.dimensions = None
        self.info.config(text='Click a thumbnail to preview.')
        self.canvas.delete('all')

    def load(self, path):
        self.clear()
        request = self._request
        path = Path(path)
        self.info.config(text=f'Loading {path.name}…')
        def ready(value, error):
            if request != self._request:
                return
            if error:
                self.info.config(text=f'Cannot preview {path.name}: {error}')
                return
            self.image, self.dimensions, _ = value
            self.path = path
            w, h = self.dimensions
            self.info.config(text=f'{path.name}\n{w} × {h}\n{path}\nRead-only preview · display capped at 1600 px')
            self.fit()
        self._loading = self.submit(lambda: read_preview(path, 1600), ready)

    def fit(self):
        self.zoom, self.pan = 1.0, [0, 0]
        self.render()

    def change_zoom(self, factor):
        self.zoom = max(.1, min(8, self.zoom * factor))
        self.render()

    def _press(self, event):
        self._drag = (event.x, event.y, *self.pan)

    def _move(self, event):
        if self._drag:
            x, y, px, py = self._drag
            self.pan = [px + event.x - x, py + event.y - y]
            self.render()

    def render(self):
        self.canvas.delete('all')
        self.zoom_label.config(text=f'{self.zoom * 100:.0f}%')
        if self.image is None:
            return
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        scale = min(cw/self.image.width, ch/self.image.height) * self.zoom
        # Crop the visible source before resize, keeping zoom rendering memory bounded.
        ox = (cw-self.image.width*scale)/2 + self.pan[0]
        oy = (ch-self.image.height*scale)/2 + self.pan[1]
        left, top = max(0, -ox/scale), max(0, -oy/scale)
        right = min(self.image.width, (cw-ox)/scale)
        bottom = min(self.image.height, (ch-oy)/scale)
        if right <= left or bottom <= top:
            return
        crop = self.image.crop((int(left), int(top), int(right)+1, int(bottom)+1))
        crop.thumbnail((max(1, int(crop.width*scale)), max(1, int(crop.height*scale))), Image.Resampling.LANCZOS)
        if scale > 1:
            crop = crop.resize((max(1, int(crop.width*scale)), max(1, int(crop.height*scale))), Image.Resampling.BILINEAR)
        self.photo = ImageTk.PhotoImage(crop, master=self.canvas)
        self.canvas.create_image(max(0, ox), max(0, oy), image=self.photo, anchor='nw')


class ImageCompareViewer(ttk.Frame):
    """Reusable, read-only side-by-side comparison using the shared viewer."""
    def __init__(self, parent, left=None, right=None):
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        ttk.Label(self, text='LEFT').grid(row=0, column=0, sticky='w', padx=8)
        ttk.Label(self, text='RIGHT').grid(row=0, column=1, sticky='w', padx=8)
        self.left = ImageViewer(self)
        self.right = ImageViewer(self)
        self.left.grid(row=1, column=0, sticky='nsew', padx=(0, 4))
        self.right.grid(row=1, column=1, sticky='nsew', padx=(4, 0))
        if left is not None and right is not None:
            self.load(left, right)

    def load(self, left, right):
        self.left.load(left)
        self.right.load(right)


def compare_images(parent, left, right):
    """Open a non-destructive comparison window for two explicit image paths."""
    paths = tuple(Path(path) for path in (left, right))
    if any(not path.is_file() for path in paths):
        raise FileNotFoundError('Both comparison images must exist.')
    win = tk.Toplevel(parent)
    win.title('GENESIS · Image Viewer / Compare')
    win.geometry('1320x760')
    win.minsize(900, 560)
    win.transient(parent.winfo_toplevel())
    viewer = ImageCompareViewer(win, *paths)
    viewer.pack(fill='both', expand=True, padx=12, pady=12)
    ttk.Button(win, text='Close comparison', command=win.destroy).pack(pady=(0, 12))
    win.bind('<Escape>', lambda _: win.destroy())
    return win


class VisualBrowser(AsyncFrame):
    PAGE_SIZE = 24

    def __init__(self, parent, initial_folder=None, multiple=False, on_accept=None):
        super().__init__(parent)
        self.multiple, self.on_accept = multiple, on_accept
        self.folder = None
        self.files, self.directories = [], []
        self.selected = OrderedDict()
        self.page, self._generation = 0, 0
        self._scan = None
        self._thumb_jobs, self._tiles, self._photos = [], [], []
        self.cache = ThumbnailCache()
        self.path_var = tk.StringVar(value=str(initial_folder or Path.home()))
        self.sort_var = tk.StringVar(value='Name')
        self.size_var = tk.StringVar(value='160')
        nav = ttk.Frame(self)
        nav.grid(row=0, column=0, sticky='ew', pady=8)
        ttk.Button(nav, text='Up', command=self.up, width=5).pack(side='left')
        entry = ttk.Entry(nav, textvariable=self.path_var)
        entry.pack(side='left', fill='x', expand=True, padx=7)
        entry.bind('<Return>', lambda _: self.open_folder(self.path_var.get()))
        ttk.Button(nav, text='Go / Refresh', command=lambda: self.open_folder(self.path_var.get())).pack(side='left')
        ttk.Label(nav, text='  Sort:').pack(side='left')
        sort = ttk.Combobox(nav, textvariable=self.sort_var, values=['Name', 'Newest'], width=8, state='readonly')
        sort.pack(side='left', padx=4)
        sort.bind('<<ComboboxSelected>>', lambda _: self.open_folder(self.folder) if self.folder else None)
        ttk.Label(nav, text='  Thumbnails:').pack(side='left')
        size = ttk.Combobox(nav, textvariable=self.size_var, values=['128', '160', '192'], width=5, state='readonly')
        size.pack(side='left', padx=4)
        size.bind('<<ComboboxSelected>>', lambda _: self.show_page(self.page))
        body = ttk.Panedwindow(self, orient='horizontal')
        body.grid(row=1, column=0, sticky='nsew')
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        folders, centre, right = ttk.Frame(body), ttk.Frame(body), ttk.Frame(body)
        body.add(folders, weight=1); body.add(centre, weight=3); body.add(right, weight=2)
        ttk.Label(folders, text='Folders · double-click to open').pack(anchor='w', pady=5)
        self.folder_list = tk.Listbox(folders, exportselection=False, width=22)
        folder_scroll = ttk.Scrollbar(folders, orient='vertical', command=self.folder_list.yview)
        self.folder_list.configure(yscrollcommand=folder_scroll.set)
        folder_scroll.pack(side='right', fill='y')
        self.folder_list.pack(fill='both', expand=True)
        self.folder_list.bind('<Double-Button-1>', self._enter_folder)
        self.folder_list.bind('<Return>', self._enter_folder)
        paging = ttk.Frame(centre); paging.pack(fill='x', padx=8, pady=4)
        self.previous = ttk.Button(paging, text='Previous', command=lambda: self.show_page(self.page-1))
        self.previous.pack(side='left')
        self.page_label = ttk.Label(paging, text='No folder open'); self.page_label.pack(side='left', padx=8)
        self.next = ttk.Button(paging, text='Next', command=lambda: self.show_page(self.page+1))
        self.next.pack(side='right')
        holder = ttk.Frame(centre); holder.pack(fill='both', expand=True, padx=8)
        self.canvas = tk.Canvas(holder, bg='#171b18', highlightthickness=0, width=500)
        scroll = ttk.Scrollbar(holder, orient='vertical', command=self.canvas.yview)
        scroll.pack(side='right', fill='y'); self.canvas.pack(side='left', fill='both', expand=True)
        self.canvas.configure(yscrollcommand=scroll.set)
        self.grid_frame = ttk.Frame(self.canvas)
        self._window = self.canvas.create_window(0, 0, window=self.grid_frame, anchor='nw')
        self.grid_frame.bind('<Configure>', lambda _: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', self._resize)
        self._bind_scroll(self.canvas)
        self.viewer = ImageViewer(right); self.viewer.pack(fill='both', expand=True, padx=8, pady=4)
        self.status = ttk.Label(self, text='No files selected.', wraplength=1000)
        self.status.grid(row=2, column=0, sticky='ew', pady=8)
        actions = ttk.Frame(self); actions.grid(row=3, column=0, sticky='ew', pady=5)
        ttk.Button(actions, text='Clear selection', command=self.clear_selection).pack(side='left')
        self.selection_label = ttk.Label(actions, text='0 selected'); self.selection_label.pack(side='left', padx=10)
        self.compare_button = ttk.Button(
            actions,
            text='Compare selected',
            command=self.compare_selected,
            state='disabled',
        )
        if multiple:
            self.compare_button.pack(side='left', padx=4)
        self.accept_button = ttk.Button(actions, text='Use selected images' if multiple else 'Open selected image', command=self.accept, state='disabled')
        self.accept_button.pack(side='right')
        self.open_folder(self.path_var.get())

    def _bind_scroll(self, widget):
        widget.bind('<Button-4>', lambda _: self.canvas.yview_scroll(-1, 'units'))
        widget.bind('<Button-5>', lambda _: self.canvas.yview_scroll(1, 'units'))
        widget.bind('<MouseWheel>', lambda e: self.canvas.yview_scroll(-1 if e.delta > 0 else 1, 'units'))

    def _resize(self, event):
        self.canvas.itemconfigure(self._window, width=event.width)
        self._layout_tiles()

    def _layout_tiles(self):
        columns = max(1, self.canvas.winfo_width() // (int(self.size_var.get())+25))
        for i, (frame, _, _) in enumerate(self._tiles):
            frame.grid(row=i//columns, column=i%columns, sticky='n', padx=5, pady=5)

    def _enter_folder(self, _event=None):
        choice = self.folder_list.curselection()
        if choice and choice[0] < len(self.directories):
            self.open_folder(self.directories[choice[0]])

    def up(self):
        if self.folder is not None:
            self.open_folder(self.folder.parent)

    def open_folder(self, folder):
        if not folder:
            return
        self._generation += 1
        generation = self._generation
        if self._scan:
            self._scan.cancel()
        for job in self._thumb_jobs:
            job.cancel()
        self.status.config(text='Reading folder…')
        newest = self.sort_var.get() == 'Newest'
        def ready(value, error):
            if generation != self._generation:
                return
            self._scan = None
            if error:
                self.status.config(text=f'Cannot open folder: {error}')
                return
            self.folder, self.directories, self.files = value
            self.path_var.set(str(self.folder))
            self.folder_list.delete(0, 'end')
            for path in self.directories:
                self.folder_list.insert('end', path.name)
            self.viewer.clear()
            self.show_page(0)
        self._scan = self.submit(lambda: folder_entries(folder, newest), ready)

    def show_page(self, page):
        # A pending folder navigation owns the next render; do not invalidate it.
        if self._scan is not None:
            return
        self._generation += 1
        generation = self._generation
        for job in self._thumb_jobs:
            job.cancel()
        self._thumb_jobs.clear()
        for frame, _, _ in self._tiles:
            frame.destroy()
        self._tiles, self._photos = [], []
        pages = max(1, (len(self.files)+self.PAGE_SIZE-1)//self.PAGE_SIZE)
        self.page = max(0, min(page, pages-1))
        self.previous.config(state='normal' if self.page else 'disabled')
        self.next.config(state='normal' if self.page < pages-1 else 'disabled')
        self.page_label.config(text=f'Page {self.page+1} / {pages}')
        self.status.config(text=f'{len(self.files)} images in this folder. Click to preview; check to select. No files are modified.')
        bound = int(self.size_var.get())
        for path in self.files[self.page*self.PAGE_SIZE:(self.page+1)*self.PAGE_SIZE]:
            frame = ttk.Frame(self.grid_frame, padding=4, relief='solid', borderwidth=1)
            label = ttk.Label(frame, text='Loading…', anchor='center', width=20)
            label.pack()
            label.bind('<Button-1>', lambda _, p=path: self.viewer.load(p))
            self._bind_scroll(label)
            var = tk.BooleanVar(value=path in self.selected)
            check = ttk.Checkbutton(frame, text=path.name[:24], variable=var,
                                    command=lambda p=path, v=var: self.toggle(p, v.get()))
            check.pack(anchor='w', pady=(5, 0))
            self._bind_scroll(check)
            self._tiles.append((frame, path, var))
            def ready(image, error, label=label, generation=generation):
                if generation != self._generation or not label.winfo_exists():
                    return
                if error:
                    label.config(text='Preview unavailable', image='')
                    return
                photo = ImageTk.PhotoImage(image, master=label)
                self._photos.append(photo)
                label.config(text='', image=photo)
            self._thumb_jobs.append(self.submit(lambda p=path: self.cache.get(p, bound), ready))
        self._layout_tiles()
        self.canvas.yview_moveto(0)
        self._sync_selection()

    def toggle(self, path, checked):
        if checked:
            if not self.multiple:
                self.selected.clear()
            self.selected[path] = None
            self.viewer.load(path)
        else:
            self.selected.pop(path, None)
        self._sync_selection()

    def _sync_selection(self):
        for _, path, var in self._tiles:
            var.set(path in self.selected)
        self.selection_label.config(text=f'{len(self.selected)} selected (all browsed folders)')
        self.compare_button.config(state='normal' if len(self.selected) == 2 else 'disabled')
        self.accept_button.config(state='normal' if self.selected else 'disabled')

    def compare_selected(self):
        paths = tuple(self.selected)
        if len(paths) != 2:
            self.status.config(text='Select exactly two images to compare.')
            return None
        try:
            return compare_images(self, *paths)
        except OSError as exc:
            self.status.config(text=f'Cannot compare selected images: {exc}')
            return None

    def clear_selection(self):
        self.selected.clear()
        self._sync_selection()

    def accept(self):
        paths = tuple(self.selected)
        if not paths:
            return
        missing = [p for p in paths if not p.is_file()]
        if missing:
            self.status.config(text='A selected file is missing. Clear or update the selection before continuing.')
            return
        if self.on_accept:
            self.on_accept(paths)


def pick_images(parent, initial_folder=None, multiple=False):
    """Modal explicit selection. Cancel returns None; does not alter caller state."""
    result = None
    win = tk.Toplevel(parent)
    win.title('GENESIS · Visual Image Picker / Viewer')
    win.geometry('1240x780')
    win.minsize(940, 580)
    win.transient(parent.winfo_toplevel())
    def accept(paths):
        nonlocal result
        result = paths
        win.destroy()
    browser = VisualBrowser(win, initial_folder, multiple, on_accept=accept)
    ttk.Button(win, text='Cancel — keep current image', command=win.destroy).pack(side='bottom', pady=(0, 10))
    browser.pack(fill='both', expand=True, padx=12, pady=8)
    win.bind('<Escape>', lambda _: win.destroy())
    previous_grab = parent.grab_current()
    try:
        win.wait_visibility()
        win.grab_set()
        parent.wait_window(win)
    except tk.TclError:
        if win.winfo_exists():
            raise
    finally:
        if win.winfo_exists():
            win.destroy()
        if previous_grab is not None and previous_grab.winfo_exists():
            previous_grab.grab_set()
    return result
