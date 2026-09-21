"""Static safety checks for manual GPU benchmark definitions."""

from genesis.model_compatibility import is_compatible
from tests.gpu_klein4b_lora_benchmark import LORAS as KLEIN4B_LORAS, MODEL as KLEIN4B_MODEL
from tests.gpu_klein9b_lora_benchmark import APPROVED_LORAS as KLEIN9B_LORAS, MODEL as KLEIN9B_MODEL


def test_klein4b_benchmark_contains_only_compatible_loras():
    assert KLEIN4B_LORAS
    for _label, lora, _strength in KLEIN4B_LORAS:
        assert is_compatible(KLEIN4B_MODEL, lora), lora


def test_klein9b_benchmark_contains_only_compatible_loras():
    assert KLEIN9B_LORAS
    for lora in KLEIN9B_LORAS.values():
        assert is_compatible(KLEIN9B_MODEL, lora), lora
