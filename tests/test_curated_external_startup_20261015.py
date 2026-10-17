"""Curated preset links should work with exact indexed external Pose Maker assets."""
import json
from pathlib import Path

from PyQt6.QtCore import QUrl
import qt_cockpit as c


def test_exact_declared_external_pose_is_linked_and_unsafe_files_rejected(tmp_path,monkeypatch):
    home=tmp_path/'home';home.mkdir()
    project=tmp_path/'project';project.mkdir()
    library=home/'AI/GENESIS_POSE_MAKER/assets/pose_library'
    valid=library/'lying/768512/valid_bone_structure.png'
    valid.parent.mkdir(parents=True)
    valid.write_bytes(b'pose')
    outside=library.parent/'private.png';outside.write_bytes(b'private')
    (home/'GENESIS_CURATED_PRESETS_DATABASE.json').write_text(json.dumps({
        'sexual_act_presets':[{'id':'curated-exact','name':'Example',
        'prompt':'A posed scene','skeletons':['../private.png','lying/768512/valid_bone_structure.png']}],
    }))
    monkeypatch.setattr(c,'PROJECT_ROOT',project)
    monkeypatch.setattr(Path,'home',classmethod(lambda cls:home))
    valid_row={'source':valid.as_uri(),'thumbnail':valid.as_uri(),'category':'Lying','poseId':'lying/768512/valid'}
    unsafe_row={'source':outside.as_uri(),'category':'Private','poseId':'private'}
    result=next(p for p in c.load_curated_pose_presets(pose_rows=[unsafe_row,valid_row]) if p.get('id')=='curated18:curated-exact')
    assert result['source']==valid.as_uri()
    assert result['poseId']=='lying/768512/valid'
    assert result['requiresPoseSelection'] is False
    without_index=next(p for p in c.load_curated_pose_presets(pose_rows=[unsafe_row]) if p.get('id')=='curated18:curated-exact')
    assert without_index['requiresPoseSelection'] is True
    assert 'source' not in without_index


def test_real_launcher_supplies_installed_index_to_curated_pairing():
    source=(c.PROJECT_ROOT/'qt_cockpit.py').read_text()
    assert 'installed_pose_rows = load_pose_items(limit=10000)' in source
    assert 'load_curated_pose_presets(pose_rows=installed_pose_rows)' in source
    assert 'context.setContextProperty("poseItems", installed_pose_rows[:12])' in source
