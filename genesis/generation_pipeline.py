"""Order-independent generation state and model-aware prompt adaptation.

This module deliberately contains no Qt or ComfyUI side effects.  The UI can
change source, preset, model, LoRA, or stage switches in any order and derive a
validated execution plan only when Generate is pressed.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable
import re

from genesis.model_compatibility import is_compatible, model_family, lora_trigger

REFCONTROL_LORA = "refcontrol_v2_poses.safetensors"
REFCONTROL_TRIGGER = lora_trigger(REFCONTROL_LORA)
REFCONTROL_DEFAULT_STRENGTH = 0.9


def uses_refcontrol(model: str, loras: Iterable[str]) -> bool:
    return any(Path(name.replace("\\", "/")).name == REFCONTROL_LORA
               and is_compatible(model, name) for name in loras)


def refcontrol_prompt(prompt: str, model: str, loras: Iterable[str], *, has_pose: bool, has_source: bool) -> str:
    if uses_refcontrol(model, loras):
        if not has_pose or not has_source:
            raise ValueError("RefControl requires a separate pose/control image and original source image.")
        if REFCONTROL_TRIGGER not in prompt:
            return REFCONTROL_TRIGGER + ". " + prompt
    return prompt


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


REALISM_COMPONENTS = (
    ("natural realistic skin texture", r"(?:natural (?:realistic )?|realistic )skin texture"),
    ("coherent anatomy", r"(?:coherent|realistic) anatomy"),
    ("natural body proportions", r"(?:natural|realistic) (?:body )?proportions"),
    ("fine hair and detail", r"fine hair(?: and detail| detail)?"),
    ("natural photographic lighting", r"natural (?:photographic )?lighting"),
    ("natural photographic sharpness", r"natural (?:photographic )?sharpness|sharp focus"),
)
IDENTITY_INSTRUCTION = (
    "Preserve recognizable facial identity and distinguishing features. "
    "Allow pose, viewpoint, expression and lighting to change naturally."
)


def normalize_identity_instruction(prompt: str) -> str:
    """Remove preset-wide rigid identity rules while preserving the pose text."""
    text = prompt or ""
    rules = (
        r"Keep the exact same person, face, hair, body proportions and appearance from image1\.\s*",
        r"Do not change facial features\.\s*",
        r"Maintain pixel[- ]perfect fidelity to the original face\.\s*",
    )
    for rule in rules:
        text = re.sub(rule, "", text, flags=re.I)
    text = re.sub(r"pixel[- ]perfect (?:facial identity|face|fidelity)",
                  "recognizable facial identity and distinguishing features", text, flags=re.I)
    return " ".join(text.split())


def realism_prompt(prompt: str, *, include_realism: bool = True) -> str:
    """Add missing photographic qualities once; refinement inherits them."""
    text = normalize_identity_instruction(prompt)
    missing = []
    for phrase, pattern in REALISM_COMPONENTS:
        seen = False
        def replace(match):
            nonlocal seen
            if not include_realism or seen:
                return ""
            seen = True
            return phrase
        text = re.sub(pattern, replace, text, flags=re.I)
        if include_realism and not seen:
            missing.append(phrase)
    # Remove separators left by duplicate preset descriptors.
    text = re.sub(r"(?:,\s*){2,}", ", ", text)
    text = re.sub(r"\s+([,.])", r"\1", text).strip(" ,.")
    if missing:
        text += ". Realism: " + ", ".join(missing)
    return text.rstrip(" .") + "." if text else ""


def adapt_prompt(prompt: str, model: str, *, source_image: bool = False,
                 pose_image: bool = False, include_realism: bool = True) -> str:
    """Use model-specific syntax with a shared, deduplicated I2I realism baseline.

    Pose instructions remain intact. Rigid library-wide identity wording is
    replaced by recognizable identity preservation, and no appearance LoRA
    triggers or unsupported negative syntax are injected.
    """
    text = normalize_identity_instruction(prompt)
    if not text:
        return ""
    family = model_family(model)
    if family == "qwen_image_2_1":
        if source_image:
            pose = ("Use <image2> only for pose and composition. " if pose_image else "")
            result = ("Use <image1> as the original identity reference. " + IDENTITY_INSTRUCTION
                      + " " + pose + "Instruction: " + text)
            return realism_prompt(result, include_realism=include_realism)
        return "Create the requested image with coherent anatomy and composition. Instruction: " + text
    if family == "qwen_image":
        if source_image:
            identity = "Preserve the same person and facial identity, recognizable facial features and distinguishing features from image1. "
            pose = ("Use image2 only for pose, body arrangement, and composition; keep image1 as the identity reference. "
                    if pose_image else "")
            result = (identity + pose + "Allow the body pose, body position, framing, composition, viewpoint, expression and lighting to change naturally according to the instruction. "
                      + "Edit instruction: " + text)
            return realism_prompt(result, include_realism=include_realism)
        return "Create one coherent subject with stable identity. Instruction: " + text
    if family in {"flux2_klein_4b", "flux2_klein_9b_base", "flux2_klein_9b_kv", "aisha_9b"}:
        if source_image:
            result = ("Subject: " + text + " Identity: " + IDENTITY_INSTRUCTION
                      + " Setting: preserve or infer a coherent environment."
                      + " Composition: follow the selected pose/control independently of the original identity source."
                      + " Lighting: follow the requested scene naturally."
                      + " Texture: preserve distinguishing appearance details.")
            return realism_prompt(result, include_realism=include_realism)
        return (
            "Subject: " + text
            + " Setting: preserve or infer a coherent environment."
            + " Composition: natural camera perspective, stable body geometry, readable hands and limbs."
            + " Lighting: physically plausible light and shadow."
            + " Texture: photorealistic skin, hair, fabric, and fine detail."
        )
    if family == "sdxl":
        if source_image:
            return realism_prompt(text + ". " + IDENTITY_INSTRUCTION,
                                  include_realism=include_realism)
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
    if len(set(selected)) != len(selected):
        raise ValueError("Select each LoRA only once.")
    blocked = [name for name in selected if not is_compatible(model, name)]
    if blocked:
        raise ValueError("Incompatible model/LoRA selection: " + ", ".join(blocked))
    return selected
