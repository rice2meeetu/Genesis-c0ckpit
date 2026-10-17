"""Conservative model/LoRA compatibility rules for GENESIS.

Compatibility is evidence-gated.  Exact files with verified base-model metadata
are preferred over filename heuristics, and explicitly blocked/unverified files
remain unavailable until a repeatable render proves the combination.
"""

from __future__ import annotations

from pathlib import Path

WORKFLOW_DEFAULT = "Use workflow default"

# Loaded exclusively by the FaceID pipeline, never as a user-stackable LoRA.
INTERNAL_FACEID_LORAS = {"ip-adapter-faceid-plusv2_sdxl_lora.safetensors"}

KLEIN_4B_LORAS = {
    "F2K4BBabe_Engel_v1.0.safetensors",
    "F2K4BBabe_Americano_v1.0.safetensors",
    "f2k_4B_consist_20260314.safetensors",
    # Structurally validated and completed a coherent 512px render on
    # 2026-09-11. Keep strictly scoped to Klein 4B.
    "klein4b-deepthroat-22epoc-k3nk.safetensors",
}

# Explicit Qwen Image 2.1 adapter. Its upstream model card targets 2.1 and
# weight keys are ComfyUI model-only compatible; never enable Qwen Image 2.0
# LoRAs just because their training metadata says qwen_image_2.
# Keep the otherwise matching TheseAlpacas V2 *out* of the picker on this
# PC: ComfyUI's Qwen 2.1 + adapter render caused system-wide RAM pressure
# and Linux OOM-killed genesis-comfyui.service on 2026-10-17 at 18:01.
# Its exact file SHA matches an upstream 2.1 file, but that is not a local
# runtime pass. Revisit after a controlled lower-memory or RunPod validation.
QWEN_IMAGE21_LORAS = {"Qwen2.1_Anything2RealCharacters.safetensors"}

# Family compatibility is not enough after the 2026-09-21 KFD/SVM incident.
# Keep this empty until a LoRA completes a guarded current-profile render
# without any KFD/SVM warning.  This makes ordinary 4B baseline generation
# usable while preventing unverified adapter memory transitions.
KLEIN_4B_RUNTIME_VERIFIED_LORAS: set[str] = set()

# Metadata-verified on the GENESIS machine as flux2_klein_9b.
KLEIN_9B_LORAS = {
    # Exact source hashes matched the 9B repositories on 2026-10-13;
    # tensor projections are 4096 wide, matching Klein 9B rather than 4B.
    "flux2klein_bj.safetensors",
    "flux2klein_cowgirl.safetensors",
    "f2k_9B_lcs_consist_20260415.safetensors",
    # Shared-volume safetensors metadata inspected on B2, 2026-10-05.
    "Flux2 Klein 9B Realistic Detail LoRA.safetensors",
    "Flux2-Klein-9B-consistency-V2.safetensors",
    "Flux Klein - NSFW v2.safetensors",
    "Klein_Anatomy_Revamped.safetensors",
    "flux2klein_body_version_a.safetensors",
    # Base-family metadata recovered from the 2026-09-19 LoRA audit.
    "flux2klein_tocowgirl.safetensors",
    "FK_sloppydeepthroat_epoch_10.safetensors",
    "FK_teeththroat.safetensors",
    # RunPod inventory + upstream model documentation identify this as a
    # FLUX.2 Klein 9B reference-pose adapter. Runtime quality remains
    # experimental until a controlled GENESIS render is reviewed.
    "refcontrol_v2_poses.safetensors",
}

# Expose verified training triggers to the UI/assistant. Prompt adaptation never
# injects appearance triggers silently. RefControl routing adds its required phrase.
LORA_TRIGGERS = {
    "Flux2 Klein 9B Realistic Detail LoRA.safetensors": "srx_detail",
    "Flux2-Klein-9B-consistency-V2.safetensors": "consistency",
    "F2K4BBabe_Engel_v1.0.safetensors": "F2K4BBabe_Engel_v1.0",
    "FK_sloppydeepthroat_epoch_10.safetensors": "FK_sloppydeepthroat",
    "FK_teeththroat.safetensors": "FK_strappadoblowjob",
    "refcontrol_v2_poses.safetensors": "apply pose from image 1 with reference from image 2",
}

# Exact local files whose base family is known to be Krea 2.
KREA2_LORAS = {
    "k_blackanal.safetensors",
    "lenovo_krea2_2.safetensors",
    "snofs_krea_v1_3D.safetensors",
}

