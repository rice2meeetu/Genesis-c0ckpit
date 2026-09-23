"""Bounded CPU-only, linked-file Canvas layers. Source images are never edited."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import tempfile
import uuid

from PIL import Image, ImageOps

MAX_PIXELS = 32_000_000
MAX_DIMENSION = 16_384
MAX_LAYERS = 32
MAX_PREVIEW = 1600
MAX_HISTORY = 30
MAX_PROJECT_BYTES = 256_000
_LAYER_KEYS = {"id", "name", "path", "x", "y", "width", "height",
               "opacity", "visible", "rotation"}
_STATE_KEYS = {"width", "height", "layers", "selected_id"}


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    if not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return value


def _size(width, height):
    if type(width) is not int or type(height) is not int:
        raise ValueError("Image dimensions must be integers")
    if not (1 <= width <= MAX_DIMENSION and 1 <= height <= MAX_DIMENSION):
        raise ValueError("Image dimensions exceed the Canvas limits")
    if width * height > MAX_PIXELS:
        raise ValueError("Image exceeds the 32 megapixel Canvas limit")


def _image(path):
    """Check the header before decoding; always detach from the input file."""
    with Image.open(path) as source:
        _size(*source.size)
        return ImageOps.exif_transpose(source).convert("RGBA")


class CanvasDocument:
    """Layers are ordered bottom to top; history stores metadata only."""

    def __init__(self):
        self.width = self.height = 0
        self.layers = []
        self.selected_id = None
        self._undo = []
        self._redo = []
        self._source_paths = set()

    @property
    def can_undo(self):
        return bool(self._undo)

    @property
    def can_redo(self):
        return bool(self._redo)

    def _snapshot(self):
        return {"width": self.width, "height": self.height,
                "layers": [dict(layer) for layer in self.layers],
                "selected_id": self.selected_id}

    def _restore(self, state):
        self.width, self.height = state["width"], state["height"]
        self.layers = [dict(layer) for layer in state["layers"]]
        self.selected_id = state["selected_id"]

    def _checkpoint(self):
        self._undo.append(self._snapshot())
        self._undo = self._undo[-MAX_HISTORY:]
        self._redo.clear()

    def _layer(self, layer_id):
        return next((layer for layer in self.layers if layer["id"] == layer_id), None)

    def add_image(self, path):
        if len(self.layers) >= MAX_LAYERS:
            raise ValueError("Canvas supports at most 32 layers")
        resolved = str(Path(path).expanduser().resolve(strict=True))
        with _image(resolved) as source:
            width, height = source.size
        self._checkpoint()
        if not self.width:
            self.width, self.height = width, height
        ratio = min(1.0, self.width / width, self.height / height)
        width, height = max(1, round(width * ratio)), max(1, round(height * ratio))
        layer_id = uuid.uuid4().hex
        self.layers.append({"id": layer_id, "name": Path(resolved).name[:256],
                            "path": resolved, "x": (self.width - width) / 2,
                            "y": (self.height - height) / 2,
                            "width": width, "height": height,
                            "opacity": 1.0, "visible": True, "rotation": 0.0})
        self._source_paths.add(resolved)
        self.selected_id = layer_id
        return layer_id

    def select_layer(self, layer_id):
        if not self._layer(layer_id) or self.selected_id == layer_id:
            return False
        self.selected_id = layer_id
        return True

    def update_layer(self, layer_id, **updates):
        layer = self._layer(layer_id)
        if layer is None:
            return False
        if set(updates) - (_LAYER_KEYS - {"id", "path"}):
            raise ValueError("Unsupported layer property")
        updated = dict(layer)
        for key, value in updates.items():
            if key in {"x", "y", "width", "height", "opacity", "rotation"}:
                value = _number(value, key)
                low, high = (0.0, 1.0) if key == "opacity" else (
                    (-3600.0, 3600.0) if key == "rotation" else
                    ((1, MAX_DIMENSION) if key in {"width", "height"}
                    else (-MAX_DIMENSION, MAX_DIMENSION)))
                value = max(low, min(high, value))
                if key in {"width", "height"}:
                    value = round(value)
            elif key == "visible" and type(value) is not bool:
                raise ValueError("Visibility must be boolean")
            elif key == "name":
                if not isinstance(value, str) or not value.strip() or len(value) > 256:
                    raise ValueError("Layer name must contain 1 to 256 characters")
            if key == "rotation":
                value = value % 360.0
            updated[key] = value
        if updated["width"] * updated["height"] > MAX_PIXELS:
            ratio = math.sqrt(MAX_PIXELS / (updated["width"] * updated["height"]))
            updated["width"] = max(1, int(updated["width"] * ratio))
            updated["height"] = max(1, int(updated["height"] * ratio))
        if updated == layer:
            return False
        self._checkpoint()
        layer.update(updated)
        return True

    def duplicate_layer(self, layer_id):
        layer = self._layer(layer_id)
        if layer is None:
            return False
        if len(self.layers) >= MAX_LAYERS:
            raise ValueError("Canvas supports at most 32 layers")
        self._checkpoint()
        duplicate = dict(layer)
        duplicate["id"] = uuid.uuid4().hex
        duplicate["name"] = ("Copy of " + layer["name"])[:256]
        duplicate["x"] = max(-MAX_DIMENSION, min(MAX_DIMENSION, layer["x"] + 24))
        duplicate["y"] = max(-MAX_DIMENSION, min(MAX_DIMENSION, layer["y"] + 24))
        self.layers.insert(self.layers.index(layer) + 1, duplicate)
        self.selected_id = duplicate["id"]
        return duplicate["id"]

    def remove_layer(self, layer_id):
        layer = self._layer(layer_id)
        if layer is None:
            return False
        self._checkpoint()
        index = self.layers.index(layer)
        self.layers.remove(layer)
        if self.selected_id == layer_id:
            self.selected_id = self.layers[min(index, len(self.layers) - 1)]["id"] if self.layers else None
        return True

    def move_layer(self, layer_id, delta):
        layer = self._layer(layer_id)
        if layer is None:
            return False
        if type(delta) is not int:
            raise ValueError("Layer movement must be an integer")
        index = self.layers.index(layer)
        target = max(0, min(len(self.layers) - 1, index + delta))
        if target == index:
            return False
        self._checkpoint()
        self.layers.insert(target, self.layers.pop(index))
        return True

    def clear(self):
        if not self.layers and not self.width:
            return False
        self._checkpoint()
        self.width = self.height = 0
        self.layers = []
        self.selected_id = None
        return True

    def undo(self):
        if not self._undo:
            return False
        self._redo.append(self._snapshot())
        self._restore(self._undo.pop())
        return True

    def redo(self):
        if not self._redo:
            return False
        self._undo.append(self._snapshot())
        self._undo = self._undo[-MAX_HISTORY:]
        self._restore(self._redo.pop())
        return True

    def render(self, bound=None):
        if bound is not None:
            if type(bound) is not int or bound < 1:
                raise ValueError("Preview bound must be a positive integer")
            bound = min(bound, MAX_PREVIEW)
        if not self.width:
            return Image.new("RGBA", (1, 1))
        ratio = min(1.0, bound / max(self.width, self.height)) if bound else 1.0
        size = (max(1, round(self.width * ratio)), max(1, round(self.height * ratio)))
        canvas = Image.new("RGBA", size)
        for layer in self.layers:
            if not layer["visible"] or not layer["opacity"]:
                continue
            with _image(layer["path"]) as source:
                layer_size = (max(1, round(layer["width"] * ratio)),
                              max(1, round(layer["height"] * ratio)))
                resized = source.resize(layer_size, Image.Resampling.LANCZOS)
            try:
                if layer["opacity"] < 1:
                    alpha = resized.getchannel("A")
                    adjusted = alpha.point([round(i * layer["opacity"]) for i in range(256)])
                    resized.putalpha(adjusted)
                    alpha.close()
                    adjusted.close()
                x, y = round(layer["x"] * ratio), round(layer["y"] * ratio)
                if layer.get("rotation", 0):
                    center_x = x + resized.width / 2
                    center_y = y + resized.height / 2
                    rotated = resized.rotate(-layer["rotation"], resample=Image.Resampling.BICUBIC, expand=True)
                    resized.close()
                    resized = rotated
                    x = round(center_x - resized.width / 2)
                    y = round(center_y - resized.height / 2)
                left, top = max(0, x), max(0, y)
                right, bottom = min(size[0], x + resized.width), min(size[1], y + resized.height)
                if right > left and bottom > top:
                    with resized.crop((left - x, top - y, right - x, bottom - y)) as part:
                        canvas.alpha_composite(part, (left, top))
            finally:
                resized.close()
        return canvas

    def _output_path(self, path):
        target = Path(path).expanduser().resolve()
        for source in self._source_paths | {layer["path"] for layer in self.layers}:
            if str(target) == source or (target.exists() and Path(source).exists()
                                        and os.path.samefile(target, source)):
                raise ValueError("Choose a new output path; source images are protected")
        if not target.parent.is_dir():
            raise ValueError("Output folder does not exist")
        return target

    def _atomic_write(self, path, writer):
        target = self._output_path(path)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", dir=target.parent,
                                             prefix=".genesis-canvas-", delete=False) as stream:
                temporary = stream.name
                writer(stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
        return str(target)

    def save_project(self, path):
        data = {"schema": "genesis-canvas", "version": 1, **self._snapshot()}
        self._validate_state(data)
        payload = json.dumps(data, indent=2, allow_nan=False).encode("utf-8")
        return self._atomic_write(path, lambda stream: stream.write(payload))

    @classmethod
    def load_project(cls, path):
        with open(path, "rb") as stream:
            payload = stream.read(MAX_PROJECT_BYTES + 1)
        if len(payload) > MAX_PROJECT_BYTES:
            raise ValueError("Canvas project is too large")
        try:
            data = json.loads(payload)
        except (ValueError, UnicodeError, RecursionError) as error:
            raise ValueError("Invalid Canvas project JSON") from error
        cls._validate_state(data)
        document = cls()
        for layer in data["layers"]:
            layer["path"] = str(Path(layer["path"]).resolve(strict=True))
            with _image(layer["path"]):
                pass
            document._source_paths.add(layer["path"])
        document._restore(data)
        return document

    @staticmethod
    def _validate_state(data):
        if not isinstance(data, dict) or set(data) != _STATE_KEYS | {"schema", "version"}:
            raise ValueError("Invalid Canvas project fields")
        if data["schema"] != "genesis-canvas" or type(data["version"]) is not int or data["version"] != 1:
            raise ValueError("Unsupported Canvas project version")
        layers = data["layers"]
        if not isinstance(layers, list) or len(layers) > MAX_LAYERS:
            raise ValueError("Invalid Canvas layer count")
        width, height = data["width"], data["height"]
        if type(width) is not int or type(height) is not int:
            raise ValueError("Canvas dimensions must be integers")
        if layers or width or height:
            _size(width, height)
        ids = set()
        for layer in layers:
            if not isinstance(layer, dict) or set(layer) != _LAYER_KEYS:
                raise ValueError("Invalid Canvas layer fields")
            identifier = layer["id"]
            if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identifier) or identifier in ids:
                raise ValueError("Invalid or duplicate Canvas layer id")
            ids.add(identifier)
            if not isinstance(layer["name"], str) or not layer["name"].strip() or len(layer["name"]) > 256:
                raise ValueError("Invalid Canvas layer name")
            source = layer["path"]
            if not isinstance(source, str) or len(source) > 4096 or "\x00" in source or not Path(source).is_absolute():
                raise ValueError("Layer source must be an absolute local file path")
            _size(layer["width"], layer["height"])
            for key in ("x", "y"):
                if abs(_number(layer[key], key)) > MAX_DIMENSION:
                    raise ValueError("Layer position exceeds Canvas limits")
            if not 0 <= _number(layer["opacity"], "opacity") <= 1:
                raise ValueError("Layer opacity is out of range")
            rotation = _number(layer["rotation"], "rotation")
            if not 0 <= rotation < 360:
                raise ValueError("Layer rotation is out of range")
            if type(layer["visible"]) is not bool:
                raise ValueError("Layer visibility must be boolean")
        selected = data["selected_id"]
        if selected is not None and (not isinstance(selected, str) or selected not in ids):
            raise ValueError("Invalid selected Canvas layer")

    def export_png(self, path):
        if not self.width:
            raise ValueError("Add an image before exporting the Canvas")
        self._output_path(path)
        with self.render() as image:
            return self._atomic_write(path, lambda stream: image.save(stream, format="PNG"))
