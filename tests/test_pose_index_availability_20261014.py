"""Missing/private pose assets must not masquerade as selectable skeletons."""
import json
from pathlib import Path
from genesis import workflow_lab


def test_only_installed_skeletons_are_listed(monkeypatch, tmp_path):
    library = tmp_path / "assets" / "pose_library"
    library.mkdir(parents=True)
    (library / "actual.png").write_bytes(b"fixture")
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"outside")
    index = tmp_path / "pose_library_index.json"
    index.write_text(json.dumps([
        {"category": "A", "path": "actual.png"},
        {"category": "B", "path": "not-installed.png"},
        {"category": "C", "path": "../../outside.png"},
        {"category": "D", "path": str(outside)},
    ]))
    monkeypatch.setattr(workflow_lab, "REFERENCE_DIR", tmp_path)
    monkeypatch.setattr(workflow_lab, "POSE_INDEX_PATH", index)
    assert workflow_lab.pose_library_index() == [{"category": "A", "path": "actual.png"}]
    assert workflow_lab.pose_library_page()["total"] == 1
    (library / "actual.png").unlink()
    assert workflow_lab.pose_library_index() == []
    assert workflow_lab.pose_library_page()["total"] == 0


def test_legacy_pose_maker_files_remain_available_without_bundled_pack(monkeypatch, tmp_path):
    home = tmp_path / "home"
    external = home / "AI" / "GENESIS_POSE_MAKER" / "assets" / "pose_library"
    external.mkdir(parents=True)
    (external / "installed.png").write_bytes(b"pose")
    manifest = tmp_path / "pose_library_index.json"
    manifest.write_text(json.dumps([
        {"category": "Imported", "path": "installed.png"},
        {"category": "Imported", "path": "not-installed.png"},
        {"category": "Imported", "path": "../outside.png"},
    ]))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(workflow_lab, "REFERENCE_DIR", tmp_path)
    monkeypatch.setattr(workflow_lab, "POSE_INDEX_PATH", manifest)
    assert workflow_lab.pose_library_index() == [
        {"category": "Imported", "path": "installed.png"}
    ]
    assert workflow_lab.pose_library_page()["total"] == 1
