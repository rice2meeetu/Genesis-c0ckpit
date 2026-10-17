from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_launchers_load_machine_local_current_runpod_endpoint():
    for name in ('launch-qt-cockpit.sh', 'launch-qt-cockpit-runpod.sh'):
        text = (ROOT / name).read_text(encoding='utf-8')
        assert '.genesis-runpod-current' in text
        assert 'source "$SCRIPT_DIR/.genesis-runpod-current"' in text


def test_current_endpoint_file_is_gitignored():
    text = (ROOT / '.gitignore').read_text(encoding='utf-8')
    assert '.genesis-runpod-current' in text
