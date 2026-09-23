from pathlib import Path
from PIL import Image
from genesis.canvas_document import CanvasDocument

def make_image(path: Path, size=(80, 40), color=(255, 0, 0, 255)):
    Image.new("RGBA", size, color).save(path)
    return path

def test_canvas_layer_edit_history_and_duplicate(tmp_path):
    src = make_image(tmp_path / "source.png")
    doc = CanvasDocument()
    first = doc.add_image(src)
    assert doc.width == 80 and doc.height == 40
    assert doc.layers[0]["rotation"] == 0.0
    assert doc.update_layer(first, rotation=90)
    assert doc.layers[0]["rotation"] == 90
    duplicate = doc.duplicate_layer(first)
    assert duplicate != first
    assert len(doc.layers) == 2
    assert doc.selected_id == duplicate
    assert doc.layers[1]["rotation"] == 90
    assert doc.undo()
    assert len(doc.layers) == 1
    assert doc.redo()
    assert len(doc.layers) == 2

def test_canvas_project_roundtrip_and_export_preserves_source(tmp_path):
    src = make_image(tmp_path / "source.png", (60, 30))
    before = src.read_bytes()
    doc = CanvasDocument()
    layer = doc.add_image(src)
    doc.update_layer(layer, rotation=90, opacity=0.75)
    project = tmp_path / "scene.genesis-canvas.json"
    doc.save_project(project)
    loaded = CanvasDocument.load_project(project)
    assert loaded.layers[0]["rotation"] == 90
    assert loaded.layers[0]["opacity"] == 0.75
    output = tmp_path / "flattened.png"
    loaded.export_png(output)
    assert output.exists()
    assert src.read_bytes() == before

def test_canvas_rotation_render_is_bounded_to_document(tmp_path):
    src = make_image(tmp_path / "source.png", (80, 40))
    doc = CanvasDocument()
    layer = doc.add_image(src)
    doc.update_layer(layer, rotation=90)
    with doc.render() as result:
        assert result.size == (80, 40)
