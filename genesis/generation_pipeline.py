"""Order-independent generation state and model-aware prompt adaptation.

This module deliberately contains no Qt or ComfyUI side effects.  The UI can
change source, preset, model, LoRA, or stage switches in any order and derive a
validated execution plan only when Generate is pressed.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

from genesis.model_compatibility import is_compatible, model_family


@dataclass(frozen=True)
class GenerationState:
    source_image: str = ""
    pose_image: str = ""
    preset_id: str = ""
    prompt: str = ""
    negative_prompt: str = ""
    model: str = ""
    lora: str = "None"
    use_stage2: bool = False
    use_stage3: bool = False
    use_upscale: bool = False

    def with_changes(self, **changes) -> "GenerationState":
        """Return a changed state without clearing unrelated selections."""
        unknown = set(changes) - set(self.__dataclass_fields__)
        if unknown:
            raise TypeError("Unknown generation state field(s): " + ", ".join(sorted(unknown)))
        return replace(self, **changes)


@dataclass(frozen=True)
class PipelineStage:
    number: int
    name: str
    workflow: str
    input_source: str


def adapt_prompt(prompt: str, model: str, *, source_image: bool = False) -> str:
    """Wrap user/preset text in a family-specific prompt structure.

    The user's text is retained verbatim.  Adapters add structure only and do
    not silently inject LoRA trigger words or unsupported negative syntax.
    """
    text = " ".join((prompt or "").split())
    if not text:
        return ""
    family = model_family(model)
    if family == "qwen_image":
        identity = (
            "Preserve the same person, facial identity, skin tone, hair, and clothing from image1. "
            if source_image else "Create one coherent subject with stable identity. "
        )
        return identity + "Pose and action: " + text + " Change only what the instruction requires."
    if family in {"flux2_klein_4b", "flux2_klein_9b_base", "flux2_klein_9b_kv", "aisha_9b"}:
        return (
            "Subject: " + text
            + " Setting: preserve or infer a coherent environment."
            + " Composition: natural camera perspective, stable body geometry, readable hands and limbs."
            + " Lighting: physically plausible light and shadow."
            + " Texture: photorealistic skin, hair, fabric, and fine detail."
        )
    if family == "sdxl":
        return text + ", photorealistic, coherent composition, realistic anatomy, detailed texture"
    return text


def validate_generation_state(state: GenerationState) -> list[str]:
    errors: list[str] = []
    if not state.prompt.strip():
        errors.append("A prompt or preset is required.")
    if not state.model.strip():
        errors.append("A model is required.")
    if not is_compatible(state.model, state.lora):
        errors.append(f"LoRA {state.lora!r} is incompatible with model {state.model!r}.")
    if state.use_stage3 and not state.source_image:
        errors.append("Stage 3 face lock requires an original source image.")
    return errors


def build_pipeline_plan(state: GenerationState, workflow_root: str | Path = "") -> list[PipelineStage]:
    """Describe stage hand-offs; each later stage consumes the prior output."""
    errors = validate_generation_state(state)
    if errors:
        raise ValueError(" ".join(errors))
    root = Path(workflow_root) if workflow_root else Path()
    stages = [
        PipelineStage(
            1,
            "Phr00t pose" if state.source_image else "Model generation",
            str(root / "STAGE_1_PHR00T_POSE.json") if state.source_image else "validated-create",
            state.source_image or "text-to-image",
        )
    ]
    previous = "stage1.output"
    if state.use_stage2:
        stages.append(PipelineStage(2, "Lustify refine", str(root / "STAGE_2_LUSTIFY_REFINE.json"), previous))
        previous = "stage2.output"
    if state.use_stage3:
        stages.append(PipelineStage(3, "ReActor face lock", str(root / "STAGE_3_REACTOR_ROCM.json"), previous))
        previous = "stage3.output"
    if state.use_upscale:
        stages.append(PipelineStage(4, "Ultimate SD upscale", str(root / "SD_UPSCALE_REFERENCE.json"), previous))
    return stages


def compatible_selection(model: str, selected_loras: Iterable[str]) -> list[str]:
    """Reject, rather than silently discard, an incompatible selection."""
    selected = [name for name in selected_loras if name and name != "None"]
    blocked = [name for name in selected if not is_compatible(model, name)]
    if blocked:
        raise ValueError("Incompatible model/LoRA selection: " + ", ".join(blocked))
    return selected
