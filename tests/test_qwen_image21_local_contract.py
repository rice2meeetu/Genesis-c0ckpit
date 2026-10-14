"""Local Qwen UI-to-prompt contract; no generation or backend mutation.

The optional installed-ComfyUI check executes its real V3 input parser on the
production graph, so a successful graph-shape mock cannot hide dropped refs.
"""
import json
import os
from pathlib import Path
import subprocess
from unittest.mock import Mock

import pytest
import qt_cockpit as cockpit

SCHEMA_PATH = Path(__file__).parent / 'fixtures/local_qwen21_node_schema.json'


def build_from_ui(monkeypatch, tmp_path, *, source, pose, denoise=1.0):
    monkeypatch.setattr(cockpit, 'remote_url', lambda: '')
    info = json.loads(SCHEMA_PATH.read_text())
    bridge = cockpit.GenerationBridge()
    bridge._output_dir = tmp_path
    client = Mock()
    client.object_info.return_value = info
    client.upload_image.side_effect = lambda p: {'name': p.name}
    monkeypatch.setattr(bridge, '_connect_comfyui', lambda: (client, {}))
    monkeypatch.setattr(bridge, '_record_finish', Mock())
    statuses = []
    monkeypatch.setattr(bridge, '_set_status', statuses.append)
    # Capture precisely what the existing QML-facing slot sends into queueGenerate.
    snapshots = []
    queued = Mock(side_effect=lambda *args: snapshots.append(dict(bridge._next_generation_controls)))
    monkeypatch.setattr(bridge, 'queueGenerate', queued)
    bridge.queueGenerateAdvanced('A standing portrait', 'blur', 768, 1152,
        cockpit.QWEN21_MODEL, 'None', 'None', str(source or ''), str(pose or ''),
        False, False, False, 25, 1.7, 123, denoise, 'euler', 'simple')
    queued.assert_called_once()
    assert len(snapshots) == 1
    controls = snapshots[0]
    assert bridge._next_generation_controls is None
    # queueGenerate attaches the negative prompt before starting the worker.
    controls['negative_prompt'] = queued.call_args.args[1]
    captured = {}
    output = tmp_path / 'output.png'
    monkeypatch.setattr(bridge, '_submit_and_save',
                        lambda client, prompt, stamp, stage: captured.update(prompt) or output)
    result = bridge._run_generate('A standing portrait', 'blur', 768, 1152,
        cockpit.QWEN21_MODEL, 'None', 'None', 'None', 0, 0, 0,
        source, pose, False, False, False, controls)
    assert result == output, statuses
    return captured, client


@pytest.mark.parametrize('has_source,has_pose,denoise', [
    (True, False, 1.0), (False, True, 1.0),
    (True, True, 1.0), (True, True, 0.3),
])
def test_local_ui_controls_reach_final_reference_prompt(monkeypatch, tmp_path, has_source, has_pose, denoise):
    source = tmp_path / 'source.png' if has_source else None
    pose = tmp_path / 'pose.png' if has_pose else None
    prompt, client = build_from_ui(monkeypatch, tmp_path, source=source, pose=pose, denoise=denoise)
    encoder = prompt['7']['inputs']
    assert encoder['resolution'] == 768
    assert encoder['negative_prompt'] == 'blur'
    assert 'A standing portrait' in encoder['prompt']
    assert encoder['images.image_1'] == ['5', 0]
    assert prompt['5']['inputs']['image'] == ('source.png' if has_source else 'pose.png')
    assert 'images' not in encoder
    if has_source and has_pose:
        assert encoder['images.image_2'] == ['6', 0]
        assert prompt['6']['inputs']['image'] == 'pose.png'
        assert '<image2>' in encoder['prompt']
    else:
        assert 'images.image_2' not in encoder
        assert '6' not in prompt
    assert client.upload_image.call_count == int(has_source) + int(has_pose)
    sampler = prompt['8']['inputs']
    for key, value in {'steps': 25, 'cfg': 1.7, 'seed': 123, 'denoise': denoise,
                       'sampler_name': 'euler', 'scheduler': 'simple'}.items():
        assert sampler[key] == value
    if has_source and denoise < 1:
        assert sampler['latent_image'] == ['__qwen21_source_latent__', 0]
        assert prompt['__qwen21_source_scale__']['inputs']['megapixels'] == 0.5625
    else:
        assert sampler['latent_image'] == ['7', 2]
    assert prompt['1']['class_type'] == 'GenesisQwen21ReferenceUNETLoader'
    assert prompt['3']['class_type'] == 'GenesisQwen21ReferenceCLIPLoader'
    assert prompt['4']['inputs']['vae_name'] == cockpit.QWEN21_VAE


def test_installed_comfy_parser_retains_both_production_references(monkeypatch, tmp_path):
    root = Path(os.environ.get('GENESIS_TEST_COMFY_ROOT', Path.home() / 'AI/ComfyUI'))
    python = root / '.venv/bin/python'
    if not python.exists():
        pytest.skip('Installed ComfyUI runtime unavailable; required for local release verification')
    prompt, _ = build_from_ui(monkeypatch, tmp_path, source=tmp_path/'source.png', pose=tmp_path/'pose.png')
    payload = tmp_path / 'prompt.json'
    payload.write_text(json.dumps(prompt))
    script = '''
import json, sys
from comfy_api.latest import _io
schema=json.load(open(sys.argv[1]))['TextEncodeQwenImage21']['input']
inputs=json.load(open(sys.argv[2]))['7']['inputs']
def parse(values):
    finalized, _, v3 = _io.get_finalized_class_inputs(schema, values)
    recognized={k:v for k,v in values.items() if any(k in finalized.get(t,{}) for t in ('required','optional'))}
    return _io.build_nested_inputs(recognized,v3).get('images')
expected={'image_1':['5',0],'image_2':['6',0]}
assert parse(inputs)==expected, parse(inputs)
legacy={k:v for k,v in inputs.items() if not k.startswith('images.')}
legacy['images']=expected
assert parse(legacy)=={}, 'Recheck parser behavior: the legacy format is no longer discarded'
print('Actual ComfyUI parser retained both production image links')
'''
    result = subprocess.run([str(python), '-c', script, str(SCHEMA_PATH.resolve()), str(payload)],
                            cwd=root, env={**os.environ, 'PYTHONPATH': str(root)},
                            capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('references', [{}, {'image_1': ['6', 0], 'image_2': ['5', 0]}])
def test_damaged_reference_links_are_rejected_before_submission(monkeypatch, tmp_path, references):
    monkeypatch.setattr(cockpit, 'remote_url', lambda: '')
    info = json.loads(SCHEMA_PATH.read_text())
    graph = json.loads(cockpit.QWEN21_REFERENCE_WORKFLOW.read_text())
    graph['7']['inputs']['images'] = references
    monkeypatch.setattr(cockpit.workflow_lab, 'workflow_to_prompt', lambda *args: graph)
    bridge = cockpit.GenerationBridge()
    submit = Mock()
    monkeypatch.setattr(bridge, '_submit_and_save', submit)
    client = Mock()
    client.upload_image.side_effect = lambda p: {'name': p.name}
    with pytest.raises(cockpit.workflow_lab.ComfyError, match='reference connections are invalid'):
        bridge._run_reference_stage(client, info, cockpit.QWEN21_REFERENCE_WORKFLOW,
            tmp_path/'source.png', 'A portrait', 'stamp', 'Qwen21',
            secondary_image=tmp_path/'pose.png', model_override=cockpit.QWEN21_MODEL)
    submit.assert_not_called()
