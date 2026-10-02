import json
import struct
from pathlib import Path
import pytest
from genesis.runpod_model_cache import MODELS, prepare_active_model


def weight(root, key, broken=False):
    category, name = MODELS[key]
    path = root / category / name
    path.parent.mkdir(parents=True, exist_ok=True)
    header = json.dumps({'x': {'dtype': 'U8', 'shape': [4], 'data_offsets': [0, 4]}}).encode()
    path.write_bytes(struct.pack('<Q', len(header)) + header + (b'a' if broken else b'abcd'))
    return path


def test_atomic_selection_preserves_source_and_previous_cache(tmp_path):
    source, cache = tmp_path / 'volume', tmp_path / 'cache'
    original = weight(source, 'phr00t-v19')
    before = original.read_bytes()
    first = prepare_active_model('phr00t-v19', source, cache)
    weight(source, 'aisha', broken=True)
    with pytest.raises(ValueError, match='Incomplete'):
        prepare_active_model('aisha', source, cache)
    assert json.loads((cache / 'active.json').read_text()) == first
    weight(source, 'aisha')
    second = prepare_active_model('aisha', source, cache)
    assert second['port'] == 8188
    assert Path(first['path']).is_file()
    assert original.read_bytes() == before
    assert not list(cache.glob('.staging-*'))


def test_cache_cannot_write_global_volume(tmp_path):
    source = tmp_path / 'volume'
    weight(source, 'miraclein')
    for cache in [source / 'cache', Path('/workspace/paul/cache')]:
        with pytest.raises(ValueError):
            prepare_active_model('miraclein', source, cache)


def test_no_space_preserves_active(tmp_path, monkeypatch):
    from genesis import runpod_model_cache as cache_module
    source, cache = tmp_path / 'volume', tmp_path / 'cache'
    weight(source, 'miraclein')
    monkeypatch.setattr(cache_module.shutil, 'disk_usage', lambda path: type('Space', (), {'free': 0})())
    with pytest.raises(ValueError, match='space'):
        prepare_active_model('miraclein', source, cache)
    assert not (cache / 'active.json').exists()


def test_gguf_partial_header_does_not_replace_selection(tmp_path):
    source, cache = tmp_path / 'volume', tmp_path / 'cache'
    weight(source, 'phr00t-v19')
    previous = prepare_active_model('phr00t-v19', source, cache)
    category, filename = MODELS['phr00t-v23']
    path = source / category / filename
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(b'GGUF' + struct.pack('<IQQ', 3, 100, 1) + b'partial')
    with pytest.raises(ValueError):
        prepare_active_model('phr00t-v23', source, cache)
    assert json.loads((cache / 'active.json').read_text()) == previous
