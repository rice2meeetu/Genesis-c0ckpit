"""Conservative model/LoRA compatibility rules for GENESIS.

Names from ComfyUI are classified without loading model tensors.  Unknown
adapters are deliberately not offered for a known model family: choosing no
LoRA is safer than submitting an adapter with incompatible tensor shapes.
"""

from __future__ import annotations

from pathlib import Path


WORKFLOW_DEFAULT = "Use workflow default"

KLEIN_4B_LORAS = {
    "F2K4BBabe_Engel_v1.0.safetensors",
    "hina_flux2klein4b_asianMix_v4.0-lora.safetensors",
}

KLEIN_9B_LORAS = {
    "Flux Klein - NSFW v2.safetensors",
    "Klein_Anatomy_Revamped.safetensors",
    "flux2klein_body_version_a.safetensors",
    "flux2klein_tocowgirl.safetensors",
    "FK_sloppydeepthroat_epoch_10.safetensors",
    "FK_teeththroat.safetensors",
}

# Empty until a repeatable render succeeds with the validated four-step KV
# workflow.  Ordinary Klein 9B compatibility does not prove KV compatibility.
KLEIN_9B_KV_VERIFIED_LORAS: set[str] = set()

FLUX1_LORAS = {
    "Flux-NSFW-uncensored.safetensors",
    "alimama-creative---FLUX.1-Turbo-Alpha/diffusion_pytorch_model.safetensors",
}

SDXL_LORAS = {
    "add-detail-xl (1).safetensors",
    "add-detail-xl.safetensors",
    "latent-consistency---lcm-lora-sdxl/pytorch_lora_weights.safetensors",
    "genshin impact pierro-V1.safetensors",
}

KNOWN_MODELS = {
    "biglust17_v17.safetensors": "sdxl",
    "juggernautXL_ragnarokBy.safetensors": "sdxl",
    "lustifySDXLNSFW_endgameDMD2.safetensors": "sdxl",
    "lustifySDXLNSFWSFW_v20LIGHTNING.safetensors": "sdxl",
    "Qwen-Rapid-AIO-NSFW-v19.safetensors": "qwen_image",
    "aisha_nsfw_beta_v8_fp8.safetensors": "aisha_9b",
    "flux-2-klein-4b.safetensors": "flux2_klein_4b",
    "flux-2-klein-9b-kv-fp8.safetensors": "flux2_klein_9b_kv",
    "flux1-dev-kontext_fp8_scaled.safetensors": "flux1",
    "fluxedUpFluxNSFW_40DevFp8.safetensors": "flux1",
}


def model_family(name: str | None) -> str:
    value = (name or "").replace("\\", "/").lower()
    stem = Path(value).name
    if stem in {key.lower(): family for key, family in KNOWN_MODELS.items()}:
        return {key.lower(): family for key, family in KNOWN_MODELS.items()}[stem]
    if "aisha" in stem:
        return "aisha_9b"
    if "klein" in stem and "9b" in stem and ("kv" in stem or "9b_kv" in value):
        return "flux2_klein_9b_kv"
    if "klein" in stem and "9b" in stem:
        return "flux2_klein_9b_base"
    if "klein" in stem and "4b" in stem:
        return "flux2_klein_4b"
    if any(token in value for token in ("fluxup", "fluxedup", "persephone", "flux.1", "flux1")):
        return "flux1"
    if any(token in value for token in ("sdxl", "lustify", "pony")):
        return "sdxl"
    return "unknown"


def lora_family(name: str | None) -> str:
    value = (name or "").replace("\\", "/")
    base = Path(value).name
    if value in KLEIN_4B_LORAS or base in KLEIN_4B_LORAS:
        return "flux2_klein_4b"
    if value in KLEIN_9B_LORAS or base in KLEIN_9B_LORAS:
        return "flux2_klein_9b_base"
    if value in FLUX1_LORAS or base in {Path(item).name for item in FLUX1_LORAS}:
        return "flux1"
    if value in SDXL_LORAS or base in {Path(item).name for item in SDXL_LORAS}:
        return "sdxl"
    lowered = value.lower()
    if "klein4b" in lowered or "klein_4b" in lowered:
        return "flux2_klein_4b"
    if "klein" in lowered and "9b" in lowered:
        return "flux2_klein_9b_base"
    if "sdxl" in lowered or "xl" in lowered:
        return "sdxl"
    return "unknown"


def is_compatible(model: str | None, lora: str | None) -> bool:
    if not lora or lora == WORKFLOW_DEFAULT or lora == "None":
        return True
    family = model_family(model)
    base = Path(lora.replace("\\", "/")).name
    if family == "flux2_klein_9b_kv":
        return base in KLEIN_9B_KV_VERIFIED_LORAS
    return lora_family(lora) == family


def compatible_loras(model: str | None, available: list[str]) -> list[str]:
    return [name for name in available if is_compatible(model, name)]


def compatibility_note(model: str | None) -> str:
    family = model_family(model)
    return {
        "flux2_klein_4b": "Klein 4B · only 4B LoRAs",
        "flux2_klein_9b_base": "Klein 9B Base · only 9B LoRAs",
        "flux2_klein_9b_kv": "Klein 9B-KV · LoRAs disabled until KV render verification",
        "aisha_9b": "Aisha 9B · use only adapters verified specifically with Aisha",
        "flux1": "FLUX.1 · only FLUX.1 LoRAs",
        "sdxl": "SDXL · only SDXL LoRAs",
        "qwen_image": "Qwen Image · no installed LoRA has verified compatibility",
    }.get(family, "Unknown model family · workflow defaults only")
