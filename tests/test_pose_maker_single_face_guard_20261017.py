"""Isolated guard regression; do not import or launch the Gradio application."""
import ast
from pathlib import Path
import pytest


def guard():
    source = Path(__file__).resolve().parents[1] / 'genesis/reference/pose_maker_app.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
              and node.name == '_single_reactor_face_index')
    namespace = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])),
                 str(source), 'exec'), namespace)
    return namespace['_single_reactor_face_index']


@pytest.mark.parametrize('value,expected', [(0, '0'), (1, '1'), ('2', '2'), (3.0, '3')])
def test_single_face_index_accepts_one_valid_target(value, expected):
    assert guard()(value, 'Target face') == expected


@pytest.mark.parametrize('value', ['0,1', 'all', -1, 1.5, None, float('inf')])
def test_single_face_index_blocks_multiple_or_invalid_targets(value):
    with pytest.raises(ValueError, match='one non-negative face index'):
        guard()(value, 'Target face')
