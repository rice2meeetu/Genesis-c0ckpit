"""CPU-only document and editor regression tests."""
import copy
import json
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
os.environ.setdefault("QT_QUICK_BACKEND","software")
import pytest
from genesis.pose_document import (PARTS,add_hands,new_document,
    validate_document,merged_document)

def test_roundtrip_keeps_identity_metadata_and_hands():
    doc=new_document()
    doc["people"][0]["person_id"]=[42]
    doc["custom"]={"label":"neutral standing pose"}
    add_hands(doc["people"][0],768,1024)
    assert len(doc["people"][0][PARTS[1]])==63
    assert validate_document(json.loads(json.dumps(doc)))==doc

def test_merge_rescales_each_person_without_mutating_sources():
    a,b=new_document(768,1024),new_document(384,512)
    before=copy.deepcopy((a,b))
    result=merged_document(a,b)
    assert len(result["people"])==2
    assert result["people"][1][PARTS[0]]==a["people"][0][PARTS[0]]
    assert (a,b)==before

@pytest.mark.parametrize("bad",[float("nan"),float("inf"),True,"12"])
def test_bad_coordinates_rejected(bad):
    d=new_document()
    d["people"][0][PARTS[0]][0]=bad
    with pytest.raises(ValueError):validate_document(d)

def test_invalid_and_multiple_frames_are_rejected():
    with pytest.raises(ValueError):validate_document([new_document(),new_document()])
    d=new_document()
    d["people"][0][PARTS[0]]=[1,2]
    with pytest.raises(ValueError):validate_document(d)

def test_missing_dimensions_require_explicit_canvas():
    d=new_document()
    del d["canvas_width"]
    with pytest.raises(ValueError):validate_document(d)
    assert validate_document(d,(512,512))["canvas_width"]==512

def test_body25_and_face_points_preserved():
    d=new_document()
    d["people"][0][PARTS[0]]=[100,100,1]*25
    d["people"][0][PARTS[3]]=[120,130,.8]*70
    assert validate_document(d)==d

def test_document_people_limit():
    d=new_document()
    d["people"]*=33
    with pytest.raises(ValueError):validate_document(d)

def test_editor_interaction_roundtrip(tmp_path,monkeypatch):
    from PyQt6.QtWidgets import QApplication,QFileDialog
    from PyQt6.QtCore import QPoint,Qt
    from PyQt6.QtTest import QTest
    from genesis.skeleton_editor import SkeletonEditor,read_document
    app=QApplication.instance() or QApplication([])
    editor=SkeletonEditor()
    editor.show()
    app.processEvents()
    original=copy.deepcopy(editor.document)
    editor.add_person()
    editor.make_hands()
    assert len(editor.document["people"])==2
    assert len(editor.document["people"][1][PARTS[1]])==63
    editor.undo()
    assert editor.document["people"][1][PARTS[1]]==[]
    editor.redo()
    assert len(editor.document["people"][1][PARTS[1]])==63
    editor.person.setCurrentIndex(0)
    scale,x,y=editor.canvas.transform()
    pts=editor.document["people"][0][PARTS[0]]
    start=QPoint(round(x+pts[0]*scale),round(y+pts[1]*scale))
    QTest.mousePress(editor.canvas,Qt.MouseButton.LeftButton,pos=start)
    QTest.mouseMove(editor.canvas,start+QPoint(20,15))
    QTest.mouseRelease(editor.canvas,Qt.MouseButton.LeftButton,pos=start+QPoint(20,15))
    assert editor.document["people"][0][PARTS[0]][:2]!=original["people"][0][PARTS[0]][:2]
    saved=tmp_path/"pose.json"
    monkeypatch.setattr(QFileDialog,"getSaveFileName",lambda *a,**k:(str(saved),""))
    assert editor.save()
    assert read_document(saved)==editor.document
    exported=tmp_path/"pose.png"
    monkeypatch.setattr(QFileDialog,"getSaveFileName",lambda *a,**k:(str(exported),""))
    editor.export_png()
    from PyQt6.QtGui import QImage
    image=QImage(str(exported))
    assert image.width()==768 and image.height()==1024
    assert image.pixelColor(0,0).name()=="#000000"
    editor.close()


def test_dwpose_single_frame_normalized_and_null_parts():
    raw={"canvas_width":768,"canvas_height":1024,"people":[{
        PARTS[0]:[.5,.25,1]*18,PARTS[1]:None,PARTS[2]:None,PARTS[3]:None}]}
    doc=validate_document([raw])
    assert doc["people"][0][PARTS[0]][:3]==[384,256,1]
    assert doc["people"][0][PARTS[1]]==[]
    assert validate_document(doc)==doc


def test_nested_triples_and_pixel_marker():
    raw={"canvas_width":768,"canvas_height":1024,"genesis_coordinate_space":"pixels",
         "people":[{PARTS[0]:[[.5,.25,1]]*18}]}
    doc=validate_document(raw)
    assert doc["people"][0][PARTS[0]][:3]==[.5,.25,1]
