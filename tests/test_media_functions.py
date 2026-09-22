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
def test_extract_audio_and_video_with_audio(tmp_path):
    source = tmp_path / "source.mp4"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=160x120:rate=12",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
        "-t", "0.6", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", str(source),
    ], check=True)

    audio = extract_media(source, tmp_path / "audio.mp3", kind="audio")
    video = extract_media(source, tmp_path / "video.mp4", kind="video")
    audio_info = probe_media(audio.output)
    video_info = probe_media(video.output)
    assert audio_info["has_audio"] and not audio_info["has_video"]
    assert video_info["has_video"] and video_info["has_audio"]


@pytest.mark.parametrize("operation", ["extract_media", "remove_background", "upscale_enhance"])
def test_operations_preserve_original(tmp_path, operation):
    from genesis import media_functions
    source = tmp_path / "original.png"
    Image.new("RGB", (8, 8), "red").save(source)
    before = source.read_bytes()
    with pytest.raises(media_functions.MediaFunctionError, match="original"):
        getattr(media_functions, operation)(source, source)
    assert source.read_bytes() == before


def test_fallback_enhance_preserves_transparency(tmp_path):
    source = tmp_path / "cutout.png"
    image = Image.new("RGBA", (12, 8), (255, 0, 0, 0))
    for x in range(3, 9):
        for y in range(2, 7):
            image.putpixel((x, y), (255, 0, 0, 255))
    image.save(source)

    output = tmp_path / "cutout-2x.png"
    result = upscale_enhance(source, output, scale=2, prefer_ai=False)

    assert result.details["alpha_preserved"] is True
    with Image.open(output) as enhanced:
        assert enhanced.mode == "RGBA"
        assert enhanced.size == (24, 16)
        assert enhanced.getchannel("A").getextrema() == (0, 255)


def test_require_ai_refuses_silent_cpu_fallback(tmp_path, monkeypatch):
    from genesis import media_functions

    source = tmp_path / "source.png"
    _make_image(source)
    monkeypatch.setattr(media_functions, "UPSCALE_MODEL", tmp_path / "missing-model.pth")

    with pytest.raises(media_functions.MediaFunctionError, match="GPU upscale model missing"):
        media_functions.upscale_enhance(
            source, tmp_path / "strict.png", scale=4, prefer_ai=True, require_ai=True
        )


def test_batch_background_removal_preserves_sources_and_uses_unique_outputs(tmp_path, monkeypatch):
    from genesis import media_functions

    first = tmp_path / "one.png"
    second = tmp_path / "two.png"
    _make_image(first)
    _make_image(second)
    before = {first: first.read_bytes(), second: second.read_bytes()}
    output_dir = tmp_path / "batch"
    output_dir.mkdir()
    (output_dir / "one_cutout.png").write_bytes(b"existing")

    def fake_remove(source, target):
        target = Path(target)
        target.write_bytes(Path(source).read_bytes())
        return media_functions.OperationResult(target, "fake-rembg", {})

    monkeypatch.setattr(media_functions, "remove_background", fake_remove)
    result = media_functions.batch_remove_background([first, second], output_dir)

    completed = [Path(value).name for value in result.details["completed"]]
    assert completed == ["one_cutout_2.png", "two_cutout.png"]
    assert result.details["count"] == 2
    assert first.read_bytes() == before[first]
    assert second.read_bytes() == before[second]
