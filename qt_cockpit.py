"""Launch the Qt Quick GENESIS Cockpit reconstruction preview.

The existing Tk application remains the production entry point while this
frontend is reviewed and connected to the established backend.
"""

from __future__ import annotations
import urllib.parse
import random

import argparse
import hashlib
import json
import os
import signal
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path
from math import sqrt

from PyQt6.QtCore import QObject, QSettings, QTimer, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QDesktopServices, QGuiApplication, QIcon
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWidgets import QApplication
from genesis.qt_media_picker import FilePicker as QFileDialog

from genesis.model_compatibility import compatibility_note, compatible_loras, is_compatible, lora_trigger, lora_help, model_family
from genesis.model_registry import MODEL_ROOTS, readiness_report
from genesis.asset_inventory import unavailable_local_assets
from genesis.pose_preset_payload import preset_payload, source_metadata, pose_preset_references
from genesis.pose_prompt_profiles import PosePromptMap
from genesis.generation_pipeline import (adapt_prompt, compatible_selection, refcontrol_prompt,
                                         REFCONTROL_DEFAULT_STRENGTH, REFCONTROL_LORA,
                                         normalize_identity_instruction, uses_refcontrol, realism_prompt)
from genesis import integrations, workflow_lab
from genesis.finishing import finishing_plan, run_finishing, REFINE_INSTRUCTION
from genesis.character_library import add_reference, character_items, preferred_reference, save_character, update_reference, get_character, set_reference_details, reference_is_approved, reference_category
from genesis.media_bridge import MediaBridge
from genesis.backend_routing import Route, remote_url, local_start_allowed, use_route
# GENESIS_COMFY_URL remains supported through backend_routing for older launchers.


PROJECT_ROOT = Path(__file__).resolve().parent
UI_ROOT = PROJECT_ROOT / "genesis" / "qt_ui"
ASSET_ROOT = PROJECT_ROOT / "genesis" / "assets" / "panel_backgrounds"
POSE_INDEX = PROJECT_ROOT / "genesis" / "reference" / "pose_library_index.json"
POSE_THUMB_CACHE = Path.home() / "GENESIS-Photo-Studio" / "cache" / "thumbnails"
WORKFLOW_ROOT = Path.home() / "AI" / "ComfyUI" / "user" / "default" / "workflows"
GENERATION_WORKFLOW = WORKFLOW_ROOT / "GENESIS_FLUX2_KLEIN_9B_KV_OFFICIAL_T2I.json"
REGULAR_9B_WORKFLOWS = (
    Path("/mnt/AI-Storage/ComfyUI/workflows/Flux.2 Klein 9b Text To Image.json"),
    WORKFLOW_ROOT / "Flux.2 Klein 9b Text To Image.json",
)
EDIT_WORKFLOW = PROJECT_ROOT / "genesis" / "reference" / "pose_workflows" / "FLUXUP_IMG2IMG_RX9060.json"
INPAINT_CHECKPOINT = "juggernautXL_ragnarokBy.safetensors"
REGULAR_9B_MODEL = "flux-2-klein-base-9b-Q4_K_M.gguf"
KV_9B_MODEL = "flux-2-klein-9b-kv-fp8.safetensors"
QWEN_MODEL = "Qwen-Rapid-AIO-NSFW-v19_Q4_K.gguf"
QWEN21_MODEL = "qwen_image_2.1_bf16.safetensors"
QWEN21_CLIP = "qwen3vl_8b_int8_convrot.safetensors"
QWEN21_VAE = "qwen_image_2.1_vae_bf16.safetensors"
FOUR_B_MODEL = "aisha_nsfw_beta_v1_4b_distilled_bf16.safetensors"
TEXT_ENCODER_4B = "qwen_3_4b.safetensors"
TEXT_ENCODER_9B = "qwen_3_8b_fp8mixed.safetensors"

# MARTY RunPod models verified from the live ComfyUI catalog.
REMOTE_PHR00T_MODEL = "Qwen-Rapid-AIO-NSFW-v23.safetensors"
REMOTE_PHR00T_V23_GGUF_MODEL = "Qwen-Rapid-NSFW-v23_Q8_0.gguf"
REMOTE_PHR00T_V23_Q2_MODEL = "Qwen-Rapid-NSFW-v23_Q2_K.gguf"
REMOTE_PHR00T_V23_MODELS = {REMOTE_PHR00T_MODEL}
REMOTE_PHR00T_V22_GGUF_MODEL = "Qwen-Rapid-NSFW-v22_Q8_0.gguf"
REMOTE_PHR00T_V23_CACHE_MODELS = {REMOTE_PHR00T_V23_GGUF_MODEL, REMOTE_PHR00T_V23_Q2_MODEL, REMOTE_PHR00T_V22_GGUF_MODEL}
REMOTE_PHR00T_V19_MODEL = "Qwen-Rapid-AIO-NSFW-v19.safetensors"
REMOTE_PHR00T_V19_GGUF_MODEL = "Qwen-Rapid-AIO-NSFW-v19_Q8_0.gguf"
REMOTE_PHR00T_MODELS = {REMOTE_PHR00T_V22_GGUF_MODEL, *REMOTE_PHR00T_V23_MODELS, REMOTE_PHR00T_V23_GGUF_MODEL, REMOTE_PHR00T_V23_Q2_MODEL, REMOTE_PHR00T_V19_MODEL, REMOTE_PHR00T_V19_GGUF_MODEL}
REMOTE_PHR00T_CLIP = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
REMOTE_PHR00T_GGUF_CLIP = "Qwen2.5-VL-7B-Instruct-Q8_0.gguf"
REMOTE_PHR00T_CLIP_CANDIDATES = (REMOTE_PHR00T_CLIP, REMOTE_PHR00T_GGUF_CLIP)
REMOTE_PHR00T_VAE = "qwen_image_vae.safetensors"
REMOTE_KLEIN_9B_MODEL = "flux-2-klein-9b.safetensors"
REMOTE_AISHA_9B_MODEL = "aisha_nsfw_beta_v9_7_distilled_fp8.safetensors"
REMOTE_AISHA_BF16_MODEL = "aisha_nsfw_beta_v9_7_distilled_bf16.safetensors"
REMOTE_MIRACLEIN_V2_MODEL = "miracleinNSFWGeneration_20FP8.safetensors"
REMOTE_PORNMASTER_9B_MODEL = "pornmasterFlux2Klein_v3-fp8.safetensors"
REMOTE_MIRACLEIN_9B_MODEL = "Miraclein NSFW v3.0 FP8 - Klein9B - 12steps,euler,cfg1.1.safetensors"
REMOTE_DONUTS_MODEL = "donutsdeliverymixV4_v41.safetensors"
REMOTE_BIGLUSTY_DONUT_MODEL = "biglustydonutmixNSFW_v12.safetensors"
REMOTE_EPICREALISM_MODEL = 'epicrealismXL_vxviLastfameRealism.safetensors'
REMOTE_REALISTIC_VISION_MODEL = 'Realistic_Vision_V6.0_NV_B1.safetensors'
REMOTE_SDXL_MODELS = {REMOTE_DONUTS_MODEL, REMOTE_BIGLUSTY_DONUT_MODEL, REMOTE_EPICREALISM_MODEL}
REMOTE_PONY_MODEL = 'ponyRealism_V23.safetensors'
REMOTE_SDXL_MODELS.add(REMOTE_PONY_MODEL)
REMOTE_MOP_MODEL = 'mopMixtureOfPerverts_instaV10DMD.safetensors'
REMOTE_SDXL_MODELS.add(REMOTE_MOP_MODEL)
REMOTE_SD15_MODELS = {REMOTE_REALISTIC_VISION_MODEL}
REMOTE_CHECKPOINT_MODELS = REMOTE_SDXL_MODELS | REMOTE_SD15_MODELS
REMOTE_DARKBEAST_9B_MODEL = "darkBeastMar0326Latest_dbkleinv2BFS.safetensors"
LOCAL_AISHA_9B_MODEL = "aisha-official-flux-2-klein-9b-base-nsfw-standard.safetensors"
LOCAL_MIRACLEIN_9B_MODEL = "Miraclein NSFW v3.0 FP8 - Klein9B - 12steps,euler,cfg1.1.safetensors"
LOCAL_PORNMASTER_9B_MODEL = "PornMaster v4.0 Turbo Q8_0 - Klein9B - cfg1,4steps,cfg1.5,8steps,edit cfg2,4steps.gguf"
LOCAL_DARKBEAST_9B_MODEL = REMOTE_DARKBEAST_9B_MODEL
LOCAL_PENDING_KLEIN_MODELS = {LOCAL_DARKBEAST_9B_MODEL, REGULAR_9B_MODEL, KV_9B_MODEL}
REMOTE_9B_CLIP = "qwen_3_8b.safetensors"
REMOTE_9B_CLIP_CANDIDATES = (REMOTE_9B_CLIP, "qwen_3_8b_fp8mixed.safetensors")
REMOTE_9B_VAE = "flux2-vae.safetensors"
REMOTE_KLEIN9B_SOURCE_MODELS = {
    REMOTE_KLEIN_9B_MODEL,
    REMOTE_AISHA_9B_MODEL,
    REMOTE_AISHA_BF16_MODEL,
    REMOTE_MIRACLEIN_V2_MODEL,
    REMOTE_PORNMASTER_9B_MODEL,
    REMOTE_MIRACLEIN_9B_MODEL,
    REMOTE_DARKBEAST_9B_MODEL,
    LOCAL_PORNMASTER_9B_MODEL,
}
KLEIN9B_REFERENCE_MODELS = REMOTE_KLEIN9B_SOURCE_MODELS | {REGULAR_9B_MODEL, LOCAL_AISHA_9B_MODEL}
REMOTE_SOURCE_MODELS = {*REMOTE_PHR00T_MODELS, *KLEIN9B_REFERENCE_MODELS}
REFINEMENT_MODELS = REMOTE_KLEIN9B_SOURCE_MODELS | REMOTE_CHECKPOINT_MODELS
SOURCE_EDIT_MODELS = {QWEN_MODEL, QWEN21_MODEL, FOUR_B_MODEL} | REMOTE_SOURCE_MODELS | REMOTE_CHECKPOINT_MODELS

SUPPORTED_CREATE_MODELS = {
    FOUR_B_MODEL, REGULAR_9B_MODEL, KV_9B_MODEL, QWEN_MODEL, QWEN21_MODEL, LOCAL_AISHA_9B_MODEL,
    *REMOTE_SOURCE_MODELS, *REMOTE_CHECKPOINT_MODELS,
}
# Installed files and a valid graph do not verify memory/kernel safety on the
# local 16 GB AMD GPU. Larger routes remain available on the selected RunPod.
# Qwen Image 2.1 local source-reference generation was completed at 512/768,
# but its 1024 Quality setting remains slow and is not a speed guarantee.
LOCAL_SAFE_CREATE_MODELS = {FOUR_B_MODEL, QWEN_MODEL, QWEN21_MODEL, REMOTE_PHR00T_V23_Q2_MODEL} | REMOTE_SDXL_MODELS
OUTPUT_DIR = Path.home() / "GENESIS-Exports"
REFERENCE_WORKFLOW_ROOT = PROJECT_ROOT / "genesis" / "reference" / "pose_workflows"
REMOTE_PHR00T_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "PHR00T_QWEN_RAPID_V23.json"
REMOTE_PHR00T_V19_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "PHR00T_QWEN_RAPID_V19_AIO.json"
REMOTE_KLEIN9B_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "KLEIN9B_REMOTE.json"
REMOTE_PORNMASTER_V4_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "GENESIS_PORNMASTER_9B_EDIT.json"
REMOTE_MIRACLEIN_EDIT_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "GENESIS_MIRACLEIN_9B_EDIT.json"
REMOTE_MIRACLEIN_T2I_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "GENESIS_MIRACLEIN_9B_T2I.json"
REMOTE_DARKBEAST_IDENTITY_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "GENESIS_DARKBEAST_9B_IDENTITY.json"
REMOTE_PORNMASTER_T2I_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "GENESIS_PORNMASTER_9B_T2I.json"
QWEN21_T2I_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "QWEN_IMAGE_2_1_T2I.json"
QWEN21_REFERENCE_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "QWEN_IMAGE_2_1_REFERENCE.json"
LOCAL_AISHA_9B_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "GENESIS_AISHA_9B_TEST.json"
REMOTE_KLEIN_REFERENCE_WORKFLOWS = {REMOTE_KLEIN9B_WORKFLOW, REMOTE_PORNMASTER_V4_WORKFLOW, REMOTE_MIRACLEIN_EDIT_WORKFLOW, REMOTE_DARKBEAST_IDENTITY_WORKFLOW}
STAGE_1_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "STAGE_1_PHR00T_POSE.json"
REMOTE_SDXL_T2I_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "GENESIS_SDXL_SHARED_T2I.json"
REMOTE_SDXL_POSE_CONTROLNET = "OpenPoseXL2.safetensors"
STAGE_3_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "STAGE_3_REACTOR_ROCM.json"
FOUR_B_SOURCE_WORKFLOW = WORKFLOW_ROOT / "FLUX2_Klein_Deepthroat_FaceSwap.json"
UPSCALE_WORKFLOW = REFERENCE_WORKFLOW_ROOT / "SD_UPSCALE_REFERENCE.json"
UPSCALE_REQUIRED_ASSETS = {
    "Realistic_Vision_V6.0_NV_B1.safetensors",
    "vae-ft-mse-840000-ema-pruned.safetensors",
    "4x-UltraSharp.safetensors",
}


def model_lora_limit(model_name: str) -> int:
    """Use the same stacking limit in profiles and generation validation."""
    return 3 if model_name in (REMOTE_KLEIN9B_SOURCE_MODELS | REMOTE_CHECKPOINT_MODELS | {REGULAR_9B_MODEL, FOUR_B_MODEL, QWEN21_MODEL}) else 0


def model_generation_settings(model_name: str, *, source=False, remote=False) -> dict:
    """Complete defaults for the graph actually selected by the generation route."""
    values = dict(defaultWidth=1024, defaultHeight=1024, defaultSteps=4,
                  defaultCfg=1.0, defaultDenoise=1.0, defaultSampler="euler",
                  defaultScheduler="simple", schedulerFixed=False, denoiseFixed=False)
    if model_name in ({QWEN_MODEL} | REMOTE_PHR00T_MODELS):
        values.update(defaultWidth=832, defaultHeight=1216, defaultSteps=6,
                      defaultSampler="er_sde", defaultScheduler="beta")
        if model_name in (REMOTE_PHR00T_V23_MODELS | REMOTE_PHR00T_V23_CACHE_MODELS):
            values.update(defaultWidth=2264, defaultHeight=1360, defaultSteps=4,
                          defaultCfg=1.2, defaultSampler="euler_ancestral")
    elif model_name == REGULAR_9B_MODEL:
        values.update(defaultSteps=50, defaultCfg=4.0)
    elif model_name == QWEN21_MODEL:
        # Publisher full-quality baseline; callers can lower steps for drafts.
        values.update(defaultSteps=40)
        if source and not remote:
            values.update(defaultWidth=768, defaultHeight=768)
    elif model_name == LOCAL_AISHA_9B_MODEL:
        values.update(defaultSteps=50, defaultCfg=4.0, defaultScheduler="Flux2Scheduler",
                      schedulerFixed=True, denoiseFixed=True)
    elif model_name in {FOUR_B_MODEL, KV_9B_MODEL}:
        if source and model_name == FOUR_B_MODEL:
            values.update(defaultSteps=8, defaultSampler="res_multistep")
        else:
            values.update(defaultScheduler="Flux2Scheduler", schedulerFixed=True, denoiseFixed=True)
    elif model_name in {REMOTE_KLEIN_9B_MODEL, REMOTE_AISHA_9B_MODEL, REMOTE_AISHA_BF16_MODEL}:
        # Klein 9B and both Aisha v9.7 files are distilled.  The saved
        # reference workflow uses five steps; T2I is a four-step route.
        values.update(defaultSteps=5 if source else 4, defaultCfg=1.0)
        if source:
            values.update(defaultScheduler="Flux2Scheduler", schedulerFixed=True,
                          denoiseFixed=True)
    elif model_name == REMOTE_DARKBEAST_9B_MODEL:
        # DarkBeast V2 BFS: its dedicated reference graph and model guidance
        # both specify five steps, CFG 1, not Miraclein's 12/1.1.
        values.update(defaultSteps=5, defaultCfg=1.0)
        if source:
            values.update(defaultScheduler="Flux2Scheduler", schedulerFixed=True,
                          denoiseFixed=True)
    elif model_name == REMOTE_PORNMASTER_9B_MODEL:
        # v3 FP8 is the 9B base fine-tune, not the separate v4 Turbo GGUF.
        # Without an explicitly selected Turbo adapter, use base sampling for
        # T2I.  Its existing reference graph is separately five-step/CFG 1;
        # do not silently substitute v4's edit settings for a v3 reference.
        values.update(defaultSteps=5 if source else 50,
                      defaultCfg=1.0 if source else 4.0)
        if source:
            values.update(defaultScheduler="Flux2Scheduler", schedulerFixed=True,
                          denoiseFixed=True)
    elif model_name in REMOTE_KLEIN9B_SOURCE_MODELS:
        if source:
            values.update(defaultSteps=5, defaultScheduler="Flux2Scheduler",
                          schedulerFixed=True, denoiseFixed=True)
            if remote:
                values.update(defaultWidth=1920, defaultHeight=1520)
            if model_name in {REMOTE_MIRACLEIN_9B_MODEL, REMOTE_MIRACLEIN_V2_MODEL}:
                values.update(defaultSteps=12, defaultCfg=1.1)
            elif model_name == LOCAL_PORNMASTER_9B_MODEL:
                values.update(defaultSteps=4, defaultCfg=2.0)
        else:
            # This route uses the saved Miraclein T2I graph, or PornMaster T2I.
            values.update(defaultSteps=12, defaultCfg=1.1)
            if model_name == LOCAL_PORNMASTER_9B_MODEL:
                values.update(defaultSteps=8, defaultCfg=1.5)
    elif model_name in REMOTE_CHECKPOINT_MODELS:
        values.update(defaultSteps=25, defaultCfg=4.0,
                      defaultSampler="dpmpp_sde" if model_name == REMOTE_DONUTS_MODEL else "dpmpp_3m_sde",
                      defaultScheduler="karras", defaultDenoise=0.65 if source else 1.0)
    if model_name == REMOTE_PONY_MODEL:
        values.update(defaultSteps=25, defaultCfg=6.0, defaultSampler='dpmpp_2m', defaultScheduler='karras')
    if model_name == REMOTE_MOP_MODEL:
        values.update(defaultSteps=10, defaultCfg=1.0, defaultSampler='lcm',
                      defaultScheduler='ddim_uniform')
    if model_name in REMOTE_SD15_MODELS:
        values.update(defaultWidth=512, defaultHeight=512, defaultSteps=25,
                      defaultCfg=7.0, defaultSampler='dpmpp_2m', defaultScheduler='karras',
                      defaultDenoise=0.65 if source else 1.0)
    if source and model_name == REGULAR_9B_MODEL:
        values.update(defaultScheduler="Flux2Scheduler", schedulerFixed=True, denoiseFixed=True)
    return values



def quality_sizes(defaults: dict) -> dict:
    """Model-native aspect ratio: Quality never shrinks the model baseline."""
    w,h = int(defaults["defaultWidth"]),int(defaults["defaultHeight"])
    def scaled(factor):
        if factor == 1.0:
            return {"width":w,"height":h}
        return {"width":max(256,int(round(w*factor/64))*64),
                "height":max(256,int(round(h*factor/64))*64)}
    return {"Fast":scaled(0.60),"Balanced":scaled(0.80),"Quality":scaled(1.0)}


def model_profile_settings(model_name: str, *, remote=False) -> dict:
    create = model_generation_settings(model_name, remote=remote)
    source = model_generation_settings(model_name, source=True, remote=remote)
    result = {**(source if remote and model_name in REMOTE_SOURCE_MODELS else create),
              "createDefaults": create, "sourceDefaults": source}
    result["faceidSupported"] = model_name in REMOTE_SDXL_MODELS
    family = model_family(model_name)
    if family == "qwen_image":
        result["identityGuidance"] = "Phr00t: source = image1 identity; pose = image2. v19 favors consistency; v23 is the instruction alternative. Use 4–8 steps with the saved sampler/CFG defaults. Lower denoise on its empty-latent edit graph does not lock the source face."
    elif family == "sdxl":
        result["identityGuidance"] = ("SDXL: with a source only, FaceID starts at denoise 0.55 (0.45–0.60 for source editing). With a separate OpenPose skeleton, FaceID uses the original source (Person A only) for facial guidance and generates the new pose at denoise 1.0. Text-only presets cannot enforce exact pose geometry: select a skeleton too. FaceID is global and cannot guarantee Person A is the only influenced face; manual Person A-only ReActor is available."
                                      + (" Mixture of Perverts DMD: start with no additional appearance LoRAs, then try one at 0.35 and compare the face; 10 steps, CFG 1, LCM/ddim_uniform are the current tested baseline." if model_name == REMOTE_MOP_MODEL else ""))
    elif family.startswith("flux2_klein") or family == "aisha_9b":
        result["identityGuidance"] = "Klein: keep the original identity source separate from pose control. RefControl on compatible 9B models uses pose image1, identity image2; start at 0.9 strength. Keep model sampler/CFG defaults. More steps or CFG do not guarantee facial identity; Stage 3 uses the original source."
    else:
        result["identityGuidance"] = "Keep model defaults initially. Steps and CFG do not guarantee facial identity."
    result["qualityPresets"] = quality_sizes(source if remote and model_name in REMOTE_SOURCE_MODELS else create)
    result["sourceQualityPresets"] = quality_sizes(source)
    result["createQualityPresets"] = quality_sizes(create)
    result["qualityNote"] = "Fast/Balanced reduce sampling size, and on applicable models the step count. Quality restores the selected model's full baseline. 2K/4K is applied after native sampling. CFG, scheduler and denoise stay model-specific; seed, prompt and source image are preserved."
    # Do not apply non-distilled step reductions to four/five-step models.
    # Each route (text or source/edit) starts from its own workflow baseline.
    def tune_steps(presets, defaults, *, editing=False):
        baseline = int(defaults["defaultSteps"])
        if model_name in {REGULAR_9B_MODEL, LOCAL_AISHA_9B_MODEL, REMOTE_PORNMASTER_9B_MODEL}:
            if baseline >= 40:
                presets["Fast"].update(steps=24)
                presets["Balanced"].update(steps=36)
                presets["Quality"].update(steps=baseline)
        elif model_name == QWEN21_MODEL and baseline >= 40:
            presets["Fast"].update(steps=20)
            presets["Balanced"].update(steps=30)
            presets["Quality"].update(steps=baseline)
        elif model_name == REMOTE_MOP_MODEL:
            presets["Fast"].update(steps=6)
            presets["Balanced"].update(steps=8)
            presets["Quality"].update(steps=baseline)
        elif model_name in REMOTE_CHECKPOINT_MODELS:
            presets["Fast"].update(steps=12)
            presets["Balanced"].update(steps=18)
            presets["Quality"].update(steps=baseline)
        elif model_name == LOCAL_PORNMASTER_9B_MODEL and not editing:
            # Only the explicitly turbo-distilled v4 benefits from this 4/8
            # division; do not reuse for the v3 base checkpoint.
            presets["Fast"].update(steps=4, cfg=1.0)
            presets["Balanced"].update(steps=8, cfg=1.5)
            presets["Quality"].update(steps=baseline, cfg=1.5)

    tune_steps(result["createQualityPresets"], create)
    tune_steps(result["sourceQualityPresets"], source, editing=True)
    result["qualityPresets"] = (result["sourceQualityPresets"]
                                 if remote and model_name in REMOTE_SOURCE_MODELS
                                 else result["createQualityPresets"])
    if model_name in ({QWEN_MODEL} | REMOTE_PHR00T_MODELS):
        for presets in (result["qualityPresets"], result["sourceQualityPresets"], result["createQualityPresets"]):
            # CFG 1.0 skips the unconditional pass in ComfyUI.  Phr00t is
            # distilled; retain its recommended sampler/scheduler/denoise.
            presets["Fast"].update(cfg=1.0, steps=4)
            if model_name in (REMOTE_PHR00T_V23_MODELS | REMOTE_PHR00T_V23_CACHE_MODELS):
                # v22/v23 Quality stays at its original 2264x1360. Use a
                # smaller native inference size for everyday previews instead.
                presets["Fast"].update(width=1024, height=640)
                presets["Balanced"].update(width=1344, height=832, cfg=1.0, steps=4)
                presets["Quality"].update(cfg=source["defaultCfg"], steps=source["defaultSteps"])
        if model_name in (REMOTE_PHR00T_V23_MODELS | REMOTE_PHR00T_V23_CACHE_MODELS):
            result["qualityNote"] = "Phr00t Fast 1024x640 and Balanced 1344x832 use 4 steps/CFG 1.0 (one sampling pass). Quality keeps native 2264x1360 with the model's saved CFG 1.2. Smaller previews may lose fine detail; original image and pose references are unchanged."
            if model_name == REMOTE_PHR00T_V23_Q2_MODEL and not remote:
                # The 16GB local AMD GPU is VRAM-limited at 3MP. Prefer a
                # balanced start without silently reducing Quality itself.
                result["preferredPreset"] = "Balanced"
        else:
            result["qualityNote"] = "Phr00t v19 Fast uses 4 steps/CFG 1.0; Balanced and Quality retain the verified 6-step consistency baseline. Lower preview resolutions trade off detail for speed."
            if model_name == QWEN_MODEL and not remote:
                # v19 Q4 is a 12.43 GiB weight file on a 16 GiB AMD GPU.
                # Cold loading is expensive and native VAE decoding may fall
                # back to tiles. Prefer tested Fast for local previews while
                # keeping 6-step Balanced/Quality available for consistency.
                result["preferredPreset"] = "Fast"
                result["qualityNote"] += " Local v19 Q4 starts on Fast. When supported, GENESIS uses tiled VAE decoding to avoid full-size VAE memory failures. Balanced/Quality retain six steps."
    if model_name == LOCAL_MIRACLEIN_9B_MODEL and not remote:
        for presets in (result["qualityPresets"], result["sourceQualityPresets"], result["createQualityPresets"]):
            presets["Fast"]["cfg"] = 1.0
        result["sourceQualityPresets"]["Fast"]["referenceMegapixels"] = (640 / 1024) ** 2
        result["qualityNote"] = "Fast uses CFG 1.0 and, with a source image, about 640×640 of reference detail. Balanced/Quality restore CFG 1.1 and full reference detail. Smaller references speed up previews but may lose facial detail."
    if model_name == QWEN21_MODEL and not remote:
        result["qualityNote"] += " With a source or pose, the smaller selected dimension controls reference detail; output keeps the first reference image's proportions. Balanced/768 is verified locally; Quality/1024 did not finish within an eight-minute test."
    if remote and model_name in {REMOTE_MIRACLEIN_9B_MODEL, REMOTE_MIRACLEIN_V2_MODEL}:
        result["qualityNote"] += " Miraclein source/edit uses its own 12-step CFG 1.1 profile; Quality preserves its larger 1920×1520 RunPod source default."
    return result