# Cross-family adapters remain blocked on Klein 9B until a local fixed-seed
# validation passes without model-shape errors or KFD/SVM warnings.
KLEIN_9B_COMMUNITY_CROSS_FAMILY_LORAS: set[str] = set()

# These names must stay blocked even if their filename looks like a known
# family.  Move a file into a verified set only after metadata/source evidence
# and a repeatable generation test.
BLOCKED_UNVERIFIED_LORAS = {
    "FLUX2_KLEIN_UNLOCKED_V1.safetensors",
}

# Files with matching family metadata that nevertheless produced a runtime
# safety signal on the GENESIS RX 9060 XT are quarantined separately from
# structurally unverified adapters.
RUNTIME_QUARANTINED_LORAS = {
    # 2026-09-21: neutral Klein 4B render completed sampling, then triggered
    # amdgpu_amdkfd_restore_userptr_worker workqueue warnings (4/5/7/11).
    "hina_flux2klein4b_asianMix_v4.0-lora.safetensors",
}

# Ordinary Klein 9B compatibility does not prove KV compatibility.
KLEIN_9B_KV_VERIFIED_LORAS: set[str] = set()

FLUX1_LORAS = {
    "Flux-NSFW-uncensored.safetensors",
    "alimama-creative---FLUX.1-Turbo-Alpha/diffusion_pytorch_model.safetensors",
}

SDXL_LORAS = {
    "skin texture style v4.safetensors",
    "face_xl_v0_1.safetensors",
    "add-detail-xl (1).safetensors",
    "add-detail-xl.safetensors",
    "latent-consistency---lcm-lora-sdxl/pytorch_lora_weights.safetensors",
    "genshin impact pierro-V1.safetensors",
}

PONY_LORAS = {
    'Realism_Lora_By_Stable_Yogi_Pony_V2.safetensors',
    'Super_Skin_Detailer_By_Stable_Yogi_PD0_V1.safetensors',
}

KNOWN_MODELS = {
    'ponyRealism_V23.safetensors': 'pony_sdxl',
    'mopMixtureOfPerverts_instaV10DMD.safetensors': 'sdxl',
    'epicrealismXL_vxviLastfameRealism.safetensors': 'sdxl',
    'Realistic_Vision_V6.0_NV_B1.safetensors': 'sd15',
    "Qwen-Rapid-AIO-NSFW-v19_Q4_K.gguf": "qwen_image",
    "Qwen-Rapid-NSFW-v23_Q2_K.gguf": "qwen_image",
    "aisha_nsfw_beta_v1_4b_distilled_bf16.safetensors": "flux2_klein_4b",
    "aisha-official-flux-2-klein-9b-base-nsfw-standard.safetensors": "aisha_9b",
    "biglust17_v17.safetensors": "sdxl",
    "biglustydonutmixNSFW_v12.safetensors": "sdxl",
    "donutsdeliverymixV4_v41.safetensors": "sdxl",
    "juggernautXL_ragnarokBy.safetensors": "sdxl",
    "lustifySDXLNSFW_endgameDMD2.safetensors": "sdxl",
    "lustifySDXLNSFWSFW_v20LIGHTNING.safetensors": "sdxl",
    "Qwen-Rapid-AIO-NSFW-v19.safetensors": "qwen_image",
    "Qwen-Rapid-NSFW-v23_Q8_0.gguf": "qwen_image",
    "Qwen-Rapid-AIO-NSFW-v23.safetensors": "qwen_image",
    "qwen_image_2.1_bf16.safetensors": "qwen_image_2_1",
    "aisha_nsfw_beta_v8_fp8.safetensors": "aisha_9b",
    "aisha_nsfw_beta_v9_7_distilled_bf16.safetensors": "aisha_9b",
    "flux-2-klein-4b.safetensors": "flux2_klein_4b",
    "flux-2-klein-9b.safetensors": "flux2_klein_9b_base",
    "flux-2-klein-base-9b-Q4_K_M.gguf": "flux2_klein_9b_base",
    "flux-2-klein-9b-kv-fp8.safetensors": "flux2_klein_9b_kv",
    "miracleinNSFWGeneration_20FP8.safetensors": "flux2_klein_9b_base",
    "pornmasterFlux2Klein_v3-fp8.safetensors": "flux2_klein_9b_base",
    "darkBeast_DBKleinv2BFS.safetensors": "flux2_klein_9b_base",
    "darkBeastMar0326Latest_dbkleinv2BFS.safetensors": "flux2_klein_9b_base",
    "flux1-dev-kontext_fp8_scaled.safetensors": "flux1",
    "fluxedUpFluxNSFW_40DevFp8.safetensors": "flux1",
}

