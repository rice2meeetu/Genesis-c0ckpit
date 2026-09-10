"""Model-aware pose prompt-map loading for the GENESIS Pose Library.

The source Grok JSON is preserved verbatim.  This module adds a safe runtime
view around it: stable template IDs, model-specific negative behavior, LoRA
recommendation filtering, missing-pose fallback support, and review flags.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from genesis.model_compatibility import compatible_loras, model_family

DEFAULT_KLEIN_MODEL = "flux-2-klein-base-9b-Q4_K_M.gguf"
DEFAULT_MAP_PATH = (
    Path(__file__).resolve().parent
    / "reference"
    / "prompt_maps"
    / "GENESIS_POSE_PROMPTS_KLEIN_v1.json"
)

# The current source map is known to omit this library pose.  Keeping the ID
# explicit makes the omission testable and prevents silent fake coverage.
KNOWN_UNMAPPED_POSE_IDS = {"lying/768512/lying009"}

NEGATIVE_MODE_BY_FAMILY = {
    "flux2_klein_9b_base": "paired",
    "flux2_klein_4b": "paired",
    "flux2_klein_9b_kv": "paired",
    "qwen_image": "zeroed",
}


def template_id(prompt: str) -> str:
    """Stable, content-derived ID without exposing prompt text in metadata."""
    return "grok-" + sha256(prompt.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class PosePromptRecord:
    pose_id: str
    category: str
    resolution: str
    prompt: str
    negative_prompt: str
    prompt_template_id: str
    source: str = "GROK_KLEIN_MAP"


class PosePromptMap:
    def __init__(self, payload: Mapping[str, Any], negative_overrides: Mapping[str, str] | None = None):
        self.payload = dict(payload)
        self.schema_version = str(self.payload.get("schema_version", ""))
        self.model_target = str(self.payload.get("model_target", ""))
        self.negative_overrides = dict(negative_overrides or {})
        raw_poses = self.payload.get("poses")
        if not isinstance(raw_poses, dict):
            raise ValueError("Grok pose prompt map must contain a 'poses' object")

        records: dict[str, PosePromptRecord] = {}
        for key, raw in raw_poses.items():
            if not isinstance(raw, dict):
                raise ValueError(f"Pose record {key!r} is not an object")
            pose_id = str(raw.get("id") or key)
            prompt = str(raw.get("prompt") or "").strip()
            negative = str(raw.get("negative_prompt") or "").strip()
            if pose_id != str(key):
                raise ValueError(f"Pose key/id mismatch: {key!r} != {pose_id!r}")
            if not prompt:
                raise ValueError(f"Pose {pose_id!r} has no positive prompt")
            records[pose_id] = PosePromptRecord(
                pose_id=pose_id,
                category=str(raw.get("category") or "Uncategorised"),
                resolution=str(raw.get("resolution") or ""),
                prompt=prompt,
                negative_prompt=negative,
                prompt_template_id=template_id(prompt),
            )
        self.records = records

    @classmethod
    def load(cls, path: str | Path = DEFAULT_MAP_PATH, negative_overrides_path: str | Path | None = None):
        path = Path(path)
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        overrides: dict[str, str] = {}
        if negative_overrides_path:
            override_payload = json.loads(Path(negative_overrides_path).read_text(encoding="utf-8-sig"))
            if not isinstance(override_payload, dict):
                raise ValueError("Negative override file must contain an object keyed by template ID")
            overrides = {str(k): str(v).strip() for k, v in override_payload.items() if str(v).strip()}
        return cls(payload, overrides)

    @property
    def template_count(self) -> int:
        return len({record.prompt_template_id for record in self.records.values()})

    @property
    def source_negative_count(self) -> int:
        return len({record.negative_prompt for record in self.records.values()})

    @property
    def negative_review_required(self) -> bool:
        # A single global source negative across many distinct positive
        # templates is intentionally flagged for Grok/user review.
        return self.template_count > 1 and self.source_negative_count <= 1

    def record_for(self, pose_id: str, fallback_prompt: str = "", fallback_negative: str = "") -> PosePromptRecord:
        record = self.records.get(pose_id)
        if record is not None:
            override = self.negative_overrides.get(record.prompt_template_id)
            if override:
                return PosePromptRecord(**{**record.__dict__, "negative_prompt": override})
            return record
        prompt = fallback_prompt.strip()
        if not prompt:
            raise KeyError(f"No mapped prompt for pose {pose_id!r}; caller must supply an AUTO/manual fallback")
        return PosePromptRecord(
            pose_id=pose_id,
            category=pose_id.split("/", 1)[0] if "/" in pose_id else "Uncategorised",
            resolution=pose_id.split("/")[1] if pose_id.count("/") >= 2 else "",
            prompt=prompt,
            negative_prompt=fallback_negative.strip(),
            prompt_template_id=template_id(prompt),
            source="AUTO_FALLBACK",
        )

    def negative_for_model(self, record: PosePromptRecord, model: str) -> tuple[str, str]:
        """Return (mode, negative_text) for the selected model family."""
        family = model_family(model)
        mode = NEGATIVE_MODE_BY_FAMILY.get(family, "disabled")
        if mode == "zeroed":
            return mode, ""
        if mode == "paired":
            return mode, record.negative_prompt
        return mode, ""

    def filtered_lora_recommendations(self, model: str, available: list[str] | None = None) -> list[dict[str, Any]]:
        """Return source recommendations only when compatible with model.

        If ``available`` is supplied, a recommendation must also be installed.
        The original source JSON is never modified.
        """
        source = [
            item for key in ("recommended_loras", "optional_loras")
            for item in (self.payload.get(key) or [])
            if isinstance(item, dict) and item.get("name")
        ]
        names = [str(item["name"]) for item in source]
        allowed = set(compatible_loras(model, names))
        if available is not None:
            allowed &= set(available)
        return [dict(item) for item in source if str(item["name"]) in allowed]

    def coverage(self, pose_ids: set[str]) -> dict[str, Any]:
        mapped = set(self.records)
        return {
            "library_total": len(pose_ids),
            "mapped_total": len(mapped & pose_ids),
            "missing": sorted(pose_ids - mapped),
            "extra": sorted(mapped - pose_ids),
            "template_count": self.template_count,
            "source_negative_count": self.source_negative_count,
            "negative_review_required": self.negative_review_required,
        }
