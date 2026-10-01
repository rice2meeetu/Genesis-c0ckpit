from pathlib import Path
from PIL import Image
from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from genesis.canvas_bridge import CanvasBridge
from genesis.canvas_document import CanvasDocument


def test_explicit_canvas_size_blank_roundtrip_and_undo(tmp_path):
    doc = CanvasDocument()
    doc.set_size(640, 480)
    doc.save_project(tmp_path / 'blank.json')
    loaded = CanvasDocument.load_project(tmp_path / 'blank.json')
    assert (loaded.width, loaded.height, loaded.layers) == (640, 480, [])
    source = tmp_path / 'source.png'
    Image.new('RGB', (40, 20), 'blue').save(source)
    doc.add_image(source)
    assert (doc.width, doc.height) == (640, 480)
    doc.set_size(800, 600)
    doc.undo()
    assert (doc.width, doc.height) == (640, 480)


def test_processed_layer_keeps_transform_original_and_single_undo(tmp_path):
    source = tmp_path / 'source.png'; output = tmp_path / 'cutout.png'
    Image.new('RGBA', (40, 20), 'blue').save(source)
    Image.new('RGBA', (80, 40), (0, 0, 0, 0)).save(output)
    doc = CanvasDocument(); layer = doc.add_image(source)
    doc.update_layer(layer, x=12, y=15, rotation=90, opacity=0.6)
    before = doc._snapshot()
    doc.add_processed_layer(layer, output)
    assert not doc.layers[0]['visible']
    assert doc.layers[1]['width'] == 40 and doc.layers[1]['x'] == 12
    assert doc.layers[1]['rotation'] == 90 and doc.layers[1]['opacity'] == 0.6
    doc.undo(); assert doc._snapshot() == before
    doc.redo(); assert len(doc.layers) == 2
    assert Image.open(source).size == (40, 20)


def test_new_canvas_validates_before_discard_and_allows_cancellation(monkeypatch):
    bridge = CanvasBridge()
    calls = []
    monkeypatch.setattr(bridge, 'confirm_discard', lambda: calls.append(True) or False)
    assert not bridge.createProject(16384, 16384)
    assert not calls
    assert not bridge.createProject(640, 480)
    assert (bridge.canvasWidth, bridge.canvasHeight) == (3840, 2160)
    monkeypatch.setattr(bridge, 'confirm_discard', lambda: True)
    assert bridge.createProject(640, 480)
    assert bridge.dirty and not bridge.canUndo


class FakeTools(QObject):
    busyChanged = pyqtSignal(); statusChanged = pyqtSignal(); resultChanged = pyqtSignal()
    busy = False; resultUrl = ''; status = ''
    def process_canvas_image(self, source, target, kind, scale):
        self.args = (source, target, kind, scale); self.busy = True; self.busyChanged.emit()


def test_canvas_processing_is_explicit_and_targets_original_layer(tmp_path, monkeypatch):
    source = tmp_path / 'source.png'; result = tmp_path / 'result.png'
    Image.new('RGB', (30, 20), 'green').save(source)
    Image.new('RGB', (60, 40), 'green').save(result)
    bridge = CanvasBridge(); tools = FakeTools(); bridge.attach_media_tools(tools)
    bridge.addImage(str(source)); original = bridge.selected['id']
    monkeypatch.setattr('genesis.canvas_bridge.QFileDialog.getSaveFileName', lambda *a: (str(result), ''))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path / 'data'))
    bridge.processSelected('upscale', 2)
    target = tools.args[1]
    assert tools.args == (source, target, 'upscale', 2)
    assert target.parent == tmp_path / 'data/genesis/canvas-assets'
    assert target != source
    Image.new('RGB', (60, 40), 'green').save(target)
    result = target
    bridge.duplicateSelected()
    tools.resultUrl = QUrl.fromLocalFile(str(result)).toString(); tools.resultChanged.emit()
    assert bridge.document.layers[0]['id'] == original and not bridge.document.layers[0]['visible']
    assert bridge.document.layers[1]['path'] == str(result)


def test_canvas_background_removal_does_not_prompt_or_overwrite(tmp_path, monkeypatch):
    source = tmp_path / 'source.png'; Image.new('RGB', (30, 20)).save(source)
    original = source.read_bytes()
    bridge = CanvasBridge(); tools = FakeTools(); bridge.attach_media_tools(tools); bridge.addImage(str(source))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path / 'data'))
    def unexpected_dialog(*args):
        raise AssertionError('Canvas processing must not ask for a save location')
    monkeypatch.setattr('genesis.canvas_bridge.QFileDialog.getSaveFileName', unexpected_dialog)
    bridge.processSelected('background remover', 2)
    first = tools.args[1]
    assert tools.busy and first != source and source.read_bytes() == original
    tools.busy = False
    bridge.processSelected('background remover', 2)
    assert tools.args[1] != first


def test_standard_resize_roundtrip_uses_worker_and_adds_result(tmp_path, monkeypatch):
    from PyQt6.QtTest import QTest
    from genesis.media_bridge import MediaBridge
    source = tmp_path / 'source.png'; result = tmp_path / 'double.png'
    Image.new('RGBA', (30, 20), (10, 90, 180, 128)).save(source)
    bridge = CanvasBridge(); tools = MediaBridge(); bridge.attach_media_tools(tools); bridge.addImage(str(source))
    monkeypatch.setattr('genesis.canvas_bridge.QFileDialog.getSaveFileName', lambda *a: (str(result), ''))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path / 'data'))
    bridge.processSelected('standard resize', 2)
    for _ in range(100):
        if not bridge.busy: break
        QTest.qWait(20)
    assert not bridge.busy and len(bridge.layers) == 2, bridge.status
    result = Path(bridge.selected['path'])
    assert Image.open(result).size == (60, 40)
    project = tmp_path / 'saved.json'
    bridge.document.save_project(project)
    assert len(CanvasDocument.load_project(project).layers) == 2
    assert bridge.selected['width'] == 30
    bridge.undo(); assert len(bridge.layers) == 1 and bridge.layers[0]['visible']


def test_canvas_eight_times_upscale_keeps_working_asset_and_no_save_prompt(tmp_path, monkeypatch):
    source = tmp_path / 'source.png'; Image.new('RGB', (30, 20)).save(source)
    bridge = CanvasBridge(); tools = FakeTools(); bridge.attach_media_tools(tools); bridge.addImage(str(source))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path / 'data'))
    monkeypatch.setattr('genesis.canvas_bridge.QFileDialog.getSaveFileName', lambda *args: (_ for _ in ()).throw(AssertionError('Unexpected save dialog')))
    bridge.processSelected('upscale', 8)
    assert tools.args[0] == source and tools.args[2:] == ('upscale', 8)
    assert tools.args[1].parent == tmp_path / 'data/genesis/canvas-assets'