_KNOWN_MODELS_LOWER = {key.lower(): family for key, family in KNOWN_MODELS.items()}


def _basename(name: str | None) -> str:
    return Path((name or "").replace("\\", "/")).name


def model_family(name: str | None) -> str:
    value = (name or "").replace("\\", "/").lower()
    stem = Path(value).name
    if stem in _KNOWN_MODELS_LOWER:
        return _KNOWN_MODELS_LOWER[stem]
    if "qwen-rapid" in stem or "qwenrapid" in stem or "phr00t" in stem:
        return "qwen_image"
    if "aisha" in stem:
        return "aisha_9b"
    if "klein" in stem and "9b" in stem and ("kv" in stem or "9b_kv" in value):
        return "flux2_klein_9b_kv"
    if "klein" in stem and "9b" in stem:
        return "flux2_klein_9b_base"
    if "klein" in stem and "4b" in stem:
        return "flux2_klein_4b"
    if "krea2" in stem or "krea_2" in stem or "krea-2" in stem:
        return "krea2"
    if any(token in value for token in ("fluxup", "fluxedup", "persephone", "flux.1", "flux1")):
        return "flux1"
    if any(token in value for token in ("sdxl", "lustify", "pony")):
        return "sdxl"
    return "unknown"


def lora_family(name: str | None) -> str:
    value = (name or "").replace("\\", "/")
    base = _basename(value)
    if base in RUNTIME_QUARANTINED_LORAS:
        return "runtime_quarantined"
    if base in BLOCKED_UNVERIFIED_LORAS:
        return "unverified"
    if base in QWEN_IMAGE21_LORAS:
        return "qwen_image_2_1"
    if value in KLEIN_4B_LORAS or base in KLEIN_4B_LORAS:
        return "flux2_klein_4b"
    if value in KLEIN_9B_LORAS or base in KLEIN_9B_LORAS:
        return "flux2_klein_9b_base"
    if value in KREA2_LORAS or base in KREA2_LORAS:
        return "krea2"
    if value in FLUX1_LORAS or base in {Path(item).name for item in FLUX1_LORAS}:
        return "flux1"
    if value in PONY_LORAS or base in PONY_LORAS:
        return 'pony_sdxl'
    if value in SDXL_LORAS or base in {Path(item).name for item in SDXL_LORAS}:
        return "sdxl"
    lowered = value.lower()
    # Heuristics can classify otherwise-unknown files, but exact blocked names
    # above always win.
    if "krea2" in lowered or "krea_2" in lowered or "krea-2" in lowered:
        return "krea2"
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
    base = _basename(lora)
    if base in INTERNAL_FACEID_LORAS:
        return False  # internal adapter is loaded once by attach_sdxl_faceid
    if base in BLOCKED_UNVERIFIED_LORAS or base in RUNTIME_QUARANTINED_LORAS:
        return False
    family = model_family(model)
    if family == "unknown":
        return False
    if family == "flux2_klein_4b":
        return base in KLEIN_4B_RUNTIME_VERIFIED_LORAS
    if family == "flux2_klein_9b_kv":
        return base in KLEIN_9B_KV_VERIFIED_LORAS
    return lora_family(lora) == family


def compatible_loras(model: str | None, available: list[str]) -> list[str]:
    return [name for name in available if not any(part.startswith(".") or "partial" in part.lower() for part in Path(name).parts) and is_compatible(model, name)]


def lora_trigger(name: str | None) -> str:
    """Return a metadata-verified trigger without modifying a prompt."""

    base = _basename(name)
    import re
    canonical = re.sub(r" \(\d+\)(?=\.safetensors$)", "", base)
    return LORA_TRIGGERS.get(base, LORA_TRIGGERS.get(canonical, ""))



