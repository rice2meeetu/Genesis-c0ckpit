"""Non-mutating source-pack selection; generation supplies the model edit template."""
from __future__ import annotations
import json
import math
import re
from pathlib import Path
from genesis.model_compatibility import model_family
from genesis.generation_pipeline import REFCONTROL_TRIGGER, normalize_identity_instruction


def source_metadata(row, source_path=None):
    """Read declared import metadata or a same-name JSON sidecar, never image pixels."""
    declared = row.get("sourceMetadata") or row.get("source_metadata")
    if isinstance(declared, dict):
        return dict(declared)
    if row.get("source_prompt"):
        return {"prompt": row["source_prompt"], "settings": row.get("source_settings", {}),
                "trigger_words": row.get("source_trigger_words", []),
                "models": row.get("source_models", []),
                "attribution": row.get("source_attribution", "Original import metadata")}
    if source_path and row.get("prompt"):
        return {key: row[key] for key in ("prompt", "negative_prompt", "settings", "models", "model_prompts", "trigger_words", "attribution") if key in row} | {"attribution": row.get("attribution") or str(Path(source_path).parent)}
    if source_path:
        sidecar = Path(source_path).with_suffix(".json")
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                return {**data, "attribution": data.get("attribution") or str(sidecar)}
        except (OSError, ValueError):
            pass
    return {}


def preset_payload(row, model):
    """Prefer suitable original text, without combining it with the Grok fallback.

    Variants are keyed by exact model filename (v19/v23 remain distinct) or
    architecture. Sampler settings require an explicit matching target.
    RefControl's trigger is supplied later, only with its validated image inputs.
    """
    family = model_family(model)
    original = source_metadata(row)
    variants = original.get("model_prompts", {})
    variant = variants.get(model, variants.get(family, {})) if isinstance(variants, dict) else {}
    if isinstance(variant, str):
        variant = {"prompt": variant}
    if not isinstance(variant, dict):
        variant = {}
    targets = original.get("models", original.get("model_target", original.get("model", [])))
    if isinstance(targets, str):
        targets = [targets]
    elif not isinstance(targets, (list, tuple)):
        targets = ["invalid-target"]
    def matches(target):
        def stem(value):
            value = str(value).replace("\\", "/").split("/")[-1].lower()
            return value.rsplit(".", 1)[0] if value.endswith((".safetensors", ".gguf", ".ckpt")) else value
        return str(target) == family or stem(target) == stem(model)
    matched = any(matches(target) for target in targets)
    suitable = not targets or matched
    chosen = {**original, **variant} if suitable else dict(variant)
    source_prompt = str(chosen.get("prompt") or "").strip()
    text = source_prompt or str(row.get("prompt") or "").strip()
    # Image ordering syntax belongs to the executable RefControl route alone.
    text = re.sub(re.escape(REFCONTROL_TRIGGER) + r"[.\s]*", "", text, flags=re.I)
    scoped = bool(variant) or matched
    triggers = chosen.get("trigger_words", []) if scoped else []
    if isinstance(triggers, str):
        triggers = [triggers]
    elif not isinstance(triggers, (list, tuple)):
        triggers = []
    for trigger in triggers:
        trigger = str(trigger).strip()
        if trigger and trigger.lower() != REFCONTROL_TRIGGER.lower() and trigger.lower() not in text.lower():
            text += ". " + trigger
    negative = str(chosen["negative_prompt"] or "") if "negative_prompt" in chosen else str(row.get("negativePrompt") or "")
    if family == "qwen_image":
        negative = ""
    settings = {}
    # Unscoped pack settings can be for a completely different architecture.
    values = chosen.get("settings", {})
    if scoped and isinstance(values, dict):
        values = dict(values)
        for canonical, alias in (("steps", "num_steps"), ("cfg", "cfg_scale"), ("denoise", "denoising_strength"), ("sampler", "sampler_name")):
            if canonical not in values and alias in values:
                values[canonical] = values[alias]
        ranges = {"steps": (1,100), "cfg": (0,30), "denoise": (0,1),
                  "width": (64,4096), "height": (64,4096), "seed": (-1,2**53-1)}
        for key, (low, high) in ranges.items():
            value = values.get(key)
            if isinstance(value, (int,float)) and not isinstance(value,bool) and math.isfinite(value) and low <= value <= high:
                settings[key] = int(value) if key in ("steps","width","height","seed") else value
        for key, allowed in {
            "sampler": {"er_sde","euler","euler_ancestral","res_multistep","dpmpp_2m","dpmpp_2m_sde","dpmpp_sde","dpmpp_3m_sde"},
            "scheduler": {"beta","simple","normal","karras","sgm_uniform"},
        }.items():
            if values.get(key) in allowed:
                settings[key] = values[key]
    attribution = chosen.get("attribution", original.get("attribution", "")) if source_prompt or settings or triggers else row.get("promptSource", "Grok fallback")
    if isinstance(attribution, dict):
        attribution = " · ".join(str(attribution[k]) for k in ("author", "title", "url") if attribution.get(k))
    return {"prompt": normalize_identity_instruction(text), "negativePrompt": negative,
            "settings": settings, "promptSource": "SOURCE_PACK" if source_prompt else row.get("promptSource", "GROK_FALLBACK"),
            "attribution": str(attribution),
            "settingsSource": "SOURCE_PACK" if settings else "MODEL_DEFAULT",
            "settingsNote": "Pack settings applied for this model." if settings else "Using this model’s defaults; no matching tested pack settings."}


def pose_preset_references(rows):
    """Preset sections reference the existing control file; no copying or new identities."""
    seen = set()
    result = []
    for row in rows:
        key = row.get("source") or row.get("poseId")
        if not key or key in seen:
            continue
        seen.add(key)
        result.append({**row, "id": "pose:" + str(row.get("poseId", key)),
                       "label": row.get("name", "Pose"), "collection": "Imported poses"})
    return result