def load_curated_pose_presets(pose_rows: list[dict] | None = None) -> list[dict]:
    """Load authored text presets and verified pose+JSON-prompt pairs."""
    presets: list[dict] = []
    # Curated declarations must match an indexed, installed skeleton at its
    # exact relative path, never a filename or category guess. Imported private
    # packs may live in either legacy Pose Maker root instead of this checkout.
    library_roots = tuple(path.resolve() for path in (
        PROJECT_ROOT / "genesis/reference/assets/pose_library",
        Path.home() / "AI/GENESIS_POSE_MAKER/assets/pose_library",
        Path.home() / "Downloads/GENESIS_POSE_MAKER_V15_USER_IMAGE_SLOTS(1)/GENESIS_POSE_MAKER/assets/pose_library",
    ))
    indexed_skeletons = {}
    for pose in pose_rows or ():
        local_file = QUrl(str(pose.get("source", ""))).toLocalFile()
        if local_file and Path(local_file).is_file():
            indexed_skeletons[Path(local_file).resolve()] = pose
    full_path = PROJECT_ROOT / "genesis/reference/prompt_maps/pose_presets_full.json"
    try:
        payload = json.loads(full_path.read_text(encoding="utf-8"))
        for category, rows in payload.get("categories", {}).items():
            for position, row in enumerate(rows):
                if not isinstance(row, dict) or not row.get("prompt"):
                    continue
                presets.append({
                    "sourceMetadata": source_metadata(row),
                    "id": "full70:" + str(row.get("id", "")),
                    "label": str(row.get("name", "Preset")),
                    "prompt": normalize_identity_instruction(str(row["prompt"])),
                    "priority": len(presets) + 1,
                    "collection": "Full 70 · select skeleton",
                    "category": str(category),
                    # This is a category recommendation, never a claimed
                    # skeleton match. A real image must be explicitly selected.
                    "poseHintCategory": {
                        "Oral_BJ": "Kneeling",
                        "Missionary": "Lying",
                        "Doggy": "All Fours",
                        "Cowgirl": "Squatting",
                        "Seated_Chair": "Sitting",
                        "Standing": "Standing",
                        "Spooning_Side": "Lying",
                    }.get(str(category), "All"),
                    "requiresPoseSelection": True,
                })
    except (OSError, ValueError, TypeError):
        pass

    candidates = (
        Path.home() / "GENESIS_CURATED_PRESETS_DATABASE.json",
        Path.home() / "AI/GENESIS_POSE_MAKER/GENESIS_CURATED_PRESETS_DATABASE.json",
    )
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows = payload.get("sexual_act_presets", [])
            curated = []
            for row in rows:
                if not isinstance(row, dict) or not row.get("prompt"):
                    continue
                declared = row.get("skeletons", [])
                if not isinstance(declared, list):
                    declared = []
                bound = None
                for relative_path in declared:
                    if not isinstance(relative_path, str) or Path(relative_path).is_absolute():
                        continue
                    for library_root in library_roots:
                        skeleton_path = (library_root / relative_path).resolve()
                        if skeleton_path.is_relative_to(library_root) and skeleton_path in indexed_skeletons:
                            bound = indexed_skeletons[skeleton_path]
                            break
                    if bound is not None:
                        break
                preset = {
                    "sourceMetadata": source_metadata(row),
                    "id": "curated18:" + str(row.get("id", "")),
                    "name": str(row.get("name", "Preset")),
                    "label": str(row.get("name", "Preset")) + " · Curated 18",
                    "prompt": normalize_identity_instruction(str(row.get("prompt", ""))),
                    "priority": 70 + int(row.get("priority", 9999)),
                    "collection": "Curated 18",
                    "category": "Curated",
                    "skeletons": declared,
                    "requiresPoseSelection": bound is None,
                }
                if bound:
                    preset.update({
                        "source": bound["source"],
                        "thumbnail": bound.get("thumbnail") or bound["source"],
                        "poseId": bound.get("poseId", ""),
                        "poseHintCategory": bound.get("category", "All"),
                    })
                curated.append(preset)
            presets.extend(sorted(curated, key=lambda row: (row["priority"], row["label"])))
            break
        except (OSError, ValueError, TypeError):
            continue

    # Every added "Linked Pose" preset has a one-to-one indexed skeleton
    # and authored JSON prompt. No filename guessing or synthetic matching.
    # The original Klein prompt map stays untouched; these entries use the
    # model-aware generation pipeline and pose images as separate inputs.
    for pose in pose_rows or ():
        if not (pose.get("promptMapped") and pose.get("source") and pose.get("prompt")):
            continue
        source = QUrl(str(pose["source"])).toLocalFile()
        if not source or not Path(source).is_file():
            continue
        presets.append({
            **pose,
            "id": "mapped:" + str(pose.get("poseId", "")),
            "label": str(pose.get("name") or pose.get("poseId") or "Mapped Pose"),
            "collection": "Linked Pose + JSON Prompt",
            "category": str(pose.get("category", "Pose")),
            "requiresPoseSelection": False,
            "priority": 1000 + len(presets),
        })
    return presets


def upscale_assets_available() -> bool:
    found: set[str] = set()
    for root in MODEL_ROOTS:
        if not root.is_dir():
            continue
        try:
            found.update(path.name for path in root.rglob("*") if path.is_file())
        except OSError:
            continue
    return UPSCALE_WORKFLOW.is_file() and UPSCALE_REQUIRED_ASSETS <= found



def local_output_upscale_assets_available() -> bool:
    return any(path.is_file() and path.name in {"4x-UltraSharp.safetensors", "4x-UltraSharp.pth"}
               for root in MODEL_ROOTS if (root / "upscale_models").is_dir()
               for path in (root / "upscale_models").rglob("*"))


def upscale_catalog_readiness(info: dict) -> tuple[bool, bool]:
    choices = _remote_choice_values(info, ("UpscaleModelLoader",), "model_name")
    output_ready = bool(set(choices) & {"4x-UltraSharp.safetensors", "4x-UltraSharp.pth"}) and all(
        node in info for node in ("LoadImage", "UpscaleModelLoader", "ImageUpscaleWithModel", "ImageScale", "SaveImage"))
    try:
        validate_remote_workflow_assets(UPSCALE_WORKFLOW, info)
        legacy_ready = True
    except (ValueError, OSError, workflow_lab.ComfyError):
        legacy_ready = False
    return legacy_ready, output_ready


def verified_lora_trigger_words(name: str, metadata: dict[str, list[str]]) -> list[str]:
    """Prefer explicit activation metadata; fall back to an approved exact-file trigger.

    Most LoRA files only contain training tag frequencies, which are not
    reliable trigger phrases. Preserve the known compatibility map for both
    local and remote catalogs rather than hiding it when metadata is empty.
    """
    explicit = metadata.get(name) or []
    if explicit:
        return list(dict.fromkeys(explicit))[:12]
    phrase = lora_trigger(name)
    return [phrase] if phrase else []


def build_generation_profiles(
    report: dict,
    installed_loras: list[str],
    lora_triggers: dict[str, list[str]] | None = None,
) -> list[dict]:
    """Convert filesystem readiness evidence into QML-safe model choices."""
    lora_triggers = lora_triggers or {}
    upscale_ready = upscale_assets_available()
    output_upscale_ready = local_output_upscale_assets_available()
    profiles = []
    for profile in report.get("profiles", []):
        evidence = profile.get("evidence") or {}
        model_path = evidence.get("MODEL")
        if model_path is None:
            continue
        model_name = Path(model_path).name
        compatible = compatible_loras(model_name, installed_loras)
        ready = bool(profile.get("ready"))
        runnable = ready and model_name in LOCAL_SAFE_CREATE_MODELS
        note = compatibility_note(model_name)
        if ready and not runnable:
            if model_name in SUPPORTED_CREATE_MODELS:
                note = "Installed · editable workflow available · AMD/KFD render pending"
            else:
                note += " · Create workflow not yet validated"
        row = {
            "label": ("Aisha NSFW Beta v1 · FLUX.2 Klein 4B" if model_name == FOUR_B_MODEL
                      else str(profile.get("name") or model_name)),
            "model": model_name,
            "note": note,
            "modelPath": str(model_path),
            "workflowPath": str(evidence.get("WORKFLOW") or ""),
            "loras": ["None", *compatible],
            "triggers": {name: verified_lora_trigger_words(name, lora_triggers)
                         for name in compatible},
            "loraHelp": {name: lora_help(name) for name in compatible},
            "ready": ready,
            "upscaleReady": upscale_ready,
            "outputUpscaleReady": output_upscale_ready,
            "runnable": runnable,
            "stageOneEligible": model_name in SUPPORTED_CREATE_MODELS,
            "sourceSupported": model_name in SOURCE_EDIT_MODELS,
            "stageTwoEligible": model_name in REFINEMENT_MODELS,
            # Phr00t's Qwen edit encoder accepts zero, one, or more references.
            # Missing images select genuine text-to-image, not a placeholder.
            "sourceRequired": False,
            "maxLoras": model_lora_limit(model_name) if compatible else 0,
            "experimentalLoras": model_name in {REGULAR_9B_MODEL, FOUR_B_MODEL},
        }
        if model_name in REMOTE_SDXL_MODELS:
            # Explicit local evidence must override the configured remote fallback.
            # Submission revalidates the active ComfyUI catalog before uploading.
            row["poseReady"] = ready and any(
                (root / "controlnet" / REMOTE_SDXL_POSE_CONTROLNET).is_file()
                for root in MODEL_ROOTS
            )
            row["poseMethod"] = "SDXL OpenPoseXL2 ControlNet"
        row.update(model_profile_settings(model_name))
        profiles.append(row)
    priority = {FOUR_B_MODEL: 0, QWEN21_MODEL: 1, REGULAR_9B_MODEL: 2, KV_9B_MODEL: 3, QWEN_MODEL: 4}
    profiles.sort(key=lambda item: (priority.get(item["model"], 99), item["label"].casefold()))
    return profiles


def lora_trigger_words(path: Path) -> list[str]:
    """Extract explicit activation terms without loading LoRA tensor data."""
    try:
        with path.open("rb") as handle:
            header_size = struct.unpack("<Q", handle.read(8))[0]
            if header_size > 16 * 1024 * 1024:
                return []
            metadata = json.loads(handle.read(header_size)).get("__metadata__", {})
    except (OSError, ValueError, json.JSONDecodeError, struct.error):
        return []

    words: list[str] = []
    for key in ("modelspec.trigger_phrase", "trigger_words", "activation text"):
        value = metadata.get(key)
        if isinstance(value, str):
            words.extend(part.strip() for part in value.split(",") if part.strip())
    # ss_tag_frequency contains training captions, *not* verified activation
    # phrases. Do not label broad tags like "portrait", "all" or "misc" as
    # required LoRA triggers in the UI.
    return list(dict.fromkeys(words))[:12]



def load_grok_preset_items() -> list[dict]:
    p = PROJECT_ROOT / "genesis/reference/prompt_maps/pose_presets_full.json"
    if not p.is_file():
        return []
    try:
        d = __import__("json").loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    out = [{"label": "Grok preset…", "prompt": ""}]
    for cat, rows in d.get("categories", {}).items():
        for row in rows or []:
            if row.get("prompt"):
                out.append({
                    "label": f"{cat.replace('_', '/')} · {row.get('name', row.get('id', 'Preset'))}",
                    "prompt": row["prompt"],
                })
    return out

def _remote_choice_values(info: dict, node_types: tuple[str, ...], input_name: str) -> list[str]:
    values: set[str] = set()
    for node_type in node_types:
        spec = (info.get(node_type, {}).get("input", {}).get("required", {}) or {}).get(input_name)
        values.update(str(value) for value in workflow_lab._choice_values(spec) if value and not any(part.startswith(".") or "partial" in part.lower() for part in Path(str(value)).parts))
    return sorted(values, key=str.casefold)


def configured_stage_one_profiles() -> list[dict]:
    """Keep every configured Stage-1 model visible without claiming it is installed.

    The live /object_info catalog remains the source of truth for readiness.  These
    rows only prevent older GENESIS Stage-1 routes from disappearing from the UI
    when a RunPod cache/model is not mounted in the current session.
    """
    names = [
        REMOTE_PHR00T_MODEL,
        REMOTE_PHR00T_V23_GGUF_MODEL,
        REMOTE_PHR00T_V23_Q2_MODEL,
        REMOTE_PHR00T_V22_GGUF_MODEL,
        REMOTE_PHR00T_V19_MODEL,
        REMOTE_PHR00T_V19_GGUF_MODEL,
        REMOTE_AISHA_9B_MODEL,
        REMOTE_AISHA_BF16_MODEL,
        REMOTE_MIRACLEIN_V2_MODEL,
        REMOTE_MIRACLEIN_9B_MODEL,
        REMOTE_PORNMASTER_9B_MODEL,
        LOCAL_PORNMASTER_9B_MODEL,
        REMOTE_DARKBEAST_9B_MODEL,
        REMOTE_KLEIN_9B_MODEL,
        FOUR_B_MODEL,
        REGULAR_9B_MODEL,
        KV_9B_MODEL,
        QWEN_MODEL,
        QWEN21_MODEL,
        LOCAL_AISHA_9B_MODEL,
        REMOTE_DONUTS_MODEL,
        REMOTE_BIGLUSTY_DONUT_MODEL, REMOTE_EPICREALISM_MODEL, REMOTE_REALISTIC_VISION_MODEL, REMOTE_MOP_MODEL, REMOTE_PONY_MODEL,
    ]
    rows = build_remote_generation_profiles({
        "UNETLoader": {"input": {"required": {"unet_name": [names]}}},
        "UnetLoaderGGUF": {"input": {"required": {"unet_name": [names]}}},
    })
    for row in rows:
        row.update(
            ready=False,
            runnable=False,
            routeReady=False,
            stageOneConfigured=True,
            stageOneEligible=True,
            stageTwoConfigured=row.get("model") in REMOTE_KLEIN9B_SOURCE_MODELS,
            configured=True,
            note="Not active in current backend catalog · configured Stage-1 profile.",
        )
    return rows


def remote_reference_workflow(model_name: str) -> Path:
    if model_name in REMOTE_PHR00T_V23_MODELS:
        return REMOTE_PHR00T_WORKFLOW
    if model_name in REMOTE_PHR00T_V23_CACHE_MODELS:
        # Both quantizations use the shared-volume GGUF loader and Qwen encoder.
        # The live catalog validates exact filenames before any submission.
        return STAGE_1_WORKFLOW
    if model_name == REMOTE_PHR00T_V19_MODEL:
        return REMOTE_PHR00T_V19_WORKFLOW
    if model_name in {REMOTE_PHR00T_V19_GGUF_MODEL, QWEN_MODEL}:
        return STAGE_1_WORKFLOW
    if model_name == LOCAL_PORNMASTER_9B_MODEL:
        return REMOTE_PORNMASTER_V4_WORKFLOW
    if model_name == REMOTE_MIRACLEIN_9B_MODEL:
        return REMOTE_MIRACLEIN_EDIT_WORKFLOW
    if model_name == REMOTE_DARKBEAST_9B_MODEL:
        return REMOTE_DARKBEAST_IDENTITY_WORKFLOW
    if model_name in REMOTE_CHECKPOINT_MODELS:
        return REMOTE_SDXL_T2I_WORKFLOW
    if model_name in KLEIN9B_REFERENCE_MODELS:
        return REMOTE_KLEIN9B_WORKFLOW
    raise workflow_lab.ComfyError(f"No mapped reference workflow for {model_name}.")


def remote_reference_controls(model_name: str) -> dict:
    values = model_generation_settings(model_name, source=True, remote=True)
    return {key: values["default" + key[0].upper() + key[1:]]
            for key in ("steps", "cfg", "denoise", "sampler", "scheduler")}


def build_remote_generation_profiles(info: dict) -> list[dict]:
    """Build GENESIS model rows from a live remote ComfyUI /object_info catalog."""
    checkpoints = _remote_choice_values(info, ("CheckpointLoaderSimple",), "ckpt_name")
    diffusion = _remote_choice_values(info, ("UNETLoader", "UnetLoaderGGUF"), "unet_name")
    loras = _remote_choice_values(
        info, ("LoraLoader", "LoraLoaderModelOnly", "LoraLoaderBypass"), "lora_name"
    )
    pose_models = _remote_choice_values(info, ("ControlNetLoader",), "control_net_name")
    upscale_ready, output_upscale_ready = upscale_catalog_readiness(info)
    models = list(dict.fromkeys(Path(name).name for name in [*checkpoints, *diffusion]))
    labels = {
        REMOTE_PHR00T_MODEL: "RunPod · Phr00t v23 · Prompt",
        REMOTE_PHR00T_V23_GGUF_MODEL: "RunPod · Phr00t v23 Q8",
        REMOTE_PHR00T_V23_Q2_MODEL: "RunPod · Phr00t v23 Q2",
        REMOTE_PHR00T_V22_GGUF_MODEL: "RunPod · Phr00t v22 Q8",
        REMOTE_PHR00T_V19_MODEL: "Phr00t v19 · Consistency",
        REMOTE_PHR00T_V19_GGUF_MODEL: "RunPod · Phr00t v19 Q8",
        REMOTE_AISHA_BF16_MODEL: "RunPod · Aisha 9B v9.7 BF16",
        REMOTE_MIRACLEIN_V2_MODEL: "RunPod · Miraclein 9B v2 FP8",
        REMOTE_KLEIN_9B_MODEL: "RunPod · FLUX.2 Klein 9B",
        REMOTE_AISHA_9B_MODEL: "RunPod · Aisha 9B v9.7",
        REMOTE_PORNMASTER_9B_MODEL: "RunPod · PornMaster FLUX.2 Klein v3 FP8",
        LOCAL_PORNMASTER_9B_MODEL: "RunPod · PornMaster FLUX.2 Klein v4 Q8",
        REMOTE_MIRACLEIN_9B_MODEL: "RunPod · Miraclein FLUX.2 Klein v3 FP8",
        REMOTE_DARKBEAST_9B_MODEL: "RunPod · DarkBeast FLUX.2 Klein",
        LOCAL_AISHA_9B_MODEL: "RunPod · Aisha 9B Base",
        QWEN_MODEL: "RunPod · Phr00t v19 Q4",
        QWEN21_MODEL: "RunPod · Qwen Image 2.1 BF16",
        FOUR_B_MODEL: "RunPod · Aisha NSFW Beta v1 · FLUX.2 Klein 4B",
        REGULAR_9B_MODEL: "RunPod · FLUX.2 Klein 9B Base",
        KV_9B_MODEL: "RunPod · FLUX.2 Klein 9B-KV FP8",
        REMOTE_DONUTS_MODEL: "RunPod · DonutsDeliveryMix V4.1 · SDXL",
        REMOTE_BIGLUSTY_DONUT_MODEL: "RunPod · BigLustyDonutMix v1.2 · SDXL",
        REMOTE_EPICREALISM_MODEL: "RunPod · EpicRealism XL XVI",
        REMOTE_REALISTIC_VISION_MODEL: "RunPod · Realistic Vision 6 · SD 1.5",
        REMOTE_MOP_MODEL: "RunPod · Mixture of Perverts Insta 1.0 DMD",
        REMOTE_PONY_MODEL: "RunPod · Pony Realism v2.3",
    }
    rows: list[dict] = []
    for model_name in models:
        # WAN is offered by the dedicated video workflow, not the still-image picker.
        if model_name in {"wan2.2_ti2v_5B_fp16.safetensors", "wan2.1_i2v_480p_14B_fp8_e4m3fn.safetensors"}:
            continue
        compatible = compatible_loras(model_name, loras)
        runnable = model_name in SUPPORTED_CREATE_MODELS
        route_error = ""
        if runnable:
            try:
                # Picker readiness comes from the live model inventory.  Do not
                # reject an installed model merely because a cached /object_info
                # snapshot omitted unrelated node schemas; full workflow assets
                # are validated again immediately before submission.
                if model_name in REMOTE_SOURCE_MODELS or model_name == QWEN_MODEL:
                    workflow = remote_reference_workflow(model_name)
                    if not workflow.is_file():
                        raise workflow_lab.ComfyError(f"Workflow file missing: {workflow.name}")
                elif model_name == QWEN21_MODEL and not QWEN21_T2I_WORKFLOW.is_file():
                    raise workflow_lab.ComfyError(f"Workflow file missing: {QWEN21_T2I_WORKFLOW.name}")
                elif model_name in REMOTE_CHECKPOINT_MODELS and not REMOTE_SDXL_T2I_WORKFLOW.is_file():
                    raise workflow_lab.ComfyError(f"Workflow file missing: {REMOTE_SDXL_T2I_WORKFLOW.name}")
            except (workflow_lab.ComfyError, OSError, KeyError, ValueError) as exc:
                runnable = False
                route_error = str(exc)
        row = {
            "label": labels.get(model_name, "RunPod · " + model_name),
            "model": model_name,
            "modelPath": "RunPod catalog · " + model_name,
            "workflowPath": str((remote_reference_workflow(model_name) if model_name in REMOTE_SOURCE_MODELS or model_name == QWEN_MODEL else (QWEN21_T2I_WORKFLOW if model_name == QWEN21_MODEL else (REMOTE_SDXL_T2I_WORKFLOW if model_name in REMOTE_CHECKPOINT_MODELS else "")))),
            "note": ((compatibility_note(model_name) + ((" · SDXL OpenPose ready" if REMOTE_SDXL_POSE_CONTROLNET in pose_models else " · SDXL OpenPose asset missing") if model_name in REMOTE_SDXL_MODELS else ""))
                     if runnable and model_name in REMOTE_CHECKPOINT_MODELS else
                     (compatibility_note(model_name) if runnable else (route_error or "Remote model detected · workflow mapping pending"))),
            "loras": ["None", *compatible],
            "triggers": {
                name: ([lora_trigger(name)] if lora_trigger(name) else [])
                for name in compatible
            },
            "loraHelp": {name: lora_help(name) for name in compatible},
            "ready": True,
            "runnable": runnable,
            "stageOneEligible": model_name in SUPPORTED_CREATE_MODELS,
            "sourceSupported": model_name in SOURCE_EDIT_MODELS,
            "sourceRequired": False,
            "stageTwoConfigured": model_name in REMOTE_KLEIN9B_SOURCE_MODELS,
            "stageTwoEligible": model_name in REFINEMENT_MODELS and runnable,
            "maxLoras": model_lora_limit(model_name) if compatible else 0,
            "experimentalLoras": model_name in {REMOTE_KLEIN_9B_MODEL, REGULAR_9B_MODEL, FOUR_B_MODEL},
            # Distinguish native OpenPose ControlNet from Qwen image-2 pose
            # conditioning. Both routes exist; only SDXL has live-tested
            # reliable skeleton geometry at present.
            "poseReady": (model_name in REMOTE_SDXL_MODELS and REMOTE_SDXL_POSE_CONTROLNET in pose_models)
                         or (runnable and model_name in ({QWEN_MODEL, QWEN21_MODEL, FOUR_B_MODEL} | REMOTE_PHR00T_MODELS | KLEIN9B_REFERENCE_MODELS)),
            "poseMethod": ("SDXL OpenPoseXL2 ControlNet" if model_name in REMOTE_SDXL_MODELS else
                           "Image-2 pose reference · skeleton accuracy experimental" if model_name in ({QWEN_MODEL,QWEN21_MODEL} | REMOTE_PHR00T_MODELS) else
                           "Klein image reference · requires a compatible workflow; not OpenPose ControlNet" if model_name in KLEIN9B_REFERENCE_MODELS else
                           "Klein 4B image reference · source image required" if model_name == FOUR_B_MODEL else
                           "Not verified"),
            "remote": True,
            "upscaleReady": upscale_ready,
            "outputUpscaleReady": output_upscale_ready,
        }
        row.update(model_profile_settings(model_name, remote=True))
        if runnable and row["poseMethod"].startswith("Image-2"):
            row["note"] += " · Pose via image2 reference, NOT OpenPoseXL2. Bare skeleton adherence is weaker than a photographed pose in live v19 testing."
        rows.append(row)
    priority = {
        REMOTE_PHR00T_MODEL: 0, REMOTE_PHR00T_V19_MODEL: 1,
        REMOTE_KLEIN_9B_MODEL: 2, REMOTE_AISHA_9B_MODEL: 3,
        FOUR_B_MODEL: 5, REGULAR_9B_MODEL: 6, KV_9B_MODEL: 7,
    }
    rows.sort(key=lambda item: (priority.get(item["model"], 99), item["label"].casefold()))
    return rows


def remote_catalog_path(url: str) -> Path:
    endpoint_key = hashlib.sha256(url.rstrip("/").encode()).hexdigest()[:16]
    return Path.home() / ".cache" / "genesis" / f"runpod-{endpoint_key}-object-info.json"


def read_remote_catalog(url: str, max_age: float = 300) -> dict | None:
    path = remote_catalog_path(url)
    try:
        if time.time() - path.stat().st_mtime > max_age:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) and data else None
    except (OSError, json.JSONDecodeError):
        return None


