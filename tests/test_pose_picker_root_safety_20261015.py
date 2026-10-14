"""The Qt pose picker must obey the same installed-root boundary as workflow_lab."""
import json
from pathlib import Path
from PyQt6.QtCore import QUrl
import qt_cockpit as cockpit


def _setup(tmp_path,monkeypatch):
    root=tmp_path/'project'
    bundle=root/'genesis/reference/assets/pose_library'
    bundle.mkdir(parents=True)
    home=tmp_path/'home'
    legacy=home/'AI/GENESIS_POSE_MAKER/assets/pose_library'
    legacy.mkdir(parents=True)
    index=tmp_path/'index.json'
    monkeypatch.setattr(cockpit,'PROJECT_ROOT',root)
    monkeypatch.setattr(cockpit,'POSE_INDEX',index)
    monkeypatch.setattr(Path,'home',classmethod(lambda cls:home))
    return bundle,legacy,index


def test_legacy_manifest_cannot_expose_paths_outside_installed_library(tmp_path,monkeypatch):
    bundle,legacy,index=_setup(tmp_path,monkeypatch)
    inside=legacy/'valid.png';inside.write_bytes(b'pose')
    outside=legacy.parent/'outside.png';outside.write_bytes(b'private')
    link=legacy/'alias.png';link.symlink_to(outside)
    index.write_text(json.dumps([
        {'path':'valid.png','category':'Safe','name':'Good'},
        {'path':'../outside.png','category':'Escape','name':'Parent'},
        {'path':str(outside),'category':'Escape','name':'Absolute'},
        {'path':'alias.png','category':'Escape','name':'Symlink'},
        {'path':'missing.png','category':'Missing','name':'Missing'},
    ]))
    rows=cockpit.load_pose_items(limit=20)
    assert len(rows)==1
    assert Path(QUrl(rows[0]['source']).toLocalFile())==inside.resolve()
    assert rows[0]['category']=='Safe'


def test_external_pose_pack_fallback_if_bundled_index_has_missing_images(tmp_path,monkeypatch):
    bundle,legacy,index=_setup(tmp_path,monkeypatch)
    (bundle/'index.json').write_text(json.dumps([
        {'path':'removed-private-control.png','category':'Bundled'}]))
    valid=legacy/'available.png';valid.write_bytes(b'valid')
    index.write_text(json.dumps([{'path':'available.png','category':'Legacy'}]))
    rows=cockpit.load_pose_items(limit=20)
    assert len(rows)==1
    assert rows[0]['category']=='Legacy'
    assert Path(QUrl(rows[0]['source']).toLocalFile())==valid.resolve()


def test_bundled_pose_wins_when_installed_and_valid(tmp_path,monkeypatch):
    bundle,legacy,index=_setup(tmp_path,monkeypatch)
    installed=bundle/'valid.png';installed.write_bytes(b'valid')
    (bundle/'index.json').write_text(json.dumps([{'path':'valid.png','category':'Bundled'}]))
    (legacy/'also.png').write_bytes(b'legacy')
    index.write_text(json.dumps([{'path':'also.png','category':'Legacy'}]))
    rows=cockpit.load_pose_items(limit=20)
    assert len(rows)==1
    assert rows[0]['category']=='Bundled'
    assert Path(QUrl(rows[0]['source']).toLocalFile())==installed.resolve()
