"""UI-independent media functions for GENESIS c0ckpit.

These helpers deliberately avoid assumptions about tabs or page layout.  They
provide stable operations that any current or future UI can call.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

from genesis.comfy_client import ComfyClient, ComfyError

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".mpeg", ".mpg"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wma"}
MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GPU_TOOLS_PYTHON = Path.home() / "miniforge3/envs/genesis-gpu-tools/bin/python"
COMFY_PYTHON = Path.home() / "miniforge3/envs/comfyui-reactor-rocm/bin/python"
BACKGROUND_WORKER = PROJECT_ROOT / "genesis/gpu_background_worker.py"
FACE_WORKER = PROJECT_ROOT / "genesis/gpu_face_worker.py"
UPSCALE_MODEL = Path.home() / "AI/ComfyUI/models/upscale_models/4x-UltraSharp.safetensors"


class MediaFunctionError(RuntimeError):
    """Raised when a media operation cannot be completed safely."""


@dataclass(slots=True)
class OperationResult:
    output: Path | None
    backend: str
    details: dict = field(default_factory=dict)


def _require_file(path: str | Path) -> Path:
    value = Path(path).expanduser().resolve()
    if not value.is_file():
        raise FileNotFoundError(value)
    return value


def _run(command: Sequence[str], *, timeout: int = 600) -> subprocess.CompletedProcess:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise MediaFunctionError(detail[-4000:] or f"Command failed: {command[0]}")
    return result

def probe_media(path: str | Path) -> dict:
    """Return normalized FFprobe metadata for audio/video files."""
    source = _require_file(path)
    result = _run([
        "ffprobe", "-v", "error", "-show_format", "-show_streams",
        "-of", "json", str(source),
    ], timeout=30)
    payload = json.loads(result.stdout or "{}")
    streams = payload.get("streams") or []
    return {
        "path": str(source),
        "duration": float((payload.get("format") or {}).get("duration") or 0),
        "size": int((payload.get("format") or {}).get("size") or source.stat().st_size),
        "format": (payload.get("format") or {}).get("format_name", ""),
        "has_audio": any(item.get("codec_type") == "audio" for item in streams),
        "has_video": any(item.get("codec_type") == "video" for item in streams),
        "streams": streams,
    }


def _trim_args(start: float | None, end: float | None) -> list[str]:
    args: list[str] = []
    if start is not None:
        if start < 0:
            raise ValueError("start must be zero or greater")
        args += ["-ss", str(float(start))]
    if end is not None:
        if end < 0 or (start is not None and end <= start):
            raise ValueError("end must be greater than start")
        args += ["-to", str(float(end))]
    return args

def extract_media(
    path: str | Path,
    output: str | Path,
    *,
    kind: str = "audio",
    audio_format: str = "mp3",
    start: float | None = None,
    end: float | None = None,
) -> OperationResult:
    """Extract audio or a silent video from one source file."""
    source = _require_file(path)
    target = Path(output).expanduser().resolve()
    if target == source or (target.exists() and target.samefile(source)):
        raise MediaFunctionError("Choose a different output file; the original must be preserved")
    target.parent.mkdir(parents=True, exist_ok=True)
    info = probe_media(source)
    trim = _trim_args(start, end)
    if kind == "audio":
        if not info["has_audio"]:
            raise MediaFunctionError("Source has no audio stream")
        fmt = audio_format.lower().lstrip(".")
        codecs = {
            "mp3": ["-c:a", "libmp3lame", "-q:a", "2"],
            "wav": ["-c:a", "pcm_s16le"],
            "flac": ["-c:a", "flac"],
            "m4a": ["-c:a", "aac", "-b:a", "256k"],
        }
        if fmt not in codecs:
            raise ValueError(f"Unsupported audio format: {audio_format}")
        _run(["ffmpeg", "-y", *trim, "-i", str(source), "-vn", *codecs[fmt], str(target)])
        return OperationResult(target, "ffmpeg", {"kind": "audio", "format": fmt})
    if kind == "video":
        if not info["has_video"]:
            raise MediaFunctionError("Source has no video stream")
        command = ["ffmpeg", "-y", *trim, "-i", str(source)]
        if trim:
            command += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k"]
        else:
            command += ["-c", "copy"]
        command.append(str(target))
        _run(command)
        return OperationResult(target, "ffmpeg", {"kind": "video", "audio_preserved": bool(info["has_audio"])})
    raise ValueError("kind must be 'audio' or 'video'")


def remove_background(path: str | Path, output: str | Path) -> OperationResult:
    """Remove an image background with the isolated ROCm rembg worker."""
    source = _require_file(path)
    target = Path(output).expanduser().resolve()
    if target == source or (target.exists() and target.samefile(source)):
        raise MediaFunctionError("Choose a different output file; the original must be preserved")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not GPU_TOOLS_PYTHON.is_file():
        raise MediaFunctionError(f"Background-removal runtime missing: {GPU_TOOLS_PYTHON}")
    if not BACKGROUND_WORKER.is_file():
        raise MediaFunctionError(f"Background-removal worker missing: {BACKGROUND_WORKER}")
    with tempfile.TemporaryDirectory(prefix="genesis-rmbg-") as temp:
        temp_dir = Path(temp)
        result = _run([str(GPU_TOOLS_PYTHON), str(BACKGROUND_WORKER), str(temp_dir), str(source)], timeout=300)
        generated = temp_dir / f"{source.stem}_cutout.png"
        if not generated.is_file():
            raise MediaFunctionError(result.stdout or "Background remover produced no output")
        shutil.copy2(generated, target)
    return OperationResult(target, "rembg-rocm", {"model": "u2net"})


def _enhance_pillow(source: Path, target: Path, scale: float) -> OperationResult:
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert("RGB")
        if scale != 1:
            size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
            image = image.resize(size, Image.Resampling.LANCZOS)
        image = ImageEnhance.Contrast(image).enhance(1.04)
        image = ImageEnhance.Sharpness(image).enhance(1.18)
        image = image.filter(ImageFilter.UnsharpMask(radius=1.2, percent=80, threshold=3))
        image.save(target)
    return OperationResult(target, "pillow", {"scale": scale, "mode": "enhance"})


def upscale_enhance(
    path: str | Path,
    output: str | Path,
    *,
    scale: float = 2.0,
    prefer_ai: bool = True,
) -> OperationResult:
    """Upscale/enhance an image, preferring 4x-UltraSharp through ComfyUI."""
    source = _require_file(path)
    target = Path(output).expanduser().resolve()
    if target == source or (target.exists() and target.samefile(source)):
        raise MediaFunctionError("Choose a different output file; the original must be preserved")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("scale must be greater than zero")
    if prefer_ai and UPSCALE_MODEL.is_file():
        try:
            client = ComfyClient(timeout=8)
            client.system_stats()
            uploaded = client.upload_image(source, subfolder="genesis_media")
            prompt = {
                "1": {"class_type": "LoadImage", "inputs": {"image": f"{uploaded.get('subfolder','')}/{uploaded['name']}"}},
                "2": {"class_type": "UpscaleModelLoader", "inputs": {"model_name": UPSCALE_MODEL.name}},
                "3": {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["2", 0], "image": ["1", 0]}},
                "4": {"class_type": "SaveImage", "inputs": {"filename_prefix": "genesis_upscale", "images": ["3", 0]}},
            }
            prompt_id = client.submit(prompt)
            result = client.wait(prompt_id, timeout=900)
            if result.status != "completed" or not result.outputs:
                raise ComfyError(result.error or "Upscale workflow returned no image")
            target.write_bytes(client.view(result.outputs[0]))
            requested_size = None
            with Image.open(source) as original:
                requested_size = (max(1, round(original.width * scale)), max(1, round(original.height * scale)))
            if scale != 4.0:
                with Image.open(target) as generated:
                    resized = ImageOps.exif_transpose(generated).convert("RGB").resize(requested_size, Image.Resampling.LANCZOS)
                    resized.save(target)
            return OperationResult(target, "comfyui-4x-ultrasharp", {"native_scale": 4.0, "output_scale": scale})
        except (ComfyError, OSError, TimeoutError):
            pass
    return _enhance_pillow(source, target, scale)

def scan_media(folder: str | Path, *, recursive: bool = True) -> list[dict]:
    """Return lightweight metadata for media files without changing the library."""
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    iterator = root.rglob("*") if recursive else root.glob("*")
    found: list[dict] = []
    for path in iterator:
        if not path.is_file() or path.suffix.lower() not in MEDIA_EXTENSIONS:
            continue
        stat = path.stat()
        item = {
            "path": str(path), "name": path.name, "suffix": path.suffix.lower(),
            "size": stat.st_size, "modified": stat.st_mtime,
            "kind": "image" if path.suffix.lower() in IMAGE_EXTENSIONS else
                    "video" if path.suffix.lower() in VIDEO_EXTENSIONS else "audio",
        }
        if item["kind"] == "image":
            try:
                with Image.open(path) as image:
                    item["width"], item["height"] = image.size
            except Exception:
                item["width"], item["height"] = None, None
        found.append(item)
    return sorted(found, key=lambda item: (item["kind"], item["name"].lower()))


def list_camera_devices() -> list[dict]:
    """List Linux V4L2 devices and whether they are currently capturable."""
    devices: list[dict] = []
    for path in sorted(Path("/dev").glob("video*")):
        label = path.name
        capabilities: list[str] = []
        try:
            result = _run(["v4l2-ctl", "-D", "-d", str(path)], timeout=5)
            for raw in result.stdout.splitlines():
                line = raw.strip()
                if "Card type" in line:
                    label = line.split(":", 1)[-1].strip() or label
                elif line and not line.startswith(("Driver", "Bus", "Device Caps", "Capabilities")) and line[0].isalpha():
                    if line in {"Video Capture", "Video Capture Multiplanar", "Video Output", "Streaming", "Read/Write"}:
                        capabilities.append(line)
        except Exception:
            pass
        can_capture = any(value.startswith("Video Capture") for value in capabilities)
        devices.append({
            "path": str(path), "name": label, "can_capture": can_capture,
            "capabilities": sorted(set(capabilities)),
        })
    return devices


def capture_camera_frame(device: str | Path, output: str | Path) -> OperationResult:
    """Capture one still frame from a V4L2 camera without requiring a UI."""
    import cv2

    target = Path(output).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    value = str(device)
    if value.isdigit():
        source = int(value)
    elif value.startswith("/dev/video") and value[len("/dev/video"):].isdigit():
        source = int(value[len("/dev/video"):])
    else:
        source = value
    camera = cv2.VideoCapture(source, cv2.CAP_V4L2)
    try:
        if not camera.isOpened():
            raise MediaFunctionError(f"Could not open camera {device}")
        frame = None
        for _ in range(6):
            ok, candidate = camera.read()
            if ok and candidate is not None:
                frame = candidate
        if frame is None or not cv2.imwrite(str(target), frame):
            raise MediaFunctionError(f"Could not capture frame from {device}")
    finally:
        camera.release()
    return OperationResult(target, "opencv-v4l2", {"device": value})


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dhash(path: Path, size: int = 8) -> int:
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
        pixels = np.asarray(image, dtype=np.int16)
    bits = pixels[:, 1:] > pixels[:, :-1]
    value = 0
    for bit in bits.ravel():
        value = (value << 1) | int(bit)
    return value

def find_duplicates(
    paths: Iterable[str | Path], *, near_distance: int = 6
) -> dict[str, list]:
    """Find exact duplicates and perceptually similar image pairs."""
    files = [Path(value).expanduser().resolve() for value in paths]
    files = [path for path in files if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS]
    exact_groups: dict[str, list[Path]] = {}
    hashes: list[tuple[Path, int]] = []
    for path in files:
        exact_groups.setdefault(_sha256(path), []).append(path)
        try:
            hashes.append((path, _dhash(path)))
        except Exception:
            continue
    exact = [[str(path) for path in group] for group in exact_groups.values() if len(group) > 1]
    exact_pairs = {tuple(sorted((group[0], other))) for group in exact for other in group[1:]}
    near: list[dict] = []
    for index, (left, left_hash) in enumerate(hashes):
        for right, right_hash in hashes[index + 1:]:
            if tuple(sorted((str(left), str(right)))) in exact_pairs:
                continue
            distance = (left_hash ^ right_hash).bit_count()
            if distance <= near_distance:
                near.append({"left": str(left), "right": str(right), "distance": distance})
    near.sort(key=lambda item: item["distance"])
    return {"exact_groups": exact, "near_pairs": near}


def find_duplicates_in_folder(folder: str | Path, *, near_distance: int = 6) -> dict[str, list]:
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    return find_duplicates(
        (path for path in root.rglob("*") if path.is_file()),
        near_distance=near_distance,
    )

def detect_faces(paths: Iterable[str | Path]) -> list[dict]:
    """Run InsightFace once for a batch and return normalized embeddings/bounds."""
    files = [Path(value).expanduser().resolve() for value in paths]
    files = [path for path in files if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS]
    if not files:
        return []
    if not COMFY_PYTHON.is_file() or not FACE_WORKER.is_file():
        raise MediaFunctionError("InsightFace ROCm worker is unavailable")
    requests = "".join(json.dumps({"path": str(path)}) + "\n" for path in files)
    proc = subprocess.run(
        [str(COMFY_PYTHON), str(FACE_WORKER)],
        input=requests, capture_output=True, text=True, timeout=max(120, len(files) * 30), check=False,
    )
    if proc.returncode:
        raise MediaFunctionError((proc.stderr or proc.stdout)[-4000:])
    rows = [line for line in proc.stdout.splitlines() if line.strip()]
    if len(rows) != len(files):
        raise MediaFunctionError("Face worker returned an unexpected response count")
    results: list[dict] = []
    for path, raw in zip(files, rows):
        payload = json.loads(raw)
        if not payload.get("ok"):
            raise MediaFunctionError(payload.get("error") or f"Face scan failed: {path}")
        results.append({"path": str(path), "faces": payload.get("faces") or []})
    return results


def group_faces(scan_results: Iterable[dict], *, similarity: float = 0.55) -> list[dict]:
    """Greedily group face embeddings into people-like clusters for later naming."""
    clusters: list[dict] = []
    for item in scan_results:
        for face in item.get("faces") or []:
            embedding = np.asarray(face.get("embedding") or [], dtype=np.float32)
            if embedding.size == 0:
                continue
            norm = float(np.linalg.norm(embedding))
            if norm:
                embedding = embedding / norm
            best_index, best_score = None, -1.0
            for index, cluster in enumerate(clusters):
                score = float(np.dot(cluster["centroid"], embedding))
                if score > best_score:
                    best_index, best_score = index, score
            member = {
                "path": item.get("path"),
                "bbox": face.get("bbox"),
                "det_score": face.get("det_score"),
            }
            if best_index is not None and best_score >= similarity:
                cluster = clusters[best_index]
                count = len(cluster["members"])
                centroid = (cluster["centroid"] * count + embedding) / (count + 1)
                centroid_norm = float(np.linalg.norm(centroid))
                if centroid_norm:
                    centroid = centroid / centroid_norm
                cluster["centroid"] = centroid
                cluster["members"].append(member)
            else:
                clusters.append({"centroid": embedding, "members": [member]})
    return [
        {"group_id": index + 1, "count": len(cluster["members"]), "members": cluster["members"]}
        for index, cluster in enumerate(clusters)
    ]


def face_organizer_scan(folder: str | Path, *, similarity: float = 0.55) -> list[dict]:
    """Detect and group faces from every supported image under a folder."""
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)
    images = [
        path for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    return group_faces(detect_faces(images), similarity=similarity)