def load_remote_catalog(client, *, refresh: bool = False) -> dict:
    info = None if refresh else read_remote_catalog(client.base_url)
    if info is None:
        info = client.object_info()
        if not info:
            raise workflow_lab.ComfyError("RunPod returned an empty node catalog.")
        path = remote_catalog_path(client.base_url)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + f".{time.time_ns()}.tmp")
            temporary.write_text(json.dumps(info), encoding="utf-8")
            temporary.replace(path)
        except OSError:
            pass  # A cache write must not block an otherwise working backend.
    return info


def _reconcile_remote_klein_clip(prompt: dict, info: dict) -> None:
    """Use whichever verified Qwen 3 8B encoder the connected catalog exposes."""
    clip_spec = (
        info.get("CLIPLoader", {})
        .get("input", {}).get("required", {}).get("clip_name", [[], {}])
    )
    available = set(clip_spec[0]) if clip_spec and isinstance(clip_spec[0], list) else set()
    if not available:
        return
    selected = next((name for name in REMOTE_9B_CLIP_CANDIDATES if name in available), None)
    if not selected:
        return
    for node in prompt.values():
        if node.get("class_type") == "CLIPLoader" and "clip_name" in node.get("inputs", {}):
            if node["inputs"]["clip_name"] in REMOTE_9B_CLIP_CANDIDATES:
                node["inputs"]["clip_name"] = selected


def remote_workflow_prompt(workflow: Path, info: dict) -> dict:
    prompt = workflow_lab.workflow_to_prompt(workflow, info)
    if workflow == REMOTE_PHR00T_WORKFLOW:
        available = _remote_choice_values(info, ("CLIPLoader",), "clip_name")
        for node in prompt.values():
            if node.get("class_type") == "CLIPLoader":
                if "type" in info.get("CLIPLoader", {}).get("input", {}).get("required", {}):
                    node["inputs"]["type"] = "qwen_image"
                if node["inputs"].get("clip_name") not in available and REMOTE_PHR00T_CLIP in available:
                    node["inputs"]["clip_name"] = REMOTE_PHR00T_CLIP
    elif workflow == STAGE_1_WORKFLOW:
        # The connected 8189 backend exposes the FP8 Qwen encoder in both
        # loader choice lists, but CLIPLoaderGGUF cannot actually load scaled
        # FP8 safetensors (it raises "Mixing scaled FP8 with GGUF"). Prefer a
        # real GGUF encoder only when one is installed; otherwise convert the
        # workflow node to the regular CLIPLoader for the FP8 safetensors.
        gguf_available = _remote_choice_values(info, ("CLIPLoaderGGUF",), "clip_name")
        regular_available = _remote_choice_values(info, ("CLIPLoader",), "clip_name")
        for node in prompt.values():
            if node.get("class_type") != "CLIPLoaderGGUF":
                continue
            gguf = next((name for name in (REMOTE_PHR00T_GGUF_CLIP,) if name in gguf_available), None)
            if gguf:
                node["inputs"]["clip_name"] = gguf
                if "type" in info.get("CLIPLoaderGGUF", {}).get("input", {}).get("required", {}):
                    node["inputs"]["type"] = "qwen_image"
            elif REMOTE_PHR00T_CLIP in regular_available:
                node["class_type"] = "CLIPLoader"
                node["inputs"]["clip_name"] = REMOTE_PHR00T_CLIP
                if "type" in info.get("CLIPLoader", {}).get("input", {}).get("required", {}):
                    node["inputs"]["type"] = "qwen_image"
    return prompt


def validate_remote_workflow_assets(workflow: Path, info: dict, model_override=None):
    prompt = remote_workflow_prompt(workflow, info)
    if workflow in REMOTE_KLEIN_REFERENCE_WORKFLOWS and model_override == REGULAR_9B_MODEL:
        prompt["1"] = {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": model_override}}
    controls = workflow_lab.discover_workflow_controls(prompt)
    if model_override and controls.get("model"):
        node_id, field = controls["model"]
        prompt[str(node_id)]["inputs"][field] = model_override
    if workflow in REMOTE_KLEIN_REFERENCE_WORKFLOWS:
        _reconcile_remote_klein_clip(prompt, info)
    validate_operation_prompt(prompt, info, f"Workflow {workflow.stem}")


def reconcile_model_paths(prompt, info):
    for node in prompt.values():
        required = info.get(node.get('class_type'), {}).get('input', {}).get('required', {})
        for field in ('ckpt_name', 'unet_name'):
            name = node.get('inputs', {}).get(field)
            choices = [str(v) for v in workflow_lab._choice_values(required.get(field))
                       if not any(part.startswith('.') or 'partial' in part.lower() for part in Path(str(v)).parts)]
            if isinstance(name, str) and name not in choices:
                matches = [v for v in choices if Path(v).name == name]
                if len(matches) == 1:
                    node['inputs'][field] = matches[0]


def validate_operation_prompt(prompt, info, label):
    reconcile_model_paths(prompt, info)
    validation = workflow_lab.validate_prompt(prompt, info)
    problems = validation["missing_nodes"] + validation["missing_inputs"]
    asset_fields = {"ckpt_name", "unet_name", "clip_name", "vae_name", "lora_name",
                    "swap_model", "face_restore_model", "model_name"}
    for node in prompt.values():
        specs = info.get(node["class_type"], {}).get("input", {}).get("required", {})
        for field, value in node.get("inputs", {}).items():
            spec = specs.get(field, [])
            choices = workflow_lab._choice_values(spec)
            if field in asset_fields and choices and value not in choices:
                problems.append(f"{field}: {value}")
    if problems:
        raise workflow_lab.ComfyError(
            f"{label} requires unavailable components: " + ", ".join(problems)
        )


def load_generation_profiles() -> list[dict]:
    """Read the active backend catalog without blocking the Qt startup thread."""
    try:
        backend_url = remote_url()
    except ValueError:
        return []
    if backend_url:
        info = read_remote_catalog(backend_url)
        return build_remote_generation_profiles(info) if info else []
    loras: set[str] = set()
    triggers: dict[str, list[str]] = {}
    for root in MODEL_ROOTS:
        lora_root = root / "loras"
        if not lora_root.is_dir():
            continue
        try:
            for path in lora_root.rglob("*"):
                if path.is_file() and path.suffix.lower() in {".safetensors", ".pt"}:
                    name = path.relative_to(lora_root).as_posix()
                    loras.add(name)
                    triggers[name] = lora_trigger_words(path)
        except OSError:
            continue
    return build_generation_profiles(
        readiness_report(),
        sorted(loras, key=str.casefold),
        triggers,
    )


def insert_model_only_loras(
    prompt: dict,
    source_node: str,
    consumer_node: str,
    consumer_input: str,
    loras: list[str],
    strengths: list[float] | None = None,
    strength: float = 0.65,
) -> dict:
    """Chain model-only LoRAs in selection order with per-slot strengths."""
    pairs = [
        (name, float((strengths or [])[index] if index < len(strengths or []) else strength))
        for index, name in enumerate(loras)
        if name and name != "None"
    ]
    if len(pairs) > 3:
        raise workflow_lab.ComfyError("GENESIS currently allows at most 3 stacked LoRAs.")
    if len({name for name, _ in pairs}) != len(pairs):
        raise workflow_lab.ComfyError("Select each LoRA only once.")
    if any(value < 0.0 or value > 1.0 for _, value in pairs):
        raise workflow_lab.ComfyError("LoRA strengths must be between 0.00 and 1.00.")

    model_link: list = [str(source_node), 0]
    for index, (name, value) in enumerate(pairs, 1):
        node_id = f"genesis_lora_{index}"
        prompt[node_id] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": model_link,
                "lora_name": name,
                "strength_model": value,
            },
            "_meta": {"title": f"GENESIS LoRA {index}: {name}"},
        }
        model_link = [node_id, 0]
    prompt[str(consumer_node)]["inputs"][consumer_input] = model_link
    return prompt


def insert_sdxl_loras(prompt: dict, loras: list[str], strengths: list[float] | None = None) -> None:
    """Chain SDXL adapters through both checkpoint MODEL and CLIP outputs."""
    selected = [(name, float((strengths or [])[index] if index < len(strengths or []) else 0.65))
                for index, name in enumerate(loras) if name and name != "None"]
    if len(selected) > 3 or len({name for name, _ in selected}) != len(selected):
        raise workflow_lab.ComfyError("Select up to three distinct SDXL LoRAs.")
    model_link, clip_link = ["1", 0], ["1", 1]
    for index, (name, strength) in enumerate(selected, 1):
        if not is_compatible(prompt["1"]["inputs"]["ckpt_name"], name) or not 0 <= strength <= 1:
            raise workflow_lab.ComfyError(f"Incompatible SDXL LoRA or strength: {name}")
        node_id = f"genesis_sdxl_lora_{index}"
        prompt[node_id] = {"class_type": "LoraLoader", "inputs": {
            "model": model_link, "clip": clip_link, "lora_name": name,
            "strength_model": strength, "strength_clip": strength}}
        model_link, clip_link = [node_id, 0], [node_id, 1]
    prompt["5"]["inputs"]["model"] = model_link
    prompt["2"]["inputs"]["clip"] = clip_link
    prompt["3"]["inputs"]["clip"] = clip_link



FACEID_SDXL_MODEL = "ip-adapter-faceid-plusv2_sdxl.bin"
FACEID_SDXL_LORA = "ip-adapter-faceid-plusv2_sdxl_lora.safetensors"
FACEID_CLIP = "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"


