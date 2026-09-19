from pathlib import Path
import shutil
import subprocess

import pytest
from PIL import Image, ImageDraw

from genesis.media_functions import (
    extract_media,
    find_duplicates_in_folder,
    group_faces,
    probe_media,
    scan_media,
    upscale_enhance,
)


def _make_image(path: Path) -> None:
    image = Image.new("RGB", (64, 48), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, 40, 35), fill="black")
    image.save(path)


def test_scan_duplicates_and_fallback_enhance(tmp_path):
    source = tmp_path / "a.png"
    _make_image(source)
    (tmp_path / "a-copy.png").write_bytes(source.read_bytes())
    items = scan_media(tmp_path)
    assert {item["name"] for item in items} == {"a.png", "a-copy.png"}
    duplicates = find_duplicates_in_folder(tmp_path)
    assert len(duplicates["exact_groups"]) == 1
    assert set(duplicates["exact_groups"][0]) == {
        str(source.resolve()), str((tmp_path / "a-copy.png").resolve())
    }

    output = tmp_path / "enhanced.png"
    result = upscale_enhance(source, output, scale=2, prefer_ai=False)
    assert result.backend == "pillow"
    with Image.open(output) as image:
        assert image.size == (128, 96)


def test_group_faces_clusters_similar_embeddings():
    scan = [
        {"path": "a.jpg", "faces": [{"embedding": [1.0, 0.0], "bbox": [0, 0, 1, 1], "det_score": 0.9}]},
        {"path": "b.jpg", "faces": [{"embedding": [0.99, 0.01], "bbox": [0, 0, 1, 1], "det_score": 0.9}]},
        {"path": "c.jpg", "faces": [{"embedding": [0.0, 1.0], "bbox": [0, 0, 1, 1], "det_score": 0.9}]},
    ]
    groups = group_faces(scan, similarity=0.8)
    assert [group["count"] for group in groups] == [2, 1]


@pytest.mark.skipif(shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
                    reason="FFmpeg tools unavailable")
def test_extract_audio_and_silent_video(tmp_path):
    source = tmp_path / "source.mp4"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=160x120:rate=12",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
        "-t", "0.6", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", str(source),
    ], check=True)

    audio = extract_media(source, tmp_path / "audio.mp3", kind="audio")
    video = extract_media(source, tmp_path / "silent.mp4", kind="video")
    audio_info = probe_media(audio.output)
    video_info = probe_media(video.output)
    assert audio_info["has_audio"] and not audio_info["has_video"]
    assert video_info["has_video"] and not video_info["has_audio"]


@pytest.mark.parametrize("operation", ["extract_media", "remove_background", "upscale_enhance"])
def test_operations_preserve_original(tmp_path, operation):
    from genesis import media_functions
    source = tmp_path / "original.png"
    Image.new("RGB", (8, 8), "red").save(source)
    before = source.read_bytes()
    with pytest.raises(media_functions.MediaFunctionError, match="original"):
        getattr(media_functions, operation)(source, source)
    assert source.read_bytes() == before
