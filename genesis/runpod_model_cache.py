"""Pod-local, read-only-source model cache. Never deploys or restarts ComfyUI.

The active manifest is a prepared selection, not a live ComfyUI path change.
Configure Paul’s stopped 8188 instance separately; 8189 is never contacted.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import tempfile

MODELS = {
    'phr00t-v19': ('checkpoints', 'Qwen-Rapid-AIO-NSFW-v19.safetensors'),
    'phr00t-v23': ('diffusion_models', 'Qwen-Rapid-NSFW-v23_Q8_0.gguf'),
    'aisha': ('diffusion_models', 'aisha_nsfw_beta_v9_7_distilled_fp8.safetensors'),
    'miraclein': ('diffusion_models', 'Miraclein NSFW v3.0 FP8 - Klein9B - 12steps,euler,cfg1.1.safetensors'),
}


def validate_weight(path: Path) -> None:
    """Reject partial safetensors and malformed GGUF headers before publication."""
    size = path.stat().st_size
    with path.open('rb') as stream:
        if path.suffix == '.gguf':
            header = stream.read(24)
            if len(header) != 24 or header[:4] != b'GGUF':
                raise ValueError('Invalid GGUF header')
            version, tensors, metadata = struct.unpack('<IQQ', header[4:])
            if version not in {2, 3} or not tensors or not metadata or size <= 24:
                raise ValueError('Invalid GGUF structure')
            # Fail closed when the full parser is unavailable: a valid header
            # alone cannot establish that the interrupted v23 download finished.
            try:
                from gguf import GGUFReader
            except ImportError as exc:
                raise ValueError('Full GGUF validation requires the gguf parser') from exc
            try:
                reader = GGUFReader(str(path))
                if len(reader.tensors) != tensors:
                    raise ValueError('Incomplete GGUF tensor table')
                for tensor in reader.tensors:
                    if tensor.data_offset + tensor.n_bytes > size:
                        raise ValueError('Incomplete GGUF tensor data')
            except Exception as exc:
                raise ValueError(f'GGUF validation failed: {exc}') from exc
            return
        raw = stream.read(8)
        if len(raw) != 8:
            raise ValueError('Incomplete safetensors header')
        length = struct.unpack('<Q', raw)[0]
        if not 2 <= length <= min(size - 8, 16 * 1024 * 1024):
            raise ValueError('Invalid safetensors header length')
        header = json.loads(stream.read(length))
        offsets = sorted(value['data_offsets'] for key, value in header.items() if key != '__metadata__')
        end = 0
        for start, stop in offsets:
            if start != end or stop <= start:
                raise ValueError('Invalid safetensors data offsets')
            end = stop
        if not offsets or end != size - 8 - length:
            raise ValueError('Incomplete safetensors data')


def prepare_active_model(model: str, source_root: Path, cache_root: Path) -> dict:
    """Copy one mapped weight and atomically select it; retain all old cache files.

    No eviction, source rename/unlink, volume writes, service calls, or downloads.
    Copy failure leaves the previous selection intact. Consumers must use the
    manifest only between jobs; this helper does not reconfigure a live loader.
    """
    category, filename = MODELS[model]
    source_root = source_root.resolve(strict=True)
    cache_root = cache_root.resolve()
    if cache_root == Path('/workspace') or Path('/workspace') in cache_root.parents:
        raise ValueError('Cache must be outside the Global Volume /workspace')
    if cache_root == source_root or source_root in cache_root.parents or cache_root in source_root.parents:
        raise ValueError('Source and cache must be separate')
    source = source_root / category / filename
    if source.is_symlink() or source.resolve(strict=True).parent != (source_root / category).resolve():
        raise ValueError('Unexpected source path')
    validate_weight(source)
    cache_root.mkdir(parents=True, exist_ok=True)
    if (source_root == Path('/workspace') or Path('/workspace') in source_root.parents) and cache_root.stat().st_dev == source_root.stat().st_dev:
        raise ValueError('Cache must use a different filesystem from the Global Volume')
    with (cache_root / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        before = source.stat()
        if shutil.disk_usage(cache_root).free < before.st_size + 64 * 1024 * 1024:
            raise ValueError('Insufficient cache space; no files were evicted')
        stage = Path(tempfile.mkdtemp(prefix='.staging-', dir=cache_root))
        try:
            destination = stage / filename
            digest = hashlib.sha256()
            with source.open('rb') as reader, destination.open('xb') as writer:
                while block := reader.read(8 * 1024 * 1024):
                    digest.update(block)
                    writer.write(block)
                writer.flush()
                os.fsync(writer.fileno())
            after = source.stat()
            if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                raise ValueError('Source changed during copy')
            validate_weight(destination)
            checksum = digest.hexdigest()
            target = cache_root / f'{model}-{checksum}'
            if target.exists():
                existing = target / filename
                with existing.open('rb') as reader:
                    if hashlib.file_digest(reader, 'sha256').hexdigest() != checksum:
                        raise ValueError('Cached model failed checksum verification')
            else:
                stage.rename(target)
            manifest = {'model': model, 'category': category, 'filename': filename,
                        'path': str(target / filename), 'sha256': checksum,
                        'size': before.st_size, 'port': 8188}
            pending = cache_root / '.active.pending'
            with pending.open('w') as writer:
                json.dump(manifest, writer, indent=2)
                writer.flush()
                os.fsync(writer.fileno())
            pending.replace(cache_root / 'active.json')
            return manifest
        finally:
            if stage.exists():
                shutil.rmtree(stage)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model', choices=MODELS)
    parser.add_argument('--source-root', type=Path, default=Path('/workspace/models'))
    parser.add_argument('--cache-root', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare_active_model(args.model, args.source_root, args.cache_root), indent=2))
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f'Cache preparation failed: {exc}\n')


if __name__ == '__main__':
    main()
