"""Explicit source/pose handoffs consumed by the maintained GENESIS cockpit."""
import json
from pathlib import Path

POSE_WORKBENCH_HANDOFF_FILE = Path.home() / '.config/genesis-photo-studio/pose-workbench-handoff.json'


def consume_pose_workbench_handoff(source, pose, pose_mode, handoff_file=POSE_WORKBENCH_HANDOFF_FILE):
    handoff_file = Path(handoff_file)
    if not handoff_file.is_file():
        return source, pose, pose_mode
    try:
        payload = json.loads(handoff_file.read_text(encoding='utf-8'))
        path = Path(payload['path']).expanduser().resolve()
        if payload.get('version') != 1 or not path.is_file():
            raise ValueError('Invalid or missing pose handoff image')
        role = payload.get('role')
        if role == 'pose_reference':
            result = source, str(path), 'skeleton'
        elif role == 'source_image':
            result = str(path), pose, pose_mode
        else:
            raise ValueError('Unsupported pose handoff role')
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ValueError('Unable to consume pose handoff: ' + str(exc)) from exc
    handoff_file.unlink()
    return result