# Descriptions are guidance, not claims of measured improvements. Keep
# compatibility gating separate from descriptions; don't expose a LoRA just
# because a name implies a family.
LORA_HELP_BY_FILENAME = {
    "add-detail-xl.safetensors": (
        "SDXL detail adapter. Adds texture/sharpness emphasis; watch for overly "
        "crisp faces or loss of likeness."
    ),
    "add-detail-xl (1).safetensors": (
        "SDXL detail adapter (alternate filename). Adds texture/sharpness emphasis; "
        "compare with the original before increasing strength."
    ),
    "skin texture style v4.safetensors": (
        "SDXL skin-texture style adapter. Inspect faces closely and use a light "
        "strength if the source person must remain recognisable."
    ),
    "face_xl_v0_1.safetensors": (
        "SDXL face-oriented adapter. Filename suggests face styling; this is "
        "not a FaceID/identity-lock model. Test for identity drift."
    ),
    "Flux2 Klein 9B Realistic Detail LoRA.safetensors": (
        "Klein 9B Base detail adapter. Tends toward realism/detail; "
        "check results with the specific checkpoint."
    ),
    "Flux2-Klein-9B-consistency-V2.safetensors": (
        "Klein 9B Base consistency adapter. Intended to help consistency "
        "across outputs; consistent identity is not guaranteed."
    ),
    "refcontrol_v2_poses.safetensors": (
        "Klein 9B pose-reference adapter. Requires the correct two-image roles "
        "in its supported workflow; selecting it alone does not add pose control."
    ),
    "Klein_Anatomy_Revamped.safetensors": (
        "Klein 9B Base anatomy adapter. Intended for body proportions; "
        "inspect outputs for unexpected changes."
    ),
    "flux2klein_body_version_a.safetensors": (
        "Klein 9B Base body-focused adapter. Use conservative strengths and "
        "compare the pose and subject identity."
    ),
    "Qwen2.1_Anything2RealCharacters.safetensors": (
        "Qwen Image 2.1 character-realism adapter. Only for the Qwen Image 2.1 "
        "route; not compatible with Phr00t/Qwen Image 2.0."
    ),
    "NSFW Qwen by TheseAlpacas V2.safetensors": (
        "TheseAlpacas V2 was verified against the published Qwen Image 2.1 "
        "SHA-256 checksum, but is temporarily DISABLED on this local PC: "
        "a 512px four-step render with strength 0.6 caused system RAM exhaustion "
        "and Linux killed ComfyUI. Do not retry without a safer memory profile "
        "or adequate RunPod memory; not compatible with Phr00t/Qwen 2.0."
    ),
    "Realism_Lora_By_Stable_Yogi_Pony_V2.safetensors": (
        "Pony/SDXL realism style adapter; not for ordinary SDXL checkpoints. "
        "Validate skin texture and likeness."
    ),
    "Super_Skin_Detailer_By_Stable_Yogi_PD0_V1.safetensors": (
        "Pony/SDXL skin detail adapter; not for ordinary SDXL checkpoints. "
        "Start gently to avoid overprocessing."
    ),
}


def lora_help(name: str | None) -> str:
    """Concise guidance for a *compatible* picker entry.

    This deliberately does not infer activation words, benchmark scores,
    or provenance from arbitrary safetensors filenames.
    """
    base = _basename(name)
    import re
    canonical = re.sub(r" \(\d+\)(?=\.safetensors$)", "", base)
    text = LORA_HELP_BY_FILENAME.get(base) or LORA_HELP_BY_FILENAME.get(canonical)
    if text:
        return text
    family = lora_family(name)
    display = {
        "sdxl": "SDXL",
        "pony_sdxl": "Pony/SDXL",
        "flux2_klein_9b_base": "Klein 9B Base",
        "flux2_klein_4b": "Klein 4B",
        "qwen_image_2_1": "Qwen Image 2.1",
        "flux1": "FLUX.1",
        "krea2": "Krea 2",
    }.get(family, "Unclassified")
    return (f"{display} adapter. No reviewed purpose or activation phrase is "
            "available for this exact file; use a low strength and compare "
            "outputs rather than assuming the filename guarantees an effect.")

def compatibility_note(model: str | None) -> str:
    family = model_family(model)
    return {
        "flux2_klein_4b": "Klein 4B · LoRAs held until current-profile runtime verification",
        "flux2_klein_9b_base": "Klein 9B Base · native verified 9B LoRAs only",
        "flux2_klein_9b_kv": "Klein 9B-KV · LoRAs disabled until KV render verification",
        "krea2": "Krea 2 · only Krea 2 LoRAs",
        "aisha_9b": "Aisha 9B · use only adapters verified specifically with Aisha",
        "flux1": "FLUX.1 · only FLUX.1 LoRAs",
        "sdxl": "SDXL · only SDXL LoRAs",
        "pony_sdxl": "Pony · only Pony LoRAs",
        "sd15": "SD 1.5 · only SD 1.5 LoRAs",
        "qwen_image": "Qwen Image · no installed LoRA has verified compatibility",
        "qwen_image_2_1": "Qwen Image 2.1 · local TheseAlpacas V2 LoRA held after RAM OOM (2026-10-17); do not force-enable. Only verified 2.1 adapters are offered.",
    }.get(family, "Unknown model family · workflow defaults only")
