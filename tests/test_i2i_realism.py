"""Neutral, offline prompt contracts; no image generation or inspection."""
import json
import pytest
import qt_cockpit as c
from genesis.generation_pipeline import (adapt_prompt, realism_prompt,
    normalize_identity_instruction, REALISM_COMPONENTS, REFCONTROL_TRIGGER)

@pytest.mark.parametrize('model', [c.REMOTE_PHR00T_V19_MODEL,
    c.REMOTE_PHR00T_MODEL, c.REMOTE_PHR00T_V23_Q2_MODEL,
    c.FOUR_B_MODEL, c.REGULAR_9B_MODEL, c.LOCAL_AISHA_9B_MODEL,
    c.REMOTE_MIRACLEIN_9B_MODEL, c.QWEN21_MODEL, c.REMOTE_DONUTS_MODEL])
def test_i2i_realism_baseline_and_flexible_identity(model):
    result = adapt_prompt('Stand beside a chair with realistic skin texture, realistic anatomy.',
                          model, source_image=True, pose_image=True)
    for phrase, _ in REALISM_COMPONENTS:
        assert result.lower().count(phrase) == 1
    assert 'distinguishing features' in result
    assert 'expression' in result and 'viewpoint' in result
    assert REFCONTROL_TRIGGER not in result
    assert 'pixel-perfect' not in result


def test_realism_deduplication_and_refinement_inheritance():
    first = realism_prompt('Stand beside a chair, realistic skin texture, natural skin texture, sharp focus.')
    assert realism_prompt(first) == first
    for phrase, _ in REALISM_COMPONENTS:
        assert first.count(phrase) == 1
    second = adapt_prompt(first, c.REMOTE_PHR00T_MODEL,
                          source_image=True, include_realism=False)
    assert 'Stand beside a chair' in second
    assert all(phrase not in second for phrase, _ in REALISM_COMPONENTS)


def test_universal_rigid_rules_removed_without_losing_pose():
    original = ('Keep the exact same person, face, hair, body proportions and appearance from image1. '
                'Do not change facial features. Maintain pixel-perfect fidelity to the original face. '
                'Stand with the left hand on a chair.')
    assert normalize_identity_instruction(original) == 'Stand with the left hand on a chair.'


@pytest.mark.parametrize('name,node', [
    ('STAGE_1_PHR00T_POSE', '4'), ('PHR00T_QWEN_RAPID_V19_AIO', '4'),
    ('PHR00T_QWEN_RAPID_V23', '5'), ('KLEIN9B_REMOTE', '4'),
    ('GENESIS_MIRACLEIN_9B_EDIT', '4'), ('GENESIS_PORNMASTER_9B_EDIT', '4'),
    ('GENESIS_DARKBEAST_9B_IDENTITY', '4')])
def test_saved_i2i_templates_have_shared_realism(name, node):
    graph = json.loads((c.REFERENCE_WORKFLOW_ROOT / (name + '.json')).read_text())
    text = graph[node]['inputs']['text'] if 'nodes' not in graph else next(
        n['widgets_values'][0] for n in graph['nodes'] if str(n['id']) == node)
    assert all(text.count(phrase) == 1 for phrase, _ in REALISM_COMPONENTS)
    assert 'pixel-perfect' not in text


@pytest.mark.parametrize('source', [False, True])
def test_undistilled_base_9b_keeps_base_settings(source):
    values = c.model_generation_settings(c.REGULAR_9B_MODEL, source=source)
    assert values['defaultSteps'] == 50
    assert values['defaultCfg'] == 4.0
    assert c.model_generation_settings(c.FOUR_B_MODEL)['defaultSteps'] == 4


def test_v23_quantizations_use_v23_sampler_instead_of_v19():
    for model in c.REMOTE_PHR00T_V23_MODELS | c.REMOTE_PHR00T_V23_CACHE_MODELS:
        settings = c.model_generation_settings(model, source=True)
        assert settings['defaultSteps'] == 4
        assert settings['defaultSampler'] == 'euler_ancestral'
        assert settings['defaultScheduler'] == 'beta'
    assert c.model_generation_settings(c.REMOTE_PHR00T_V19_MODEL)['defaultSampler'] == 'er_sde'