def attach_sdxl_faceid(prompt: dict, info: dict, controls: dict, *, pose_driven: bool = False) -> None:
    """Explicit loaders preserve user LoRAs and fail before submission on missing assets."""
    required = {
        "IPAdapterModelLoader": ("ipadapter_file", FACEID_SDXL_MODEL),
        "LoraLoaderModelOnly": ("lora_name", FACEID_SDXL_LORA),
        "CLIPVisionLoader": ("clip_name", FACEID_CLIP),
    }
    for kind, (field, asset) in required.items():
        if asset not in _remote_choice_values(info, (kind,), field):
            raise workflow_lab.ComfyError("SDXL FaceID asset unavailable: " + asset)
    for kind in ("IPAdapterFaceID", "IPAdapterInsightFaceLoader"):
        if kind not in info:
            raise workflow_lab.ComfyError("SDXL FaceID node unavailable: " + kind)
    if "genesis_source" not in prompt:
        raise workflow_lab.ComfyError("SDXL FaceID requires a Person A source face reference.")
    weight = float(controls.get("faceid_strength", 0.8))
    denoise = float(controls.get("denoise", 0.55))
    if not (0.0 <= weight <= 1.5 and (pose_driven or 0.45 <= denoise <= 0.60)):
        raise workflow_lab.ComfyError("FaceID strength must be 0–1.5 and denoise 0.45–0.60.")
    model = prompt["5"]["inputs"]["model"]
    prompt["genesis_faceid_lora"] = {"class_type": "LoraLoaderModelOnly", "inputs": {
        "model": model, "lora_name": FACEID_SDXL_LORA, "strength_model": 0.6}}
    prompt["genesis_faceid_adapter"] = {"class_type": "IPAdapterModelLoader", "inputs": {
        "ipadapter_file": FACEID_SDXL_MODEL}}
    prompt["genesis_faceid_clip"] = {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": FACEID_CLIP}}
    prompt["genesis_faceid_insight"] = {"class_type": "IPAdapterInsightFaceLoader", "inputs": {
        "provider": "CPU", "model_name": "buffalo_l"}}
    prompt["genesis_faceid"] = {"class_type": "IPAdapterFaceID", "inputs": {
        "model": ["genesis_faceid_lora", 0], "ipadapter": ["genesis_faceid_adapter", 0],
        "image": ["genesis_source", 0], "weight": weight, "weight_faceidv2": 1.0,
        "weight_type": "linear", "combine_embeds": "concat", "start_at": 0.0, "end_at": 1.0,
        "embeds_scaling": "V only", "clip_vision": ["genesis_faceid_clip", 0],
        "insightface": ["genesis_faceid_insight", 0]}}
    # A new OpenPose body must begin from noise, not the old photograph.
    prompt["5"]["inputs"].update(model=["genesis_faceid", 0], denoise=1.0 if pose_driven else denoise)


def attach_sdxl_pose(prompt: dict, info: dict, uploaded_pose: dict, width: int, height: int) -> None:
    """Apply an already rendered skeleton through the active backend's SDXL ControlNet."""
    available = _remote_choice_values(info, ("ControlNetLoader",), "control_net_name")
    if REMOTE_SDXL_POSE_CONTROLNET not in available:
        raise workflow_lab.ComfyError("SDXL pose guidance needs OpenPoseXL2.safetensors in the active ComfyUI ControlNet catalog.")
    pose_name = "/".join(value for value in (uploaded_pose.get("subfolder"), uploaded_pose.get("name")) if value)
    prompt["genesis_pose_image"] = {"class_type": "LoadImage", "inputs": {"image": pose_name}}
    prompt["genesis_pose_scale"] = {"class_type": "ImageScale", "inputs": {
        "image": ["genesis_pose_image", 0], "upscale_method": "nearest-exact",
        "width": width, "height": height, "crop": "disabled"}}
    prompt["genesis_pose_controlnet"] = {"class_type": "ControlNetLoader", "inputs": {
        "control_net_name": REMOTE_SDXL_POSE_CONTROLNET}}
    prompt["genesis_pose_apply"] = {"class_type": "ControlNetApplyAdvanced", "inputs": {
        "positive": ["2", 0], "negative": ["3", 0],
        "control_net": ["genesis_pose_controlnet", 0], "image": ["genesis_pose_scale", 0],
        "strength": 0.8, "start_percent": 0.0, "end_percent": 1.0}}
    prompt["5"]["inputs"].update(positive=["genesis_pose_apply", 0], negative=["genesis_pose_apply", 1])


def build_create_prompt(
    info: dict,
    prompt_text: str,
    width: int,
    height: int,
    model_name: str,
    loras: list[str] | None = None,
    lora_strengths: list[float] | None = None,
) -> dict:
    """Build one of the two live-validated Create graphs selected in QML."""
    # Keep the RX 9060 local path conservative, but let the remote A100
    # honor the full resolution range exposed by the premium UI.
    max_dimension = 4096 if remote_url() else 1536
    width = max(256, min(max_dimension, int(width)))
    height = max(256, min(max_dimension, int(height)))
    loras = loras or []

    if model_name in REMOTE_CHECKPOINT_MODELS:
        prompt = workflow_lab.workflow_to_prompt(REMOTE_SDXL_T2I_WORKFLOW, info)
        prompt["1"]["inputs"]["ckpt_name"] = model_name
        prompt["2"]["inputs"]["text"] = prompt_text
        prompt["4"]["inputs"].update(width=width, height=height, batch_size=1)
        defaults = model_generation_settings(model_name)
        prompt["5"]["inputs"].update(steps=defaults["defaultSteps"], cfg=defaults["defaultCfg"],
                                      sampler_name=defaults["defaultSampler"], scheduler=defaults["defaultScheduler"])
        prompt["7"]["inputs"]["filename_prefix"] = "GENESIS-" + Path(model_name).stem
        insert_sdxl_loras(prompt, loras, lora_strengths)
    elif model_name == QWEN21_MODEL:
        compatible_selection(model_name, loras)
        prompt = workflow_lab.workflow_to_prompt(QWEN21_T2I_WORKFLOW, info)
        prompt["1"]["inputs"]["unet_name"] = QWEN21_MODEL
        prompt["3"]["inputs"]["clip_name"] = QWEN21_CLIP
        prompt["4"]["inputs"]["vae_name"] = QWEN21_VAE
        prompt["5"]["inputs"]["prompt"] = prompt_text
        prompt["6"]["inputs"].update({"width": width, "height": height, "batch_size": 1})
        insert_model_only_loras(prompt, "1", "2", "model", loras, lora_strengths, strength=0.5)
        prompt["9"]["inputs"]["filename_prefix"] = "GENESIS-QwenImage21"
    elif model_name == LOCAL_AISHA_9B_MODEL:
        selected = [name for name in loras if name and name != "None"]
        if selected:
            raise workflow_lab.ComfyError("Aisha 9B Base LoRAs are disabled until a model-specific adapter is verified.")
        prompt = workflow_lab.workflow_to_prompt(LOCAL_AISHA_9B_WORKFLOW, info)
        prompt["1"]["inputs"]["unet_name"] = LOCAL_AISHA_9B_MODEL
        prompt["3"]["inputs"]["text"] = prompt_text
        prompt["8"]["inputs"].update({"width": width, "height": height})
        prompt["9"]["inputs"].update({"width": width, "height": height, "batch_size": 1})
        prompt["13"]["inputs"]["filename_prefix"] = "GENESIS-Aisha9B-Base"
    elif model_name in REMOTE_KLEIN9B_SOURCE_MODELS:
        selected = [name for name in loras if name and name != "None"]
        workflow = REMOTE_PORNMASTER_T2I_WORKFLOW if model_name == LOCAL_PORNMASTER_9B_MODEL else REMOTE_MIRACLEIN_T2I_WORKFLOW
        if not workflow.is_file():
            raise workflow_lab.ComfyError("The RunPod Klein-family text-to-image workflow is unavailable.")
        prompt = workflow_lab.workflow_to_prompt(workflow, info)
        loader = prompt.get("126")
        if not loader:
            raise workflow_lab.ComfyError("Klein-family T2I workflow is missing model loader node 126.")
        if model_name == LOCAL_PORNMASTER_9B_MODEL:
            loader["class_type"] = "UnetLoaderGGUF"
        else:
            loader["class_type"] = "UNETLoader"
        loader["inputs"] = {"unet_name": model_name, **({"weight_dtype": "default"} if loader["class_type"] == "UNETLoader" else {})}
        prompt["136"]["inputs"]["clip_name"] = TEXT_ENCODER_9B
        prompt["102"]["inputs"]["vae_name"] = REMOTE_9B_VAE
        prompt["107"]["inputs"]["text"] = prompt_text
        prompt["105"]["inputs"].update({"width": width, "height": height, "batch_size": 1})
        # The graph template is only a loader/conditioning layout; apply the
        # selected model's own sampling profile rather than Miraclein's values.
        sampling = model_generation_settings(model_name)
        prompt["134"]["inputs"].update(steps=sampling["defaultSteps"],
                                       cfg=sampling["defaultCfg"],
                                       sampler_name=sampling["defaultSampler"],
                                       scheduler=sampling["defaultScheduler"])
        prompt["9"]["inputs"]["filename_prefix"] = "GENESIS-Klein9B-T2I"
        insert_model_only_loras(prompt, "126", "134", "model", loras, lora_strengths)
    elif model_name == REGULAR_9B_MODEL:
        workflow = next((path for path in REGULAR_9B_WORKFLOWS if path.is_file()), None)
        if workflow is None:
            raise workflow_lab.ComfyError("The regular Klein 9B workflow is unavailable.")
        prompt = workflow_lab.workflow_to_prompt(workflow, info)
        prompt["126"]["class_type"] = "UnetLoaderGGUF"
        prompt["126"]["inputs"] = {"unet_name": REGULAR_9B_MODEL}
        prompt["136"]["inputs"]["clip_name"] = TEXT_ENCODER_9B
        prompt["107"]["inputs"]["text"] = prompt_text
        # This is the non-distilled Base Q4, not the four-step distilled 9B.
        sampling = model_generation_settings(model_name)
        prompt["134"]["inputs"].update(steps=sampling["defaultSteps"],
                                       cfg=sampling["defaultCfg"])
        prompt["105"]["inputs"].update({"width": width, "height": height, "batch_size": 1})
        prompt["9"]["inputs"]["filename_prefix"] = "GENESIS-Klein9B-Regular"
        insert_model_only_loras(prompt, "126", "134", "model", loras, lora_strengths)
    elif model_name == KV_9B_MODEL:
        selected = [name for name in loras if name and name != "None"]
        if selected:
            raise workflow_lab.ComfyError("Klein 9B-KV has no validated LoRA route.")
        if not GENERATION_WORKFLOW.is_file():
            raise workflow_lab.ComfyError("The validated Klein 9B-KV workflow is unavailable.")
        prompt = workflow_lab.workflow_to_prompt(GENERATION_WORKFLOW, info)
        prompt["1"]["inputs"]["unet_name"] = KV_9B_MODEL
        prompt["2"]["inputs"]["clip_name"] = TEXT_ENCODER_9B
        prompt["3"]["inputs"]["text"] = prompt_text
        prompt["9"]["inputs"].update({"steps": 4, "width": width, "height": height})
        prompt["10"]["inputs"].update({"width": width, "height": height, "batch_size": 1})
        prompt["14"]["inputs"]["filename_prefix"] = "GENESIS-Klein9B-KV"
    elif model_name == FOUR_B_MODEL:
        prompt = workflow_lab.workflow_to_prompt(GENERATION_WORKFLOW, info)
        prompt["1"]["inputs"]["unet_name"] = FOUR_B_MODEL
        prompt["2"]["inputs"]["clip_name"] = TEXT_ENCODER_4B
        prompt["3"]["inputs"]["text"] = prompt_text
        prompt.pop("5", None)
        prompt["6"]["inputs"]["model"] = ["1", 0]
        prompt["9"]["inputs"].update({"steps": 4, "width": width, "height": height})
        prompt["10"]["inputs"].update({"width": width, "height": height, "batch_size": 1})
        prompt["14"]["inputs"]["filename_prefix"] = "GENESIS-Klein4B-Fast"
        insert_model_only_loras(prompt, "1", "6", "model", loras, lora_strengths, strength=0.5)
    else:
        raise workflow_lab.ComfyError(f"No validated Create workflow for {model_name}.")

    validation = workflow_lab.validate_prompt(prompt, info)
    if not validation["valid"]:
        missing = validation["missing_nodes"] + validation["missing_inputs"]
        raise workflow_lab.ComfyError("Workflow is not runnable: " + ", ".join(missing))
    return prompt


def apply_create_controls(prompt: dict, controls: dict) -> None:
    """Apply visible numeric controls without replacing graph connections."""
    fields = workflow_lab.discover_workflow_controls(prompt)
    for name in ("steps", "cfg", "denoise", "sampler", "scheduler"):
        target = fields.get(name)
        if target and name in controls:
            inputs = prompt[str(target[0])]["inputs"]
            if not isinstance(inputs.get(target[1]), list):
                inputs[target[1]] = controls[name]
    seed = int(controls.get("seed", -1))
    if seed < 0:
        seed = int(time.time_ns() & 0xFFFFFFFFFFFF)
    for node in prompt.values():
        inputs = node.get("inputs", {})
        for key in ("seed", "noise_seed"):
            if key in inputs and not isinstance(inputs[key], list):
                inputs[key] = seed
        if node.get("class_type") == "Flux2Scheduler":
            for key in ("steps", "width", "height"):
                if key in controls:
                    inputs[key] = controls[key]


def _pose_thumbnail_for(source: Path) -> Path:
    """Prefer the Photo Studio visual preview while preserving skeleton input separately."""
    stem = source.stem
    for suffix in ("_bone_structure", "_bone_strucure"):
        if stem.endswith(suffix):
            stem = stem[:-len(suffix)]
            break
    for variant in ("depth", "lineart", "bone_structure"):
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            candidate = POSE_THUMB_CACHE / f"{stem}_{variant}{ext}"
            if candidate.is_file():
                return candidate
    return source


def load_pose_items(limit: int = 12) -> list[dict[str, str]]:
    """Return indexed local poses, preferring the bundled GENESIS library."""
    bundled_root = PROJECT_ROOT / "genesis" / "reference" / "assets" / "pose_library"
    roots = (
        Path.home() / "AI" / "GENESIS_POSE_MAKER" / "assets" / "pose_library",
        Path.home() / "Downloads" / "GENESIS_POSE_MAKER_V15_USER_IMAGE_SLOTS(1)"
        / "GENESIS_POSE_MAKER" / "assets" / "pose_library",
    )
    # A bundled index alone is not proof its optional private images are
    # installed. Fall back to the user's existing external pose import when
    # no valid bundled controls are present.
    bundles = []
    bundled_index = bundled_root / "index.json"
    if bundled_index.is_file():
        bundles.append((bundled_root, bundled_index))
    if POSE_INDEX.is_file():
        bundles.extend((root, POSE_INDEX) for root in roots if root.is_dir())
    if not bundles:
        return []

    try:
        prompt_map = PosePromptMap.load()
    except (OSError, ValueError, json.JSONDecodeError):
        prompt_map = None

    categories: dict[str, list[dict]] = {}
    for library_root, index_path in bundles:
        try:
            indexed = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(indexed, list):
            continue
        root_resolved = library_root.resolve()
        for item in indexed:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                continue
            # Never display or read an arbitrary local image through a
            # user-imported pose manifest. This also blocks symlink escapes.
            source = (root_resolved / item["path"]).resolve()
            if not source.is_relative_to(root_resolved) or not source.is_file():
                continue
            category = str(item.get("category", "Pose"))
            resolution = str(item.get("resolution", ""))
            raw_name = str(item.get("name", source.stem))
            pose_id = f"{category}/{resolution}/{raw_name}"
            record = prompt_map.records.get(pose_id) if prompt_map is not None else None
            categories.setdefault(category, []).append({
                **item,
                "source": QUrl.fromLocalFile(str(source)).toString(),
                "thumbnail": QUrl.fromLocalFile(str(_pose_thumbnail_for(source))).toString(),
                "poseId": pose_id,
                "sourceMetadata": source_metadata(item, source),
                "prompt": record.prompt if record else "",
                "negativePrompt": record.negative_prompt if record else "",
                "promptSource": record.source if record else "AUTO_FALLBACK",
                "promptTemplateId": record.prompt_template_id if record else "",
                "promptMapped": bool(record),
            })
        if categories:
            break

    result: list[dict[str, str]] = []
    while len(result) < limit and any(categories.values()):
        for category in list(categories):
            if categories[category] and len(result) < limit:
                item = categories[category].pop(0)
                result.append({
                    "name": str(item.get("name", "Pose")).replace("_", " ").title(),
                    "category": category.replace("NSFW_", "").replace("_", " ").title(),
                    "resolution": str(item.get("resolution", "")),
                    "source": str(item["source"]),
                    "thumbnail": str(item.get("thumbnail", item["source"])),
                    "poseId": str(item.get("poseId", "")),
                    "prompt": str(item.get("prompt", "")),
                    "negativePrompt": str(item.get("negativePrompt", "")),
                    "promptSource": str(item.get("promptSource", "AUTO_FALLBACK")),
                    "promptTemplateId": str(item.get("promptTemplateId", "")),
                    "promptMapped": bool(item.get("promptMapped", False)),
                    "sourceMetadata": item.get("sourceMetadata", {}),
                })
    return result


def load_runtime_status(*, probe_remote: bool = True) -> dict:
    """Probe the active backend; remote probes run off the Qt startup thread."""
    try:
        backend_url = remote_url()
    except ValueError as exc:
        return {"comfyOnline": False, "gpuName": "RunPod endpoint blocked", "vramUsedGiB": 0,
                "vramTotalGiB": 0, "ready": False, "remote": True, "error": str(exc)}
    if not backend_url and not probe_remote:
        return {"comfyOnline": False, "gpuName": "Checking local backend", "vramUsedGiB": 0,
                "vramTotalGiB": 0, "ready": False, "remote": False}
    if backend_url:
        status = {
            "comfyOnline": False, "gpuName": "RunPod offline",
            "vramUsedGiB": 0, "vramTotalGiB": 0,
            "ready": False, "remote": True,
        }
        if not probe_remote:
            return status
        try:
            stats = workflow_lab.ComfyClient(backend_url, timeout=20).system_stats()
            metrics = workflow_lab.gpu_metrics(stats)
            status.update({
                "comfyOnline": True, "gpuName": metrics["name"],
                "vramUsedGiB": round(metrics["vram_used"] / 1024 ** 3, 1),
                "vramTotalGiB": round(metrics["vram_total"] / 1024 ** 3, 1),
                "ready": workflow_lab.gpu_acceleration_available(stats),
            })
        except Exception as exc:
            status["error"] = str(exc)
        return status
    try:
        stats = workflow_lab.system_stats()
        metrics = workflow_lab.gpu_metrics(stats)
        gib = 1024 ** 3
        return {
            "comfyOnline": True,
            "gpuName": metrics["name"],
            "vramUsedGiB": round(metrics["vram_used"] / gib, 1),
            "vramTotalGiB": round(metrics["vram_total"] / gib, 1),
            "ready": workflow_lab.gpu_acceleration_available(stats),
            "remote": False,
        }
    except Exception:
        return {
            "comfyOnline": False,
            "gpuName": "Unavailable",
            "vramUsedGiB": 0,
            "vramTotalGiB": 0,
            "ready": False,
            "remote": False,
        }


class RemoteRuntimeMonitor(QObject):
    """Refresh cloud status/catalog without blocking the desktop or starting services."""

    statusReady = pyqtSignal(object)
    profilesReady = pyqtSignal(object)
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._catalog_checked = False
        self._last_profiles = None
        self.finished.connect(self._finish)
        self.timer = QTimer(self)
        self.timer.setInterval(30000)
        self.timer.timeout.connect(self.refresh)

    def start(self):
        self.timer.start()
        self.refresh()

    @pyqtSlot()
    def _finish(self):
        self._running = False

    @pyqtSlot()
    def refresh(self):
        if self._running:
            return
        self._running = True
        threading.Thread(target=self._probe, daemon=True).start()

    def _probe(self):
        try:
            status = load_runtime_status()
            self.statusReady.emit(status)
            if status["comfyOnline"] and status.get("remote"):
                url = remote_url()
                client = workflow_lab.ComfyClient(url, timeout=20)
                info = load_remote_catalog(client, refresh=not self._catalog_checked)
                self._catalog_checked = True
                profiles = build_remote_generation_profiles(info)
                if profiles != self._last_profiles:
                    self._last_profiles = profiles
                    self.profilesReady.emit(profiles)
        except Exception as exc:
            print(f"Backend status refresh failed: {exc}", file=sys.stderr)
        finally:
            self.finished.emit()


class LayoutSettingsBridge(QObject):
    """Persist user-adjustable QML layout values without touching generation state."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._settings = QSettings("GENESIS", "c0ckpit")

    backgroundChanged = pyqtSignal()

    @pyqtProperty(str, notify=backgroundChanged)
    def backgroundUrl(self):
        path = str(self._settings.value("appearance/background", ""))
        return QUrl.fromLocalFile(path).toString() if path and Path(path).is_file() else ""

    @pyqtProperty(float, notify=backgroundChanged)
    def backgroundOpacity(self):
        try:
            return max(0.0, min(1.0, float(self._settings.value("appearance/backgroundOpacity", 0.24))))
        except (TypeError, ValueError):
            return 0.24

    @pyqtSlot()
    def chooseBackground(self):
        from genesis.qt_media_picker import choose_image
        from PyQt6.QtGui import QImageReader
        path = choose_image("GENESIS · Choose workspace background")
        if not path or not QImageReader(path).canRead():
            return
        self._settings.setValue("appearance/background", str(Path(path).resolve()))
        self._settings.sync()
        self.backgroundChanged.emit()

    @pyqtSlot(float)
    def setBackgroundOpacity(self, value):
        import math
        if not math.isfinite(value):
            return
        self._settings.setValue("appearance/backgroundOpacity", max(0.0, min(1.0, value)))
        self._settings.sync()
        self.backgroundChanged.emit()

    @pyqtSlot()
    def resetBackground(self):
        self._settings.remove("appearance/background")
        self._settings.remove("appearance/backgroundOpacity")
        self._settings.sync()
        self.backgroundChanged.emit()

    @pyqtSlot(result="QVariant")
    def loadCreateLayout(self):
        defaults = {
            "previewWidth": 370.0,
            "promptHeight": 106.0,
            "referenceHeight": 112.0,
            "sourceHeight": 92.0,
            "outputHeight": 88.0,
        }
        return {key: float(self._settings.value("layout/create/" + key, value)) for key, value in defaults.items()}

    @pyqtSlot(float, float, float, float, float)
    def saveCreateLayout(self, previewWidth, promptHeight, referenceHeight, sourceHeight, outputHeight) -> None:
        values = {
            "previewWidth": previewWidth,
            "promptHeight": promptHeight,
            "referenceHeight": referenceHeight,
            "sourceHeight": sourceHeight,
            "outputHeight": outputHeight,
        }
        for key, value in values.items():
            self._settings.setValue("layout/create/" + key, float(value))
        self._settings.sync()

    @pyqtSlot()
    def resetCreateLayout(self) -> None:
        self._settings.remove("layout/create")
        self._settings.sync()


class ModuleBridge(QObject):
    """Route Qt module cards to existing GENESIS tools and services."""

    statusChanged = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._status = "Ready · choose a module action"
        self.backend_router = None
        self._grok_sessions = {}

    @pyqtSlot("QVariantMap", str, result="QVariantMap")
    def posePresetPayload(self, row, model):
        return preset_payload(row, model)

    @pyqtProperty(str, notify=statusChanged)
    def studioUrl(self):
        return getattr(self, '_studio_url', '')

    @pyqtProperty('QVariantList', notify=statusChanged)
    def cameraStreams(self):
        return getattr(self, '_camera_streams', [])

    @pyqtSlot()
    def refreshCameras(self):
        def check():
            try:
                with urllib.request.urlopen(integrations.GO2RTC_URL + '/api/streams', timeout=5) as response:
                    streams = json.load(response)
                self._camera_streams = [{'name': name, 'url': integrations.GO2RTC_URL + '/stream.html?src=' + urllib.parse.quote(name, safe='') + '&mode=mse'} for name in sorted(streams)]
                self._set_status(str(len(self._camera_streams)) + ' camera streams available.')
            except Exception as exc:
                self._camera_streams = []
                self._set_status('Camera service unavailable · use Open Camera Hub to start it.')
        threading.Thread(target=check, daemon=True).start()

    @pyqtSlot("QVariantMap", str, result="QVariantMap")
    def posePresetPayload(self, row, model):
        return preset_payload(row, model)

    @pyqtProperty(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    def _set_status(self, value: str) -> None:
        self._status = value
        self.statusChanged.emit()

    def _open(self, target: str | Path, label: str) -> None:
        url = QUrl(str(target)) if str(target).startswith(("http://", "https://")) else QUrl.fromLocalFile(str(target))
        ok = QDesktopServices.openUrl(url)
        self._set_status(f"{label} opened" if ok else f"Could not open {label}")

    def _legacy(self, action: str) -> None:
        if integrations.process_running(r"Genesis-c0ckpit/main.py"):
            self._set_status(f"{action} · full GENESIS workspace is already running")
            return
        try:
            subprocess.Popen(
                [sys.executable, str(PROJECT_ROOT / "main.py")],
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self._set_status(f"{action} · full GENESIS workspace opened")
        except OSError as exc:
            self._set_status(f"{action} failed · {exc}")

    def _pose_maker(self) -> None:
        root = Path.home() / "AI" / "GENESIS_POSE_MAKER"
        run_script = root / "run.sh"
        url = "http://127.0.0.1:7861"

        def worker() -> None:
            if not integrations.endpoint_online(url, "/", timeout=0.8):
                if not run_script.is_file():
                    self._set_status("Pose Maker is not installed")
                    return
                try:
                    subprocess.Popen(
                        [str(run_script)],
                        cwd=str(root),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                except OSError as exc:
                    self._set_status(f"Pose Maker failed · {exc}")
                    return
                for _ in range(60):
                    if integrations.endpoint_online(url, "/", timeout=0.5):
                        break
                    time.sleep(0.5)
                else:
                    self._set_status("Pose Maker did not come online on port 7861")
                    return
            integrations.open_url(url)
            self._set_status("Pose Maker workbench opened")

        self._set_status("Starting Pose Maker workbench…")
        threading.Thread(target=worker, daemon=True).start()

    def _service(self, url: str, health_path: str, service: str, label: str) -> None:
        def worker() -> None:
            online = integrations.endpoint_online(url, health_path)
            ok, detail = integrations.start_user_service(service, already_online=online)
            if ok:
                for _ in range(40):
                    if integrations.endpoint_online(url, health_path, timeout=0.5):
                        integrations.open_url(url)
                        self._set_status(f"{label} online")
                        return
                    time.sleep(0.75)
            self._set_status(f"{label} · {detail}")
        self._set_status(f"Starting {label}…")
        threading.Thread(target=worker, daemon=True).start()

    @pyqtSlot()
    def refresh(self) -> None:
        def worker() -> None:
            snapshot = integrations.status_snapshot()
            online = [
                name for name, item in snapshot.get("integrations", {}).items()
                if item.get("online")
            ]
            summary = ", ".join(online) if online else "no local services online"
            if remote_url():
                remote = load_runtime_status()
                summary = ("RunPod ready" if remote.get("ready") else "RunPod unavailable") + " · " + summary
            self._set_status("Health check · " + summary)
        self._set_status("Running health check…")
        threading.Thread(target=worker, daemon=True).start()

    def _open_grok_runpod(self) -> None:
        """Open an isolated studio bound to the selected remote endpoint."""
        from genesis.backend_routing import normalize_endpoint
        import socket

        router = self.backend_router
        if router is None or router.mode != "RUNPOD":
            self._set_status("Select RUNPOD before opening Grok from GENESIS.")
            return
        try:
            endpoint = normalize_endpoint(router.endpoint)
        except ValueError as exc:
            self._set_status(str(exc))
            return
        if not endpoint:
            self._set_status("Set the RunPod ComfyUI endpoint before opening Grok.")
            return
        grok_root = Path.home() / "MUNGBEAN"
        launcher = grok_root / "START_LOCAL.sh"
        if not launcher.is_file():
            self._set_status("MUNGBEAN Grok Imagine is not installed")
            return
        brain_url = (os.environ.get("GENESIS_BRAIN_URL") or os.environ.get("GENESIS_CLOUD_BASE_URL", "")).strip().rstrip("/")
        brain_model = (os.environ.get("GENESIS_BRAIN_MODEL") or os.environ.get("GENESIS_CLOUD_MODEL", "")).strip()
        session_key = (endpoint, brain_url, brain_model)
        session = self._grok_sessions.get(session_key)
        if session and session[0].poll() is None:
            self._studio_url = session[1]
            self.statusChanged.emit()
            return
        try:
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                port = listener.getsockname()[1]
            env = os.environ.copy()
            env.update(COMFY_URL=endpoint, IMAGINE_HOST="127.0.0.1", IMAGINE_PORT=str(port),
                       MUNGBEAN_MANAGE_BRAIN="0", MUNGBEAN_OPEN_BROWSER="0")
            if brain_url:
                env.update(BRAIN_URL=brain_url if brain_url.endswith("/v1") else brain_url + "/v1",
                           GENESIS_BRAIN_MODEL=brain_model)
            process = subprocess.Popen(
                [str(launcher)], cwd=str(grok_root), env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self._grok_sessions[session_key] = (process, f"http://127.0.0.1:{port}")
            self._studio_url = f"http://127.0.0.1:{port}"
            self._set_status("Grok launched for RunPod · connection and models must be ready")
        except OSError as exc:
            self._set_status(f"Grok launch failed · {exc}")

    @pyqtSlot(str)
    def triggerAction(self, action: str) -> None:
        key = action.strip().lower()
        if not key:
            return
        if key in {"refresh", "health check"}:
            self.refresh()
        elif any(word in key for word in ("output", "export")):
            self._open(OUTPUT_DIR, "GENESIS exports")
        elif any(word in key for word in ("workflow", "json", "nodes", "preflight", "validate")):
            self._open(WORKFLOW_ROOT, "ComfyUI workflows")
        elif any(word in key for word in ("camera", "grid", "recordings", "hub")):
            self._service(integrations.GO2RTC_URL, "/api/streams", "go2rtc.service", "Camera Hub")
        elif "pose maker" in key or "pose workbench" in key:
            self._pose_maker()
        elif any(word in key for word in ("movie", "video library")):
            ok, detail = integrations.launch_jellyfin_desktop()
            self._set_status(detail if ok else f"Jellyfin failed · {detail}")
        elif "comfyui" in key or key == "manage service":
            self._service(integrations.COMFYUI_URL, "/system_stats", integrations.COMFYUI_SERVICE, "ComfyUI")
        elif "ai settings" in key or "ai assistant" in key:
            self._service(integrations.QWEN_URL, "/health", integrations.QWEN_SERVICE, "GENESIS AI")
        elif "grok imagine" in key or "mungbean" in key:
            self._open_grok_runpod()
        elif "monitor" in key:
            try:
                subprocess.Popen(["gnome-system-monitor"], start_new_session=True)
                self._set_status("System monitor opened")
            except OSError as exc:
                self._set_status(f"System monitor failed · {exc}")
        elif "backup" in key or "recovery" in key:
            self._open(PROJECT_ROOT / "backups", "GENESIS recovery")
        elif "storage" in key or "model" in key:
            self._open(Path("/mnt/AI-Storage"), "Models and storage")
        elif "settings" in key:
            self._open(PROJECT_ROOT, "GENESIS settings")
        else:
            self._legacy(action)


class GenerationBridge(QObject):
    """Asynchronous Qt boundary around the preserved local ComfyUI client."""

    statusChanged = pyqtSignal()
    busyChanged = pyqtSignal()
    progressChanged = pyqtSignal()
    previewChanged = pyqtSignal()
    charactersChanged = pyqtSignal()
    queueChanged = pyqtSignal()
    stageThreeSelectionRequired = pyqtSignal(str, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._status = "Ready"
        self._busy = False
        self._progress = -1.0
        self._preview = ""
        self._character_a = ""
        self._original_master = None
        self._finish_results = []
        self._finish_contexts = {}
        self._finish_info = {}
        self._upscale_model = ""
        self._finish_route = None
        self._finish_width, self._finish_height = 1024, 1024
        self._stage_two_model = REMOTE_AISHA_9B_MODEL
        self._sdxl_faceid_enabled = False
        self._sdxl_faceid_strength = 0.8
        self._stage_three_engine = "reactor_inswapper"
        # Job-scoped engine is separate from the selection shown in the UI.
        self._active_stage_three_engine = None
        # Installed MIGraphX provider is opt-in until a full GPU inference
        # passes on this hardware. An offline neutral-image test timed out
        # after 150s despite a clean kernel preflight (2026-10-15).
        self._facefusion_provider = "cpu"
        self._cancel_requested = False
        self._active_client = None
        self._active_prompt_id = None
        self._output_target_long_edge = 0
        self._source_reference_megapixels = 0.0
        self._extra_reference_url = ""
        self._pending_generations = []
        self._queue_active = False
        self._queued_route_override = None
        self._queued_character_override = None
        self._pending_stage_three = False
        self.backend_router = None
        # Always dispatch queued jobs on Qt's owning thread after a worker ends.
        from PyQt6.QtCore import Qt
        self.busyChanged.connect(self._queue_busy_transition, Qt.ConnectionType.QueuedConnection)
        self.stageThreeSelectionRequired.connect(self._choose_stage_three_faces, Qt.ConnectionType.QueuedConnection)
        self._settings = QSettings("GENESIS", "c0ckpit")
        configured_output = str(self._settings.value("generation/output_dir", str(OUTPUT_DIR)))
        self._output_dir = Path(configured_output).expanduser()

    @pyqtProperty(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @pyqtProperty(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @pyqtProperty(float, notify=progressChanged)
    def progress(self) -> float:
        return self._progress

    @pyqtProperty(str, notify=previewChanged)
    def previewUrl(self) -> str:
        return self._preview

    @pyqtProperty(bool, constant=True)
    def editAvailable(self) -> bool:
        return EDIT_WORKFLOW.is_file()

    @pyqtProperty(bool, constant=True)
    def inpaintAvailable(self) -> bool:
        return True

    @pyqtProperty(str, notify=statusChanged)
    def faceFusionProvider(self):
        return self._facefusion_provider

    @pyqtSlot(str)
    def setFaceFusionProvider(self, provider):
        if provider in {'migraphx', 'cpu'} and not self._busy:
            self._facefusion_provider = provider
            self.statusChanged.emit()

    @staticmethod
    def _facefusion_python() -> Path:
        # Keep the availability indicator and launch path on the same runtime.
        ff_venv = integrations.FACEFUSION_ROOT / ".venv/bin/python"
        return (ff_venv if ff_venv.is_file()
                else Path.home() / "miniforge3/envs/facefusion-rocm/bin/python")

    @pyqtProperty(bool, constant=True)
    def faceFusionAvailable(self) -> bool:
        ff_root = integrations.FACEFUSION_ROOT
        return (self._facefusion_python().is_file()
                and (ff_root / "facefusion.py").is_file()
                and (ff_root / "facefusion.ini").is_file())

    @pyqtProperty(bool, constant=True)
    def upscaleAvailable(self) -> bool:
        if remote_url():
            # Remote assets are checked against the pod catalog before submission.
            return UPSCALE_WORKFLOW.is_file()
        return upscale_assets_available()

    def _set_status(self, value: str) -> None:
        self._status = value
        self.statusChanged.emit()

    def _set_busy(self, value: bool) -> None:
        self._busy = value
        self.busyChanged.emit()

    def _start_busy_worker(self, target, args=(), *, label: str) -> bool:
        """Start an already-marked-Busy operation without leaving a stuck UI.

        Thread creation and start can fail synchronously; no worker would then
        exist to execute the normal busy cleanup in the operation's finally.
        """
        try:
            threading.Thread(target=target, args=args, daemon=True).start()
        except Exception as exc:
            self._set_status(f"{label} could not start · {exc}")
            self._set_busy(False)
            return False
        return True

    def _set_progress(self, value: float) -> None:
        self._progress = max(-1.0, min(1.0, float(value)))
        self.progressChanged.emit()

    def _set_preview(self, value: str) -> None:
        self._preview = value
        self.previewChanged.emit()

    @pyqtSlot()
    def cancelGeneration(self) -> None:
        if not self._busy:
            return
        self._cancel_requested = True
        if self._pending_stage_three:
            # Generation has saved; no Stage 3 prompt may be uploaded after Cancel.
            self._pending_stage_three = False
            self._cancel_requested = False  # No Stage 3 worker exists yet.
            self._set_status("Generation saved · pending Stage 3 cancelled.")
            self._set_busy(False)
            return
        self._set_status("Cancelling generation…")
        # Do not wait for the polling loop to notice the flag: interrupt the
        # active ComfyUI backend immediately. This targets the client used by
        # this GENESIS run (8189 for RunPod), never the brother's 8188 client.
        client = self._active_client
        prompt_id = self._active_prompt_id
        if client is not None:
            def interrupt_active():
                # /interrupt stops the currently executing prompt; /queue delete
                # also removes this exact prompt if it is still pending. Keep
                # both scoped to the active GENESIS client/prompt only.
                try:
                    client.interrupt()
                except Exception:
                    pass
                if prompt_id:
                    try:
                        client.cancel([prompt_id])
                    except Exception:
                        pass
            threading.Thread(target=interrupt_active, daemon=True).start()

    def _abort_reason(self) -> str | None:
        if self._cancel_requested:
            return "Cancelled by user"
        if not remote_url():
            return integrations.gpu_kernel_abort_reason()
        return None

    def _check_cancelled(self) -> None:
        if self._cancel_requested:
            raise workflow_lab.ComfyError("Generation cancelled.")

    def _connect_comfyui(self):
        comfy_url = (remote_url() or workflow_lab.COMFY_URL).rstrip("/")
        remote_backend = comfy_url != workflow_lab.COMFY_URL.rstrip("/")
        if not remote_backend:
            safe, detail = integrations.gpu_kernel_preflight()
            if not safe:
                raise workflow_lab.ComfyError(detail)
            online = integrations.endpoint_online(
                integrations.COMFYUI_URL, "/system_stats", timeout=0.8
            )
            if not online and not local_start_allowed():
                raise workflow_lab.ComfyError("AUTO selected Local, but it went offline. Refresh backends and retry.")
            ok, detail = integrations.start_user_service(
                integrations.COMFYUI_SERVICE, already_online=online
            )
            if not ok:
                raise workflow_lab.ComfyError(detail)
        client = workflow_lab.ComfyClient(comfy_url, timeout=20)
        deadline = time.monotonic() + 30
        last_error = "backend not ready"
        if remote_backend:
            self._set_status("Connecting to RunPod ComfyUI…")
        while time.monotonic() < deadline:
            try:
                stats = client.system_stats()
                if workflow_lab.gpu_acceleration_available(stats):
                    return client, stats
                last_error = "GPU acceleration unavailable"
            except Exception as exc:
                last_error = str(exc)
            time.sleep(0.5)
        if remote_backend:
            raise workflow_lab.ComfyError(
                "RunPod ComfyUI is unavailable at the configured endpoint: " + last_error
            )
        raise workflow_lab.ComfyError(f"ComfyUI did not become GPU-ready: {last_error}")

    @pyqtProperty("QVariantList", notify=charactersChanged)
    def characters(self):
        return character_items()

    @pyqtSlot(str, str, bool, result=str)
    def createCharacterFromImage(self, name: str, source_url: str, adult_confirmed: bool) -> str:
        source = Path(QUrl(source_url).toLocalFile()) if source_url else Path()
        try:
            row = save_character(name, str(source), adult_confirmed=adult_confirmed)
        except ValueError as exc:
            self._set_status(str(exc))
            return ""
        self.charactersChanged.emit()
        self._set_status(f"Character saved · {row['name']}")
        return row["id"]

    @pyqtSlot(str, result=str)
    @pyqtSlot(str, str, result=str)
    def characterIdentitySource(self, character_id: str, role: str = "") -> str:
        source = preferred_reference(character_id, role)
        return QUrl.fromLocalFile(source).toString() if source else ""

    @pyqtSlot(str, str, str, result=bool)
    def addCharacterReference(self, character_id: str, source_url: str, role: str) -> bool:
        source = Path(QUrl(source_url).toLocalFile()) if source_url else Path()
        try:
            row = add_reference(character_id, str(source), role=role)
        except ValueError as exc:
            self._set_status(str(exc))
            return False
        self.charactersChanged.emit()
        self._set_status(f"Character anchor added · {row['name']} · {role or 'anchor'}")
        return True

    @pyqtSlot(str, str, str, str, result=bool)
    def importCharacterCandidate(self, character_id, source_url, angle, category):
        source = QUrl(source_url).toLocalFile()
        row = get_character(character_id) or {}
        if not source or str(Path(source).resolve()) in row.get("references", []):
            self._set_status("Choose a new candidate image; existing references stay unchanged.")
            return False
        try:
            add_reference(character_id, source, role=angle or "Generated candidate", category=category, approved=False)
        except ValueError as exc:
            self._set_status(str(exc))
            return False
        self.charactersChanged.emit()
        return True

    @pyqtSlot(str, str, result=str)
    def characterReferenceSource(self, character_id, instruction):
        from genesis.character_library import best_reference
        path = best_reference(character_id, instruction)
        return QUrl.fromLocalFile(path).toString() if path else ""

    @pyqtSlot(str, str, bool)
    def queueCharacterReferenceSet(self, character_id, model, adult_nsfw=False):
        if self._busy:
            return
        character = get_character(character_id)
        if not character or model not in SOURCE_EDIT_MODELS or model not in SUPPORTED_CREATE_MODELS:
            self._set_status("Select a saved character and a supported source-image model in Create.")
            return
        if adult_nsfw and not character.get("adult_confirmed", False):
            self._set_status("Adult NSFW reference mode requires a confirmed 18+ character.")
            return
        source = Path(character['primary_image'])
        if not source.is_file():
            self._set_status("The master reference is unavailable.")
            return
        try:
            route = self.backend_router.resolve(model) if self.backend_router else None
            if model in LOCAL_PENDING_KLEIN_MODELS and (route is None or route.destination != "RUNPOD"):
                raise ValueError("This model's local render is not verified; choose a supported model.")
        except ValueError as exc:
            self._set_status(str(exc))
            return
        self._cancel_requested = False
        self._finish_route = route
        self._set_busy(True)
        self._set_status("Preparing character reference set for review…")
        self._start_busy_worker(self._run_character_reference_set,
                                (route, character_id, source, model, adult_nsfw),
                                label="Character reference set")

    def _run_character_reference_set(self, route, character_id, source, model, adult_nsfw=False):
        from genesis.character_library import REFERENCE_BUILD_REQUESTS
        from contextlib import nullcontext
        try:
            with use_route(route) if route else nullcontext():
                defaults = model_generation_settings(model, source=True, remote=bool(remote_url()))
                controls = {key: defaults['default' + key.capitalize()] for key in ('steps', 'cfg', 'denoise', 'sampler', 'scheduler')}
                controls['seed'] = -1
                candidates = []
                for angle, category, instruction in REFERENCE_BUILD_REQUESTS:
                    self._check_cancelled()
                    if adult_nsfw:
                        instruction += " Adult 18+ character reference; mature nude anatomy permitted where supported by the selected model. Preserve identity, proportions, and neutral reference pose."
                    output = self._run_generate(instruction, "", defaults['defaultWidth'], defaults['defaultHeight'], model,
                        "None", "None", "None", 0, 0, 0, source, None, False, False, False, controls, release_busy=False)
                    if output is None:
                        return
                    candidates.append(output)
                    add_reference(character_id, str(output), role=angle, category=category, approved=False)
                    self.charactersChanged.emit()
                from genesis.reference_sheet import create_reference_sheet
                from genesis.character_library import save_reference_sheet
                sheet = create_reference_sheet(candidates, self._output_dir / ('GENESIS-ReferenceSheet-' + str(time.time_ns()) + '.png'))
                save_reference_sheet(character_id, str(sheet))
                self.charactersChanged.emit()
                self._set_status("Reference set and review sheet saved · candidates need review and approval.")
        except (ValueError, OSError, workflow_lab.ComfyError) as exc:
            self._set_status("Reference builder stopped · " + str(exc))
        finally:
            self._cancel_requested = False
            self._set_busy(False)

    def _snapshot_character_a(self):
        """Freeze character details before queuing so later selection cannot alter a job."""
        from copy import deepcopy
        character_id = self._character_a
        character = deepcopy(get_character(character_id) or {}) if character_id else {}
        master = preferred_reference(character_id) if character_id else ""
        return {"id": character_id, "data": character, "master": str(master or ""),
                "primary_image": str(character.get("primary_image") or "")}

    def _identity_master(self, master_url=""):
        if self._character_a:
            value = preferred_reference(self._character_a)
            return Path(value) if value else None
        row = next((r for r in self._finish_results if r['source'] == self._preview), None)
        if row and row.get('identitySource'):
            return Path(QUrl(row['identitySource']).toLocalFile())
        return self._original_master

    @pyqtSlot(str)
    def selectCharacterA(self, character_id):
        self._character_a = character_id
        self.charactersChanged.emit()

    @pyqtProperty(str, notify=charactersChanged)
    def selectedCharacterA(self):
        return self._character_a

    @pyqtSlot(str, str, str, bool, result=bool)
    def setCharacterReferenceDetails(self, character_id, image, category, approved):
        try:
            set_reference_details(character_id, image, category, approved)
        except ValueError as exc:
            self._set_status(str(exc))
            return False
        self.charactersChanged.emit()
        return True

    @pyqtSlot(str, str, str, str, result=bool)
    def updateCharacterReference(self, character_id, old_path, new_url, role):
        try:
            new_path = QUrl(new_url).toLocalFile() if new_url else ''
            update_reference(character_id, old_path, new_path, role=role)
        except ValueError as exc:
            self._set_status(str(exc))
            return False
        self.charactersChanged.emit()
        return True

    @pyqtProperty('QVariantList', notify=previewChanged)
    def finishingResults(self):
        return list(self._finish_results)

    @pyqtSlot(str)
    def selectFinishingResult(self, url):
        if not self._busy and any(r['source'] == url for r in self._finish_results):
            self._restore_finishing_context(url)
            self._set_preview(url)

    @pyqtSlot()
    def rejectFinishingResult(self):
        if self._busy:
            return
        row = next((r for r in self._finish_results if r['source'] == self._preview), None)
        if row and row.get('inputSource'):
            self._restore_finishing_context(row['inputSource'])
            self._set_preview(row['inputSource'])
            self._set_status('Rejected refinement · previous result selected; both files remain saved.')

    @pyqtSlot()
    def keepResult(self):
        if self._preview and Path(QUrl(self._preview).toLocalFile()).is_file():
            self._set_status('Kept · the selected result is already saved in your output folder.')

    @pyqtSlot(str, str, int, result='QVariantMap')
    def finishingAvailability(self, model, master_url, scale):
        result = dict(refine=False, identity=False, upscale=False, reason='Generate a result first.')
        if not self._preview or not Path(QUrl(self._preview).toLocalFile()).is_file() or not self._finish_info:
            return result
        # Remote refinement and upscaling require the original endpoint, but
        # local Person A correction must remain available on a saved image even
        # if RunPod disconnects after generation.
        remote_finish_ready = True
        if self._finish_route and self._finish_route.destination == "RUNPOD" and self.backend_router:
            remote_finish_ready = bool(self.backend_router._connected
                                       and self.backend_router._remote_status.get("ready")
                                       and self.backend_router._endpoint == self._finish_route.url)
        info = self._finish_info
        def available(workflow, override=None):
            try:
                validate_remote_workflow_assets(workflow, info, override)
                return True
            except (ValueError, OSError, workflow_lab.ComfyError):
                return False
        result['refine'] = bool(remote_finish_ready and model in REFINEMENT_MODELS
                                and available(remote_reference_workflow(model), model))
        master = self._identity_master(master_url)
        # The target is confirmed AFTER generation/finishing by the user.
        # Do not advertise availability using the unsafe legacy face-index graph.
        selected_swap = {"reactor_inswapper": "inswapper_128.onnx",
                         "reactor_reswapper": "reswapper_256.onnx",
                         "reactor_hyperswap": "hyperswap_1a_256.onnx"}.get(self._stage_three_engine)
        if self.backend_router is not None:
            # Face Lock runs locally even when refinement/generation is remote.
            local_status = getattr(self.backend_router, '_local_status', {})
            local_identity_ready = bool(getattr(self.backend_router, '_local_safe', False)
                                        and local_status.get('ready')
                                        and self._stage_three_engine in local_status.get('identityEngines', []))
        else:
            # Direct backend callers without a router retain the old local
            # catalog-based capability check for compatibility.
            local_identity_ready = bool(all(kind in info for kind in ('ReActorFaceSwapOpt','ReActorOptions'))
                                        and selected_swap in _remote_choice_values(info, ('ReActorFaceSwapOpt',), 'swap_model'))
        # FaceFusion is a standalone LOCAL processor, independent of local
        # ComfyUI/ReActor node readiness (e.g. after a RunPod generation).
        identity_ready = (self.faceFusionAvailable if self._stage_three_engine == "facefusion_nsfw"
                          else local_identity_ready)
        result['identity'] = bool(master and Path(master).is_file() and identity_ready)
        choices = _remote_choice_values(info, ('UpscaleModelLoader',), 'model_name')
        self._upscale_model = next((name for name in ('4x-UltraSharp.safetensors', '4x-UltraSharp.pth') if name in choices), '')
        result['upscale'] = bool(remote_finish_ready and scale in (2, 4)
                                  and all(n in info for n in ('LoadImage', 'UpscaleModelLoader', 'ImageUpscaleWithModel', 'ImageScaleBy', 'SaveImage'))
                                  and self._upscale_model)
        notes = []
        if not result['refine']:
            notes.append('Refine: selected compatible model or required nodes/assets unavailable.')
        if not result['identity']:
            notes.append("Face Lock: load an original Person A photo and connect ReActor Options/selected swap model. Face regions are reviewed after finishing.")
        if not result['upscale']:
            notes.append('Upscale: required nodes or 4× UltraSharp weights are missing on this backend.')
        result['reason'] = ' '.join(notes) or 'Finishing actions are ready.'
        return result

    @pyqtSlot(bool, bool, int, str, str, str, float)
    def queueFinish(self, refine, identity, scale, master_url, model, lora, strength):
        if self._busy:
            return
        try:
            plan = finishing_plan(refine, identity, scale)
            if not plan:
                raise ValueError('Choose a finishing action.')
            capabilities = self.finishingAvailability(model, master_url, scale or 2)
            if any(not capabilities[stage] for stage in plan):
                raise ValueError(capabilities['reason'])
            compatible_selection(model, [lora] if refine else [])
            if refine and uses_refcontrol(model, [lora]):
                raise ValueError('RefControl needs a separate pose; choose a detail adapter for finishing.')
            if not 0 <= strength <= 1:
                raise ValueError('LoRA strength must be between 0 and 1.')
            selected = Path(QUrl(self._preview).toLocalFile())
            master = self._identity_master(master_url)
        except ValueError as exc:
            self._set_status(str(exc))
            return
        self._set_busy(True)
        self._cancel_requested = False
        self._start_busy_worker(self._run_finish,
                                (selected, master, plan, scale, model, lora, strength),
                                label="Finishing")

    def _adopt_operation_result(self, path, info=None, master=None):
        """Keep finishing attached to this output's backend and dimensions."""
        self._finish_info = info or {}
        endpoint = remote_url() if info else ""
        self._finish_route = Route("RUNPOD", endpoint) if endpoint else (Route("LOCAL", "") if info else None)
        self._original_master = master
        self._finish_width, self._finish_height = 1024, 1024
        try:
            from PIL import Image
            with Image.open(path) as image:
                self._finish_width, self._finish_height = image.size
        except (OSError, ValueError):
            pass

    def _restore_finishing_context(self, url):
        context = self._finish_contexts.get(url, {})
        self._finish_info = context.get("info", {})
        self._finish_route = context.get("route")
        self._finish_width, self._finish_height = context.get("size", (1024, 1024))
        self._original_master = context.get("master")

    def _record_finish(self, stage, path, *, input_source=None):
        url = QUrl.fromLocalFile(str(path)).toString()
        # Recorded history must reflect the saved output, not the sampler size.
        from PIL import Image
        try:
            with Image.open(path) as image:
                self._finish_width, self._finish_height = image.size
        except (OSError, ValueError):
            pass
        self._finish_contexts[url] = {"info": self._finish_info, "route": self._finish_route,
                                      "size": (self._finish_width, self._finish_height), "master": self._original_master}
        if not any(r['source'] == url for r in self._finish_results):
            self._finish_results.append({'label': stage, 'source': url, 'inputSource': self._preview if input_source is None else input_source,
                                         'identitySource': QUrl.fromLocalFile(str(self._original_master)).toString() if self._original_master else ''})
        self._set_preview(url)

    def _refine_result(self, client, info, current, model, stamp, lora='None', strength=0.65, include_realism=True):
        if not remote_url() and model in {LOCAL_MIRACLEIN_9B_MODEL, LOCAL_PORNMASTER_9B_MODEL}:
            # Refinement must not inherit Stage 1's scene/pose replacement instructions.
            text = realism_prompt(
                REFINE_INSTRUCTION + " Keep the existing background, clothing, objects, camera angle,"
                " expression and lighting. Make only subtle detail corrections; do not add or replace content.",
                include_realism=include_realism,
            )
        else:
            text = adapt_prompt(REFINE_INSTRUCTION, model, source_image=True, include_realism=include_realism)
        if model in REMOTE_CHECKPOINT_MODELS:
            graph = build_create_prompt(info, text, self._finish_width, self._finish_height, model, [lora], [strength])
            uploaded = client.upload_image(current)
            graph['finish_source'] = {'class_type': 'LoadImage', 'inputs': {'image': '/'.join(v for v in (uploaded.get('subfolder'), uploaded.get('name')) if v)}}
            graph['finish_encode'] = {'class_type': 'VAEEncode', 'inputs': {'pixels': ['finish_source', 0], 'vae': ['1', 2]}}
            graph['5']['inputs'].update(latent_image=['finish_encode', 0], denoise=0.3)
            validate_operation_prompt(graph, info, 'Refine')
            return self._submit_and_save(client, graph, stamp, 'Refine')
        return self._run_reference_stage(client, info, remote_reference_workflow(model), current, text, stamp, 'Refine',
            model_override=model, controls={**remote_reference_controls(model), "width": self._finish_width, "height": self._finish_height}, loras=[lora], lora_strengths=[strength])

    def _run_finish(self, selected, master, plan, scale, model, lora, strength):
        try:
            self._original_master = master
            if list(plan) == ['identity']:
                # No remote client or image upload is required for an identity-
                # only finish. The saved result is passed to local Person A
                # selection; the local ReActor worker runs only after review.
                capabilities = self.finishingAvailability(model, '', scale or 2)
                if not capabilities['identity']:
                    raise ValueError(capabilities['reason'])
                if not (master and Path(master).is_file()):
                    raise ValueError('Person A source image is missing.')
                self._pending_stage_three = True
                self._set_status('Finishing saved · confirm Person A for local Face Lock…')
                self.stageThreeSelectionRequired.emit(str(selected), str(master))
                return
            with use_route(self._finish_route):
                if 'refine' in plan and not remote_url() and model not in LOCAL_SAFE_CREATE_MODELS:
                    raise ValueError('Local refinement is blocked; GPU/memory verification is pending. Choose RunPod.')
                client, _ = self._connect_comfyui()
                info = client.object_info()
                self._finish_info = info
                # Validate every requested stage against fresh backend metadata before submitting.
                capabilities = self.finishingAvailability(model, QUrl.fromLocalFile(str(master)).toString() if master else '', scale or 2)
                if any(not capabilities[stage] for stage in plan):
                    raise ValueError(capabilities['reason'])
                if 'refine' in plan and lora != 'None':
                    available_loras = _remote_choice_values(info, ('LoraLoader', 'LoraLoaderModelOnly'), 'lora_name')
                    if lora not in available_loras:
                        raise ValueError('The selected refinement LoRA is unavailable on this backend.')
                stamp = str(time.time_ns())
                def execute(stage, current, identity_source):
                    self._check_cancelled()
                    if stage == 'refine':
                        return self._refine_result(client, info, current, model, stamp, lora, strength)
                    if stage == 'identity':
                        raise ValueError('Person A confirmation must happen in the UI, not inside a background GPU worker.')
                    uploaded = client.upload_image(current)
                    graph = {
                        '1': {'class_type': 'LoadImage', 'inputs': {'image': '/'.join(v for v in (uploaded.get('subfolder'), uploaded.get('name')) if v)}},
                        '2': {'class_type': 'UpscaleModelLoader', 'inputs': {'model_name': self._upscale_model}},
                        '3': {'class_type': 'ImageUpscaleWithModel', 'inputs': {'upscale_model': ['2', 0], 'image': ['1', 0]}},
                        '4': {'class_type': 'ImageScaleBy', 'inputs': {'image': ['3', 0], 'upscale_method': 'lanczos', 'scale_by': scale / 4}},
                        '5': {'class_type': 'SaveImage', 'inputs': {'images': ['4', 0], 'filename_prefix': 'GENESIS-Finish'}}}
                    validate_operation_prompt(graph, info, 'Upscale')
                    return self._submit_and_save(client, graph, stamp, 'Upscale')
                # Face correction is last: the confirmed box must match the
                # actual final image, including after optional upscaling.
                steps = [step for step in plan if step != 'identity']
                results = run_finishing(selected, master, steps, execute, self._record_finish) if steps else [selected]
                final_image = results[-1]
                if 'identity' in plan:
                    if not (master and Path(master).is_file()):
                        raise ValueError('Person A source image was not found. Intermediate results remain saved.')
                    self._pending_stage_three = True
                    self._set_status('Finishing saved · confirm Person A for Face Lock…')
                    self.stageThreeSelectionRequired.emit(str(final_image), str(master))
                else:
                    self._set_status('Finishing complete · every intermediate is saved.')
        except Exception as exc:
            self._set_status('Finishing stopped · ' + str(exc))
        finally:
            self._cancel_requested = False
            if not self._pending_stage_three:
                self._set_busy(False)

    @pyqtSlot("QVariantMap", str, result="QVariantMap")
    def posePresetPayload(self, row, model):
        return preset_payload(row, model)

    @pyqtProperty(str, notify=previewChanged)
    def videoUrl(self):
        return getattr(self, '_video_url', '')

    @pyqtProperty('QVariantMap', notify=statusChanged)
    def wanAvailability(self):
        from genesis.wan_video import availability, LORA_14B
        return availability(getattr(self, '_wan_info', {}), self.wanModel,
                            LORA_14B if self.wanAdapterEnabled else None)

    @pyqtProperty(str, notify=statusChanged)
    def wanModel(self):
        from genesis.wan_video import MODEL
        return getattr(self, '_wan_model', os.environ.get('GENESIS_WAN_MODEL', MODEL))

    @pyqtProperty(bool, notify=statusChanged)
    def wanAdapterEnabled(self):
        from genesis.wan_video import MODEL_14B
        return self.wanModel == MODEL_14B and getattr(self, '_wan_adapter_enabled', os.environ.get('GENESIS_WAN_14B_ADAPTER') == '1')

    @pyqtSlot(str)
    def setWanModel(self, model):
        from genesis.wan_video import MODEL, MODEL_14B
        if self._busy or model not in {MODEL, MODEL_14B}: return
        self._wan_model = model
        if model == MODEL: self._wan_adapter_enabled = False
        self._set_status(self.wanAvailability['reason'])

    @pyqtSlot(bool)
    def setWanAdapter(self, enabled):
        from genesis.wan_video import MODEL_14B
        if self._busy: return
        self._wan_adapter_enabled = bool(enabled) and self.wanModel == MODEL_14B
        self._set_status(self.wanAvailability['reason'])

    @pyqtSlot()
    def refreshWan(self):
        if self._busy: return
        def check():
            try:
                url = remote_url()
                if not url or urllib.parse.urlparse(url).port == 8188:
                    raise ValueError('Select the user RunPod 8189 connection.')
                from genesis.comfy_client import ComfyClient
                self._wan_info = ComfyClient(url).object_info()
                self._set_status(self.wanAvailability['reason'])
            except Exception as exc: self._set_status('Wan check: ' + str(exc))
        threading.Thread(target=check, daemon=True).start()

    @pyqtSlot(str, str, int, int)
    def queueWanVideo(self, source_url, motion, frames, seed):
        if self._busy: return
        source = Path(QUrl(source_url).toLocalFile())
        if not source.is_file():
            self._set_status('Choose a source image for video.'); return
        url = remote_url()
        if not url or urllib.parse.urlparse(url).port == 8188:
            self._set_status('Select the user RunPod 8189 connection.'); return
        self._set_busy(True); self._cancel_requested = False
        def execute():
            try:
                from genesis.wan_video import availability, build_prompt, MODEL_14B, LORA_14B
                from genesis.comfy_client import ComfyClient
                client = ComfyClient(url); info = client.object_info()
                selected_model = self.wanModel
                selected_lora = LORA_14B if self.wanAdapterEnabled else None
                ready = availability(info, selected_model, selected_lora)
                if not ready['ready']: raise ValueError(ready['reason'])
                uploaded = client.upload_image(source)
                image = '/'.join(v for v in (uploaded.get('subfolder'), uploaded.get('name')) if v)
                graph = build_prompt(image, motion, width=832 if selected_model==MODEL_14B else 640, height=480 if selected_model==MODEL_14B else 384, frames=frames, seed=seed if seed >= 0 else random.randrange(2**31), model=selected_model, lora=selected_lora)
                validate_operation_prompt(graph, info, 'Wan video')
                self._set_status('Wan image-to-video running…')
                result = client.wait(client.submit(graph), timeout=3600, abort_check=lambda: 'Cancelled by user' if self._cancel_requested else None)
                if result.status != 'completed': raise ValueError(result.error or result.status)
                saved = []
                self._output_dir.mkdir(parents=True, exist_ok=True)
                for output in result.outputs:
                    if Path(output.get('filename','')).suffix.lower() != '.mp4': continue
                    path = self._output_dir / ('GENESIS-Wan-' + str(time.time_ns()) + '.mp4')
                    path.write_bytes(client.view(output)); saved.append(path)
                if not saved: raise ValueError('Wan finished without an MP4 output.')
                self._video_url = QUrl.fromLocalFile(str(saved[-1])).toString(); self.previewChanged.emit()
                self._set_status('Wan video saved · original source preserved.')
            except Exception as exc: self._set_status('Wan stopped · ' + str(exc))
            finally: self._set_busy(False)
        self._start_busy_worker(execute, label="Wan video")

    @pyqtSlot()
    def openWanVideo(self):
        if self.videoUrl: QDesktopServices.openUrl(QUrl(self.videoUrl))

    @pyqtSlot(result=str)
    def chooseSourceImage(self) -> str:
        from genesis.qt_media_picker import choose_image
        selected = choose_image("GENESIS · Choose a source image")
        return QUrl.fromLocalFile(selected).toString() if selected else ""

    @pyqtSlot(result=str)
    def chooseResultImage(self) -> str:
        from genesis.qt_media_picker import choose_image
        selected = choose_image("GENESIS · Saved results", folder=str(OUTPUT_DIR))
        return QUrl.fromLocalFile(selected).toString() if selected else ""

    def _operation_route(self, operation):
        return self.backend_router.resolve_operation(operation) if self.backend_router else None

    def _person_a_face_swap_route(self):
        # NSFW FaceFusion is a standalone LOCAL process. It must never depend
        # on RunPod or an online ComfyUI/ReActor server to handle face crops.
        engine = self._active_stage_three_engine or self._stage_three_engine
        if engine == "facefusion_nsfw":
            if not self.faceFusionAvailable:
                raise ValueError("Local NSFW FaceFusion runtime is unavailable.")
            return Route("LOCAL", "")
        return self._operation_route("face_swap") or Route("LOCAL", "")

    def _run_routed_operation(self, route, operation, *args):
        if route is None:
            return operation(*args)
        with use_route(route):
            self._set_status(f"{route.destination} · preparing operation…")
            return operation(*args)

    @pyqtSlot(str, str)
    def queueFaceSwap(self, target_url: str, source_url: str) -> None:
        """Run the isolated two-image ReActor route for ordinary images."""
        if self._busy:
            return
        self._active_stage_three_engine = None  # manual swap uses current UI choice
        target = Path(QUrl(target_url).toLocalFile()) if target_url else Path()
        source = Path(QUrl(source_url).toLocalFile()) if source_url else Path()
        if not target.is_file() or not source.is_file():
            self._set_status("Choose both a target image and a source image.")
            return
        try:
            route = self._person_a_face_swap_route()
            if route.destination != 'LOCAL':
                raise ValueError('Face swapping is local-only; RunPod cannot be selected.')
        except ValueError as exc:
            self._set_status(str(exc))
            return
        from genesis.person_a_targeting import choose_face_region
        try:
            target_region = choose_face_region(target, "target")
            if target_region is None:
                self._set_status("Face swap cancelled; no target confirmed.")
                return
            source_region = choose_face_region(source, "source")
            if source_region is None:
                self._set_status("Face swap cancelled; no source confirmed.")
                return
        except (OSError, ValueError) as exc:
            self._set_status("Face selection failed · " + str(exc))
            return
        self._cancel_requested = False
        self._set_busy(True)
        self._set_status("Preparing verified Person A regions…")
        self._start_busy_worker(self._run_routed_operation,
                                (route, self._run_face_swap, target, source,
                                 (target_region, source_region)),
                                label="Face swap")

    @pyqtSlot(str, str)
    def _choose_stage_three_faces(self, target_path, source_path):
        """GUI-only Person A confirmation after the generation is saved.

        No automatic face index or scene-wide swap. The confirmation dialog
        runs in the Qt event loop. Swapping is local-only even if the image
        was originally generated on a RunPod backend.
        """
        if not self._pending_stage_three:
            return
        if self._cancel_requested:
            self._pending_stage_three = False
            self._set_status("Generation saved · Stage 3 cancelled.")
            self._set_busy(False)
            return
        from genesis.person_a_targeting import choose_face_region
        target, source = Path(target_path), Path(source_path)
        started = False
        try:
            if not target.is_file() or not source.is_file():
                raise ValueError("saved output or original identity source is missing")
            face_route = self._person_a_face_swap_route()
            if face_route.destination != 'LOCAL':
                raise ValueError('Face swapping is local-only; RunPod cannot be selected.')
            self._set_status("Stage 3 · select Person A in the generated image…")
            target_region = choose_face_region(target, "generated target · Person A")
            if self._cancel_requested:
                self._set_status("Generation saved · Stage 3 cancelled.")
                return
            if target_region is None:
                self._set_status("Generation saved · Stage 3 skipped (target face not confirmed).")
                return
            self._set_status("Stage 3 · select Person A in the original photo…")
            source_region = choose_face_region(source, "original source · Person A")
            if self._cancel_requested:
                self._set_status("Generation saved · Stage 3 cancelled.")
                return
            if source_region is None:
                self._set_status("Generation saved · Stage 3 skipped (source face not confirmed).")
                return
            # Both paths and pixel digests were reviewed by the user.
            target_region.checked_image(target)
            source_region.checked_image(source)
            if self._cancel_requested:
                self._set_status("Generation saved · Stage 3 cancelled.")
                return
            self._set_status("Stage 3 · correcting the reviewed Person A face only…")
            thread = threading.Thread(
                target=self._run_routed_operation,
                args=(face_route, self._run_face_swap, target, source,
                      (target_region, source_region)),
                daemon=True,
            )
            thread.start()
            started = True
        except (OSError, ValueError, RuntimeError) as exc:
            # Thread.start() can raise RuntimeError before any worker exists;
            # keep the saved image and release Busy for later queued jobs.
            self._set_status("Generation saved · Stage 3 selection failed · " + str(exc))
        finally:
            self._pending_stage_three = False
            if not started:
                self._cancel_requested = False
                self._set_busy(False)

    def _run_local_facefusion_command(self, command, *, cwd: Path, timeout: float):
        """Run a cancellable, isolated FaceFusion process without GPU/RunPod handoff.

        Plain subprocess.run hides its child until return; Cancel previously left
        a swap running for up to 30 minutes and could then adopt its output.
        Track only our own process session, and tear down its children on
        cancellation or timeout. Never signal another GENESIS/ComfyUI worker.
        """
        self._check_cancelled()
        process = subprocess.Popen(
            command, cwd=str(cwd), stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True,
            start_new_session=(os.name == "posix"),
        )
        started = time.monotonic()
        completed = False
        try:
            while True:
                self._check_cancelled()
                remaining = float(timeout) - (time.monotonic() - started)
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, timeout)
                try:
                    output, _ = process.communicate(timeout=min(0.25, remaining))
                except subprocess.TimeoutExpired:
                    continue
                self._check_cancelled()
                completed = True
                return subprocess.CompletedProcess(command, process.returncode, stdout=output)
        finally:
            if not completed:
                # A wrapper can exit before its helper process. Its descendants
                # may still hold stdout open, so communicate() can time out even
                # though process.poll() has already returned an exit code.
                # Always signal the unique session created for this job on POSIX;
                # never signal other GENESIS/ComfyUI processes by name.
                try:
                    if os.name == "posix":
                        os.killpg(process.pid, signal.SIGTERM)
                    elif process.poll() is None:
                        process.terminate()
                except ProcessLookupError:
                    pass
                try:
                    process.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    try:
                        if os.name == "posix":
                            os.killpg(process.pid, signal.SIGKILL)
                        elif process.poll() is None:
                            process.kill()
                    except ProcessLookupError:
                        pass
                    process.communicate(timeout=2)

    def _run_face_swap(self, target: Path, source: Path, regions=None) -> None:
        try:
            # Defense in depth: no caller can upload face crops over RunPod.
            if remote_url():
                raise workflow_lab.ComfyError('Face swapping is local-only; remote uploads are blocked.')
            import tempfile
            from genesis.person_a_targeting import prepare_crops, composite_crop
            # No fallback to full-frame index 0. Verify image digests before upload.
            self._check_cancelled()
            with tempfile.TemporaryDirectory(prefix="genesis-person-a-") as directory:
                target_crop, source_crop = prepare_crops(target, source, regions, directory)
                if (self._active_stage_three_engine or self._stage_three_engine) == "facefusion_nsfw":
                    # Exact two confirmed Person A regions only; no remote
                    # backend and no full-frame fallback, unlike manual bulk
                    # face swaps. The input image is never overwritten.
                    ff_root = integrations.FACEFUSION_ROOT
                    ff_python = self._facefusion_python()
                    ff_entry = ff_root / "facefusion.py"
                    ff_config = ff_root / "facefusion.ini"
                    if not all(path.is_file() for path in (ff_python, ff_entry, ff_config)):
                        raise workflow_lab.ComfyError("Local NSFW FaceFusion runtime is unavailable.")
                    provider = self._facefusion_provider
                    if provider != "cpu":
                        safe, detail = integrations.gpu_kernel_preflight()
                        if not safe:
                            raise workflow_lab.ComfyError(detail)
                    swapped = Path(directory) / "facefusion-result.png"
                    command = [
                        str(ff_python), str(ff_entry), "headless-run",
                        "--config-path", str(ff_config),
                        "--source-paths", str(source_crop),
                        "--target-path", str(target_crop),
                        "--output-path", str(swapped),
                        "--processors", "face_swapper",
                        "--face-swapper-model", "inswapper_128",
                        "--face-selector-mode", "one",
                        "--execution-providers", provider,
                    ]
                    completed = self._run_local_facefusion_command(
                        command, cwd=ff_root, timeout=300,
                    )
                    if completed.returncode or not swapped.is_file():
                        details = "\n".join((completed.stdout or "").splitlines()[-8:])
                        raise workflow_lab.ComfyError(details or "Local NSFW FaceFusion did not save an image.")
                    self._check_cancelled()
                    self._check_cancelled()
                    self._output_dir.mkdir(parents=True, exist_ok=True)
                    stamp = str(time.time_ns())
                    current = composite_crop(
                        target, regions[0], swapped,
                        self._output_dir / f"GENESIS-FaceFusion-PersonA-{stamp}.png",
                    )
                    # Preserve the generation/refinement route on saved output;
                    # only this local face correction has a local route.
                    previous_preview = Path(QUrl(self._preview).toLocalFile()) if self._preview else None
                    if not (self._finish_info and previous_preview == target):
                        self._adopt_operation_result(current, {}, source)
                    else:
                        self._original_master = source
                    self._record_finish("NSFW FaceFusion · Person A", current,
                                        input_source=QUrl.fromLocalFile(str(target)).toString())
                    self._set_status(f"Complete · {current.name} · reviewed Person A region only.")
                    return
                client, _ = self._connect_comfyui()
                info = client.object_info()
                required = ("ReActorFaceSwapOpt", "ReActorOptions")
                if any(kind not in info for kind in required):
                    raise workflow_lab.ComfyError("Manual Person A swap requires ReActor Options on this backend.")
                swap_model = {"reactor_inswapper": "inswapper_128.onnx",
                              "reactor_reswapper": "reswapper_256.onnx",
                              "reactor_hyperswap": "hyperswap_1a_256.onnx"}.get(
                                  self._active_stage_three_engine or self._stage_three_engine)
                if swap_model not in _remote_choice_values(info, ("ReActorFaceSwapOpt",), "swap_model"):
                    raise workflow_lab.ComfyError("Selected ReActor swap model is unavailable.")
                def upload(path):
                    self._check_cancelled()
                    result = client.upload_image(path)
                    return "/".join(v for v in (result.get("subfolder"), result.get("name")) if v)
                prompt = {
                    "target": {"class_type": "LoadImage", "inputs": {"image": upload(target_crop)}},
                    "source": {"class_type": "LoadImage", "inputs": {"image": upload(source_crop)}},
                    "options": {"class_type": "ReActorOptions", "inputs": {
                        "input_faces_order": "left-right", "input_faces_index": "0", "detect_gender_input": "no",
                        "source_faces_order": "left-right", "source_faces_index": "0", "detect_gender_source": "no",
                        "console_log_level": 1, "restore_swapped_only": True}},
                    "swap": {"class_type": "ReActorFaceSwapOpt", "inputs": {
                        "enabled": True, "input_image": ["target", 0], "source_image": ["source", 0],
                        "swap_model": swap_model, "facedetection": "retinaface_resnet50",
                        "face_restore_model": "none", "face_restore_visibility": 1.0,
                        "codeformer_weight": 0.5, "options": ["options", 0]}},
                    "save": {"class_type": "SaveImage", "inputs": {
                        "images": ["swap", 0], "filename_prefix": "GENESIS-PersonA-Crop"}},
                }
                validate_operation_prompt(prompt, info, "Manual Person A")
                self._check_cancelled()
                stamp = str(time.time_ns())
                swapped = self._submit_and_save(client, prompt, stamp, "PersonA-Crop")
                current = composite_crop(target, regions[0], swapped,
                                         self._output_dir / f"GENESIS-PersonA-{stamp}.png")
                self._adopt_operation_result(current, info, source)
                self._record_finish("Face Lock · Person A", current, input_source=QUrl.fromLocalFile(str(target)).toString())
                self._set_status(f"Complete · {current.name} · only the reviewed target area changed.")
        except Exception as exc:
            self._set_status("Face swap cancelled · saved image preserved." if self._cancel_requested
                             else f"Face swap failed · {exc}")
        finally:
            self._cancel_requested = False
            self._set_busy(False)

    @pyqtSlot(str, str)
    def queueFaceFusion(self, target_url: str, source_url: str) -> None:
        """Run the installed FaceFusion headlessly with the existing tuned config."""
        if self._busy:
            return
        target = Path(QUrl(target_url).toLocalFile()) if target_url else Path()
        source = Path(QUrl(source_url).toLocalFile()) if source_url else Path()
        if not target.is_file() or not source.is_file():
            self._set_status("Choose both a target image and a source image.")
            return

        if self.backend_router is not None and self.backend_router.mode != 'LOCAL':
            self._set_status("FaceFusion is local image-only. Select LOCAL explicitly to run it; RunPod video is not connected.")
            return
        ff_root = integrations.FACEFUSION_ROOT
        ff_python = self._facefusion_python()
        ff_entry = ff_root / "facefusion.py"
        ff_config = ff_root / "facefusion.ini"
        if not ff_python.is_file() or not ff_entry.is_file() or not ff_config.is_file():
            self._set_status("FaceFusion install is unavailable.")
            return

        if self._facefusion_provider != 'cpu':
            safe, detail = integrations.gpu_kernel_preflight()
            if not safe:
                self._set_status(detail)
                return
        self._cancel_requested = False
        self._set_busy(True)
        self._set_status("Preparing FaceFusion · local image swap…")
        self._start_busy_worker(self._run_facefusion,
                                (target, source, ff_python, ff_entry, ff_config),
                                label="FaceFusion")

    def _run_facefusion(
        self, target: Path, source: Path, ff_python: Path, ff_entry: Path, ff_config: Path
    ) -> None:
        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            if self._facefusion_provider == 'migraphx':
                probe = self._run_local_facefusion_command([str(ff_python), '-c',
                    "import ctypes,sys; from pathlib import Path; import onnxruntime as ort; "
                    "lib=ctypes.CDLL('/opt/rocm/lib/libamdhip64.so'); n=ctypes.c_int(); "
                    "status=lib.hipGetDeviceCount(ctypes.byref(n)); "
                    "sys.exit('AMD GPU is not accessible to this process') if status or n.value<1 else None; "
                    "session=ort.InferenceSession('.assets/models/hyperswap_1a_256.onnx',providers=['MIGraphXExecutionProvider']); "
                    "sys.exit('MIGraphX failed; CPU fallback is not allowed in GPU mode') if session.get_providers()[0]!='MIGraphXExecutionProvider' else None"],
                    cwd=ff_entry.parent, timeout=300)
                if probe.returncode:
                    raise RuntimeError((probe.stdout or 'AMD GPU preflight failed').strip().splitlines()[-1])
            stamp = str(time.time_ns())
            suffix = target.suffix.lower() if target.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} else ".png"
            output = self._output_dir / f"GENESIS-FaceFusion-{stamp}{suffix}"
            command = [
                str(ff_python), str(ff_entry), "headless-run",
                "--config-path", str(ff_config),
                "--source-paths", str(source.resolve()),
                "--target-path", str(target.resolve()),
                "--output-path", str(output.resolve()),
                "--workflow-mode", "image-to-image",
                "--execution-providers", self._facefusion_provider,
            ]
            completed = self._run_local_facefusion_command(
                command, cwd=integrations.FACEFUSION_ROOT, timeout=1800,
            )
            if completed.returncode != 0 or not output.is_file():
                tail = "\n".join((completed.stdout or "").splitlines()[-8:])
                raise RuntimeError(tail or f"FaceFusion exited with code {completed.returncode}")
            # User cancellation always wins over a completed result.
            self._check_cancelled()
            self._adopt_operation_result(output, master=source)
            self._record_finish("FaceFusion", output, input_source=QUrl.fromLocalFile(str(target)).toString())
            self._set_status(f"FaceFusion complete · {output.name}")
        except subprocess.TimeoutExpired:
            self._set_status("FaceFusion timed out.")
        except Exception as exc:
            self._set_status("FaceFusion cancelled · original image preserved." if self._cancel_requested
                             else f"FaceFusion failed · {exc}")
        finally:
            self._cancel_requested = False
            self._set_busy(False)

    @pyqtSlot(str)
    def setStageTwoModel(self, model_name: str) -> None:
        if model_name in REFINEMENT_MODELS:
            self._stage_two_model = model_name

    @pyqtSlot(str)
    def setStageThreeEngine(self, engine: str) -> None:
        # Keep the engine fixed throughout generation and Person A confirmation.
        # The UI also disables this picker while busy.
        if self._busy:
            return
        if engine in {"reactor_inswapper", "reactor_reswapper", "reactor_hyperswap", "facefusion_nsfw"} and engine != self._stage_three_engine:
            self._stage_three_engine = engine
            self.statusChanged.emit()

    @pyqtProperty(str, notify=statusChanged)
    def outputFolder(self) -> str:
        return str(self._output_dir)

    @pyqtSlot(result=str)
    def chooseOutputFolder(self) -> str:
        path = QFileDialog.getExistingDirectory(
            None, "Choose GENESIS output folder", str(self._output_dir),
            QFileDialog.Option.ShowDirsOnly,
        )
        if path:
            self._output_dir = Path(path).expanduser()
            self._settings.setValue("generation/output_dir", str(self._output_dir))
            self._settings.sync()
            self._set_status(f"Output folder · {self._output_dir}")
        return str(self._output_dir)

    @pyqtSlot()
    def openOutputFolder(self) -> None:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._output_dir))):
            self._set_status("Could not open the selected output folder.")

    @pyqtSlot()
    def showPreviewInFolder(self) -> None:
        source = Path(QUrl(self._preview).toLocalFile())
        if not self._preview or not source.is_file():
            self._set_status("No generated preview is available yet.")
            return
        try:
            subprocess.Popen(["xdg-open", str(source.parent)], start_new_session=True)
        except OSError as exc:
            self._set_status(f"Could not show the generated image folder · {exc}")

    @pyqtSlot()
    def openPreview(self) -> None:
        source = Path(QUrl(self._preview).toLocalFile())
        if not self._preview or not source.is_file():
            self._set_status("No generated preview is available yet.")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(source))):
            self._set_status("Could not open the generated image.")

    @pyqtSlot(str, str, int, int, str, str, str, str, str, bool, bool, bool, name="queueGenerate")
    def queueGenerateLegacy(
        self, prompt_text, negative_prompt, width, height, model_name,
        lora_one, lora_two, source_url, pose_url,
        use_stage_two, use_stage_three, use_upscale,
    ) -> None:
        """Preserve the original QML pose-button contract and model defaults."""
        strength = 0.5 if model_name == FOUR_B_MODEL else 0.65
        self.queueGenerate(
            prompt_text, negative_prompt, width, height, model_name,
            lora_one, lora_two, "None", strength, strength, strength,
            source_url, pose_url, use_stage_two, use_stage_three, use_upscale,
        )

    @pyqtSlot(bool, float)
    def setSdxlFaceID(self, enabled, strength):
        self._sdxl_faceid_enabled = bool(enabled)
        self._sdxl_faceid_strength = float(strength)

    @pyqtProperty("QVariantList", notify=queueChanged)
    def pendingGenerations(self):
        return [{"label": item["label"], "model": item["model"],
                 "output": item["output"]} for item in self._pending_generations]

    @pyqtProperty(int, notify=queueChanged)
    def pendingGenerationCount(self):
        return len(self._pending_generations)

    @pyqtSlot(int)
    def setOutputTarget(self, long_edge):
        self._output_target_long_edge = int(long_edge) if int(long_edge) in (2560, 3840) else 0

    @pyqtSlot(float)
    def setSourceReferenceMegapixels(self, megapixels):
        value = float(megapixels)
        self._source_reference_megapixels = value if 0.0 < value <= 1.0 else 0.0

    @pyqtSlot(str)
    def setExtraReferenceSource(self, url):
        # A user-selected optional Phr00t reference, saved with each queued job.
        self._extra_reference_url = str(url or "")

    @pyqtSlot()
    def clearPendingGenerations(self):
        self._pending_generations.clear()
        self.queueChanged.emit()
        self._set_status("Waiting jobs cleared; active generation was left running.")

    @pyqtSlot(int)
    def removePendingGeneration(self, index):
        if 0 <= index < len(self._pending_generations):
            self._pending_generations.pop(index)
            self.queueChanged.emit()

    @pyqtSlot(str, str, int, int, str, str, str, str, str, bool, bool, bool, int, float, int, float, str, str, str, float, float, float)
    def enqueueGenerateAdvanced(self, *args):
        """Snapshot a full job, rather than reading changing QML fields later."""
        if len(self._pending_generations) >= 25:
            self._set_status("GENESIS queue is full (25 waiting jobs).")
            return
        model=args[4]
        if model not in SUPPORTED_CREATE_MODELS:
            self._set_status("The selected model has no configured generation route.")
            return
        try:
            pinned_route = self.backend_router.resolve(model) if self.backend_router else None
        except ValueError as exc:
            self._set_status("Cannot queue without a ready backend: " + str(exc))
            return
        job={"args": tuple(args), "model": model,
             "label": (str(args[0])[:58] or model),
             "output": self._output_target_long_edge,
             "source_reference_megapixels": self._source_reference_megapixels,
             "extra_reference_url": self._extra_reference_url,
             "faceid": (bool(getattr(self,'_sdxl_faceid_enabled',False)),float(getattr(self,'_sdxl_faceid_strength',0.8))),
             "stage2": self._stage_two_model,
             "stage3_engine": self._stage_three_engine,
             "route": pinned_route,
             "character_snapshot": self._snapshot_character_a(),
             "endpoint": (self.backend_router.mode,self.backend_router.endpoint) if self.backend_router else None}
        self._pending_generations.append(job)
        self.queueChanged.emit()
        self._set_status(f"Queued {model} · {len(self._pending_generations)} waiting")
        self._dispatch_next_generation()

    @pyqtSlot()
    def _queue_busy_transition(self):
        if not self._busy:
            self._queue_active = False
            self._active_stage_three_engine = None
            self._dispatch_next_generation()

    def _dispatch_next_generation(self):
        if self._busy or self._queue_active:
            return
        while self._pending_generations:
            job=self._pending_generations.pop(0)
            self.queueChanged.emit()
            current=(self.backend_router.mode,self.backend_router.endpoint) if self.backend_router else None
            try:
                resolved_route = self.backend_router.resolve(job["model"]) if self.backend_router else None
            except ValueError:
                resolved_route = None
            if current != job["endpoint"] or resolved_route != job["route"]:
                self._set_status("Skipped queued job: original resolved backend is no longer ready. Requeue explicitly.")
                continue
            # queueGenerateAdvanced captures settings synchronously into
            # generation_controls before launching its worker. Never leave a
            # past job's controls in the bridge fields used by later manual
            # jobs; the UI may already have selected different settings.
            ui_settings = (self._sdxl_faceid_enabled, self._sdxl_faceid_strength,
                           self._stage_two_model, self._output_target_long_edge,
                           self._source_reference_megapixels, self._extra_reference_url)
            self._queue_active=True
            self._sdxl_faceid_enabled,self._sdxl_faceid_strength=job["faceid"]
            self._stage_two_model=job["stage2"]
            self._active_stage_three_engine=job["stage3_engine"]
            self._output_target_long_edge=job["output"]
            self._source_reference_megapixels=job["source_reference_megapixels"]
            self._extra_reference_url=job["extra_reference_url"]
            self._queued_route_override = job["route"]
            self._queued_character_override = job["character_snapshot"]
            try:
                self.queueGenerateAdvanced(*job["args"])
            except Exception as exc:
                # Unexpected synchronous launch failures must not strand the
                # pending queue. Do not touch an already-running worker.
                self._set_status(f"Queued generation could not start · {exc}")
            finally:
                (self._sdxl_faceid_enabled, self._sdxl_faceid_strength,
                 self._stage_two_model, self._output_target_long_edge,
                 self._source_reference_megapixels, self._extra_reference_url) = ui_settings
                self._queued_route_override = None
                self._queued_character_override = None
            if self._busy:
                return
            self._queue_active=False
            self._active_stage_three_engine=None

    @pyqtSlot(str, str, int, int, str, str, str, str, str, bool, bool, bool, int, float, int, float, str, str, str, float, float, float)
    @pyqtSlot(str, str, int, int, str, str, str, str, str, bool, bool, bool, int, float, int, float, str, str)
    def queueGenerateAdvanced(
        self, prompt_text, negative_prompt, width, height, model_name,
        lora_one, lora_two, source_url, pose_url,
        use_stage_two, use_stage_three, use_upscale,
        steps, cfg, seed, denoise, sampler, scheduler,
        lora_three="None", strength_one=None, strength_two=None, strength_three=None,
    ) -> None:
        # SDXL should render at its native ~1 MP working size. 2K/4K are
        # finishing targets, not native KSampler sizes; sending 2048/4096
        # directly makes the shared A100 do 4x/16x the pixel work. Preserve
        # the requested aspect ratio while constraining only SDXL.
        requested_width, requested_height = int(width), int(height)
        if model_name in REMOTE_CHECKPOINT_MODELS and max(requested_width, requested_height) > 1536:
            scale = (1024 * 1024 / float(requested_width * requested_height)) ** 0.5
            width = max(64, int(round(requested_width * scale / 64.0)) * 64)
            height = max(64, int(round(requested_height * scale / 64.0)) * 64)
        self._next_generation_controls = {
            "faceid_enabled": bool(getattr(self, "_sdxl_faceid_enabled", False)),
            "faceid_strength": float(getattr(self, "_sdxl_faceid_strength", 0.8)),
            "steps": max(1, int(steps)),
            "cfg": max(0.0, float(cfg)),
            "seed": int(seed),
            "denoise": max(0.0, min(1.0, float(denoise))),
            "sampler": str(sampler),
            "scheduler": str(scheduler),
            "width": int(width),
            "height": int(height),
            "output_long_edge": int(getattr(self, "_output_target_long_edge", 0)),
            "source_reference_megapixels": self._source_reference_megapixels,
            "extra_reference_url": self._extra_reference_url,
            "character_snapshot": (self._queued_character_override if self._queue_active
                                   else self._snapshot_character_a()),
        }
        strength = 0.5 if model_name == FOUR_B_MODEL else 0.65
        controls = self._next_generation_controls
        try:
            self.queueGenerate(
                prompt_text, negative_prompt, int(width), int(height), model_name,
                lora_one, lora_two, lora_three,
                strength if strength_one is None else strength_one,
                strength if strength_two is None else strength_two,
                strength if strength_three is None else strength_three,
                source_url, pose_url, use_stage_two, use_stage_three, use_upscale,
            )
        finally:
            # Rejected/aborted requests never leave controls that a later
            # legacy/manual generation could accidentally pick up.
            if self._next_generation_controls is controls:
                self._next_generation_controls = None

    @pyqtSlot(str, str, int, int, str, str, str, str, float, float, float, str, str, bool, bool, bool)
    def queueGenerate(
        self,
        prompt_text: str,
        negative_prompt: str,
        width: int,
        height: int,
        model_name: str,
        lora_one: str,
        lora_two: str,
        lora_three: str,
        lora_one_strength: float,
        lora_two_strength: float,
        lora_three_strength: float,
        source_url: str,
        pose_url: str,
        use_stage_two: bool,
        use_stage_three: bool,
        use_upscale: bool,
    ) -> None:
        if self._busy:
            return
        prompt_text = prompt_text.strip()
        if not prompt_text:
            self._set_status("Enter a prompt before generating.")
            return
        if model_name not in SUPPORTED_CREATE_MODELS:
            self._set_status("That model has no validated Create workflow yet.")
            return
        source = Path(QUrl(source_url).toLocalFile()) if source_url else None
        pose = Path(QUrl(pose_url).toLocalFile()) if pose_url else None
        if source_url and (source is None or not source.is_file()):
            self._set_status("The selected source image is unavailable.")
            return
        if pose_url and (pose is None or not pose.is_file()):
            self._set_status("The selected pose/control image is unavailable.")
            return
        extra_reference_url = str(getattr(self, "_extra_reference_url", "") or "")
        if extra_reference_url:
            extra = Path(QUrl(extra_reference_url).toLocalFile())
            if (model_name not in ({QWEN_MODEL} | REMOTE_PHR00T_MODELS)
                    or source is None or not extra.is_file()
                    or extra.resolve() in {source.resolve(), *( [pose.resolve()] if pose else [] )}):
                self._set_status("Phr00t extra reference requires a separate valid image and Source Image mode.")
                return
        if model_name in ({QWEN_MODEL} | REMOTE_PHR00T_MODELS) and source is None and pose is not None:
            self._set_status("Phr00t Text to Image needs no image references. Clear the pose, or enable Image to Image and load a source.")
            return
        if source is not None and model_name not in SOURCE_EDIT_MODELS:
            self._set_status(
                "That engine has no validated source-image graph. Choose 4B/Phr00t or a RunPod reference model."
            )
            return
        if use_stage_three and source is None:
            self._set_status("Stage 3 face lock requires an original source image.")
            return
        try:
            route = (self._queued_route_override if self._queue_active
                     else self.backend_router.resolve(model_name) if self.backend_router else None)
        except ValueError as exc:
            self._set_status(str(exc))
            return
        if model_name not in LOCAL_SAFE_CREATE_MODELS and (route is None or route.destination != "RUNPOD"):
            self._set_status("Local model execution is blocked; GPU/memory verification is pending. Choose RunPod.")
            return
        if use_upscale:
            remote = bool(route and route.destination == "RUNPOD")
            output_target = int(getattr(self, "_output_target_long_edge", 0))
            available = (True if remote else local_output_upscale_assets_available()) if output_target in (2560, 3840) else (UPSCALE_WORKFLOW.is_file() if remote else upscale_assets_available())
            if not available:
                self._set_status("Upscale is blocked: the selected upscale workflow assets are missing.")
                return
        try:
            selected_loras = compatible_selection(model_name, [lora_one, lora_two, lora_three])
            refcontrol_prompt(prompt_text, model_name, selected_loras, has_pose=pose is not None, has_source=source is not None)
            max_loras = model_lora_limit(model_name)
            if len(selected_loras) > max_loras:
                raise ValueError(f"{model_name} allows {max_loras} LoRA slot(s).")
            if any(value < 0.0 or value > 1.0 for value in (lora_one_strength, lora_two_strength, lora_three_strength)):
                raise ValueError("LoRA strengths must be between 0.00 and 1.00.")
        except ValueError as exc:
            self._set_status(str(exc))
            return
        defaults = model_generation_settings(model_name, source=source is not None,
                                             remote=bool(route and route.destination == "RUNPOD"))
        fallback_controls = {key: defaults["default" + key[0].upper() + key[1:]]
                             for key in ("steps", "cfg", "denoise", "sampler", "scheduler")}
        fallback_controls.update(seed=-1, width=int(width), height=int(height))
        generation_controls = getattr(self, "_next_generation_controls", None) or fallback_controls
        generation_controls["stage2_model"] = self._stage_two_model
        generation_controls["negative_prompt"] = negative_prompt
        self._next_generation_controls = None
        if not self._queue_active:
            self._active_stage_three_engine = self._stage_three_engine
        self._cancel_requested = False
        self._set_progress(-1.0)
        self._set_busy(True)
        engine = {
            REMOTE_PHR00T_MODEL: "RunPod Phr00t v23",
            REMOTE_PHR00T_V19_MODEL: "Phr00t v19",
            REMOTE_KLEIN_9B_MODEL: "RunPod Klein 9B",
            REMOTE_AISHA_9B_MODEL: "RunPod Aisha 9B",
            REGULAR_9B_MODEL: "Klein 9B Base",
            KV_9B_MODEL: "Klein 9B-KV",
            FOUR_B_MODEL: "Klein 4B Fast",
            QWEN_MODEL: "Phr00t v19 Q4",
            QWEN21_MODEL: "Qwen Image 2.1",
        }.get(model_name, model_name)
        self._set_status(f"Preparing validated {engine} generation…")
        try:
            threading.Thread(
                target=self._run_routed_generate,
                args=(route, prompt_text, negative_prompt, int(width), int(height), model_name, lora_one,
                      lora_two, lora_three, float(lora_one_strength), float(lora_two_strength),
                      float(lora_three_strength), source, pose,
                      bool(use_stage_two), bool(use_stage_three),
                      bool(use_upscale), generation_controls),
                daemon=True,
            ).start()
        except Exception as exc:
            # Busy was set before Thread.start(). If the thread did not start,
            # there is no worker to clear it or advance queued jobs.
            if not self._queue_active:
                self._active_stage_three_engine = None
            self._set_progress(-1.0)
            self._set_status(f"Generation could not start · {exc}")
            self._set_busy(False)

    @pyqtSlot(str, str, str, float)
    def queueInpaint(self, source_url: str, mask_url: str, prompt_text: str, strength: float) -> None:
        if self._busy:
            return
        try:
            route = self._operation_route('inpaint')
        except ValueError as exc:
            self._set_status(str(exc))
            return
        source = Path(QUrl(source_url).toLocalFile())
        mask = Path(QUrl(mask_url).toLocalFile())
        prompt_text = prompt_text.strip()
        if not source.is_file() or not mask.is_file() or not prompt_text:
            self._set_status("Choose a source image, mask image, and enter inpaint instructions.")
            return
        self._set_busy(True)
        self._set_status("Preparing masked inpaint workflow…")
        self._start_busy_worker(self._run_routed_operation,
                                (route, self._run_inpaint, source, mask,
                                 prompt_text, float(strength)),
                                label="Inpaint")

    @pyqtSlot(str, str, float)
    def queueEdit(self, source_url: str, prompt_text: str, strength: float) -> None:
        if self._busy:
            return
        try:
            route = self._operation_route('edit')
        except ValueError as exc:
            self._set_status(str(exc))
            return
        source = Path(QUrl(source_url).toLocalFile())
        prompt_text = prompt_text.strip()
        if not source.is_file() or not prompt_text:
            self._set_status("Choose a source image and enter edit instructions.")
            return
        if not EDIT_WORKFLOW.is_file():
            self._set_status("The saved Klein image-edit workflow is unavailable.")
            return
        self._set_busy(True)
        self._set_status("Preparing validated image-edit workflow…")
        self._start_busy_worker(self._run_routed_operation,
                                (route, self._run_edit, source,
                                 prompt_text, float(strength)),
                                label="Image edit")

    def _run_routed_generate(self, route, *args):
        self._finish_route = route
        if route is None:
            return self._run_generate(*args)
        with use_route(route):
            self._set_status(f"{route.destination} · preparing generation…")
            return self._run_generate(*args)

    def _run_generate(
        self,
        prompt_text: str,
        negative_prompt: str,
        width: int,
        height: int,
        model_name: str,
        lora_one: str,
        lora_two: str,
        lora_three: str,
        lora_one_strength: float,
        lora_two_strength: float,
        lora_three_strength: float,
        source: Path | None,
        pose: Path | None,
        use_stage_two: bool,
        use_stage_three: bool,
        use_upscale: bool,
        generation_controls: dict | None = None,
        *, release_busy: bool = True,
    ) -> Path | None:
        try:
            # Do not contact a local backend with a model that has not
            # passed local GPU/memory verification.  Apply this guard to the
            # worker entrypoint as well as the queue's front-end check.
            if not remote_url():
                selected = [model_name]
                if use_stage_two:
                    selected.append((generation_controls or {}).get("stage2_model", self._stage_two_model))
                if any(model not in LOCAL_SAFE_CREATE_MODELS for model in selected):
                    raise workflow_lab.ComfyError(
                        "Local model execution is blocked; GPU/memory verification is pending. Choose RunPod."
                    )
            refcontrol_prompt(prompt_text, model_name, [lora_one, lora_two, lora_three],
                              has_pose=pose is not None, has_source=source is not None)
            if pose is not None and model_name not in ({QWEN_MODEL, QWEN21_MODEL, FOUR_B_MODEL} | REMOTE_SOURCE_MODELS | REMOTE_CHECKPOINT_MODELS):
                raise workflow_lab.ComfyError("This model has no separate pose/control workflow.")
            if model_name == FOUR_B_MODEL and not remote_url():
                required_model = Path.home() / "AI/ComfyUI/models/diffusion_models" / FOUR_B_MODEL
                ready, detail = integrations.ensure_ai_model_volume_readonly(required_model)
                if not ready:
                    raise workflow_lab.ComfyError(detail)
            client, stats = self._connect_comfyui()
            if remote_url():
                info = (load_remote_catalog(client, refresh=True)
                        if (generation_controls or {}).get("faceid_enabled")
                        else load_remote_catalog(client))
                if model_name in ({QWEN_MODEL} | REMOTE_PHR00T_MODELS) or (source is not None and model_name in REMOTE_SOURCE_MODELS):
                    validate_remote_workflow_assets(remote_reference_workflow(model_name), info, model_name)
                elif source is None and model_name in REMOTE_KLEIN9B_SOURCE_MODELS:
                    validate_remote_workflow_assets(
                        REMOTE_PORNMASTER_T2I_WORKFLOW if model_name == LOCAL_PORNMASTER_9B_MODEL else REMOTE_MIRACLEIN_T2I_WORKFLOW,
                        info, model_name,
                    )
                elif model_name == QWEN21_MODEL and (source is not None or pose is not None):
                    validate_remote_workflow_assets(QWEN21_REFERENCE_WORKFLOW, info, model_name)
                if use_stage_two:
                    stage_two_model = (generation_controls or {}).get("stage2_model", REMOTE_AISHA_9B_MODEL)
                    if stage_two_model not in REFINEMENT_MODELS:
                        raise workflow_lab.ComfyError("Select a verified FLUX.2 Klein 9B family model for RunPod Stage 2.")
                    validate_remote_workflow_assets(remote_reference_workflow(stage_two_model), info, stage_two_model)
                if use_upscale and (generation_controls or {}).get("output_long_edge") in (2560,3840):
                    self._require_output_upscaler(info)
                for enabled, workflow in ((use_upscale and (generation_controls or {}).get("output_long_edge") not in (2560,3840), UPSCALE_WORKFLOW),):
                    if enabled:
                        validate_remote_workflow_assets(workflow, info)
            else:
                info = client.object_info()
                # Check every selected local stage before spending GPU time on Stage 1.
                if model_name in ({QWEN_MODEL} | REMOTE_PHR00T_MODELS):
                    validate_remote_workflow_assets(remote_reference_workflow(model_name), info, model_name)
                if model_name == QWEN21_MODEL and (source is not None or pose is not None):
                    validate_remote_workflow_assets(QWEN21_REFERENCE_WORKFLOW, info, model_name)
                if use_stage_two:
                    stage_two_model = (generation_controls or {}).get("stage2_model", self._stage_two_model)
                    if stage_two_model not in REFINEMENT_MODELS:
                        raise workflow_lab.ComfyError("Choose an installed refinement model.")
                    validate_remote_workflow_assets(remote_reference_workflow(stage_two_model), info, stage_two_model)
                if use_upscale and (generation_controls or {}).get("output_long_edge") in (2560,3840):
                    self._require_output_upscaler(info)
                for enabled, workflow in ((use_upscale and (generation_controls or {}).get("output_long_edge") not in (2560,3840), UPSCALE_WORKFLOW),):
                    if enabled:
                        validate_remote_workflow_assets(workflow, info)
            if (generation_controls or {}).get("faceid_enabled") and model_name not in REMOTE_SDXL_MODELS:
                raise workflow_lab.ComfyError("FaceID is supported only for SDXL; disable it for this model.")
            # Stage 3 is applied after the saved generation, using two reviewed
            # face regions. Do not reject Stage 1 because ReActor needs a review.
            self._finish_info = info
            self._finish_width, self._finish_height = int(width), int(height)
            self._output_dir.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S") + "-" + str(time.time_ns())
            if model_name == QWEN21_MODEL and (source is not None or pose is not None):
                primary = source if source is not None else pose
                secondary = pose if source is not None else None
                if source is not None:
                    qwen21_prompt = adapt_prompt(prompt_text, QWEN21_MODEL, source_image=True, pose_image=pose is not None)
                else:
                    qwen21_prompt = "Use <image1> as the pose and composition reference. Create the requested subject and scene. Instruction: " + prompt_text
                current = self._run_reference_stage(
                    client, info, QWEN21_REFERENCE_WORKFLOW, primary, qwen21_prompt,
                    stamp, "QwenImage21-Reference", secondary_image=secondary,
                    controls=generation_controls, model_override=QWEN21_MODEL,
                    initialize_from_source=source is not None,
                    loras=[lora_one,lora_two,lora_three],
                    lora_strengths=[lora_one_strength,lora_two_strength,lora_three_strength],
                )
            elif model_name in REMOTE_CHECKPOINT_MODELS:
                prompt = build_create_prompt(info, adapt_prompt(prompt_text, model_name, source_image=source is not None), width, height,
                                             model_name, [lora_one, lora_two, lora_three],
                                             [lora_one_strength, lora_two_strength, lora_three_strength])
                prompt["3"]["inputs"]["text"] = negative_prompt
                # Tested live on 8189: a source-image latent at denoise .55
                # overrules a new OpenPose body. Keep the face reference, but
                # start from the template's empty latent when FaceID+pose is on.
                pose_first_faceid = bool((generation_controls or {}).get("faceid_enabled") and pose is not None)
                if source is not None:
                    uploaded = client.upload_image(source)
                    prompt["genesis_source"] = {"class_type": "LoadImage", "inputs": {"image": "/".join(v for v in (uploaded.get("subfolder"), uploaded.get("name")) if v)}}
                    if not pose_first_faceid:
                        prompt["genesis_source_scale"] = {"class_type": "ImageScale", "inputs": {"image": ["genesis_source", 0], "upscale_method": "lanczos", "width": width, "height": height, "crop": "disabled"}}
                        prompt["genesis_source_encode"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["genesis_source_scale", 0], "vae": ["1", 2]}}
                        prompt["5"]["inputs"]["latent_image"] = ["genesis_source_encode", 0]
                if pose is not None:
                    if model_name not in REMOTE_SDXL_MODELS:
                        raise workflow_lab.ComfyError('This SD 1.5 model has no installed pose ControlNet. Use a source image or text only.')
                    attach_sdxl_pose(prompt, info, client.upload_image(pose), width, height)
                apply_create_controls(prompt, generation_controls or {})
                if (generation_controls or {}).get("faceid_enabled"):
                    attach_sdxl_faceid(prompt, info, generation_controls or {}, pose_driven=pose_first_faceid)
                validate_operation_prompt(prompt, info, "SDXL source/pose")
                current = self._submit_and_save(client, prompt, stamp, "SDXL")
            elif source is not None and model_name == FOUR_B_MODEL:
                current = self._run_4b_source(
                    client, info, source, adapt_prompt(prompt_text, FOUR_B_MODEL, source_image=True, pose_image=pose is not None),
                    [lora_one, lora_two, lora_three],
                    [lora_one_strength, lora_two_strength, lora_three_strength], width, height, stamp,
                    controls=generation_controls, pose=pose,
                )
            elif source is not None and model_name in REMOTE_PHR00T_V23_MODELS:
                current = self._run_reference_stage(
                    client, info, REMOTE_PHR00T_WORKFLOW, source,
                    adapt_prompt(prompt_text, model_name, source_image=True, pose_image=pose is not None),
                    stamp, "Phr00t-v23", secondary_image=pose,
                    controls=generation_controls, model_override=model_name,
                )
            elif source is not None and model_name in REMOTE_PHR00T_V23_CACHE_MODELS:
                current = self._run_reference_stage(
                    client, info, STAGE_1_WORKFLOW, source,
                    adapt_prompt(prompt_text, model_name, source_image=True, pose_image=pose is not None),
                    stamp, ("Phr00t-v22-GGUF" if model_name == REMOTE_PHR00T_V22_GGUF_MODEL else "Phr00t-v23-GGUF"),
                    secondary_image=pose, controls=generation_controls, model_override=model_name,
                )
            elif source is not None and model_name == REMOTE_PHR00T_V19_MODEL:
                current = self._run_reference_stage(
                    client, info, REMOTE_PHR00T_V19_WORKFLOW, source,
                    adapt_prompt(prompt_text, model_name, source_image=True, pose_image=pose is not None),
                    stamp, "Phr00t-v19", secondary_image=pose,
                    controls=generation_controls, model_override=model_name,
                )
            elif source is not None and (model_name == REMOTE_PHR00T_V19_GGUF_MODEL or
                                        (remote_url() and model_name == QWEN_MODEL)):
                current = self._run_reference_stage(
                    client, info, STAGE_1_WORKFLOW, source,
                    adapt_prompt(prompt_text, model_name, source_image=True, pose_image=pose is not None),
                    stamp, "Phr00t-v19-GGUF", secondary_image=pose,
                    controls=generation_controls, model_override=model_name,
                )
            elif source is not None and model_name in KLEIN9B_REFERENCE_MODELS:
                current = self._run_reference_stage(
                    client, info, remote_reference_workflow(model_name), source,
                    adapt_prompt(prompt_text, model_name, source_image=True, pose_image=pose is not None),
                    stamp, "Aisha9B" if model_name == REMOTE_AISHA_9B_MODEL else "Klein9B",
                    secondary_image=pose,
                    controls=generation_controls, model_override=model_name,
                    loras=[lora_one, lora_two, lora_three],
                    lora_strengths=[lora_one_strength, lora_two_strength, lora_three_strength],
                )
            elif source is not None and model_name == QWEN_MODEL:
                current = self._run_reference_stage(
                    client, info, STAGE_1_WORKFLOW, source,
                    adapt_prompt(prompt_text, QWEN_MODEL, source_image=True, pose_image=pose is not None),
                    stamp, "Stage1", secondary_image=pose,
                    controls=generation_controls, model_override=QWEN_MODEL,
                )
            elif source is not None:
                raise workflow_lab.ComfyError("This model has no validated source-image workflow.")
            elif source is None and pose is None and model_name in ({QWEN_MODEL} | REMOTE_PHR00T_MODELS):
                workflow = remote_reference_workflow(model_name)
                current = self._run_reference_stage(
                    client, info, workflow, None,
                    adapt_prompt(prompt_text, model_name), stamp, "Phr00t-TextToImage",
                    controls=generation_controls, model_override=model_name,
                )
            elif pose is not None and model_name in KLEIN9B_REFERENCE_MODELS:
                current = self._run_reference_stage(client, info, remote_reference_workflow(model_name), pose,
                    adapt_prompt(prompt_text, model_name), stamp, "Klein9B-Pose", controls=generation_controls,
                    model_override=model_name, loras=[lora_one, lora_two, lora_three],
                    lora_strengths=[lora_one_strength, lora_two_strength, lora_three_strength])
            elif pose is not None:
                raise workflow_lab.ComfyError("This pose route requires an original source image.")
            else:
                prompt = build_create_prompt(
                    info, adapt_prompt(prompt_text, model_name), width, height,
                    model_name, [lora_one, lora_two, lora_three],
                    [lora_one_strength, lora_two_strength, lora_three_strength]
                )
                apply_create_controls(prompt, generation_controls or {})
                if model_name == QWEN21_MODEL and "5" in prompt:
                    prompt["5"].setdefault("inputs", {})["negative_prompt"] = negative_prompt
                elif model_name == LOCAL_AISHA_9B_MODEL and "4" in prompt:
                    prompt["4"].setdefault("inputs", {})["text"] = negative_prompt
                elif model_name in REMOTE_CHECKPOINT_MODELS:
                    prompt["3"]["inputs"]["text"] = negative_prompt
                # The Klein/Phr00t create graphs intentionally ignore unsupported
                # negative conditioning. Qwen 2.1 keeps the text for CFG > 1.
                current = self._submit_and_save(client, prompt, stamp, "QwenImage21" if model_name == QWEN21_MODEL else "Klein")

            identity_snapshot = (generation_controls or {}).get("character_snapshot") or {}
            snapshot_master = Path(identity_snapshot["master"]) if identity_snapshot.get("master") else None
            self._original_master = snapshot_master or source
            self._record_finish("Generated", current)
            self._check_cancelled()
            if use_stage_two:
                current = self._refine_result(client, info, current, stage_two_model, stamp, include_realism=False)
                self._record_finish("Refine", current)
            self._check_cancelled()
            # Identity correction comes after optional upscaling, so the user's
            # final target is inspected, not a throwaway intermediate.
            self._check_cancelled()
            if use_upscale:
                long_edge=int((generation_controls or {}).get("output_long_edge",0))
                if long_edge in (2560,3840):
                    current=self._upscale_to_long_edge(client,info,current,long_edge,stamp)
                else:
                    current = self._run_reference_stage(
                        client, info, UPSCALE_WORKFLOW, current, "", stamp, "Upscale"
                    )
            self._record_finish("Generated", current)
            self._set_progress(1.0)
            if use_stage_three:
                identity_source = self._original_master or source
                if identity_source is None or not identity_source.is_file():
                    self._set_status("Generation saved · Stage 3 skipped: original Person A image missing.")
                else:
                    try:
                        # Route Stage 3 with the snapshotted identity engine.
                        # Standalone NSFW FaceFusion must not depend on online
                        # local ComfyUI/ReActor after a successful generation.
                        face_route = self._person_a_face_swap_route()
                        if face_route.destination != 'LOCAL':
                            raise ValueError('Face swapping is local-only; RunPod cannot be selected.')
                    except ValueError as exc:
                        self._set_status(f"Generation saved · Stage 3 skipped: {exc}")
                    else:
                        # ReActor availability belongs to local ComfyUI. The
                        # generation backend may not contain ReActor at all.
                        self._pending_stage_three = True
                        self._set_status("Generation saved · confirm Person A for Stage 3…")
                        self.stageThreeSelectionRequired.emit(str(current), str(identity_source))
            else:
                self._set_status(f"Complete · {current.name}")
            return current
        except Exception as exc:
            self._set_progress(-1.0)
            if self._cancel_requested:
                self._set_status("Generation cancelled.")
            else:
                self._set_status(f"Generation failed · {exc}")
        finally:
            if release_busy and not self._pending_stage_three:
                self._cancel_requested = False
                self._set_busy(False)

    def _run_4b_source(
        self, client, info: dict, source: Path, prompt_text: str,
        loras: list[str], strengths: list[float], width: int, height: int, stamp: str,
        controls: dict | None = None, pose: Path | None = None,
    ) -> Path:
        prompt = workflow_lab.workflow_to_prompt(FOUR_B_SOURCE_WORKFLOW, info)
        # The saved template includes a face swap. Stage 1 must save its native
        # output; Stage 3 separately requests the user's reviewed face regions.
        if "12" in prompt:
            if not (
                prompt["12"].get("class_type") == "ReActorFaceSwap"
                and prompt["12"].get("inputs", {}).get("input_image") == ["10", 0]
                and prompt.get("10", {}).get("class_type") == "VAEDecode"
                and prompt.get("13", {}).get("class_type") == "SaveImage"
                and prompt["13"].get("inputs", {}).get("images") == ["12", 0]
                and all(
                    node_id == "13" and name == "images"
                    for node_id, node in prompt.items()
                    for name, value in node.get("inputs", {}).items()
                    if isinstance(value, list) and value and value[0] == "12"
                )
            ):
                raise workflow_lab.ComfyError("Klein 4B source workflow output topology changed.")
            prompt["13"]["inputs"]["images"] = ["10", 0]
            prompt.pop("12")
        prompt["1"]["inputs"]["unet_name"] = FOUR_B_MODEL
        prompt["2"]["inputs"]["clip_name"] = TEXT_ENCODER_4B
        compatible_selection(FOUR_B_MODEL, loras)
        # Remove the saved default adapter and keep CLIP conditioning pristine.
        prompt["8"]["inputs"]["model"] = ["1", 0]
        prompt["5"]["inputs"]["clip"] = ["2", 0]
        prompt["6"]["inputs"]["clip"] = ["2", 0]
        prompt.pop("4", None)
        insert_model_only_loras(prompt, "1", "8", "model", loras, strengths)
        prompt["5"]["inputs"]["text"] = prompt_text
        prompt["7"]["inputs"].update({"width": width, "height": height, "batch_size": 1})
        prompt["9"]["inputs"].update({"steps": 4, "cfg": 1.0})
        if controls:
            apply_create_controls(prompt, controls)
        uploaded = client.upload_image(source)
        prompt["11"]["inputs"]["image"] = "/".join(
            value for value in (uploaded.get("subfolder"), uploaded.get("name")) if value
        )
        # Native reference conditioning is distinct from the later face-lock input.
        references = [("identity", ["11", 0])]
        if pose is not None:
            uploaded_pose = client.upload_image(pose)
            prompt["genesis_4b_pose"] = {"class_type": "LoadImage", "inputs": {"image": "/".join(v for v in (uploaded_pose.get("subfolder"), uploaded_pose.get("name")) if v)}}
            references.insert(0, ("pose", ["genesis_4b_pose", 0]))
        positive, negative = ["5", 0], ["6", 0]
        for role, image_link in references:
            encoded = "genesis_4b_" + role + "_encode"
            prompt[encoded] = {"class_type": "VAEEncode", "inputs": {"pixels": image_link, "vae": ["3", 0]}}
            for label, conditioning in (("positive", positive), ("negative", negative)):
                node_id = "genesis_4b_" + role + "_" + label
                prompt[node_id] = {"class_type": "ReferenceLatent", "inputs": {"conditioning": conditioning, "latent": [encoded, 0]}}
            positive, negative = ["genesis_4b_" + role + "_positive", 0], ["genesis_4b_" + role + "_negative", 0]
        prompt["9"]["inputs"].update(positive=positive, negative=negative)
        validation = workflow_lab.validate_prompt(prompt, info)
        if not validation["valid"]:
            missing = validation["missing_nodes"] + validation["missing_inputs"]
            raise workflow_lab.ComfyError("Klein 4B source workflow is not runnable: " + ", ".join(missing))
        return self._submit_and_save(client, prompt, stamp, "Klein4B")

    def _require_output_upscaler(self, info):
        missing=[name for name in ('LoadImage','UpscaleModelLoader','ImageUpscaleWithModel','ImageScale','SaveImage') if name not in info]
        choices=_remote_choice_values(info,('UpscaleModelLoader',),'model_name')
        asset=next((n for n in ('4x-UltraSharp.safetensors','4x-UltraSharp.pth') if n in choices),None)
        if missing or not asset:
            raise workflow_lab.ComfyError('2K/4K finishing unavailable; missing '+', '.join(missing or ['4x-UltraSharp upscaler']))
        return asset

    def _upscale_to_long_edge(self,client,info,current,target_long_edge,stamp):
        from PIL import Image
        with Image.open(current) as image:
            w,h=image.size
        if max(w,h)<=0:
            raise workflow_lab.ComfyError('Cannot upscale a zero-size image')
        target_w=max(8,int(round(w*target_long_edge/max(w,h)/8))*8)
        target_h=max(8,int(round(h*target_long_edge/max(w,h)/8))*8)
        model=self._require_output_upscaler(info)
        upload=client.upload_image(current)
        image_path='/'.join(v for v in (upload.get('subfolder'),upload.get('name')) if v)
        graph={
            '1': {'class_type':'LoadImage','inputs':{'image':image_path}},
            '2': {'class_type':'UpscaleModelLoader','inputs':{'model_name':model}},
            '3': {'class_type':'ImageUpscaleWithModel','inputs':{'upscale_model':['2',0],'image':['1',0]}},
            '4': {'class_type':'ImageScale','inputs':{'image':['3',0], 'upscale_method':'lanczos', 'width':target_w,'height':target_h,'crop':'disabled'}},
            '5': {'class_type':'SaveImage','inputs':{'images':['4',0],'filename_prefix':f'GENESIS-{target_long_edge}-finish'}},
        }
        validate_operation_prompt(graph,info,f'{target_long_edge} output upscale')
        return self._submit_and_save(client,graph,stamp,f'{target_long_edge}Output')

    def _submit_and_save(self, client, prompt: dict, stamp: str, stage: str, *, timeout=1800) -> Path:
        # Local GPU/asset checks are deliberately skipped for a remote RunPod backend.
        if not remote_url():
            safe, detail = integrations.gpu_kernel_preflight()
            if not safe:
                raise workflow_lab.ComfyError(detail)
            problems = unavailable_local_assets(prompt, MODEL_ROOTS)
            if problems:
                raise workflow_lab.ComfyError("Local asset check failed: " + " ".join(problems))
        self._set_progress(0.05)
        self._active_client = client
        prompt_id = client.submit(prompt)
        self._active_prompt_id = prompt_id
        self._set_status(f"{stage} queued {prompt_id[:8]}…")

        def update_progress(value: dict) -> None:
            state = str(value.get("status", "working"))
            if state == "pending":
                self._set_progress(0.12)
            elif state == "running":
                self._set_progress(0.55)
            elif state == "completed":
                self._set_progress(0.95)
            self._set_status(
                f"{stage} {state} · {int(value.get('elapsed', 0))}s"
            )

        try:
            result = client.wait(
                prompt_id,
                timeout=timeout,
                progress=update_progress,
                abort_check=self._abort_reason,
            )
        finally:
            if self._active_client is client:
                self._active_client = None
            if self._active_prompt_id == prompt_id:
                self._active_prompt_id = None
        if result.status != "completed":
            raise workflow_lab.ComfyError(result.error or f"{stage} ended: {result.status}")
        # This A100 is shared with a separate 8188 ComfyUI. Once our 8189
        # stage finishes, release only this backend's loaded models/cache so
        # idle GENESIS VRAM is not held while the other instance is working.
        if remote_url():
            try:
                client._request(
                    "/free", method="POST",
                    payload={"unload_models": True, "free_memory": True},
                    timeout=10,
                )
            except Exception:
                pass
        self._output_dir.mkdir(parents=True, exist_ok=True)
        saved: list[Path] = []
        for index, output in enumerate(result.outputs, 1):
            if output.get("kind") != "images":
                continue
            suffix = Path(output.get("filename", "image.png")).suffix or ".png"
            target = self._output_dir / f"GENESIS-{stage}-{stamp}-{index}{suffix}"
            target.write_bytes(client.view(output))
            saved.append(target)
        if not saved:
            raise workflow_lab.ComfyError(f"{stage} completed without an image output.")
        return saved[-1]

    def _run_reference_stage(
        self, client, info: dict, workflow: Path, input_image: Path,
        prompt_text: str, stamp: str, stage: str, secondary_image: Path | None = None,
        controls: dict | None = None, model_override: str | None = None,
        loras: list[str] | None = None, lora_strengths: list[float] | None = None,
        initialize_from_source: bool = False,
    ) -> Path:
        if workflow == STAGE_3_WORKFLOW:
            raise workflow_lab.ComfyError("ReActor target is unverified: automatic index selection cannot identify Person A.")
        if not workflow.is_file():
            raise workflow_lab.ComfyError(f"{stage} workflow is unavailable.")
        prompt = remote_workflow_prompt(workflow, info) if remote_url() else workflow_lab.workflow_to_prompt(workflow, info)
        if workflow == QWEN21_REFERENCE_WORKFLOW and not remote_url():
            prompt["1"] = {
                "class_type": "GenesisQwen21ReferenceUNETLoader",
                "inputs": {"unet_name": QWEN21_MODEL},
            }
            prompt["3"] = {
                "class_type": "GenesisQwen21ReferenceCLIPLoader",
                "inputs": {"clip_name": QWEN21_CLIP},
            }
        # Only the explicitly selected local Miraclein Fast preset lowers source
        # detail. Preserve the original image, pose input, and saved workflow.
        if (not remote_url() and workflow == REMOTE_MIRACLEIN_EDIT_WORKFLOW
                and model_override == LOCAL_MIRACLEIN_9B_MODEL and controls):
            budget = float(controls.get("source_reference_megapixels", 0.0))
            if 0.0 < budget <= 1.0:
                scaler = prompt.get("12", {})
                encoder = prompt.get("15", {})
                if (scaler.get("class_type") != "ImageScaleToTotalPixels"
                        or scaler.get("inputs", {}).get("image") != ["10", 0]
                        or encoder.get("class_type") != "VAEEncode"
                        or encoder.get("inputs", {}).get("pixels") != ["12", 0]):
                    raise workflow_lab.ComfyError("Miraclein source-reference scaler is unavailable.")
                scaler["inputs"]["megapixels"] = budget
        if workflow in REMOTE_KLEIN_REFERENCE_WORKFLOWS:
            _reconcile_remote_klein_clip(prompt, info)
            prompt_text = refcontrol_prompt(prompt_text, model_override or REMOTE_KLEIN_9B_MODEL,
                                           loras or [], has_pose=secondary_image is not None, has_source=True)
            if model_override == REGULAR_9B_MODEL:
                prompt["1"] = {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": model_override}}
        load_nodes = sorted(
            (str(node_id) for node_id, node in prompt.items() if node.get("class_type") == "LoadImage"),
            key=lambda value: int(value) if value.isdigit() else value,
        )
        # Phr00t exposes image2 on the conditioning node but the saved graph only
        # contains the main LoadImage. Inject a transient LoadImage for GENESIS pose
        # selection while leaving MARTY's original workflow JSON untouched.
        if secondary_image is not None and workflow == REMOTE_PHR00T_WORKFLOW:
            uploaded_pose = client.upload_image(secondary_image)
            pose_name = "/".join(
                value for value in (uploaded_pose.get("subfolder"), uploaded_pose.get("name")) if value
            )
            pose_node = "__genesis_pose__"
            prompt[pose_node] = {"class_type": "LoadImage", "inputs": {"image": pose_name}}
            if "5" not in prompt:
                raise workflow_lab.ComfyError("Phr00t conditioning node 5 is unavailable.")
            prompt["5"].setdefault("inputs", {})["image2"] = [pose_node, 0]
            secondary_image = None

        # FLUX.2 Klein uses ordered reference latents. When a pose reference is
        # supplied, prepend it before the identity/source reference so the graph
        # matches the documented RefControl contract: image 1 pose, image 2 reference.
        if secondary_image is not None and workflow in REMOTE_KLEIN_REFERENCE_WORKFLOWS:
            uploaded_pose = client.upload_image(secondary_image)
            pose_name = "/".join(
                value for value in (uploaded_pose.get("subfolder"), uploaded_pose.get("name")) if value
            )
            prompt["__genesis_pose__"] = {
                "class_type": "LoadImage", "inputs": {"image": pose_name}
            }
            prompt["__genesis_pose_encode__"] = {
                "class_type": "VAEEncode",
                "inputs": {"pixels": ["__genesis_pose__", 0], "vae": ["3", 0]},
            }
            prompt["__genesis_pose_positive__"] = {
                "class_type": "ReferenceLatent",
                "inputs": {
                    "conditioning": ["4", 0],
                    "latent": ["__genesis_pose_encode__", 0],
                },
            }
            prompt["__genesis_pose_negative__"] = {
                "class_type": "ReferenceLatent",
                "inputs": {
                    "conditioning": ["5", 0],
                    "latent": ["__genesis_pose_encode__", 0],
                },
            }
            if "17" not in prompt or "18" not in prompt:
                raise workflow_lab.ComfyError("Klein reference-conditioning nodes are unavailable.")
            prompt["17"]["inputs"]["conditioning"] = ["__genesis_pose_positive__", 0]
            prompt["18"]["inputs"]["conditioning"] = ["__genesis_pose_negative__", 0]
            secondary_image = None

        if input_image is None and (workflow not in {STAGE_1_WORKFLOW, REMOTE_PHR00T_V19_WORKFLOW, REMOTE_PHR00T_WORKFLOW} or secondary_image is not None):
            raise workflow_lab.ComfyError("Only Phr00t supports this no-reference graph.")
        images = ([input_image] if input_image is not None else []) + ([secondary_image] if secondary_image is not None else [])
        used_reference_paths = {path.resolve() for path in images}
        if len(load_nodes) < len(images):
            raise workflow_lab.ComfyError(f"{stage} workflow has too few image inputs.")
        for node_id, path in zip(load_nodes, images):
            uploaded = client.upload_image(path)
            prompt[node_id]["inputs"]["image"] = "/".join(
                value for value in (uploaded.get("subfolder"), uploaded.get("name")) if value
            )
        if workflow in {STAGE_1_WORKFLOW, REMOTE_PHR00T_V19_WORKFLOW, REMOTE_PHR00T_WORKFLOW, QWEN21_REFERENCE_WORKFLOW}:
            # Saved extra reference slots are optional. Do not submit placeholder
            # filenames when the user selected fewer images.
            for node_id in load_nodes[len(images):]:
                for node in prompt.values():
                    inputs = node.get("inputs", {})
                    if node.get("class_type") == "TextEncodeQwenImageEditPlus":
                        for field in ("image1", "image2", "image3", "image4"):
                            if inputs.get(field) == [node_id, 0]:
                                inputs.pop(field)
                    elif node.get("class_type") == "TextEncodeQwenImage21":
                        refs = inputs.get("images")
                        if isinstance(refs, dict):
                            for field in list(refs):
                                if refs.get(field) == [node_id, 0]:
                                    refs.pop(field)
                prompt.pop(node_id)
        extra_url = str((controls or {}).get("extra_reference_url", "") or "")
        if extra_url and workflow in {STAGE_1_WORKFLOW, REMOTE_PHR00T_V19_WORKFLOW, REMOTE_PHR00T_WORKFLOW}:
            if input_image is None:
                raise workflow_lab.ComfyError("An extra Phr00t reference requires an original image.")
            extra_path = Path(QUrl(extra_url).toLocalFile())
            if not extra_path.is_file():
                raise workflow_lab.ComfyError("The selected extra reference image is unavailable.")
            encoder = next((node for node in prompt.values() if node.get("class_type") == "TextEncodeQwenImageEditPlus"), None)
            choices = info.get("TextEncodeQwenImageEditPlus", {}).get("input", {}).get("optional", {})
            free_slot = next((slot for slot in ("image2", "image3") if encoder and slot not in encoder["inputs"] and slot in choices), None)
            if not free_slot:
                raise workflow_lab.ComfyError("Phr00t's installed text encoder has no spare image reference slot.")
            used_reference_paths.add(extra_path.resolve())
            uploaded = client.upload_image(extra_path)
            prompt["__genesis_extra_reference__"] = {"class_type": "LoadImage", "inputs": {
                "image": "/".join(v for v in (uploaded.get("subfolder"), uploaded.get("name")) if v)}}
            encoder["inputs"][free_slot] = ["__genesis_extra_reference__", 0]
            picture_number = 2 if free_slot == "image2" else 3
            prompt_text += (f" Use Picture {picture_number} ({free_slot}) as an additional "
                            "visual reference, not a replacement for the main subject in Picture 1.")
        elif extra_url:
            raise workflow_lab.ComfyError("Extra reference images are currently supported only for Phr00t.")
        # Use the identity snapshot owned by this job, never a character selected
        # while it was waiting. Older direct callers receive a fresh snapshot.
        character_snapshot = ((controls or {}).get("character_snapshot")
                              if controls is not None and "character_snapshot" in controls
                              else self._snapshot_character_a())
        if (stage in {"Phr00t-v23", "Phr00t-v23-GGUF", "Phr00t-v22-GGUF",
                      "Phr00t-v19", "Phr00t-v19-GGUF", "Stage1"}
                and character_snapshot and character_snapshot.get("id")):
            character = character_snapshot.get("data") or {}
            primary_image = character_snapshot.get("primary_image") or character.get("primary_image", "")
            if input_image is not None and primary_image and input_image.resolve() == Path(primary_image).resolve():
                encode = next((n for n in prompt.values() if n.get("class_type") == "TextEncodeQwenImageEditPlus"), None)
                optional = info.get("TextEncodeQwenImageEditPlus", {}).get("input", {}).get("optional", {})
                if encode:
                    for ref in character.get("references", []):
                        if (Path(ref).resolve() in used_reference_paths
                                or not Path(ref).is_file()
                                or not reference_is_approved(character, ref)
                                or reference_category(character, ref) == "pose"):
                            continue
                        field = next((name for name in ("image2", "image3")
                                      if name not in encode["inputs"] and name in optional), None)
                        if not field:
                            break  # Built-in encoder supports only image1..image3.
                        used_reference_paths.add(Path(ref).resolve())
                        uploaded = client.upload_image(Path(ref))
                        node_id = "__character_a_" + field
                        prompt[node_id] = {"class_type": "LoadImage", "inputs": {"image": "/".join(v for v in (uploaded.get("subfolder"), uploaded.get("name")) if v)}}
                        encode["inputs"][field] = [node_id, 0]
                        picture_number = 2 if field == "image2" else 3
                        prompt_text += (f" Picture {picture_number} ({field}) is another "
                                        "identity view of Person A, not a different person.")
        workflow_controls = workflow_lab.discover_workflow_controls(prompt)
        if model_override:
            target = workflow_controls.get("model")
            if target:
                prompt[str(target[0])]["inputs"][target[1]] = model_override

        if workflow == QWEN21_REFERENCE_WORKFLOW and loras:
            selected=compatible_selection(QWEN21_MODEL,loras)
            if selected:
                strengths=lora_strengths or []
                insert_model_only_loras(prompt,"1","2","model", selected,
                    [float(strengths[loras.index(item)]) if loras.index(item)<len(strengths) else 0.5 for item in selected],strength=0.5)

        # The saved RunPod Klein graph is kept pristine. Apply a selected
        # model-only adapter transiently between its UNET loader and CFG guider.
        if workflow in REMOTE_KLEIN_REFERENCE_WORKFLOWS and loras:
            active_model = model_override or REMOTE_KLEIN_9B_MODEL
            selected = compatible_selection(active_model, loras)
            if selected:
                strengths = lora_strengths or []
                selected_strengths = [
                    float(strengths[loras.index(name)]) if loras.index(name) < len(strengths) else (REFCONTROL_DEFAULT_STRENGTH if Path(name).name == REFCONTROL_LORA else 0.65)
                    for name in selected
                ]
                insert_model_only_loras(
                    prompt, "1", "6", "model", selected, selected_strengths
                )

        if prompt_text:
            target = workflow_controls.get("positive")
            if target:
                prompt[str(target[0])]["inputs"][target[1]] = prompt_text
        if controls:
            negative_target = workflow_controls.get("negative")
            if negative_target and "negative_prompt" in controls and model_family(model_override or "") != "qwen_image":
                prompt[str(negative_target[0])]["inputs"][negative_target[1]] = controls["negative_prompt"]
            for name in ("width", "height", "steps", "cfg", "denoise", "sampler", "scheduler"):
                target = workflow_controls.get(name)
                if target and name in controls and not isinstance(prompt[str(target[0])]["inputs"].get(target[1]), list):
                    prompt[str(target[0])]["inputs"][target[1]] = controls[name]

            # The supplied Klein/Aisha graph has separate scheduler and latent
            # dimension nodes. Keep them synchronized when GENESIS overrides size.
            if workflow in REMOTE_KLEIN_REFERENCE_WORKFLOWS:
                for node in prompt.values():
                    inputs = node.setdefault("inputs", {})
                    kind = node.get("class_type")
                    if kind in {"EmptyFlux2LatentImage", "Flux2Scheduler"}:
                        # Preserve graph dimensions unless explicitly overridden.
                        for field in ("width", "height"):
                            if field in controls:
                                inputs[field] = int(controls[field])
                        if kind == "Flux2Scheduler" and "steps" in controls:
                            inputs["steps"] = int(controls["steps"])
                    elif kind == "CFGGuider":
                        inputs["cfg"] = float(controls.get("cfg", inputs.get("cfg", 1.0)))
                    elif kind == "KSamplerSelect":
                        inputs["sampler_name"] = str(controls.get("sampler", inputs.get("sampler_name", "euler")))

            target = workflow_controls.get("seed")
            if target and "seed" in controls:
                seed = int(controls["seed"])
                if seed < 0:
                    seed = int(time.time_ns() & 0x7FFFFFFFFFFFFFFF)
                prompt[str(target[0])]["inputs"][target[1]] = seed
        if workflow == QWEN21_REFERENCE_WORKFLOW and not remote_url() and controls:
            sizes = [int(controls[key]) for key in ("width", "height") if key in controls]
            if sizes:
                # Native reference edits preserve the first image's aspect ratio.
                # Use the shorter selected dimension as the reference pixel budget.
                prompt["7"]["inputs"]["resolution"] = max(32, min(4096, round(min(sizes) / 32) * 32))
        if (workflow == QWEN21_REFERENCE_WORKFLOW and not remote_url()
                and initialize_from_source and float(prompt["8"]["inputs"]["denoise"]) < 1.0):
            resolution = int(prompt["7"]["inputs"]["resolution"])
            prompt["__qwen21_source_scale__"] = {
                "class_type": "ImageScaleToTotalPixels",
                "inputs": {
                    "image": ["5", 0], "upscale_method": "lanczos",
                    "megapixels": (resolution / 1024) ** 2, "resolution_steps": 32,
                },
            }
            prompt["__qwen21_source_latent__"] = {
                "class_type": "VAEEncode",
                "inputs": {"pixels": ["__qwen21_source_scale__", 0], "vae": ["4", 0]},
            }
            prompt["8"]["inputs"]["latent_image"] = ["__qwen21_source_latent__", 0]
        # Phr00t's own v2 reference encoder uses the target output latent to
        # avoid unexpected zoom/cropping. Use an isolated GENESIS node only if
        # ComfyUI reports it installed, the graph supplies a real empty latent,
        # and reference dimensions fit a bounded local VRAM budget. The native
        # encoder remains the no-surprises fallback (including RunPod 8189).
        if (input_image is not None
                and workflow in {STAGE_1_WORKFLOW, REMOTE_PHR00T_V19_WORKFLOW, REMOTE_PHR00T_WORKFLOW}
                and "GenesisQwenImageEditFraming" in info):
            sampler = next((node for node in prompt.values()
                            if node.get("class_type") == "KSampler"), None)
            latent_link = sampler.get("inputs", {}).get("latent_image") if sampler else None
            latent = prompt.get(str(latent_link[0]), {}) if isinstance(latent_link, list) and len(latent_link) == 2 else {}
            dims = latent.get("inputs", {}) if latent.get("class_type") == "EmptyLatentImage" else {}
            width = int(dims.get("width", 0))
            height = int(dims.get("height", 0))
            if width >= 64 and height >= 64 and width * height <= 1_500_000:
                for node in prompt.values():
                    if node.get("class_type") == "TextEncodeQwenImageEditPlus":
                        node["class_type"] = "GenesisQwenImageEditFraming"
                        node["inputs"]["target_latent"] = latent_link
        # The local v19 Q4 occupies almost the entire 16 GiB GPU. The
        # ordinary VAE decoder has been observed to OOM even at 512x704,
        # causing ComfyUI to retry with internal 256-pixel tiles. Go directly
        # to that safe decode path for this exact local model/workflow.
        # Never modify v23, other families, or RunPod's v19 checkpoints.
        if (not remote_url() and workflow == STAGE_1_WORKFLOW
                and model_override == QWEN_MODEL and "VAEDecodeTiled" in info):
            decoder = prompt.get("8", {})
            if (decoder.get("class_type") != "VAEDecode"
                    or decoder.get("inputs", {}).get("samples") != ["7", 0]
                    or not isinstance(decoder.get("inputs", {}).get("vae"), list)):
                raise workflow_lab.ComfyError("Local Phr00t v19 Q4 decoder topology changed.")
            decoder["class_type"] = "VAEDecodeTiled"
            decoder["inputs"].update({
                "tile_size": 256,
                "overlap": 64,
                "temporal_size": 64,
                "temporal_overlap": 8,
            })
        validation = workflow_lab.validate_prompt(prompt, info)
        if not validation["valid"]:
            missing = validation["missing_nodes"] + validation["missing_inputs"]
            raise workflow_lab.ComfyError(f"{stage} is not runnable: " + ", ".join(missing))
        validate_operation_prompt(prompt, info, stage)
        if workflow == QWEN21_REFERENCE_WORKFLOW:
            # V3 Autogrow inputs use flat API keys. A nested dictionary is
            # silently discarded by ComfyUI and leaves the model without refs.
            inputs = prompt["7"]["inputs"]
            references = inputs.get("images")
            expected = {f"image_{index + 1}": [node_id, 0]
                        for index, node_id in enumerate(load_nodes[:len(images)])}
            if prompt["7"]["class_type"] != "TextEncodeQwenImage21" or references != expected:
                raise workflow_lab.ComfyError(
                    "Local Qwen 2.1 reference connections are invalid; source/pose images would be lost or reordered."
                )
            inputs.pop("images")
            for name, link in references.items():
                inputs[f"images.{name}"] = link
        return self._submit_and_save(client, prompt, stamp, stage)


    def _run_inpaint(self, source: Path, mask: Path, prompt_text: str, strength: float) -> None:
        try:
            client, stats = self._connect_comfyui()
            info = client.object_info()
            checkpoints = (
                info.get("CheckpointLoaderSimple", {})
                .get("input", {}).get("required", {}).get("ckpt_name", [[], {}])[0]
            )
            if INPAINT_CHECKPOINT not in checkpoints:
                raise workflow_lab.ComfyError(
                    f"Inpaint checkpoint is unavailable: {INPAINT_CHECKPOINT}"
                )

            src_up = client.upload_image(source)
            mask_up = client.upload_image(mask)
            src_name = "/".join(v for v in (src_up.get("subfolder"), src_up.get("name")) if v)
            mask_name = "/".join(v for v in (mask_up.get("subfolder"), mask_up.get("name")) if v)
            denoise = max(0.05, min(0.95, strength))
            seed = int(time.time_ns() & 0xFFFFFFFFFFFF)
            prompt = {
                "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": INPAINT_CHECKPOINT}},
                "2": {"class_type": "LoadImage", "inputs": {"image": src_name}},
                "3": {"class_type": "LoadImageMask", "inputs": {"image": mask_name, "channel": "red"}},
                "4": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt_text, "clip": ["1", 1]}},
                "5": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["1", 1]}},
                "6": {"class_type": "VAEEncodeForInpaint", "inputs": {
                    "pixels": ["2", 0], "vae": ["1", 2], "mask": ["3", 0], "grow_mask_by": 6
                }},
                "7": {"class_type": "KSampler", "inputs": {
                    "model": ["1", 0], "seed": seed, "steps": 24, "cfg": 5.0,
                    "sampler_name": "dpmpp_2m", "scheduler": "karras",
                    "positive": ["4", 0], "negative": ["5", 0],
                    "latent_image": ["6", 0], "denoise": denoise
                }},
                "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["1", 2]}},
                "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "GENESIS-Inpaint"}},
            }
            validation = workflow_lab.validate_prompt(prompt, info)
            if not validation["valid"]:
                missing = validation["missing_nodes"] + validation["missing_inputs"]
                raise workflow_lab.ComfyError("Inpaint workflow is not runnable: " + ", ".join(missing))
            validate_operation_prompt(prompt, info, "Inpaint")
            stamp = time.strftime("%Y%m%d-%H%M%S")
            current = self._submit_and_save(client, prompt, stamp, "Inpaint")
            self._adopt_operation_result(current, info, source)
            self._record_finish("Inpaint", current, input_source=QUrl.fromLocalFile(str(source)).toString())
            self._set_status(f"Complete · {current.name}")
        except Exception as exc:
            self._set_status(f"Inpaint failed · {exc}")
        finally:
            self._set_busy(False)

    def _run_edit(self, source: Path, prompt_text: str, strength: float) -> None:
        try:
            client, stats = self._connect_comfyui()
            info = client.object_info()
            base = workflow_lab.workflow_to_prompt(EDIT_WORKFLOW, info)
            controls = workflow_lab.discover_workflow_controls(base)
            overrides: dict[str, dict] = {}

            def override(control: str, value) -> None:
                target = controls.get(control)
                if target:
                    node_id, input_name = target
                    overrides.setdefault(str(node_id), {})[input_name] = value

            override("positive", prompt_text)
            override("denoise", max(0.05, min(0.95, strength)))
            override("steps", 8)
            override("encoder", "qwen_3_4b_fp4_flux2.safetensors")

            uploaded = client.upload_image(source)
            image_name = "/".join(
                value for value in (uploaded.get("subfolder"), uploaded.get("name")) if value
            )
            load_nodes = [
                str(node_id) for node_id, node in base.items()
                if node.get("class_type") == "LoadImage"
            ]
            if not load_nodes:
                raise workflow_lab.ComfyError("Image-edit workflow has no source-image input.")
            overrides.setdefault(load_nodes[0], {})["image"] = image_name

            prompt = workflow_lab.workflow_to_prompt(EDIT_WORKFLOW, info, overrides)
            validation = workflow_lab.validate_prompt(prompt, info)
            if not validation["valid"]:
                missing = validation["missing_nodes"] + validation["missing_inputs"]
                raise workflow_lab.ComfyError("Workflow is not runnable: " + ", ".join(missing))

            validate_operation_prompt(prompt, info, "Image edit")
            stamp = time.strftime("%Y%m%d-%H%M%S")
            current = self._submit_and_save(client, prompt, stamp, "Edit", timeout=3600)
            self._adopt_operation_result(current, info, source)
            self._record_finish("Edit", current, input_source=QUrl.fromLocalFile(str(source)).toString())
            self._set_status(f"Complete · {current.name}")
        except Exception as exc:
            self._set_status(f"Edit failed · {exc}")
        finally:
            self._set_busy(False)


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--screenshot")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    page_indexes = {
        "create": 0, "poses": 1, "workflow": 2, "media": 3,
        "photos": 4, "cameras": 5, "entertainment": 6, "system": 7, "edit": 8,
        "posemaker": 9, "characters": 15,
    }
    parser.add_argument("--page", choices=tuple(page_indexes), default="create")
    parser.add_argument("--banner", choices=("video", "photos"), default="video")
    args, qt_args = parser.parse_known_args()
    sys.argv = [sys.argv[0], *qt_args]
    app = QApplication(sys.argv)
    app.setApplicationName("GENESIS Cockpit")
    app.setWindowIcon(QIcon(str(PROJECT_ROOT / "genesis/assets/genesis-cockpit-icon-balanced-final.png")))
    engine = QQmlApplicationEngine()
    context = engine.rootContext()
    context.setContextProperty("genesisAssetRoot", QUrl.fromLocalFile(str(ASSET_ROOT) + "/"))
    context.setContextProperty("genesisUiRoot", QUrl.fromLocalFile(str(UI_ROOT) + "/"))
    installed_pose_rows = load_pose_items(limit=10000)
    context.setContextProperty("poseItems", installed_pose_rows[:12])
    context.setContextProperty("grokPresetItems", load_grok_preset_items())
    context.setContextProperty("curatedPosePresets", load_curated_pose_presets(pose_rows=installed_pose_rows) + pose_preset_references(installed_pose_rows))
    context.setContextProperty("generationProfiles", load_generation_profiles())
    context.setContextProperty("runtimeStatus", load_runtime_status())
    generation_bridge = GenerationBridge(app)
    layout_bridge = LayoutSettingsBridge(app)
    module_bridge = ModuleBridge(app)
    media_bridge = MediaBridge(app)
    context.setContextProperty("genesisBridge", generation_bridge)
    context.setContextProperty("genesisLayout", layout_bridge)
    context.setContextProperty("moduleBridge", module_bridge)
    context.setContextProperty("mediaBridge", media_bridge)
    engine.load(QUrl.fromLocalFile(str(UI_ROOT / "MainPremiumLinux.qml")))
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]
    window.setProperty("pageIndex", page_indexes[args.page])
    window.setProperty("bannerMode", 1 if args.banner == "photos" else 0)
    if args.width or args.height:
        window.resize(max(900, args.width or window.width()), max(600, args.height or window.height()))
    if args.screenshot:
        window.show()
    else:
        window.showMaximized()
    if args.screenshot:
        target = Path(args.screenshot).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)

        def save_screenshot() -> None:
            screen = window.screen() or app.primaryScreen()
            image = screen.grabWindow(int(window.winId())) if screen else None
            if image is None or image.isNull() or not image.save(str(target)):
                app.exit(2)
                return
            app.quit()

        QTimer.singleShot(2500, save_screenshot)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
