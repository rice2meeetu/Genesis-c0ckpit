from __future__ import annotations

import base64
import io
import json
import random
import hashlib
import threading
import queue as pyqueue
import re
import os
import socket
import subprocess
import signal
import time
import uuid
from functools import lru_cache
from pathlib import Path

import gradio as gr
import requests
import websocket
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
SAMPLE_SOURCE = BASE_DIR / "sample_images" / "sample_source.png"
SAMPLE_POSE = BASE_DIR / "sample_images" / "sample_pose.webp"
USER_BANNER_DIR = BASE_DIR / "assets" / "user_banner"
USER_BANNER_DIR.mkdir(parents=True, exist_ok=True)
SIDE_PANEL_DIR = BASE_DIR / "assets" / "side_panels"
PRESETS_DIR = BASE_DIR / "assets" / "presets"
POSE_LIBRARY_DIR = BASE_DIR / "assets" / "pose_library"
POSE_LIBRARY_INDEX_PATH = POSE_LIBRARY_DIR / "index.json"
POSE_LIBRARY_PAGE_SIZE = 24
STAGE_BG_DIR = BASE_DIR / "assets" / "stage_bg"
UI_RAIL_DIR = BASE_DIR / "assets" / "ui_rails"

COMFY_URL = "http://127.0.0.1:8188"
TIMEOUT_SECONDS = 1200

# GENESIS memory-safe ComfyUI process management.
COMFY_DIR = Path.home() / "AI" / "ComfyUI"
CONDA_SH = Path.home() / "miniforge3" / "etc" / "profile.d" / "conda.sh"
COMFY_ENV = "comfyui-reactor-rocm"
COMFY_PORT = 8188
COMFY_START_TIMEOUT = 180
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
COMFY_MANAGED_LOG = LOG_DIR / "comfyui-managed.log"
THUMB_CACHE_DIR = BASE_DIR / "cache" / "pose_thumbs"
THUMB_CACHE_DIR.mkdir(parents=True, exist_ok=True)
THUMB_CACHE_LIMIT = 600
THUMB_MAX_SIZE = 320
MEMORY_GUARD_DEFAULT_GIB = 4.0

CANCEL_EVENT = threading.Event()
RUN_STATE_LOCK = threading.Lock()
ACTIVE_PROMPT_ID = None
ACTIVE_STAGE = None
COMFY_STARTED_BY_GENESIS = False

class RunCancelled(RuntimeError):
    pass

PREFERRED_STAGE1 = "Qwen-Rapid-AIO-NSFW-v19.safetensors"
PREFERRED_STAGE2 = [
    "lustifySDXLNSFW_endgame.safetensors",
    "lustifySDXLNSFWSFW_v20LIGHTNING.safetensors",
]

STRICT_IDENTITY_PREFIX = (
    "IDENTITY LOCK: image1 is the only identity/person source. image2 is POSE GEOMETRY ONLY. "
    "Use image2 only for body position, limb placement, camera angle and composition. "
    "Do not copy or transfer the face, skin tone, hair, apparent ethnicity/ancestry, age appearance, "
    "clothing, or other identifying characteristics from image2. Preserve image1's facial structure, "
    "skin tone, hair, eye appearance, recognizable features and overall identity. "
)

DEFAULT_POSE_PROMPT = (
    "Change only the body pose/body position according to image2 and/or this instruction. "
    "Photorealistic, natural skin texture, realistic anatomy, sharp focus."
)

STAGE1_NEGATIVE_DEFAULT = (
    "different face, changed identity, altered skin tone, different hair, face from pose reference, "
    "distorted face, bad anatomy, extra limbs, deformed hands, blurry, low detail"
)

POSE_MODES = [
    "AUTO — GEOMETRY FIRST (recommended)",
    "PROMPT ONLY — no pose image",
    "EXTRACT SKELETON — force DWPose",
    "DIRECT POSE PHOTO — advanced / legacy",
]

STAGE1_STRENGTH_PROFILES = {
    "NATURAL": dict(steps=5, cfg=1.0, prompt=0.85, pose=0.90, identity=1.00, negative=0.80),
    "BALANCED": dict(steps=6, cfg=1.0, prompt=1.00, pose=1.00, identity=1.20, negative=1.00),
    "STRONG": dict(steps=7, cfg=1.0, prompt=1.25, pose=1.20, identity=1.30, negative=1.10),
    "STRICT": dict(steps=8, cfg=1.0, prompt=1.40, pose=1.35, identity=1.45, negative=1.20),
    "MAX POSE": dict(steps=8, cfg=1.0, prompt=1.25, pose=1.70, identity=1.25, negative=1.10),
    "MAX IDENTITY": dict(steps=7, cfg=1.0, prompt=1.00, pose=1.00, identity=1.75, negative=1.30),
    "HYBRID STRONG": dict(steps=8, cfg=1.0, prompt=1.35, pose=1.55, identity=1.55, negative=1.20),
}


STAGE2_POSITIVE = (
    "photorealistic, preserve the same person and face, natural skin texture, realistic anatomy, "
    "sharp focus, natural lighting, detailed skin, realistic body proportions"
)
STAGE2_NEGATIVE = (
    "different face, changed identity, altered skin tone, apparent ethnicity shift, different facial structure, "
    "different hair, identity from pose reference, distorted face, plastic skin, blurry, oversaturated, "
    "extra limbs, bad anatomy, deformed hands"
)

GROK_GEOMETRY_PRESETS = {
    "BACK-LYING · HIGH": "Back-lying pose, legs raised or open as needed, high-angle camera looking down. Keep body geometry natural and preserve image1 identity.",
    "BACK-LYING · SIDE": "Back-lying pose, legs raised, clear side-profile camera angle. Preserve image1 identity and use the pose reference only for geometry.",
    "ALL-FOURS · REAR 3/4": "All-fours pose, rear three-quarter camera view, natural limb placement and body proportions. Preserve image1 identity.",
    "ALL-FOURS · LOOK BACK": "All-fours pose, head turned back toward camera over the shoulder, natural anatomy and stable body geometry. Preserve image1 identity.",
    "SEATED/TOP · LOW": "Seated or top-position pose, front low-angle camera looking slightly upward, balanced body geometry. Preserve image1 identity.",
    "SEATED/TOP · REAR": "Seated or top-position pose, rear camera view, natural torso and limb placement. Preserve image1 identity.",
    "PRONE · HIGH": "Prone face-down pose, high-angle camera, natural torso alignment and limb placement. Preserve image1 identity.",
    "STANDING BENT · SIDE": "Standing bent-forward pose, clear side-profile view, stable feet and natural spine/limb geometry. Preserve image1 identity.",
    "LEGS-UP · CLOSE 3/4": "Compressed legs-up pose, close three-quarter camera view, natural anatomy and body proportions. Preserve image1 identity.",
    "WALL · LOW": "Standing against a wall, one leg optionally raised, low-angle camera, natural body alignment. Preserve image1 identity.",
}

GROK_REFERENCE_NOTE = (
    "Grok reference presets are camera/pose guidance only. They do not replace the proven GENESIS v19 settings. "
    "Main Stage 1 remains Phr00t/Qwen Rapid v19 with low-CFG GENESIS profiles."
)

POSE_PROMPT_MODES = [
    "AUTO — prompt from selected pose",
    "MANUAL — keep my written prompt",
    "POSE ONLY — no written prompt",
]

POSE_PROMPT_PRESETS = {
    "Natural full-body": "Natural full-body pose, balanced composition, realistic anatomy and proportions.",
    "Standing portrait": "Standing pose, natural posture, full-body framing, balanced weight and realistic anatomy.",
    "Seated portrait": "Seated pose, relaxed posture, natural limb placement and realistic proportions.",
    "Reclining / lying": "Reclining pose, natural torso alignment, clear limb placement and realistic anatomy.",
    "Kneeling": "Kneeling pose, balanced posture, clear hands and feet, realistic anatomy and proportions.",
    "Squatting": "Squatting pose, stable balance, natural hip and knee alignment, realistic anatomy.",
    "All fours": "All-fours pose, stable limb placement, natural spine alignment and realistic proportions.",
    "Suspended / elevated": "Elevated or suspended pose, clear body silhouette, believable balance and realistic anatomy.",
    "Split-leg composition": "Wide or split-leg pose, symmetrical composition, natural joint alignment and realistic anatomy.",
}

POSE_CATEGORY_PRESETS = {
    "standing": "Standing portrait",
    "sitting": "Seated portrait",
    "lying": "Reclining / lying",
    "kneeling": "Kneeling",
    "squatting": "Squatting",
    "all_fours": "All fours",
    "suspended": "Suspended / elevated",
    "split_leg": "Split-leg composition",
}



def _urls(path: str):
    path = path if path.startswith("/") else "/" + path
    return [COMFY_URL + path, COMFY_URL + "/api" + path]


def get_json(path: str, timeout=20):
    last = None
    for url in _urls(path):
        try:
            r = requests.get(url, timeout=timeout)
            if r.ok:
                return r.json()
            last = RuntimeError(f"GET {url}: HTTP {r.status_code} {r.text[:200]}")
        except Exception as e:
            last = e
    raise RuntimeError(f"ComfyUI request failed: {last}")


def post_json(path: str, payload: dict, timeout=30):
    last = None
    for url in _urls(path):
        try:
            r = requests.post(url, json=payload, timeout=timeout)
            if r.ok:
                return r.json()
            last = RuntimeError(f"POST {url}: HTTP {r.status_code} {r.text[:500]}")
        except Exception as e:
            last = e
    raise RuntimeError(f"ComfyUI request failed: {last}")


def comfy_alive(timeout: float = 2.5) -> bool:
    try:
        r = requests.get(f"{COMFY_URL}/system_stats", timeout=timeout)
        return r.ok
    except Exception:
        return False


def _listener_pids(port: int = COMFY_PORT) -> list[int]:
    """Return PIDs listening on the ComfyUI port without killing anything."""
    pids: set[int] = set()

    # Preferred: ss is installed on normal Ubuntu systems.
    try:
        cp = subprocess.run(
            ["ss", "-ltnp"],
            capture_output=True, text=True, timeout=10, check=False
        )
        for line in cp.stdout.splitlines():
            if f":{port}" not in line:
                continue
            for m in re.finditer(r"pid=(\d+)", line):
                pids.add(int(m.group(1)))
    except Exception:
        pass

    # Fallback: fuser when available.
    if not pids:
        try:
            cp = subprocess.run(
                ["fuser", "-n", "tcp", str(port)],
                capture_output=True, text=True, timeout=10, check=False
            )
            for token in re.findall(r"\b\d+\b", cp.stdout + " " + cp.stderr):
                pids.add(int(token))
        except Exception:
            pass

    return sorted(pids)


def _trusted_comfy_pid(pid: int) -> bool:
    """
    Only allow GENESIS to terminate a process if it really looks like the
    user's ComfyUI server. This avoids broad pkill/python matching.
    """
    proc = Path("/proc") / str(pid)
    try:
        cmdline = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore")
    except Exception:
        cmdline = ""
    try:
        cwd = (proc / "cwd").resolve()
    except Exception:
        cwd = None

    comfy_dir = COMFY_DIR.resolve()
    cwd_ok = cwd == comfy_dir
    cmd_ok = "main.py" in cmdline and "python" in cmdline.lower()
    return bool(cwd_ok and cmd_ok)


def _memory_summary() -> str:
    vals = {}
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            key, rest = line.split(":", 1)
            vals[key] = int(rest.strip().split()[0])  # KiB
    except Exception:
        return "memory unavailable"

    avail = vals.get("MemAvailable", 0) / 1024 / 1024
    swap_free = vals.get("SwapFree", 0) / 1024 / 1024
    swap_total = vals.get("SwapTotal", 0) / 1024 / 1024
    return f"RAM available {avail:.1f} GiB · Swap free {swap_free:.1f}/{swap_total:.1f} GiB"



def _available_ram_gib() -> float:
    try:
        info = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                info[k.strip()] = int(v.strip().split()[0])
        return info.get("MemAvailable", 0) / 1024 / 1024
    except Exception:
        return 0.0


def _check_cancel():
    if CANCEL_EVENT.is_set():
        raise RunCancelled("Run cancelled by user")


def _set_active_prompt(prompt_id):
    global ACTIVE_PROMPT_ID
    with RUN_STATE_LOCK:
        ACTIVE_PROMPT_ID = prompt_id


def _set_active_stage(stage):
    global ACTIVE_STAGE
    with RUN_STATE_LOCK:
        ACTIVE_STAGE = stage


def _clear_active_prompt(prompt_id=None):
    global ACTIVE_PROMPT_ID
    with RUN_STATE_LOCK:
        if prompt_id is None or ACTIVE_PROMPT_ID == prompt_id:
            ACTIVE_PROMPT_ID = None


def _request_comfy_cancel(prompt_id=None):
    # Best effort: interrupt running work and remove a queued prompt if ComfyUI supports it.
    try:
        post_json("/interrupt", {}, timeout=3)
    except Exception:
        pass
    if prompt_id:
        try:
            post_json("/queue", {"delete": [prompt_id]}, timeout=3)
        except Exception:
            pass


def cancel_run():
    CANCEL_EVENT.set()
    with RUN_STATE_LOCK:
        prompt_id = ACTIVE_PROMPT_ID
        stage = ACTIVE_STAGE
    _request_comfy_cancel(prompt_id)
    return f"Cancel requested{f' for Stage {stage}' if stage else ''}. Completed outputs will be kept."


def memory_guard(stage_label: str, min_available_gib: float, allow_reclaim: bool = True) -> str:
    _check_cancel()
    min_available_gib = max(1.0, float(min_available_gib or MEMORY_GUARD_DEFAULT_GIB))
    before = _available_ram_gib()
    if before >= min_available_gib:
        return f"Memory guard {stage_label}: PASS · {before:.1f} GiB available"

    if allow_reclaim and comfy_alive(timeout=1):
        stop_comfyui()
        time.sleep(3)
        _check_cancel()

    after = _available_ram_gib()
    if after < min_available_gib:
        raise RuntimeError(
            f"Memory guard blocked {stage_label}: only {after:.1f} GiB RAM available; "
            f"requires at least {min_available_gib:.1f} GiB. Close memory-heavy apps and retry."
        )
    return f"Memory guard {stage_label}: reclaimed RAM · {before:.1f} → {after:.1f} GiB available"

def stop_comfyui() -> str:
    """
    Stop only the process currently listening on 127.0.0.1:8188, and only
    when its cwd/cmdline identify it as ~/AI/ComfyUI/python main.py.
    """
    if not comfy_alive():
        return "ComfyUI already stopped"

    # Ask ComfyUI to stop work first. Failure here is non-fatal.
    try:
        requests.post(f"{COMFY_URL}/interrupt", json={}, timeout=3)
    except Exception:
        pass

    pids = _listener_pids()
    trusted = [pid for pid in pids if _trusted_comfy_pid(pid)]
    if not trusted:
        raise RuntimeError(
            "Memory-safe restart refused: port 8188 is active but GENESIS could not "
            "verify that the listener is your ~/AI/ComfyUI python main.py process."
        )

    for pid in trusted:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    deadline = time.time() + 20
    while time.time() < deadline:
        if not comfy_alive(timeout=1):
            break
        time.sleep(0.5)

    # Escalate only for the same already-verified PIDs.
    if comfy_alive(timeout=1):
        for pid in trusted:
            if _trusted_comfy_pid(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    deadline = time.time() + 10
    while time.time() < deadline and comfy_alive(timeout=1):
        time.sleep(0.5)

    if comfy_alive(timeout=1):
        raise RuntimeError("ComfyUI did not stop cleanly.")

    global COMFY_STARTED_BY_GENESIS
    COMFY_STARTED_BY_GENESIS = False
    object_info.cache_clear()
    return f"Stopped ComfyUI PID(s) {', '.join(map(str, trusted))}"


def start_comfyui() -> str:
    global COMFY_STARTED_BY_GENESIS
    _check_cancel()
    if comfy_alive():
        return "ComfyUI already running"

    if not COMFY_DIR.exists():
        raise RuntimeError(f"ComfyUI folder not found: {COMFY_DIR}")
    if not CONDA_SH.exists():
        raise RuntimeError(f"Conda startup script not found: {CONDA_SH}")

    cmd = (
        f'source "{CONDA_SH}" && '
        f'conda activate "{COMFY_ENV}" && '
        'exec python main.py --disable-pinned-memory --async-offload 1 --reserve-vram 1 --vram-headroom 1 --preview-method none'
    )

    log_fh = open(COMFY_MANAGED_LOG, "a", buffering=1)
    log_fh.write(
        f"\n\n===== GENESIS V13 managed ComfyUI start {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n"
    )
    subprocess.Popen(
        ["bash", "-lc", cmd],
        cwd=str(COMFY_DIR),
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    COMFY_STARTED_BY_GENESIS = True

    deadline = time.time() + COMFY_START_TIMEOUT
    last_error = ""
    while time.time() < deadline:
        if CANCEL_EVENT.is_set():
            try:
                stop_comfyui()
            except Exception:
                pass
            raise RunCancelled("Run cancelled while starting ComfyUI")
        if comfy_alive(timeout=2):
            object_info.cache_clear()
            return f"ComfyUI started on demand · {_memory_summary()}"
        try:
            if COMFY_MANAGED_LOG.exists():
                tail = COMFY_MANAGED_LOG.read_text(errors="ignore").splitlines()[-8:]
                last_error = " | ".join(tail[-3:])
        except Exception:
            pass
        time.sleep(0.5)

    raise RuntimeError(
        f"ComfyUI did not come back within {COMFY_START_TIMEOUT}s. "
        f"Check {COMFY_MANAGED_LOG}. Last log: {last_error}"
    )


def restart_comfyui_between_stages(label: str) -> str:
    _check_cancel()
    before = _memory_summary()
    stopped = stop_comfyui() if comfy_alive(timeout=1) else "ComfyUI already stopped"
    for _ in range(6):
        _check_cancel()
        time.sleep(0.5)
    started = start_comfyui()
    _check_cancel()
    after = _memory_summary()
    return f"{label}: {stopped}; {started}; before [{before}] → after [{after}]"


def _stage_badge(state: str, detail: str = "", elapsed: float | None = None,
                 progress_value: float | None = None, progress_text: str = "") -> str:
    state = state.upper()
    css_state = {
        "RUNNING": "running", "DONE": "done", "WAITING": "waiting",
        "SKIPPED": "skipped", "RESTARTING": "restarting", "ERROR": "error",
        "READY": "ready", "CANCELLED": "cancelled",
    }.get(state, "ready")
    detail_html = f'<span class="stage-detail">{detail}</span>' if detail else ""

    # Live timer/progress only exists in the currently active stage box.
    timer_html = ""
    progress_html = ""
    if state in {"RUNNING", "RESTARTING"}:
        if elapsed is not None:
            timer_html = f'<span class="stage-live-time">{elapsed:.1f}s</span>'
        if progress_value is not None:
            pct = max(0.0, min(float(progress_value), 1.0)) * 100.0
            progress_html = (
                '<div class="stage-progress-wrap">'
                f'<div class="stage-progress-fill" style="width:{pct:.1f}%"></div>'
                '</div>'
                f'<div class="stage-progress-text">{progress_text or f"{pct:.0f}%"}</div>'
            )
    elif state == "DONE" and elapsed is not None:
        timer_html = f'<span class="stage-final-time">{elapsed:.1f}s</span>'

    return (
        f'<div class="stage-status-shell state-{css_state}">'
        '<div class="stage-status-top">'
        f'<div class="stage-badge state-{css_state}"><span class="stage-dot"></span>'
        f'<strong>{state}</strong>{detail_html}</div>{timer_html}</div>'
        f'{progress_html}</div>'
    )


def upload_image(img: Image.Image, label: str) -> str:
    if img is None:
        raise ValueError(f"Missing image: {label}")
    if not isinstance(img, Image.Image):
        img = Image.open(img)
    img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    filename = f"genesis_{label}_{uuid.uuid4().hex[:10]}.png"
    last = None
    for url in _urls("/upload/image"):
        try:
            files = {"image": (filename, buf.getvalue(), "image/png")}
            data = {"type": "input", "overwrite": "true"}
            r = requests.post(url, files=files, data=data, timeout=60)
            if r.ok:
                data = r.json()
                return data.get("name") or filename
            last = RuntimeError(f"UPLOAD {url}: HTTP {r.status_code} {r.text[:300]}")
        except Exception as e:
            last = e
    raise RuntimeError(f"Image upload failed: {last}")


@lru_cache(maxsize=1)
def object_info() -> dict:
    return get_json("/object_info", timeout=30)


def refresh_object_info():
    object_info.cache_clear()
    return object_info()


def _schema(class_type: str):
    info = object_info()
    if class_type not in info:
        raise RuntimeError(f"Required ComfyUI node is missing: {class_type}")
    return info[class_type].get("input", {})


def _combo_match(value, choices):
    if value in choices:
        return value
    s = str(value).lower()
    for c in choices:
        if str(c).lower() == s:
            return c
    for c in choices:
        cl = str(c).lower()
        if s in cl or cl in s:
            return c
    return value


def _default_for(spec):
    if not isinstance(spec, (list, tuple)) or not spec:
        return None
    typ = spec[0]
    meta = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
    if "default" in meta:
        return meta["default"]
    if isinstance(typ, list) and typ:
        return typ[0]
    if typ == "INT":
        return 0
    if typ == "FLOAT":
        return 0.0
    if typ == "BOOLEAN":
        return False
    if typ == "STRING":
        return ""
    return None


def make_node(class_type: str, desired: dict) -> dict:
    schema = _schema(class_type)
    required = schema.get("required", {})
    optional = schema.get("optional", {})
    inputs = {}
    for name, spec in required.items():
        if name in desired:
            val = desired[name]
            if isinstance(spec, (list, tuple)) and spec and isinstance(spec[0], list) and not isinstance(val, list):
                val = _combo_match(val, spec[0])
            inputs[name] = val
        else:
            default = _default_for(spec)
            if default is not None:
                inputs[name] = default
    for name, val in desired.items():
        if name in required or name in optional:
            spec = required.get(name, optional.get(name))
            if isinstance(spec, (list, tuple)) and spec and isinstance(spec[0], list) and not isinstance(val, list):
                val = _combo_match(val, spec[0])
            inputs[name] = val
    return {"class_type": class_type, "inputs": inputs}


def available_checkpoints():
    spec = _schema("CheckpointLoaderSimple").get("required", {}).get("ckpt_name")
    if isinstance(spec, (list, tuple)) and spec and isinstance(spec[0], list):
        return list(spec[0])
    return []


def pick_checkpoint(preferred):
    choices = available_checkpoints()
    if isinstance(preferred, str):
        preferred = [preferred]
    for p in preferred:
        m = _combo_match(p, choices)
        if m in choices:
            return m
    needles = ["qwen-rapid" if "qwen" in p.lower() else "lustify" for p in preferred]
    for n in needles:
        for c in choices:
            if n in str(c).lower():
                return c
    raise RuntimeError(
        "Required checkpoint not found. Available checkpoints include:\n" + "\n".join(map(str, choices[:50]))
    )


def queue_and_wait(prompt: dict, progress_cb=None, progress_label: str = "ComfyUI"):
    """Queue one prompt, report real ComfyUI sampler progress, and support cancellation."""
    _check_cancel()
    client_id = str(uuid.uuid4())
    ws = None
    try:
        ws = websocket.WebSocket()
        ws.settimeout(0.35)
        ws.connect(f"ws://127.0.0.1:{COMFY_PORT}/ws?clientId={client_id}")
    except Exception:
        ws = None

    queued = post_json("/prompt", {"prompt": prompt, "client_id": client_id}, timeout=20)
    prompt_id = queued.get("prompt_id")
    if not prompt_id:
        if ws:
            try: ws.close()
            except Exception: pass
        raise RuntimeError(f"ComfyUI did not return prompt_id: {queued}")

    _set_active_prompt(prompt_id)
    if progress_cb:
        progress_cb(0, 0, f"{progress_label} · queued")

    deadline = time.time() + TIMEOUT_SECONDS
    last_status = None
    execution_done = False
    try:
        while time.time() < deadline:
            if CANCEL_EVENT.is_set():
                _request_comfy_cancel(prompt_id)
                raise RunCancelled("Run cancelled by user")

            if ws is not None:
                try:
                    out = ws.recv()
                    if isinstance(out, str):
                        message = json.loads(out)
                        mtype = message.get("type")
                        data = message.get("data") or {}
                        event_prompt_id = data.get("prompt_id")
                        if event_prompt_id and event_prompt_id != prompt_id:
                            continue

                        if mtype == "progress":
                            value = data.get("value")
                            maximum = data.get("max")
                            if progress_cb and isinstance(value, (int, float)) and isinstance(maximum, (int, float)):
                                progress_cb(int(value), int(maximum or 0), f"{progress_label} · step {int(value)}/{int(maximum or 0)}")
                        elif mtype == "executing":
                            if data.get("node") is None and data.get("prompt_id") == prompt_id:
                                execution_done = True
                        elif mtype == "execution_interrupted":
                            raise RunCancelled("ComfyUI execution interrupted")
                        elif mtype == "execution_error":
                            raise RuntimeError(f"ComfyUI execution_error: {data}")
                except websocket.WebSocketTimeoutException:
                    pass
                except (RunCancelled, RuntimeError):
                    raise
                except Exception:
                    try: ws.close()
                    except Exception: pass
                    ws = None

            # Short polling timeout keeps CANCEL responsive even when WS is unavailable.
            try:
                hist = get_json(f"/history/{prompt_id}", timeout=3)
            except Exception:
                hist = {}
            entry = None
            if isinstance(hist, dict):
                entry = hist.get(prompt_id)
                if entry is None and "history" in hist and isinstance(hist["history"], list):
                    for item in hist["history"]:
                        if item.get("prompt_id") == prompt_id:
                            entry = item
                            break
            if entry:
                last_status = entry.get("status")
                outputs = entry.get("outputs", {})
                if outputs:
                    if progress_cb:
                        progress_cb(1, 1, f"{progress_label} · complete")
                    return prompt_id, outputs
                status = entry.get("status", {})
                if isinstance(status, dict) and status.get("completed") is False:
                    msgs = status.get("messages") or []
                    if any("error" in str(m).lower() for m in msgs):
                        raise RuntimeError(f"ComfyUI execution failed: {status}")
            time.sleep(0.10 if execution_done else 0.20)

        raise TimeoutError(f"ComfyUI timed out after {TIMEOUT_SECONDS}s. Last status: {last_status}")
    finally:
        _clear_active_prompt(prompt_id)
        if ws is not None:
            try: ws.close()
            except Exception: pass


def fetch_output_image(outputs: dict, save_node_id: str) -> Image.Image:
    node = outputs.get(str(save_node_id)) or outputs.get(int(save_node_id))
    if not node:
        for v in outputs.values():
            if isinstance(v, dict) and v.get("images"):
                node = v
        if not node:
            raise RuntimeError(f"No image output found. Output nodes: {list(outputs)}")
    images = node.get("images") or []
    if not images:
        raise RuntimeError("Save node completed but returned no image metadata.")
    meta = images[-1]
    params = {
        "filename": meta["filename"],
        "subfolder": meta.get("subfolder", ""),
        "type": meta.get("type", "output"),
    }
    last = None
    for url in _urls("/view"):
        try:
            r = requests.get(url, params=params, timeout=120)
            if r.ok:
                return Image.open(io.BytesIO(r.content)).convert("RGB")
            last = RuntimeError(f"VIEW {url}: HTTP {r.status_code}")
        except Exception as e:
            last = e
    raise RuntimeError(f"Could not retrieve output image: {last}")


def _generated_image_issue(img) -> str | None:
    """Return a short failure reason for unusable generated output."""
    if img is None:
        return "no output image"
    im = img if isinstance(img, Image.Image) else Image.open(img)
    w, h = im.size
    if w < 64 or h < 64:
        return f"image is only {w}×{h}"
    extrema = im.convert("L").getextrema()
    if extrema and extrema[1] - extrema[0] < 2:
        return "output is blank/flat (ROCm/VAE generation failure)"
    return None


def _model_profile_name(model_name: str) -> str:
    name = (model_name or "").lower()
    if "qwen" in name or "rapid" in name:
        return "QWEN RAPID · 4–8 step profile"
    if "lightning" in name:
        return "SDXL LIGHTNING · low-step profile (not valid in the Qwen Stage 1 engine)"
    if "sdxl" in name or "xl" in name:
        return "SDXL · normal-step profile (requires SDXL Stage 1 engine)"
    return "GENERIC / UNKNOWN · verify model family before generation"


def model_profile_status(model_name: str) -> str:
    return f"Model-aware profile: {_model_profile_name(model_name)}"


def apply_stage1_strength_profile(profile: str, model_name: str,
                                  current_steps, current_cfg,
                                  current_prompt, current_pose, current_identity, current_negative):
    profile = (profile or "BALANCED").upper()
    if profile == "CUSTOM" or profile not in STAGE1_STRENGTH_PROFILES:
        return (current_steps, current_cfg, current_prompt, current_pose, current_identity, current_negative,
                f"CUSTOM · {_model_profile_name(model_name)}")
    p = STAGE1_STRENGTH_PROFILES[profile]
    return (p["steps"], p["cfg"], p["prompt"], p["pose"], p["identity"], p["negative"],
            f"{profile} · {_model_profile_name(model_name)} · Qwen strength changes instructions/conditioning, not a fake high CFG")


def _strength_level(value: float) -> str:
    value = float(value)
    if value >= 1.55:
        return "VERY HIGH"
    if value >= 1.25:
        return "HIGH"
    if value <= 0.85:
        return "SOFT"
    return "BALANCED"


def _compose_stage1_prompt(user_prompt: str, negative_prompt: str, strict_identity_lock: bool,
                           strength_profile: str, prompt_strength: float, pose_strength: float,
                           identity_strength: float, negative_strength: float,
                           pose_used: bool, pose_is_map: bool) -> str:
    user_prompt = (user_prompt or "").strip()
    parts = []
    if strict_identity_lock:
        parts.append(
            "IDENTITY LOCK: image1 is the only identity/person source. Preserve image1's recognizable face, "
            "facial structure, skin tone, hair, eye appearance, age appearance and overall identity. "
            f"Identity priority: {_strength_level(identity_strength)}."
        )
    if pose_used:
        if pose_is_map:
            parts.append(
                "image2 is a pose skeleton / pose map. Use image2 ONLY for body position, limb placement, "
                "orientation, camera angle and composition. Do not copy appearance from image2. "
                f"Pose priority: {_strength_level(pose_strength)}."
            )
        else:
            parts.append(
                "image2 is a pose reference. Use it for pose geometry only, not identity or appearance. "
                f"Pose priority: {_strength_level(pose_strength)}."
            )
    prompt_level = _strength_level(prompt_strength)
    if prompt_level == "VERY HIGH":
        parts.append("Follow the written instruction very literally; do not improvise away from the requested pose.")
    elif prompt_level == "HIGH":
        parts.append("Follow the written instruction closely and prioritize the requested pose details.")
    elif prompt_level == "SOFT":
        parts.append("Interpret the written instruction naturally while preserving a realistic result.")
    if user_prompt:
        parts.append(user_prompt)
    neg = (negative_prompt or "").strip()
    if neg and float(negative_strength) > 0:
        prefix = "Strongly avoid" if float(negative_strength) >= 1.2 else "Avoid"
        parts.append(f"{prefix}: {neg}.")
    parts.append(f"GENESIS strength profile: {(strength_profile or 'BALANCED').upper()}.")
    return " ".join(x.strip() for x in parts if x and x.strip())


def _dwpose_desired(image_link):
    # make_node() fills any required settings we do not specify from the node schema.
    # These common names are used when available and safely ignored when a build names them differently.
    return {
        "image": image_link,
        "detect_hand": "enable",
        "detect_body": "enable",
        "detect_face": "enable",
        "resolution": 512,
        "bbox_detector": "yolox_l.onnx",
        "pose_estimator": "dw-ll_ucoco_384.onnx",
    }


def run_stage1(source, pose, pose_prompt, negative_prompt, pose_mode, pose_source_kind,
               strength_profile, prompt_strength, pose_strength, identity_strength, negative_strength,
               model_name, width, height, seed, steps, cfg, sampler, scheduler,
               strict_identity_lock=True, progress_cb=None):
    ckpt = pick_checkpoint(model_name or PREFERRED_STAGE1)
    profile = _model_profile_name(ckpt)
    if not ("qwen" in ckpt.lower() or "rapid" in ckpt.lower()):
        raise RuntimeError(
            f"Stage 1 is currently the Qwen/Phr00t edit engine, but '{ckpt}' does not look Qwen-compatible. "
            "Use the Phr00t/Qwen checkpoint here; Lustify belongs in Stage 2."
        )

    source_name = upload_image(source, "source")
    prompt = {}
    prompt["1"] = make_node("CheckpointLoaderSimple", {"ckpt_name": ckpt})
    prompt["2"] = make_node("LoadImage", {"image": source_name})

    mode = (pose_mode or POSE_MODES[0]).upper()
    kind = (pose_source_kind or "photo").lower()
    use_pose = pose is not None and not mode.startswith("PROMPT ONLY")
    pose_is_map = False
    pose_note = "Prompt-only pose control"
    pose_link = None

    if use_pose:
        pose_name = upload_image(pose, "pose")
        prompt["3"] = make_node("LoadImage", {"image": pose_name})
        if mode.startswith("DIRECT"):
            pose_link = ["3", 0]
            pose_note = "Legacy direct pose photo supplied to Qwen"
        elif kind == "skeleton" and not mode.startswith("EXTRACT"):
            pose_link = ["3", 0]
            pose_is_map = True
            pose_note = "Pose library skeleton supplied directly to Qwen"
        else:
            if "DWPreprocessor" in object_info():
                prompt["10"] = make_node("DWPreprocessor", _dwpose_desired(["3", 0]))
                pose_link = ["10", 0]
                pose_is_map = True
                pose_note = "DWPose extracted geometry from the uploaded pose photo"
            else:
                raise RuntimeError(
                    "Geometry-first pose mode requires DWPreprocessor for uploaded pose photos, but ComfyUI does not expose it. "
                    "Install/enable comfyui_controlnet_aux / DWPose, choose a Pose Library skeleton, use PROMPT ONLY, "
                    "or explicitly choose DIRECT POSE PHOTO if you want the legacy appearance-reference path."
                )

    qwen_inputs = {
        "clip": ["1", 1], "vae": ["1", 2], "image1": ["2", 0],
        "prompt": _compose_stage1_prompt(
            pose_prompt, negative_prompt, bool(strict_identity_lock), strength_profile,
            prompt_strength, pose_strength, identity_strength, negative_strength,
            bool(pose_link), bool(pose_is_map),
        ),
    }
    if pose_link:
        qwen_inputs["image2"] = pose_link
    prompt["4"] = make_node("TextEncodeQwenImageEditPlus", qwen_inputs)
    prompt["5"] = make_node("ConditioningZeroOut", {"conditioning": ["4", 0]})
    prompt["6"] = make_node("EmptyLatentImage", {"width": int(width), "height": int(height), "batch_size": 1})
    prompt["7"] = make_node("KSampler", {
        "model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0],
        "seed": int(seed), "steps": int(steps), "cfg": float(cfg),
        "sampler_name": str(sampler), "scheduler": str(scheduler), "denoise": 1.0,
    })
    prompt["8"] = make_node("VAEDecode", {"samples": ["7", 0], "vae": ["1", 2]})
    prompt["9"] = make_node("SaveImage", {"images": ["8", 0], "filename_prefix": "GENESIS_STAGE1_PHR00T"})
    _, outputs = queue_and_wait(prompt, progress_cb, "Stage 1 · Phr00t")
    image = fetch_output_image(outputs, "9")
    issue = _generated_image_issue(image)
    if issue:
        raise RuntimeError(
            f"Phr00t Stage 1 completed but {issue}. The image was saved for diagnosis, "
            "but GENESIS will not pass it into a refinement model. Restart ComfyUI and retry."
        )
    return image, ckpt, f"{pose_note} · {profile}"


def preview_pose_geometry(pose, pose_source_kind, pose_mode, on_demand_backend, memory_guard_gib):
    if pose is None:
        return None, "No pose picture selected. Written-prompt-only mode does not need a pose map."
    kind = (pose_source_kind or "photo").lower()
    mode = (pose_mode or POSE_MODES[0]).upper()
    if kind == "skeleton" and not mode.startswith("EXTRACT"):
        return pose, "Pose Library item is already a skeleton / geometry map — no DWPose conversion needed."
    if mode.startswith("DIRECT"):
        return pose, "DIRECT POSE PHOTO selected — geometry preview is the original pose photo."

    log = []
    try:
        _ensure_backend_for_stage("Pose Geometry Preview", memory_guard_gib, log)
        if "DWPreprocessor" not in object_info():
            return None, "DWPreprocessor is not available. AUTO geometry-first will NOT fall back to appearance. Install/enable DWPose, choose a library skeleton, or explicitly select DIRECT POSE PHOTO."
        name = upload_image(pose, "pose_preview")
        prompt = {
            "1": make_node("LoadImage", {"image": name}),
            "2": make_node("DWPreprocessor", _dwpose_desired(["1", 0])),
            "3": make_node("SaveImage", {"images": ["2", 0], "filename_prefix": "GENESIS_DWPOSE_PREVIEW"}),
        }
        _, outputs = queue_and_wait(prompt, None, "Pose Geometry Preview")
        image = fetch_output_image(outputs, "3")
        return image, "PASS · DWPose geometry extracted. This map is what AUTO will use as image2."
    finally:
        _finish_on_demand_backend(bool(on_demand_backend), log)


def verify_image_output(img, label: str):
    try:
        if img is None:
            return f"FAIL · {label}: no output image", _stage_badge("FAIL", "no output")
        im = img if isinstance(img, Image.Image) else Image.open(img)
        w, h = im.size
        issue = _generated_image_issue(im)
        if issue:
            return f"FAIL · {label}: {issue}", _stage_badge("FAIL", issue[:80])
        return f"PASS · {label}: valid image {w}×{h}", _stage_badge("PASS", f"{w}×{h}")
    except Exception as e:
        return f"FAIL · {label}: {e}", _stage_badge("FAIL", str(e)[:80])


def verify_stage1(img): return verify_image_output(img, "Stage 1")
def verify_stage2(img): return verify_image_output(img, "Stage 2")
def verify_stage3(img): return verify_image_output(img, "Stage 3")


def run_stage2(stage1_img, model_name, seed, denoise, positive_prompt, negative_prompt,
               steps, cfg, sampler, scheduler, progress_cb=None):
    ckpt = pick_checkpoint(model_name or PREFERRED_STAGE2)
    image_name = upload_image(stage1_img, "stage1")
    prompt = {
        "1": make_node("CheckpointLoaderSimple", {"ckpt_name": ckpt}),
        "2": make_node("LoadImage", {"image": image_name}),
        "3": make_node("VAEEncode", {"pixels": ["2", 0], "vae": ["1", 2]}),
        "4": make_node("CLIPTextEncode", {"clip": ["1", 1], "text": (positive_prompt or STAGE2_POSITIVE).strip()}),
        "5": make_node("CLIPTextEncode", {"clip": ["1", 1], "text": (negative_prompt or STAGE2_NEGATIVE).strip()}),
        "6": make_node("KSampler", {
            "model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["3", 0],
            "seed": int(seed), "steps": int(steps), "cfg": float(cfg),
            "sampler_name": str(sampler), "scheduler": str(scheduler), "denoise": float(denoise),
        }),
        "7": make_node("VAEDecode", {"samples": ["6", 0], "vae": ["1", 2]}),
        "8": make_node("SaveImage", {"images": ["7", 0], "filename_prefix": "GENESIS_STAGE2_LUSTIFY"}),
    }
    _, outputs = queue_and_wait(prompt, progress_cb, "Stage 2 · Lustify")
    return fetch_output_image(outputs, "8"), ckpt


def run_stage3(target_img, source_img, swap_model, detector, source_face_index, target_face_index,
               face_restore, restore_model, restore_visibility, codeformer_weight, progress_cb=None):
    target_name = upload_image(target_img, "stage2")
    source_name = upload_image(source_img, "face")
    reactor_inputs = {
        "enabled": True, "input_image": ["1", 0], "source_image": ["2", 0],
        "swap_model": str(swap_model or "inswapper_128.onnx"),
        "facedetection": str(detector or "retinaface_resnet50"),
        "face_restore_model": str(restore_model or "CodeFormer") if face_restore else "none",
        "face_restore_visibility": float(restore_visibility),
        "codeformer_weight": float(codeformer_weight),
        "detect_gender_input": "no", "detect_gender_source": "no",
        "input_faces_index": str(target_face_index), "source_faces_index": str(source_face_index),
        "console_log_level": 1,
    }
    prompt = {
        "1": make_node("LoadImage", {"image": target_name}),
        "2": make_node("LoadImage", {"image": source_name}),
        "3": make_node("ReActorFaceSwap", reactor_inputs),
        "4": make_node("SaveImage", {"images": ["3", 0], "filename_prefix": "GENESIS_STAGE3_REACTOR_ROCM"}),
    }
    _, outputs = queue_and_wait(prompt, progress_cb, "Stage 3 · ReActor")
    return fetch_output_image(outputs, "4")


def pose_route_status(pose, pose_source_kind, pose_mode):
    mode = (pose_mode or POSE_MODES[0]).upper()
    kind = (pose_source_kind or "photo").lower()
    if mode.startswith("PROMPT ONLY"):
        return "ROUTE: WRITTEN PROMPT ONLY · no pose image will be used"
    if pose is None:
        return "ROUTE: WRITTEN PROMPT ONLY · add a pose image or library skeleton for exact geometry"
    if mode.startswith("DIRECT"):
        return "ROUTE: DIRECT PHOTO · advanced/legacy appearance-reference path (explicit opt-in)"
    if kind == "skeleton" and not mode.startswith("EXTRACT"):
        return "ROUTE: LIBRARY SKELETON → PHR00T image2 · no DWPose conversion needed"
    return "ROUTE: POSE PHOTO → DWPose body/hands/face geometry → rendered skeleton → PHR00T image2"


def custom_node_report():
    try:
        refresh_object_info()
        info = object_info()
    except Exception as e:
        return f"ComfyUI unavailable: {e}"

    required = [
        ("TextEncodeQwenImageEditPlus", "Phr00t/Qwen Stage 1"),
        ("DWPreprocessor", "Geometry-first uploaded pose photos"),
        ("ReActorFaceSwap", "Stage 3 identity lock"),
    ]
    optional = [
        ("FaceDetailer", "Optional post-ReActor polish"),
        ("UltimateSDUpscale", "Optional final upscale"),
        ("ControlNetLoader", "Future separate SDXL/OpenPose test workflow"),
        ("ControlNetApplyAdvanced", "Future separate SDXL/OpenPose test workflow"),
    ]
    lines = ["GENESIS NODE HEALTH"]
    for node, purpose in required:
        lines.append(f"{'PASS' if node in info else 'MISSING'} · REQUIRED · {node} · {purpose}")
    for node, purpose in optional:
        lines.append(f"{'FOUND' if node in info else 'NOT INSTALLED'} · OPTIONAL · {node} · {purpose}")
    lines.append("NOT REQUIRED · InstantID · intentionally excluded from the main GENESIS pipeline")
    return "\n".join(lines)


def connection_test():
    try:
        refresh_object_info()
        stats = get_json("/system_stats", timeout=15)
        needed = ["CheckpointLoaderSimple", "TextEncodeQwenImageEditPlus", "KSampler", "DWPreprocessor", "ReActorFaceSwap"]
        missing = [n for n in needed if n not in object_info()]
        if missing:
            return "Connected, but missing nodes: " + ", ".join(missing)
        cps = available_checkpoints()
        p1 = _combo_match(PREFERRED_STAGE1, cps)
        p2 = next((_combo_match(x, cps) for x in PREFERRED_STAGE2 if _combo_match(x, cps) in cps), "not found")
        device = ""
        try:
            devices = stats.get("devices") or stats.get("system", {}).get("devices") or []
            if devices:
                device = str(devices[0].get("name") or devices[0])
        except Exception:
            pass
        return f"ComfyUI connected | GPU: {device or 'detected'} | Stage1: {p1} | Stage2: {p2}"
    except Exception as e:
        return f"Error: {e}"


def _resolve_seed(value):
    try:
        value = int(value)
    except Exception:
        value = -1
    return value if value >= 0 else random.randint(0, 2**63 - 1)


def _threaded_call(callable_with_cb):
    """Run blocking ComfyUI work in a worker thread while yielding live timer/progress snapshots."""
    events = pyqueue.Queue()
    result = {}
    started = time.monotonic()
    last_value = None
    last_max = None
    last_text = "queued"

    def cb(value, maximum, text):
        events.put((value, maximum, text))

    def worker():
        try:
            result["value"] = callable_with_cb(cb)
        except BaseException as e:
            result["error"] = e
        finally:
            result["done"] = True

    th = threading.Thread(target=worker, daemon=True)
    th.start()
    while not result.get("done") or not events.empty():
        _check_cancel()
        try:
            while True:
                last_value, last_max, last_text = events.get_nowait()
        except pyqueue.Empty:
            pass
        elapsed = time.monotonic() - started
        pct = None
        if isinstance(last_value, (int, float)) and isinstance(last_max, (int, float)) and last_max:
            pct = max(0.0, min(float(last_value) / float(last_max), 1.0))
        yield elapsed, pct, last_text
        time.sleep(0.25)

    if "error" in result:
        raise result["error"]
    return result.get("value")


def _ensure_backend_for_stage(stage_label: str, memory_guard_gib: float, log: list[str]):
    log.append(memory_guard(stage_label, memory_guard_gib, allow_reclaim=True))
    _check_cancel()
    if not comfy_alive(timeout=1.5):
        log.append(start_comfyui())
    _check_cancel()
    available = _available_ram_gib()
    if available and available < float(memory_guard_gib):
        try: stop_comfyui()
        except Exception: pass
        raise RuntimeError(
            f"Memory guard blocked {stage_label} after backend start: {available:.1f} GiB available."
        )
    refresh_object_info()


def _finish_on_demand_backend(on_demand_backend: bool, log: list[str]):
    if on_demand_backend and COMFY_STARTED_BY_GENESIS and comfy_alive(timeout=1):
        try:
            log.append("Idle cleanup: " + stop_comfyui())
        except Exception as e:
            log.append(f"Idle cleanup warning: {e}")


def run_stage2_from_existing(
    stage1_img, stage2_workflow, stage2_model, stage2_width, stage2_height,
    stage2_seed, stage2_denoise, stage2_positive, stage2_negative,
    stage2_steps, stage2_cfg, stage2_sampler, stage2_scheduler,
    stage2_lora1_name, stage2_lora1_strength, stage2_lora2_name, stage2_lora2_strength,
    memory_safe_restart, on_demand_backend, memory_guard_gib,
):
    CANCEL_EVENT.clear()
    _set_active_stage(2)
    if stage1_img is None:
        yield None, "No Stage 1 image is loaded. Run Stage 1 first.", _stage_badge("ERROR")
        return

    seed = _resolve_seed(stage2_seed)
    log = []
    try:
        if memory_safe_restart and comfy_alive(timeout=1):
            restart_started = time.monotonic()
            yield None, "Restarting ComfyUI before Stage 2…", _stage_badge("RESTARTING", "freeing previous model memory", 0.0)
            log.append(restart_comfyui_between_stages("Before Stage 2 reuse"))
            log.append(f"Restart handoff: {time.monotonic()-restart_started:.1f}s")
        else:
            _ensure_backend_for_stage("Stage 2", memory_guard_gib, log)

        runner = _threaded_call(lambda cb: run_stage2_workflow(
            stage1_img, stage2_workflow, stage2_model, stage2_width, stage2_height,
            seed, stage2_denoise, stage2_positive, stage2_negative,
            stage2_steps, stage2_cfg, stage2_sampler, stage2_scheduler,
            stage2_lora1_name, stage2_lora1_strength, stage2_lora2_name, stage2_lora2_strength, cb
        ))
        while True:
            try:
                elapsed, pct, ptext = next(runner)
            except StopIteration as stop:
                s2, ckpt = stop.value
                break
            yield None, "\n".join(log + ["Stage 2 running…"]), _stage_badge("RUNNING", str(stage2_workflow), elapsed, pct, ptext)

        elapsed = elapsed if 'elapsed' in locals() else 0.0
        log.append(f"Stage 2 · {stage2_workflow}: {elapsed:.1f}s · {ckpt}")
        log.append(f"Seed {seed}")
        _finish_on_demand_backend(on_demand_backend, log)
        yield s2, "\n".join(log), _stage_badge("DONE", str(stage2_workflow), elapsed)

    except RunCancelled as e:
        _request_comfy_cancel()
        _finish_on_demand_backend(on_demand_backend, log)
        yield None, "\n".join(log + ["Run cancelled by user"]), _stage_badge("CANCELLED", str(stage2_workflow))
    except Exception as e:
        yield None, "\n".join(log + [f"ERROR · {e}"]), _stage_badge("ERROR", str(e)[:100])
    finally:
        _set_active_stage(None)


def run_stage3_from_existing(
    stage2_img, source_img, swap_model, detector, source_face_index, target_face_index,
    face_restore, restore_model, restore_visibility, codeformer_weight,
    memory_safe_restart, on_demand_backend, memory_guard_gib,
):
    CANCEL_EVENT.clear()
    _set_active_stage(3)
    if stage2_img is None:
        yield None, "No Stage 2 image is loaded. Run Stage 2 first.", _stage_badge("ERROR")
        return
    if source_img is None:
        yield None, "No source/person image is loaded for ReActor.", _stage_badge("ERROR")
        return

    log = []
    try:
        if memory_safe_restart and comfy_alive(timeout=1):
            yield None, "Restarting ComfyUI before Stage 3…", _stage_badge("RESTARTING", "freeing previous model memory", 0.0)
            log.append(restart_comfyui_between_stages("Before Stage 3 reuse"))
        else:
            _ensure_backend_for_stage("Stage 3", memory_guard_gib, log)

        runner = _threaded_call(lambda cb: run_stage3(
            stage2_img, source_img, swap_model, detector, source_face_index, target_face_index,
            face_restore, restore_model, restore_visibility, codeformer_weight, cb
        ))
        while True:
            try:
                elapsed, pct, ptext = next(runner)
            except StopIteration as stop:
                s3 = stop.value
                break
            yield None, "\n".join(log + ["Stage 3 running…"]), _stage_badge("RUNNING", "ReActor ROCm", elapsed, pct, ptext)

        elapsed = elapsed if 'elapsed' in locals() else 0.0
        log.append(f"Stage 3 · ReActor: {elapsed:.1f}s")
        _finish_on_demand_backend(on_demand_backend, log)
        yield s3, "\n".join(log), _stage_badge("DONE", "ReActor", elapsed)

    except RunCancelled:
        _request_comfy_cancel()
        _finish_on_demand_backend(on_demand_backend, log)
        yield None, "\n".join(log + ["Run cancelled by user"]), _stage_badge("CANCELLED", "ReActor")
    except Exception as e:
        yield None, "\n".join(log + [f"ERROR · {e}"]), _stage_badge("ERROR", str(e)[:100])
    finally:
        _set_active_stage(None)



# ============================================================
# GENESIS MODEL TESTERS
# Added locally after verified ComfyUI/model inspection.
#
# Important:
# - The verified tester graphs are also available as reusable Stage 2 refiners.
# - Klein/Aisha use the verified Flux.2/Qwen stack.
# - FluxUp uses its verified Flux.1 stack.
# - Every stage remains runnable separately for 16 GB VRAM safety.
# ============================================================

GENESIS_TESTER_KLEIN = "KLEIN 9B KV"
GENESIS_TESTER_AISHA = "AISHA 9B"
GENESIS_TESTER_PERSEPHONE = "PERSEPHONE Q8 GGUF"
GENESIS_TESTER_FLUXUP_FP8 = "FLUXUP FP8"
GENESIS_TESTER_FLUXUP_GGUF = "FLUXUP GGUF"
STAGE2_LUSTIFY = "LUSTIFY SDXL"
STAGE2_WORKFLOWS = [
    GENESIS_TESTER_FLUXUP_GGUF,
    GENESIS_TESTER_AISHA,
    GENESIS_TESTER_KLEIN,
    GENESIS_TESTER_PERSEPHONE,
    GENESIS_TESTER_FLUXUP_FP8,
    STAGE2_LUSTIFY,
]

KLEIN_9B_TEST_LORAS = [
    "None",
    "FK_sloppydeepthroat_epoch_10.safetensors",
    "FK_teeththroat.safetensors",
]

FLUX1_TEST_LORAS = [
    "None",
    "Flux-NSFW-uncensored.safetensors",
    "alimama-creative---FLUX.1-Turbo-Alpha/diffusion_pytorch_model.safetensors",
]

TESTER_MODEL_PROFILES = {
    GENESIS_TESTER_KLEIN: {
        "family": "flux2_klein_9b",
        "loras": KLEIN_9B_TEST_LORAS,
        "lora1": "FK_sloppydeepthroat_epoch_10.safetensors",
        "lora1_strength": 0.50,
        "lora2": "FK_teeththroat.safetensors",
        "lora2_strength": 0.50,
        "denoise": 0.45,
        "steps": 6,
        "sampler": "res_multistep",
        "scheduler": "simple",
        "shift": 3.0,
        "summary": "Klein 9B KV fast · 6 steps · res_multistep/simple · AuraFlow shift 3.0 · refine denoise 0.45",
    },
    GENESIS_TESTER_AISHA: {
        "family": "flux2_klein_9b",
        "loras": KLEIN_9B_TEST_LORAS,
        "lora1": "FK_sloppydeepthroat_epoch_10.safetensors",
        "lora1_strength": 0.45,
        "lora2": "FK_teeththroat.safetensors",
        "lora2_strength": 0.35,
        "denoise": 0.40,
        "steps": 6,
        "sampler": "res_multistep",
        "scheduler": "simple",
        "shift": 3.0,
        "summary": "Aisha 9B fast · 6 steps · res_multistep/simple · AuraFlow shift 3.0 · refine denoise 0.40",
    },
    GENESIS_TESTER_PERSEPHONE: {
        "family": "flux1",
        "loras": FLUX1_TEST_LORAS,
        "lora1": "Flux-NSFW-uncensored.safetensors",
        "lora1_strength": 0.45,
        "lora2": "None",
        "lora2_strength": 0.0,
        "denoise": 0.45,
        "steps": 20,
        "guidance": 3.5,
        "sampler": "dpmpp_2m",
        "scheduler": "beta",
        "max_shift": 1.15,
        "base_shift": 0.50,
        "summary": "Persephone Q8 fast · 20 steps · DPM++ 2M/beta · guidance 3.5 · refine denoise 0.45",
    },
    GENESIS_TESTER_FLUXUP_FP8: {
        "family": "flux1",
        "loras": FLUX1_TEST_LORAS,
        "lora1": "Flux-NSFW-uncensored.safetensors",
        "lora1_strength": 0.40,
        "lora2": "alimama-creative---FLUX.1-Turbo-Alpha/diffusion_pytorch_model.safetensors",
        "lora2_strength": 0.15,
        "denoise": 0.35,
        "steps": 22,
        "guidance": 4.0,
        "sampler": "dpmpp_2m",
        "scheduler": "beta",
        "max_shift": 1.21,
        "base_shift": 0.50,
        "summary": "FluxUp FP8 fast · 22 steps · DPM++ 2M/beta · guidance 4.0 · refine denoise 0.35",
    },
    GENESIS_TESTER_FLUXUP_GGUF: {
        "family": "flux1",
        "loras": FLUX1_TEST_LORAS,
        "lora1": "None",
        "lora1_strength": 0.0,
        "lora2": "None",
        "lora2_strength": 0.0,
        "denoise": 0.35,
        "steps": 5,
        "guidance": 1.2,
        "sampler": "euler",
        "scheduler": "normal",
        "max_shift": 1.21,
        "base_shift": 0.50,
        "summary": "FluxUp GGUF native distilled · 5 steps · Euler/Normal · CFG 1.2 · refine denoise 0.35 · LoRAs off for baseline",
    },
}


def tester_model_profile_update(tester_name):
    profile = TESTER_MODEL_PROFILES.get(tester_name, TESTER_MODEL_PROFILES[GENESIS_TESTER_KLEIN])
    return (
        gr.update(choices=profile["loras"], value=profile["lora1"]),
        profile["lora1_strength"],
        gr.update(choices=profile["loras"], value=profile["lora2"]),
        profile["lora2_strength"],
        profile["denoise"],
        profile["summary"],
    )


def stage2_model_profile_update(workflow_name):
    if workflow_name == STAGE2_LUSTIFY:
        return (
            PREFERRED_STAGE2[1],
            gr.update(choices=["None"], value="None"), 0.0,
            gr.update(choices=["None"], value="None"), 0.0,
            0.15, 4, 1.5,
            gr.update(choices=["euler", "dpmpp_2m", "dpmpp_2m_sde"], value="euler"),
            gr.update(choices=["normal", "karras", "beta", "simple"], value="normal"),
            "Lustify SDXL Lightning · 4 steps · Euler/Normal · CFG 1.5 · denoise 0.15",
        )

    profile = TESTER_MODEL_PROFILES.get(workflow_name, TESTER_MODEL_PROFILES[GENESIS_TESTER_FLUXUP_GGUF])
    model_names = {
        GENESIS_TESTER_KLEIN: "flux-2-klein-9b-kv-fp8.safetensors",
        GENESIS_TESTER_AISHA: "aisha_nsfw_beta_v8_fp8.safetensors",
        GENESIS_TESTER_PERSEPHONE: "Persephone_Flux_2.0_Q8_0.gguf",
        GENESIS_TESTER_FLUXUP_FP8: "fluxedUpFluxNSFW_40DevFp8.safetensors",
        GENESIS_TESTER_FLUXUP_GGUF: "fluxedUpFluxNSFW_40Q4KSGguf.gguf",
    }
    return (
        model_names[workflow_name],
        gr.update(choices=profile["loras"], value=profile["lora1"]), profile["lora1_strength"],
        gr.update(choices=profile["loras"], value=profile["lora2"]), profile["lora2_strength"],
        profile["denoise"], profile["steps"], profile.get("guidance", 1.0),
        gr.update(choices=["euler", "dpmpp_2m", "dpmpp_2m_sde", "res_multistep"], value=profile["sampler"]),
        gr.update(choices=["normal", "karras", "beta", "simple"], value=profile["scheduler"]),
        profile["summary"],
    )


def _aura_sampling_node(model_link, shift_value=3.0):
    """
    Build ModelSamplingAuraFlow from the live ComfyUI schema.

    The supplied Klein/Aisha workflows use widget value 3.
    We avoid assuming the numeric widget's internal name by
    inspecting the schema at runtime.
    """
    desired = {"model": model_link}

    schema = _schema("ModelSamplingAuraFlow")
    required = schema.get("required", {})

    for name, spec in required.items():
        if name == "model":
            continue

        if (
            isinstance(spec, (list, tuple))
            and spec
            and spec[0] in ("FLOAT", "INT")
        ):
            desired[name] = (
                float(shift_value)
                if spec[0] == "FLOAT"
                else int(shift_value)
            )
            break

    return make_node("ModelSamplingAuraFlow", desired)


def generate_stage1_only(
    source, pose, pose_prompt, stage1_negative, pose_mode, pose_source_kind,
    strength_profile, prompt_strength, pose_strength,
    identity_strength, negative_strength, strict_identity_lock,
    stage1_model, stage1_width, stage1_height,
    stage1_seed, stage1_steps, stage1_cfg,
    stage1_sampler, stage1_scheduler,
    on_demand_backend, memory_guard_gib,
):
    """
    Run ONLY existing Stage 1.

    Does not invoke Stage 2 or Stage 3 and does not alter the
    existing GENERATE FULL PIPELINE implementation.
    """
    if source is None:
        raise gr.Error("Load the person / source image first.")

    CANCEL_EVENT.clear()

    log = []
    started = time.monotonic()
    stage1_seed = _resolve_seed(stage1_seed)

    try:
        _set_active_stage(1)

        _ensure_backend_for_stage(
            "Stage 1",
            memory_guard_gib,
            log
        )

        runner = _threaded_call(
            lambda cb: run_stage1(
                source,
                pose,
                pose_prompt,
                stage1_negative,
                pose_mode,
                pose_source_kind,
                strength_profile,
                prompt_strength,
                pose_strength,
                identity_strength,
                negative_strength,
                stage1_model,
                stage1_width,
                stage1_height,
                stage1_seed,
                stage1_steps,
                stage1_cfg,
                stage1_sampler,
                stage1_scheduler,
                strict_identity_lock,
                cb,
            )
        )

        output = None
        elapsed = 0.0

        while True:
            try:
                elapsed, pct, ptext = next(runner)

            except StopIteration as stop:
                output, model_used, pose_note = stop.value
                break

            badge = _stage_badge(
                "RUNNING",
                "Phr00t",
                elapsed,
                pct,
                ptext
            )

            yield (
                output,
                "\n".join(log + ["Stage 1 running…"]),
                badge,
            )

        elapsed_total = time.monotonic() - started

        log.append(
            f"Stage 1 · Phr00t: {elapsed:.1f}s · {model_used}"
        )
        log.append("Pose control · " + pose_note)
        log.append(
            "Memory after Stage 1 · " + _memory_summary()
        )
        log.append(
            f"Stage-1-only total: {elapsed_total:.1f}s"
        )

        _finish_on_demand_backend(
            on_demand_backend,
            log
        )

        yield (
            output,
            "\n".join(log),
            _stage_badge(
                "DONE",
                "Phr00t",
                elapsed
            ),
        )

    except RunCancelled:
        yield (
            None,
            "Stage 1 cancelled.",
            _stage_badge("CANCELLED")
        )

    finally:
        _set_active_stage(None)


def _run_flux2_model_tester(
    model_name,
    positive_text,
    negative_text,
    width,
    height,
    seed,
    lora1_name,
    lora1_strength,
    lora2_name,
    lora2_strength,
    filename_prefix,
    progress_cb=None,
    init_image=None,
    denoise=1.0,
    steps=6,
    sampler_name="res_multistep",
    scheduler="simple",
    shift=3.0,
):
    """
    Verified Flux.2 Klein/Aisha path.

    Graph matches the supplied workflows:
        UNETLoader
        CLIPLoader(Qwen 8B / flux2)
        two LoraLoaderBypass nodes
        CLIPTextEncode
        EmptySD3LatentImage
        ModelSamplingAuraFlow
        KSampler
        VAEDecode
        SaveImage

    ReActor is intentionally excluded from the isolated model
    tester. The existing Stage 3 remains the identity/face pass.
    """

    prompt = {}

    prompt["1"] = make_node(
        "UNETLoader",
        {
            "unet_name": model_name,
            "weight_dtype": "default",
        },
    )

    prompt["2"] = make_node(
        "CLIPLoader",
        {
            "clip_name": "qwen_3_8b_fp8mixed.safetensors",
            "type": "flux2",
            "device": "default",
        },
    )

    prompt["3"] = make_node(
        "VAELoader",
        {
            "vae_name": "flux2-vae.safetensors",
        },
    )

    model_link = ["1", 0]
    clip_link = ["2", 0]

    if lora1_name and str(lora1_name) != "None" and float(lora1_strength) != 0:
        prompt["4"] = make_node(
            "LoraLoaderBypass",
            {
                "model": model_link,
                "clip": clip_link,
                "lora_name": str(lora1_name),
                "strength_model": float(lora1_strength),
                "strength_clip": float(lora1_strength),
            },
        )
        model_link = ["4", 0]
        clip_link = ["4", 1]

    if lora2_name and str(lora2_name) != "None" and float(lora2_strength) != 0:
        prompt["21"] = make_node(
            "LoraLoaderBypass",
            {
                "model": model_link,
                "clip": clip_link,
                "lora_name": str(lora2_name),
                "strength_model": float(lora2_strength),
                "strength_clip": float(lora2_strength),
            },
        )
        model_link = ["21", 0]
        clip_link = ["21", 1]

    prompt["5"] = make_node(
        "CLIPTextEncode",
        {
            "text": positive_text,
            "clip": clip_link,
        },
    )

    prompt["6"] = make_node(
        "CLIPTextEncode",
        {
            "text": negative_text,
            "clip": clip_link,
        },
    )

    if init_image is not None:
        init_name = upload_image(init_image, "tester_pose_render")
        prompt["22"] = make_node("LoadImage", {"image": init_name})
        prompt["23"] = make_node(
            "VAEEncode",
            {"pixels": ["22", 0], "vae": ["3", 0]},
        )
        latent_link = ["23", 0]
    else:
        prompt["7"] = make_node(
            "EmptySD3LatentImage",
            {
                "width": int(width),
                "height": int(height),
                "batch_size": 1,
            },
        )
        latent_link = ["7", 0]

    prompt["8"] = _aura_sampling_node(
        model_link,
        float(shift),
    )

    prompt["9"] = make_node(
        "KSampler",
        {
            "model": ["8", 0],
            "positive": ["5", 0],
            "negative": ["6", 0],
            "latent_image": latent_link,
            "seed": int(seed),
            "steps": int(steps),
            "cfg": 1.0,
            "sampler_name": str(sampler_name),
            "scheduler": str(scheduler),
            "denoise": float(denoise),
        },
    )

    prompt["10"] = make_node(
        "VAEDecode",
        {
            "samples": ["9", 0],
            "vae": ["3", 0],
        },
    )

    prompt["13"] = make_node(
        "SaveImage",
        {
            "images": ["10", 0],
            "filename_prefix": filename_prefix,
        },
    )

    _, outputs = queue_and_wait(
        prompt,
        progress_cb,
        filename_prefix,
    )

    return fetch_output_image(outputs, "13")


def _run_fluxup_tester(
    model_loader,
    model_name,
    positive_text,
    width,
    height,
    seed,
    filename_prefix,
    progress_cb=None,
    init_image=None,
    denoise=1.0,
    lora1_name=None,
    lora1_strength=0.0,
    lora2_name=None,
    lora2_strength=0.0,
    steps=30,
    guidance=4.0,
    sampler_name="dpmpp_2m",
    scheduler="beta",
    max_shift=1.21,
    base_shift=0.5,
    distilled_direct=False,
):
    """
    Verified FluxUp / FLUX.1 path.

    FluxUp metadata showed:
      DualCLIPLoader
      CLIPTextEncode
      ModelSamplingFlux
      FluxGuidance
      BasicGuider
      dpmpp_2m
      beta scheduler
      30 steps
      guidance 4
      separate Flux VAE

    This is deliberately NOT routed through the Flux.2/Qwen path.
    """

    prompt = {}

    prompt["1"] = make_node(
        model_loader,
        {
            "unet_name": model_name,
            "weight_dtype": "default",
        },
    )

    prompt["2"] = make_node(
        "DualCLIPLoader",
        {
            "clip_name1": "t5xxl_fp8_e4m3fn_scaled.safetensors",
            "clip_name2": "clip_l.safetensors",
            "type": "flux",
            "device": "default",
        },
    )

    prompt["3"] = make_node(
        "VAELoader",
        {
            "vae_name": "ae.safetensors",
        },
    )

    model_link = ["1", 0]

    if lora1_name and str(lora1_name) != "None" and float(lora1_strength) != 0:
        prompt["17"] = make_node(
            "LoraLoaderModelOnly",
            {
                "model": model_link,
                "lora_name": str(lora1_name),
                "strength_model": float(lora1_strength),
            },
        )
        model_link = ["17", 0]

    if lora2_name and str(lora2_name) != "None" and float(lora2_strength) != 0:
        prompt["18"] = make_node(
            "LoraLoaderModelOnly",
            {
                "model": model_link,
                "lora_name": str(lora2_name),
                "strength_model": float(lora2_strength),
            },
        )
        model_link = ["18", 0]

    prompt["4"] = make_node(
        "CLIPTextEncode",
        {
            "text": positive_text,
            "clip": ["2", 0],
        },
    )

    if init_image is not None:
        init_name = upload_image(init_image, "tester_pose_render")
        prompt["15"] = make_node("LoadImage", {"image": init_name})
        prompt["16"] = make_node(
            "VAEEncode",
            {"pixels": ["15", 0], "vae": ["3", 0]},
        )
        latent_link = ["16", 0]
    else:
        prompt["8"] = make_node(
            "EmptyLatentImage",
            {
                "width": int(width),
                "height": int(height),
                "batch_size": 1,
            },
        )
        latent_link = ["8", 0]

    if distilled_direct:
        # Native path from the supplied FluxUp Q4_K_S workflow.
        prompt["19"] = make_node("CLIPTextEncode", {"text": "", "clip": ["2", 0]})
        prompt["12"] = make_node(
            "KSampler",
            {
                "model": model_link,
                "positive": ["4", 0],
                "negative": ["19", 0],
                "latent_image": latent_link,
                "seed": int(seed),
                "steps": int(steps),
                "cfg": float(guidance),
                "sampler_name": str(sampler_name),
                "scheduler": str(scheduler),
                "denoise": float(denoise),
            },
        )
    else:
        prompt["5"] = make_node(
            "ModelSamplingFlux",
            {
                "model": model_link,
                "max_shift": float(max_shift),
                "base_shift": float(base_shift),
                "width": int(width),
                "height": int(height),
            },
        )
        prompt["6"] = make_node(
            "FluxGuidance",
            {"conditioning": ["4", 0], "guidance": float(guidance)},
        )
        prompt["7"] = make_node(
            "BasicGuider",
            {"model": ["5", 0], "conditioning": ["6", 0]},
        )
        prompt["9"] = make_node("RandomNoise", {"noise_seed": int(seed)})
        prompt["10"] = make_node("KSamplerSelect", {"sampler_name": str(sampler_name)})
        prompt["11"] = make_node(
            "BasicScheduler",
            {
                "model": ["5", 0],
                "scheduler": str(scheduler),
                "steps": int(steps),
                "denoise": float(denoise),
            },
        )
        prompt["12"] = make_node(
            "SamplerCustomAdvanced",
            {
                "noise": ["9", 0],
                "guider": ["7", 0],
                "sampler": ["10", 0],
                "sigmas": ["11", 0],
                "latent_image": latent_link,
            },
        )

    prompt["13"] = make_node(
        "VAEDecode",
        {
            "samples": ["12", 0],
            "vae": ["3", 0],
        },
    )

    prompt["14"] = make_node(
        "SaveImage",
        {
            "images": ["13", 0],
            "filename_prefix": filename_prefix,
        },
    )

    _, outputs = queue_and_wait(
        prompt,
        progress_cb,
        filename_prefix,
    )

    return fetch_output_image(outputs, "14")


def run_stage2_workflow(
    init_image, workflow_name, model_name, width, height, seed, denoise,
    positive_text, negative_text, steps, cfg, sampler, scheduler,
    lora1_name, lora1_strength, lora2_name, lora2_strength, progress_cb=None,
):
    """Run any verified model workflow as a reusable image-to-image Stage 2."""
    if init_image is None:
        raise RuntimeError("Stage 2 needs an image. Generate Stage 1 or copy a Model Tester output into Stage 1 first.")

    workflow_name = workflow_name or GENESIS_TESTER_FLUXUP_GGUF
    if workflow_name == STAGE2_LUSTIFY:
        return run_stage2(
            init_image, model_name, seed, denoise, positive_text, negative_text,
            steps, cfg, sampler, scheduler, progress_cb,
        )

    profile = TESTER_MODEL_PROFILES.get(workflow_name)
    if profile is None:
        raise RuntimeError(f"Unknown Stage 2 workflow: {workflow_name}")

    incompatible = [
        name for name in (lora1_name, lora2_name)
        if name not in set(profile["loras"])
    ]
    if incompatible:
        raise RuntimeError(
            f"Incompatible LoRA for {workflow_name}: {', '.join(incompatible)}. "
            "Choose from the model-specific dropdown."
        )

    positive_text = str(positive_text or STAGE2_POSITIVE)
    negative_text = str(negative_text or STAGE2_NEGATIVE)
    common_loras = (lora1_name, float(lora1_strength), lora2_name, float(lora2_strength))

    if workflow_name in (GENESIS_TESTER_KLEIN, GENESIS_TESTER_AISHA):
        image = _run_flux2_model_tester(
            str(model_name), positive_text, negative_text, int(width), int(height), int(seed),
            *common_loras, "GENESIS_STAGE2_FLUX2_9B", progress_cb, init_image, float(denoise),
            int(steps), str(sampler), str(scheduler), float(profile.get("shift", 3.0)),
        )
    else:
        loader = "UnetLoaderGGUF" if str(model_name).lower().endswith(".gguf") else "UNETLoader"
        image = _run_fluxup_tester(
            loader, str(model_name), positive_text, int(width), int(height), int(seed),
            "GENESIS_STAGE2_FLUX_DETAIL", progress_cb, init_image, float(denoise),
            *common_loras, int(steps), float(cfg), str(sampler), str(scheduler),
            float(profile.get("max_shift", 1.21)), float(profile.get("base_shift", 0.5)),
            distilled_direct=(workflow_name == GENESIS_TESTER_FLUXUP_GGUF),
        )

    return image, f"{workflow_name} · {model_name}"


def run_selected_tester(
    tester_name,
    positive_text,
    negative_text,
    width,
    height,
    seed,
    use_pose_refiner,
    refine_denoise,
    tester_lora1_name,
    tester_lora1_strength,
    tester_lora2_name,
    tester_lora2_strength,
    source,
    pose,
    pose_mode,
    pose_source_kind,
    strict_identity_lock,
    stage1_model,
    strength_profile,
    prompt_strength,
    pose_strength,
    identity_strength,
    negative_strength,
    stage1_steps,
    stage1_cfg,
    stage1_sampler,
    stage1_scheduler,
    memory_safe_restart,
    on_demand_backend,
    memory_guard_gib,
):
    """
    Run exactly one isolated model tester with the same live
    timer/progress mechanism used by the normal GENESIS stages.
    """

    CANCEL_EVENT.clear()
    _set_active_stage("TESTER")

    log = []

    try:
        if not positive_text or not str(positive_text).strip():
            yield (
                None,
                "Enter a prompt first.",
                _stage_badge("ERROR", "Tester prompt required"),
            )
            return

        width = int(width)
        height = int(height)
        seed = _resolve_seed(seed)
        refine_denoise = max(0.05, min(1.0, float(refine_denoise)))
        tester_lora1_strength = float(tester_lora1_strength)
        tester_lora2_strength = float(tester_lora2_strength)
        tester_profile = TESTER_MODEL_PROFILES.get(tester_name)

        if tester_profile is None:
            yield (
                None,
                f"No fast profile is defined for {tester_name}.",
                _stage_badge("ERROR", "Missing model profile"),
            )
            return

        allowed_loras = set(tester_profile["loras"])
        incompatible = [
            name for name in (tester_lora1_name, tester_lora2_name)
            if name not in allowed_loras
        ]
        if incompatible:
            yield (
                None,
                f"Incompatible LoRA for {tester_name}: {', '.join(incompatible)}. Choose only from the model-specific dropdown.",
                _stage_badge("ERROR", "Incompatible LoRA blocked"),
            )
            return

        mode = (pose_mode or POSE_MODES[0]).upper()
        pose_enabled = bool(
            use_pose_refiner
            and pose is not None
            and not mode.startswith("PROMPT ONLY")
        )

        if pose_enabled and source is None:
            yield (
                None,
                "Load the person/source image before using a Pose Library item with a model tester.",
                _stage_badge("ERROR", "Source image required"),
            )
            return

        # Immediately update the UI so the button never appears dead.
        yield (
            None,
            f"Preparing {tester_name}…",
            _stage_badge("STARTING", str(tester_name), 0.0),
        )

        # This preserves the existing verified memory guard and
        # on-demand ComfyUI startup behavior.
        _ensure_backend_for_stage(
            f"Tester · {tester_name}",
            memory_guard_gib,
            log,
        )

        pose_context = {}

        def _pose_then_refine(refiner):
            def _call(progress_cb):
                init_image = None

                if pose_enabled:
                    init_image, phr00t_model, pose_note = run_stage1(
                        source,
                        pose,
                        str(positive_text),
                        str(negative_text or ""),
                        pose_mode,
                        pose_source_kind,
                        strength_profile,
                        prompt_strength,
                        pose_strength,
                        identity_strength,
                        negative_strength,
                        stage1_model,
                        width,
                        height,
                        seed,
                        stage1_steps,
                        stage1_cfg,
                        stage1_sampler,
                        stage1_scheduler,
                        bool(strict_identity_lock),
                        progress_cb,
                    )
                    pose_context["model"] = phr00t_model
                    pose_context["note"] = pose_note

                    if bool(memory_safe_restart) and comfy_alive(timeout=1):
                        pose_context["restart"] = restart_comfyui_between_stages(
                            "Before pose-guided model refinement"
                        )

                return refiner(progress_cb, init_image)

            return _call

        if tester_name == GENESIS_TESTER_KLEIN:

            detail = (
                "Klein 9B KV · Qwen 8B · Flux2 VAE · "
                f"LoRAs: {tester_lora1_name} @ {tester_lora1_strength:g}, "
                f"{tester_lora2_name} @ {tester_lora2_strength:g}"
            )

            tester_call = _pose_then_refine(
                lambda cb, init: _run_flux2_model_tester(
                    "flux-2-klein-9b-kv-fp8.safetensors",
                    str(positive_text),
                    str(negative_text or ""),
                    width,
                    height,
                    seed,
                    tester_lora1_name,
                    tester_lora1_strength,
                    tester_lora2_name,
                    tester_lora2_strength,
                    "GENESIS-KLEIN9B-TESTER",
                    cb,
                    init,
                    refine_denoise if init is not None else 1.0,
                    tester_profile["steps"],
                    tester_profile["sampler"],
                    tester_profile["scheduler"],
                    tester_profile["shift"],
                )
            )

        elif tester_name == GENESIS_TESTER_AISHA:

            detail = (
                "Aisha 9B · Qwen 8B · Flux2 VAE · "
                f"LoRAs: {tester_lora1_name} @ {tester_lora1_strength:g}, "
                f"{tester_lora2_name} @ {tester_lora2_strength:g}"
            )

            tester_call = _pose_then_refine(
                lambda cb, init: _run_flux2_model_tester(
                    "aisha_nsfw_beta_v8_fp8.safetensors",
                    str(positive_text),
                    str(negative_text or ""),
                    width,
                    height,
                    seed,
                    tester_lora1_name,
                    tester_lora1_strength,
                    tester_lora2_name,
                    tester_lora2_strength,
                    "GENESIS-AISHA9B-TESTER",
                    cb,
                    init,
                    refine_denoise if init is not None else 1.0,
                    tester_profile["steps"],
                    tester_profile["sampler"],
                    tester_profile["scheduler"],
                    tester_profile["shift"],
                )
            )

        elif tester_name == GENESIS_TESTER_PERSEPHONE:

            detail = (
                "Persephone Q8 GGUF · FLUX.1 · T5XXL + CLIP-L · "
                f"LoRAs: {tester_lora1_name} @ {tester_lora1_strength:g}, "
                f"{tester_lora2_name} @ {tester_lora2_strength:g}"
            )

            tester_call = _pose_then_refine(
                lambda cb, init: _run_fluxup_tester(
                    "UnetLoaderGGUF",
                    "Persephone_Flux_2.0_Q8_0.gguf",
                    str(positive_text),
                    width,
                    height,
                    seed,
                    "GENESIS-PERSEPHONE-TESTER",
                    cb,
                    init,
                    refine_denoise if init is not None else 1.0,
                    tester_lora1_name,
                    tester_lora1_strength,
                    tester_lora2_name,
                    tester_lora2_strength,
                    tester_profile["steps"],
                    tester_profile["guidance"],
                    tester_profile["sampler"],
                    tester_profile["scheduler"],
                    tester_profile["max_shift"],
                    tester_profile["base_shift"],
                )
            )

        elif tester_name == GENESIS_TESTER_FLUXUP_FP8:

            detail = "FluxUp FP8 · FLUX.1 · T5XXL + CLIP-L"

            tester_call = _pose_then_refine(
                lambda cb, init: _run_fluxup_tester(
                    "UNETLoader",
                    "fluxedUpFluxNSFW_40DevFp8.safetensors",
                    str(positive_text),
                    width,
                    height,
                    seed,
                    "GENESIS-FLUXUP-FP8-TESTER",
                    cb,
                    init,
                    refine_denoise if init is not None else 1.0,
                    tester_lora1_name,
                    tester_lora1_strength,
                    tester_lora2_name,
                    tester_lora2_strength,
                    tester_profile["steps"],
                    tester_profile["guidance"],
                    tester_profile["sampler"],
                    tester_profile["scheduler"],
                    tester_profile["max_shift"],
                    tester_profile["base_shift"],
                )
            )

        elif tester_name == GENESIS_TESTER_FLUXUP_GGUF:

            detail = "FluxUp GGUF Q4_K_S · FLUX.1 · T5XXL + CLIP-L"

            tester_call = _pose_then_refine(
                lambda cb, init: _run_fluxup_tester(
                    "UnetLoaderGGUF",
                    "fluxedUpFluxNSFW_40Q4KSGguf.gguf",
                    str(positive_text),
                    width,
                    height,
                    seed,
                    "GENESIS-FLUXUP-GGUF-TESTER",
                    cb,
                    init,
                    refine_denoise if init is not None else 1.0,
                    tester_lora1_name,
                    tester_lora1_strength,
                    tester_lora2_name,
                    tester_lora2_strength,
                    tester_profile["steps"],
                    tester_profile["guidance"],
                    tester_profile["sampler"],
                    tester_profile["scheduler"],
                    tester_profile["max_shift"],
                    tester_profile["base_shift"],
                    distilled_direct=True,
                )
            )

        else:
            yield (
                None,
                f"Unknown tester: {tester_name}",
                _stage_badge("ERROR", str(tester_name)),
            )
            return

        runner = _threaded_call(tester_call)

        elapsed = 0.0

        while True:
            try:
                elapsed, pct, ptext = next(runner)

            except StopIteration as stop:
                image = stop.value
                break

            yield (
                None,
                "\n".join(
                    log
                    + [
                        f"{detail}",
                        f"Tester running… {elapsed:.1f}s",
                    ]
                ),
                _stage_badge(
                    "RUNNING",
                    str(tester_name),
                    elapsed,
                    pct,
                    ptext,
                ),
            )

        log.append(detail)
        log.append("Fast profile: " + tester_profile["summary"])
        log.append(f"Seed: {seed}")
        log.append(f"Resolution: {width} × {height}")
        if pose_enabled:
            log.append("Pose Library route: Phr00t geometry render → model refinement")
            log.append("Pose control · " + pose_context.get("note", "geometry-first"))
            log.append(f"Refinement denoise: {refine_denoise:.2f}")
        log.append(f"Tester completed in {elapsed:.1f}s")

        # Show completion before backend cleanup.
        yield (
            image,
            "\n".join(log + ["Cleaning up ComfyUI…"]),
            _stage_badge(
                "DONE",
                str(tester_name),
                elapsed,
                100,
                "complete",
            ),
        )

        _finish_on_demand_backend(
            on_demand_backend,
            log,
        )

        # Final state includes cleanup message.
        yield (
            image,
            "\n".join(log),
            _stage_badge(
                "DONE",
                str(tester_name),
                elapsed,
                100,
                "complete",
            ),
        )

    except RunCancelled:
        _request_comfy_cancel()

        try:
            _finish_on_demand_backend(
                on_demand_backend,
                log,
            )
        except Exception as cleanup_exc:
            log.append(f"Cleanup warning: {cleanup_exc}")

        yield (
            None,
            "\n".join(log + ["Tester cancelled by user"]),
            _stage_badge(
                "CANCELLED",
                str(tester_name),
            ),
        )

    except Exception as exc:

        try:
            _finish_on_demand_backend(
                on_demand_backend,
                log,
            )
        except Exception as cleanup_exc:
            log.append(f"Cleanup warning: {cleanup_exc}")

        yield (
            None,
            "\n".join(log + [f"ERROR · {exc}"]),
            _stage_badge(
                "ERROR",
                str(exc)[:100],
            ),
        )

    finally:
        _set_active_stage(None)


def _genesis_output_dir() -> Path:
    """Return the actual ComfyUI output directory used by this installation."""
    return (COMFY_DIR / "output").expanduser().resolve()


def open_genesis_output_folder():
    """Open the actual ComfyUI generation output directory."""
    output_dir = _genesis_output_dir()

    if not output_dir.is_dir():
        return f"Output folder not found: {output_dir}"

    try:
        subprocess_mod = __import__("subprocess")
        subprocess_mod.Popen(
            ["xdg-open", str(output_dir)],
            stdout=subprocess_mod.DEVNULL,
            stderr=subprocess_mod.DEVNULL,
            start_new_session=True,
        )
        return f"Opened output folder: {output_dir}"

    except Exception as exc:
        return f"Could not open {output_dir}: {exc}"


def _open_latest_genesis_image(filename_prefix: str) -> str:
    """
    Open the newest real ComfyUI SaveImage output matching filename_prefix.
    """
    output_dir = _genesis_output_dir()

    if not output_dir.is_dir():
        return f"Output folder not found: {output_dir}"

    matches = [
        path for path in output_dir.rglob(f"{filename_prefix}*")
        if path.is_file()
        and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ]

    if not matches:
        return f"No generated image found for {filename_prefix} in {output_dir}"

    image_path = max(matches, key=lambda path: path.stat().st_mtime)

    try:
        subprocess_mod = __import__("subprocess")
        subprocess_mod.Popen(
            ["xdg-open", str(image_path)],
            stdout=subprocess_mod.DEVNULL,
            stderr=subprocess_mod.DEVNULL,
            start_new_session=True,
        )
        return f"Opened image: {image_path}"

    except Exception as exc:
        return f"Could not open {image_path}: {exc}"


def open_stage1_image():
    return _open_latest_genesis_image("GENESIS_STAGE1_PHR00T")


def open_stage2_image():
    return _open_latest_genesis_image("GENESIS_STAGE2_LUSTIFY")


def open_stage3_image():
    return _open_latest_genesis_image("GENESIS_STAGE3_REACTOR_ROCM")


def open_tester_image(tester_name):
    prefixes = {
        GENESIS_TESTER_KLEIN: "GENESIS-KLEIN9B-TESTER",
        GENESIS_TESTER_AISHA: "GENESIS-AISHA9B-TESTER",
        GENESIS_TESTER_PERSEPHONE: "GENESIS-PERSEPHONE-TESTER",
        GENESIS_TESTER_FLUXUP_FP8: "GENESIS-FLUXUP-FP8-TESTER",
        GENESIS_TESTER_FLUXUP_GGUF: "GENESIS-FLUXUP-GGUF-TESTER",
    }
    prefix = prefixes.get(tester_name)
    if not prefix:
        return f"No output prefix is configured for {tester_name}."
    return _open_latest_genesis_image(prefix)


def generate(
    source, pose, pose_prompt, stage1_negative, pose_mode, pose_source_kind,
    strength_profile, prompt_strength, pose_strength, identity_strength, negative_strength, strict_identity_lock,
    use_stage2, use_stage3,
    stage1_model, stage1_width, stage1_height, stage1_seed, stage1_steps, stage1_cfg, stage1_sampler, stage1_scheduler,
    stage2_workflow, stage2_model, stage2_width, stage2_height,
    stage2_seed, stage2_denoise, stage2_positive, stage2_negative, stage2_steps, stage2_cfg, stage2_sampler, stage2_scheduler,
    stage2_lora1_name, stage2_lora1_strength, stage2_lora2_name, stage2_lora2_strength,
    swap_model, detector, source_face_index, target_face_index, face_restore, restore_model, restore_visibility, codeformer_weight,
    memory_safe_restart, on_demand_backend, memory_guard_gib,
):
    if source is None:
        raise gr.Error("Load the person / source image first.")

    CANCEL_EVENT.clear()
    started_all = time.monotonic()
    log = []
    s1 = s2 = s3 = None
    stage1_seed = _resolve_seed(stage1_seed)
    stage2_seed = _resolve_seed(stage2_seed)
    st1 = _stage_badge("WAITING")
    st2 = _stage_badge("WAITING" if use_stage2 else "SKIPPED")
    st3 = _stage_badge("WAITING" if use_stage3 else "SKIPPED")

    try:
        # ---------------- Stage 1 ----------------
        _set_active_stage(1)
        _ensure_backend_for_stage("Stage 1", memory_guard_gib, log)
        runner = _threaded_call(lambda cb: run_stage1(
            source, pose, pose_prompt, stage1_negative, pose_mode, pose_source_kind,
            strength_profile, prompt_strength, pose_strength, identity_strength, negative_strength,
            stage1_model, stage1_width, stage1_height, stage1_seed,
            stage1_steps, stage1_cfg, stage1_sampler, stage1_scheduler, strict_identity_lock, cb
        ))
        while True:
            try:
                e1, pct, ptext = next(runner)
            except StopIteration as stop:
                s1, p1, pose_note = stop.value
                break
            st1 = _stage_badge("RUNNING", "Phr00t", e1, pct, ptext)
            yield s1, s2, s3, "\n".join(log + ["Stage 1 running…"]), st1, st2, st3
        st1 = _stage_badge("DONE", "Phr00t", e1)
        log.append(f"Stage 1 · Phr00t: {e1:.1f}s · {p1}")
        log.append("Pose control · " + pose_note)
        log.append("Memory after Stage 1 · " + _memory_summary())
        yield s1, s2, s3, "\n".join(log), st1, st2, st3
        current = s1

        # ---------------- Stage 2 ----------------
        if use_stage2:
            _set_active_stage(2)
            if memory_safe_restart:
                restart_t = time.monotonic()
                st2 = _stage_badge("RESTARTING", "freeing Phr00t memory", 0.0)
                yield s1, s2, s3, "\n".join(log + ["Restarting ComfyUI before Stage 2…"]), st1, st2, st3
                log.append(restart_comfyui_between_stages("Before Stage 2"))
                log.append(f"Stage 2 backend handoff: {time.monotonic()-restart_t:.1f}s")
            else:
                _ensure_backend_for_stage("Stage 2", memory_guard_gib, log)

            runner = _threaded_call(lambda cb: run_stage2_workflow(
                current, stage2_workflow, stage2_model, stage2_width, stage2_height,
                stage2_seed, stage2_denoise, stage2_positive, stage2_negative,
                stage2_steps, stage2_cfg, stage2_sampler, stage2_scheduler,
                stage2_lora1_name, stage2_lora1_strength, stage2_lora2_name, stage2_lora2_strength, cb
            ))
            while True:
                try:
                    e2, pct, ptext = next(runner)
                except StopIteration as stop:
                    s2, p2 = stop.value
                    break
                st2 = _stage_badge("RUNNING", str(stage2_workflow), e2, pct, ptext)
                yield s1, s2, s3, "\n".join(log + ["Stage 2 running…"]), st1, st2, st3
            current = s2
            st2 = _stage_badge("DONE", str(stage2_workflow), e2)
            log.append(f"Stage 2 · {stage2_workflow}: {e2:.1f}s · {p2}")
            log.append("Memory after Stage 2 · " + _memory_summary())
            yield s1, s2, s3, "\n".join(log), st1, st2, st3

        # ---------------- Stage 3 ----------------
        if use_stage3:
            _set_active_stage(3)
            if memory_safe_restart:
                st3 = _stage_badge("RESTARTING", "freeing previous model memory", 0.0)
                yield s1, s2, s3, "\n".join(log + ["Restarting ComfyUI before Stage 3…"]), st1, st2, st3
                log.append(restart_comfyui_between_stages("Before Stage 3"))
            else:
                _ensure_backend_for_stage("Stage 3", memory_guard_gib, log)

            runner = _threaded_call(lambda cb: run_stage3(
                current, source, swap_model, detector, source_face_index, target_face_index,
                face_restore, restore_model, restore_visibility, codeformer_weight, cb
            ))
            while True:
                try:
                    e3, pct, ptext = next(runner)
                except StopIteration as stop:
                    s3 = stop.value
                    break
                st3 = _stage_badge("RUNNING", "ReActor ROCm", e3, pct, ptext)
                yield s1, s2, s3, "\n".join(log + ["Stage 3 running…"]), st1, st2, st3
            st3 = _stage_badge("DONE", "ReActor", e3)
            log.append(f"Stage 3 · ReActor: {e3:.1f}s")
            log.append("Memory after Stage 3 · " + _memory_summary())

        log.append(f"Total pipeline: {time.monotonic()-started_all:.1f}s")
        _finish_on_demand_backend(on_demand_backend, log)
        yield s1, s2, s3, "\n".join(log), st1, st2, st3

    except RunCancelled:
        _request_comfy_cancel()
        if ACTIVE_STAGE == 1: st1 = _stage_badge("CANCELLED", "Phr00t")
        elif ACTIVE_STAGE == 2: st2 = _stage_badge("CANCELLED", str(stage2_workflow))
        elif ACTIVE_STAGE == 3: st3 = _stage_badge("CANCELLED", "ReActor")
        log.append("Run cancelled by user")
        _finish_on_demand_backend(on_demand_backend, log)
        yield s1, s2, s3, "\n".join(log), st1, st2, st3
    except Exception as e:
        msg = str(e)
        log.append("ERROR · " + msg)
        if ACTIVE_STAGE == 1: st1 = _stage_badge("ERROR", msg[:100])
        elif ACTIVE_STAGE == 2: st2 = _stage_badge("ERROR", msg[:100])
        else: st3 = _stage_badge("ERROR", msg[:100])
        yield s1, s2, s3, "\n".join(log), st1, st2, st3
    finally:
        _set_active_stage(None)


def load_examples():
    src = str(SAMPLE_SOURCE) if SAMPLE_SOURCE.exists() else None
    pose = str(SAMPLE_POSE) if SAMPLE_POSE.exists() else None
    return src, pose, DEFAULT_POSE_PROMPT, "photo"



VRAM_PRESETS = {
    "QUALITY · 832×1216": (832, 1216, "Maximum Stage 1 detail; use when quality matters more than turnaround"),
    "BALANCED · 768×1152": (768, 1152, "Recommended RX 9060 XT balance of detail, time and working headroom"),
    "FAST SAFE · 704×1024": (704, 1024, "Measured stable source-plus-pose test size"),
}

def apply_vram_mode(mode: str):
    width, height, note = VRAM_PRESETS.get(mode, VRAM_PRESETS["BALANCED · 768×1152"])
    return int(width), int(height), f"VRAM mode: {mode} · {note}"

def load_preset(name: str):
    prompt = GROK_GEOMETRY_PRESETS.get(name, DEFAULT_POSE_PROMPT)
    return prompt, f"Grok pose guide selected: {name} · written/camera guidance loaded · pose image unchanged"


def load_pose_prompt_preset(name: str):
    prompt = POSE_PROMPT_PRESETS.get(name, "")
    return prompt, f"Pose prompt preset selected: {name}"


@lru_cache(maxsize=1)
def pose_library_index():
    # Metadata/paths only. No pose image is opened here.
    if not POSE_LIBRARY_INDEX_PATH.exists():
        return []
    try:
        data = json.loads(POSE_LIBRARY_INDEX_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return [dict(item) for item in data]
    except Exception:
        return []


def pose_library_categories():
    categories = sorted({
        str(item.get("category", "")).strip()
        for item in pose_library_index() if item.get("category")
    })
    return ["All"] + categories


def _filter_pose_library(category: str, search: str):
    items = pose_library_index()
    category = (category or "All").strip()
    search = (search or "").strip().lower()
    if category != "All":
        items = [x for x in items if x.get("category") == category]
    if search:
        items = [x for x in items if any(
            search in str(x.get(k, "")).lower()
            for k in ("name", "resolution", "category", "path")
        )]
    return items


def _trim_thumb_cache():
    try:
        files = sorted(
            [x for x in THUMB_CACHE_DIR.glob("*.jpg") if x.is_file()],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        for old in files[THUMB_CACHE_LIMIT:]:
            try: old.unlink()
            except Exception: pass
    except Exception:
        pass


def _thumbnail_path(full_path: Path) -> str:
    """Create/load ONE small thumbnail. Never keeps a full pose image in memory."""
    try:
        st = full_path.stat()
        key = hashlib.sha1(f"{full_path}:{st.st_mtime_ns}:{st.st_size}".encode()).hexdigest()[:20]
    except Exception:
        key = hashlib.sha1(str(full_path).encode()).hexdigest()[:20]
    thumb = THUMB_CACHE_DIR / f"{key}.jpg"
    if thumb.exists():
        try: os.utime(thumb, None)
        except Exception: pass
        return str(thumb)

    try:
        with Image.open(full_path) as im:
            im = im.convert("RGB")
            im.thumbnail((THUMB_MAX_SIZE, THUMB_MAX_SIZE), Image.Resampling.LANCZOS)
            im.save(thumb, "JPEG", quality=82, optimize=True)
        _trim_thumb_cache()
        return str(thumb)
    except Exception:
        return str(full_path)


def pose_library_page(category: str, search: str, page: int, page_size: int = 24):
    items = _filter_pose_library(category, search)
    page_size = int(page_size or 24)
    if page_size not in (12, 24, 36):
        page_size = 24
    page_count = max(1, (len(items) + page_size - 1) // page_size)
    page = max(1, min(int(page or 1), page_count))
    start = (page - 1) * page_size
    current = items[start:start + page_size]

    gallery = []
    page_state = []
    for item in current:
        full_path = POSE_LIBRARY_DIR / item["path"]
        caption = f'{item.get("name", "pose")} · {item.get("category", "")} · {item.get("resolution", "")}'.strip(" ·")
        gallery.append((_thumbnail_path(full_path), caption))
        page_state.append({
            "path": str(full_path),
            "name": item.get("name", "pose"),
            "category": item.get("category", ""),
            "resolution": item.get("resolution", ""),
        })
    status = f"{len(items)} poses on disk · page {page}/{page_count} · showing {len(current)} thumbnails · full pose loads only when clicked"
    return gallery, page, status, page_state


def pose_library_first(category: str, search: str, page_size: int):
    return pose_library_page(category, search, 1, page_size)


def pose_library_prev(category: str, search: str, page: int, page_size: int):
    return pose_library_page(category, search, max(1, int(page or 1)-1), page_size)


def pose_library_next(category: str, search: str, page: int, page_size: int):
    return pose_library_page(category, search, int(page or 1)+1, page_size)


def _automatic_pose_prompt(category: str) -> str:
    normalized = str(category or "").lower().replace("nsfw_", "")
    preset_name = next(
        (name for key, name in POSE_CATEGORY_PRESETS.items() if key in normalized),
        "Natural full-body",
    )
    return POSE_PROMPT_PRESETS[preset_name]


def select_library_pose(page_items, prompt_mode, current_prompt, evt: gr.SelectData):
    if not page_items:
        return None, DEFAULT_POSE_PROMPT, "Pose Library: no pose selected", "skeleton"
    idx = evt.index[0] if isinstance(evt.index, (tuple, list)) else int(evt.index)
    if idx < 0 or idx >= len(page_items):
        return None, DEFAULT_POSE_PROMPT, "Pose Library: selection out of range", "skeleton"
    item = page_items[idx]
    if str(prompt_mode or "").startswith("POSE ONLY"):
        prompt = ""
        prompt_note = "pose-only mode; no written prompt"
    elif str(prompt_mode or "").startswith("MANUAL"):
        prompt = str(current_prompt or "")
        prompt_note = "manual prompt preserved"
    else:
        prompt = _automatic_pose_prompt(item.get("category", ""))
        prompt_note = "automatic category prompt loaded"
    status = f'Pose Library selected: {item.get("name", "pose")} · {item.get("category", "")} · {item.get("resolution", "")} · {prompt_note}'
    return item["path"], prompt, status, "skeleton"


def _data_uri(path: Path, mime: str) -> str:
    if not path.exists():
        return ""
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


# V15: use only user-provided imagery. The top hero is a placeholder until the user
# supplies a 3-woman panoramic banner in assets/user_banner/. Side rails use the
# exact 20-image no-duplicates pack bundled in assets/ui_rails/.
def _find_user_banner() -> Path | None:
    candidates = []
    for pattern in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        candidates.extend(USER_BANNER_DIR.glob(pattern))
    candidates = sorted(candidates, key=lambda x: x.name.lower())
    return candidates[0] if candidates else None

USER_BANNER_PATH = _find_user_banner()
RAIL_FILES = sorted(
    [p for p in UI_RAIL_DIR.glob("genesis_ui_*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}],
    key=lambda p: p.name.lower(),
)
def _image_data_uri(path: Path | None) -> str:
    if path is None:
        return ""
    mime = {".png": "image/png", ".webp": "image/webp"}.get(path.suffix.lower(), "image/jpeg")
    return _data_uri(path, mime)
BANNER_URI = _image_data_uri(USER_BANNER_PATH)
RAIL_URIS = [_image_data_uri(p) for p in RAIL_FILES]
STAGE1_BG = _data_uri(STAGE_BG_DIR / "stage1_bg.png", "image/png")
STAGE2_BG = _data_uri(STAGE_BG_DIR / "stage2_bg.png", "image/png")
STAGE3_BG = _data_uri(STAGE_BG_DIR / "stage3_bg.png", "image/png")


def _img(uri: str, alt: str) -> str:
    return f'<img src="{uri}" alt="{alt}" />' if uri else ""


_rail_split = (len(RAIL_URIS) + 1) // 2
_left_rails = RAIL_URIS[:_rail_split]
_right_rails = RAIL_URIS[_rail_split:]
LEFT_RAIL_HTML = "".join(_img(uri, f"GENESIS UI left {i+1}") for i, uri in enumerate(_left_rails))
RIGHT_RAIL_HTML = "".join(_img(uri, f"GENESIS UI right {i+1}") for i, uri in enumerate(_right_rails))
SIDE_RAILS_HTML = f"""
<div id="genesis-left-rail" class="genesis-side-rail"><div class="rail-grid">{LEFT_RAIL_HTML}</div></div>
<div id="genesis-right-rail" class="genesis-side-rail"><div class="rail-grid">{RIGHT_RAIL_HTML}</div></div>
"""

if BANNER_URI:
    _banner_body = f'<img src="{BANNER_URI}" alt="User-provided three-woman GENESIS panoramic banner" />'
    _banner_status = f'USER BANNER LOADED: {USER_BANNER_PATH.name}'
else:
    _banner_body = """
    <div class="banner-placeholder">
      <div class="banner-placeholder-title">3-WOMAN PANORAMIC BANNER</div>
      <div class="banner-placeholder-sub">PLACEHOLDER — YOUR PROVIDED IMAGE GOES HERE</div>
      <div class="banner-placeholder-path">Drop one PNG/JPG/WEBP into: assets/user_banner/</div>
    </div>
    """
    _banner_status = 'WAITING FOR USER-PROVIDED 3-WOMAN BANNER'

BANNER_HTML = f"""
<div id="genesis-banner">
  <div class="banner-main">{_banner_body}</div>
  <div class="banner-status">{_banner_status}</div>
  <div class="banner-meta">PHR00T / QWEN RAPID v19 &nbsp;•&nbsp; DWPose GEOMETRY FIRST &nbsp;•&nbsp; LUSTIFY &nbsp;•&nbsp; REACTOR ROCm</div>
</div>
"""


CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;600;700&display=swap');
:root {
  --bg: #050505; --panel: #0C0C0D; --panel2: #121214; --border: #4A4028;
  --bronze: #B78A45; --gold: #D4AF37; --ivory: #F4EFE6; --steel: #AAA39A;
  --btn: #17130A; --btn-hover: #2A210D; --btn-sec: #101011;
}
.gradio-container {
  background: var(--bg) !important;
  font-family: 'Inter', system-ui, sans-serif !important;
  max-width: 1740px !important;
  margin: 0 auto !important;
  padding-left: 18px !important;
  padding-right: 18px !important;
  color: var(--ivory) !important;
}
footer { display: none !important; }


/* ---------------- V15 EXACT USER IMAGE RAILS ---------------- */
.genesis-side-rail {
  position: fixed;
  top: 0;
  bottom: 0;
  width: clamp(145px, 11.5vw, 250px);
  z-index: 35;
  padding: 7px;
  overflow-y: auto;
  overflow-x: hidden;
  background: #050505;
  border-color: rgba(198,161,90,.38);
  scrollbar-width: thin;
  scrollbar-color: rgba(198,161,90,.55) #050505;
}
#genesis-left-rail { left: 0; border-right: 1px solid rgba(198,161,90,.38); }
#genesis-right-rail { right: 0; border-left: 1px solid rgba(198,161,90,.38); }
.rail-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
.rail-grid img {
  display: block;
  width: 100%;
  height: auto;
  max-width: 100%;
  object-fit: contain;
  object-position: center center;
  background: #080808;
  border: 1px solid rgba(198,161,90,.42);
  border-radius: 8px;
  box-shadow: 0 4px 13px rgba(0,0,0,.48);
}
.rail-grid img:hover {
  border-color: var(--gold);
  box-shadow: 0 0 0 1px rgba(198,161,90,.18), 0 5px 18px rgba(0,0,0,.55);
}
@media (min-width: 900px) {
  .gradio-container {
    width: calc(100vw - 2 * clamp(145px, 11.5vw, 250px) - 18px) !important;
    max-width: 1720px !important;
    margin-left: auto !important;
    margin-right: auto !important;
  }
}
@media (max-width: 899px) {
  .genesis-side-rail { display: none !important; }
  .gradio-container { max-width: 100% !important; width: 100% !important; }
}

/* ---------------- V15 USER-PROVIDED PANORAMIC HERO ---------------- */
#genesis-banner {
  width: 100%;
  margin: 4px 0 18px 0;
  border: 1px solid rgba(198,161,90,.42);
  border-radius: 14px;
  overflow: hidden;
  background: #080808;
  box-shadow: 0 12px 34px rgba(0,0,0,.52);
}
.banner-main {
  width: 100%;
  background: #080808;
}
.banner-main img {
  display: block;
  width: 100%;
  height: auto;
  max-height: none;
  object-fit: contain;
  object-position: center center;
  background: #080808;
}

.banner-placeholder {
  min-height: clamp(220px, 27vw, 430px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 28px;
  text-align: center;
  background:
    linear-gradient(135deg, rgba(198,161,90,.08), transparent 28%, transparent 72%, rgba(181,111,79,.08)),
    #070a0e;
  border: 2px dashed rgba(198,161,90,.50);
}
.banner-placeholder-title {
  color: var(--gold);
  font-family: 'Playfair Display', serif;
  font-size: clamp(1.6rem, 3vw, 3.2rem);
  letter-spacing: 2px;
}
.banner-placeholder-sub {
  color: var(--ivory);
  font-size: clamp(.85rem, 1.2vw, 1.15rem);
  font-weight: 700;
  letter-spacing: 1.6px;
}
.banner-placeholder-path {
  color: var(--steel);
  font-size: clamp(.72rem, .9vw, .9rem);
}
.banner-status {
  padding: 7px 12px;
  text-align: center;
  color: var(--gold);
  font-size: .72rem;
  font-weight: 800;
  letter-spacing: 1.1px;
  border-top: 1px solid rgba(198,161,90,.25);
  background: #0A0A0B;
}

.banner-meta {
  padding: 8px 14px 9px;
  text-align: center;
  color: var(--steel);
  font-size: clamp(.64rem,.82vw,.82rem);
  font-weight: 650;
  letter-spacing: 1.0px;
  border-top: 1px solid rgba(198,161,90,.24);
  background: linear-gradient(90deg, #0A0A0B, #15120A, #0A0A0B);
}

/* ---------------- MAIN UI ---------------- */
.gen-card {
  background: var(--panel) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
}
.gen-card .label-wrap span {
  color: var(--steel) !important;
  font-size: .75rem !important;
  letter-spacing: 1.2px !important;
  text-transform: uppercase !important;
}
#stage1-card, #stage2-card, #stage3-card { position: relative; overflow: hidden; }
#stage1-card::before, #stage2-card::before, #stage3-card::before {
  content: "";
  position: absolute;
  inset: 0;
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
  opacity: .16;
  pointer-events: none;
  z-index: 0;
  border-radius: 12px;
}
#stage1-card::before { background-image: url('__STAGE1_BG__'); }
#stage2-card::before { background-image: url('__STAGE2_BG__'); }
#stage3-card::before { background-image: url('__STAGE3_BG__'); opacity: .20; }
#stage1-card > *, #stage2-card > *, #stage3-card > * { position: relative; z-index: 1; }
#stage3-card {
  border: 1px solid var(--bronze) !important;
  box-shadow: 0 0 22px rgba(199,142,105,.22) !important;
}
#stage3-card .label-wrap span { color: var(--bronze) !important; }
textarea, input[type="text"], input[type="number"] {
  background: var(--panel2) !important;
  border: 1px solid var(--border) !important;
  color: var(--ivory) !important;
  border-radius: 8px !important;
}
.gradio-container label span { color: var(--steel) !important; }
#generate-btn {
  background: var(--btn) !important;
  color: var(--ivory) !important;
  font-weight: 700 !important;
  font-size: 1.12rem !important;
  letter-spacing: 2.5px !important;
  border: 1px solid var(--gold) !important;
  border-radius: 10px !important;
  padding: 16px 28px !important;
  box-shadow: 0 4px 18px rgba(181,111,79,.35) !important;
}
#generate-btn:hover { background: var(--btn-hover) !important; }
.sec-btn {
  background: var(--btn-sec) !important;
  color: var(--ivory) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
}
.preset-row button {
  min-height: 42px !important;
  font-size: .82rem !important;
  background: var(--panel2) !important;
  color: var(--ivory) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
}
.preset-row button:hover { border-color: var(--bronze) !important; color: var(--gold) !important; }
#status-box textarea {
  font-family: 'Inter', monospace !important;
  font-size: .85rem !important;
  background: var(--panel2) !important;
  color: var(--steel) !important;
  border: 1px solid var(--border) !important;
}
.gradio-container .accordion {
  background: var(--panel) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
}
input[type="range"] { accent-color: var(--bronze) !important; }

/* ---------------- LIVE STAGE STATUS ---------------- */
.stage-badge {
  display: flex;
  align-items: center;
  gap: 9px;
  min-height: 38px;
  margin: 0 0 8px 0;
  padding: 8px 11px;
  border-radius: 9px;
  border: 1px solid var(--border);
  background: rgba(20,26,33,.90);
  color: var(--ivory);
  font-size: .78rem;
  letter-spacing: .8px;
}
.stage-badge .stage-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: #66717c;
  box-shadow: 0 0 0 3px rgba(102,113,124,.12);
}
.stage-badge .stage-detail {
  margin-left: auto;
  color: var(--steel);
  font-size: .72rem;
  letter-spacing: .2px;
}
.state-running {
  border-color: rgba(198,161,90,.75);
  background: rgba(198,161,90,.10);
}
.state-running .stage-dot {
  background: var(--gold);
  box-shadow: 0 0 0 4px rgba(198,161,90,.15), 0 0 14px rgba(198,161,90,.7);
  animation: genesisPulse 1.1s infinite alternate;
}
.state-done {
  border-color: rgba(96,184,121,.55);
  background: rgba(96,184,121,.08);
}
.state-done .stage-dot { background: #60B879; }
.state-waiting .stage-dot { background: #7B8793; }
.state-skipped { opacity: .58; }
.state-skipped .stage-dot { background: #62666B; }
.state-restarting {
  border-color: rgba(199,142,105,.72);
  background: rgba(199,142,105,.10);
}
.state-restarting .stage-dot {
  background: var(--bronze);
  box-shadow: 0 0 12px rgba(199,142,105,.75);
  animation: genesisPulse .75s infinite alternate;
}
.state-error {
  border-color: rgba(220,86,86,.75);
  background: rgba(220,86,86,.10);
}
.state-error .stage-dot { background: #DC5656; }
@keyframes genesisPulse {
  from { transform: scale(.85); opacity: .65; }
  to   { transform: scale(1.18); opacity: 1; }
}
.memory-safe-note {
  padding: 10px 12px;
  margin: 4px 0 10px 0;
  border-radius: 9px;
  border: 1px solid rgba(198,161,90,.28);
  background: rgba(198,161,90,.06);
  color: var(--steel);
  font-size: .78rem;
}

#genesis-timer-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin: 8px 0 12px 0;
  padding: 10px 14px;
  background: #0C0C0D;
  border: 1px solid #4A4028;
  border-radius: 10px;
}
#genesis-timer-bar .timer-label {
  color: #AAA39A;
  font-size: .72rem;
  text-transform: uppercase;
  letter-spacing: .08em;
}
#genesis-elapsed-value {
  color: #F4EFE6;
  font-size: 1.25rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
#genesis-timer-state {
  color: #D4AF37;
  font-weight: 600;
}
.preset-status input, .preset-status textarea {
  font-weight: 600 !important;
}


/* GENESIS V13 */
.stage-status-shell { width:100%; }
.stage-status-top { display:flex; align-items:center; justify-content:space-between; gap:10px; }
.stage-live-time, .stage-final-time { font-variant-numeric:tabular-nums; font-weight:800; color:#F4EFE6; font-size:.85rem; }
.stage-final-time { color:#AAA39A; }
.stage-progress-wrap { height:7px; background:#171717; border:1px solid #4A4028; border-radius:999px; overflow:hidden; margin-top:7px; }
.stage-progress-fill { height:100%; background:linear-gradient(90deg,#B78A45,#D4AF37); transition:width .2s linear; }
.stage-progress-text { font-size:.67rem; color:#AAA39A; margin-top:4px; text-align:right; }
.state-cancelled .stage-dot { background:#D07B69 !important; }
.cancel-btn button, .cancel-btn { background:#9E3F3F !important; border-color:#C76363 !important; color:white !important; font-weight:800 !important; }
.config-accordion { border:1px solid #4A4028 !important; }
.memory-guard-box { color:#D4AF37; font-size:.78rem; }
.pose-library-note { color:#AAA39A; font-size:.78rem; }
"""
CSS = CSS.replace("__STAGE1_BG__", STAGE1_BG).replace("__STAGE2_BG__", STAGE2_BG).replace("__STAGE3_BG__", STAGE3_BG)



GENESIS_JS = r"""() => {}"""




with gr.Blocks(title="GENESIS Pose Maker — V14") as demo:
    gr.HTML(SIDE_RAILS_HTML)
    gr.HTML(BANNER_HTML)

    with gr.Row(equal_height=True):
        with gr.Column(scale=1, elem_classes="gen-card"):
            source = gr.Image(label="Person / Source Image (IDENTITY)", type="pil", value=str(SAMPLE_SOURCE) if SAMPLE_SOURCE.exists() else None, height=380)
        with gr.Column(scale=1, elem_classes="gen-card"):
            pose = gr.Image(label="Pose Reference (OPTIONAL · GEOMETRY ONLY)", type="pil", value=str(SAMPLE_POSE) if SAMPLE_POSE.exists() else None, height=380)

    pose_source_kind = gr.State("photo")

    gr.Markdown("**Grok camera / pose guide** — guidance-only shortcuts extracted from the separate Grok reference workflow. They change the written pose/camera instruction but do not replace your selected skeleton/photo.")
    with gr.Row(elem_classes="preset-row"):
        preset_btns = [(label, gr.Button(label, size="sm")) for label in GROK_GEOMETRY_PRESETS]
    preset_status = gr.Textbox(value=GROK_REFERENCE_NOTE, label="Pose guide status", interactive=False)

    # Pose library: paths/metadata in memory, only small thumbnails for current page.
    initial_gallery, initial_library_page, initial_library_status, initial_library_items = pose_library_page("All", "", 1, 24)
    with gr.Accordion(f"POSE LIBRARY — {len(pose_library_index())} POSES ON DISK", open=False):
        gr.Markdown("Paths + metadata only at startup. Current page uses small cached thumbnails. The full pose image loads only when you click it.", elem_classes="pose-library-note")
        with gr.Row():
            pose_library_category = gr.Dropdown(choices=pose_library_categories(), value="All", label="Category", scale=2)
            pose_library_search = gr.Textbox(value="", label="Search filenames / metadata", placeholder="pose number, category, resolution…", scale=2)
            pose_library_page_size = gr.Radio(choices=[12,24,36], value=24, label="Thumbnails/page", scale=1)
        pose_library_gallery = gr.Gallery(value=initial_gallery, label="Lazy thumbnail library", columns=6, rows=4, height=620, object_fit="contain", allow_preview=False, type="filepath")
        pose_library_page_state = gr.State(initial_library_page)
        pose_library_items_state = gr.State(initial_library_items)
        with gr.Row():
            pose_library_prev_btn = gr.Button("◀ PREVIOUS", elem_classes="sec-btn")
            pose_library_status = gr.Textbox(value=initial_library_status, label="Library status", interactive=False, scale=3)
            pose_library_next_btn = gr.Button("NEXT ▶", elem_classes="sec-btn")

    with gr.Row():
        use_stage2 = gr.Checkbox(True, label="Enable Stage 2 — selected model refinement")
        use_stage3 = gr.Checkbox(True, label="Enable Stage 3 — ReActor")
        memory_safe_restart = gr.Checkbox(True, label="Memory-safe restart between stages")
        on_demand_backend = gr.Checkbox(True, label="On-demand ComfyUI — stop backend when idle")

    with gr.Accordion("STAGE 1 CONFIG — Phr00t / Qwen Pose", open=True, elem_classes="config-accordion"):
        with gr.Row():
            pose_mode = gr.Radio(choices=POSE_MODES, value=POSE_MODES[0], label="Pose Mode", scale=3)
            strict_identity_lock = gr.Checkbox(True, label="STRICT IDENTITY LOCK", scale=1)
        gr.Markdown("**AUTO = GEOMETRY FIRST.** Written pose works alone. Pose Library skeletons are used directly. Uploaded pose photos are converted through DWPose first. AUTO never silently sends the other person's appearance to Phr00t; Direct Photo requires explicit selection.", elem_classes="pose-library-note")
        pose_route = gr.Textbox(value="ROUTE: POSE PHOTO → DWPose body/hands/face geometry → rendered skeleton → PHR00T image2", label="Resolved pose route", interactive=False)
        with gr.Row():
            pose_prompt_mode = gr.Dropdown(choices=POSE_PROMPT_MODES, value=POSE_PROMPT_MODES[0], label="Pose prompt behavior", scale=2)
            pose_prompt_preset = gr.Dropdown(choices=list(POSE_PROMPT_PRESETS.keys()), value="Natural full-body", label="Pose prompt preset", scale=2)
        pose_prompt = gr.Textbox(label="Positive / Written Pose Instruction", value=DEFAULT_POSE_PROMPT, lines=4)
        stage1_negative = gr.Textbox(label="Negative Prompt", value=STAGE1_NEGATIVE_DEFAULT, lines=3)

        with gr.Row():
            strength_profile = gr.Dropdown(
                choices=["NATURAL","BALANCED","STRONG","STRICT","MAX POSE","MAX IDENTITY","HYBRID STRONG","CUSTOM"],
                value="BALANCED", label="Prompt / Control Profile", scale=2
            )
            stage1_model = gr.Textbox(value=PREFERRED_STAGE1, label="Stage 1 model", scale=3)
            vram_mode = gr.Radio(choices=list(VRAM_PRESETS.keys()), value="BALANCED · 768×1152", label="RX 9060 XT quality / speed mode", scale=2)
        model_profile_info = gr.Textbox(value=model_profile_status(PREFERRED_STAGE1), label="Model-aware preset profile", interactive=False)
        grok_profile_note = gr.Textbox(value="MAIN: Phr00t/Qwen Rapid v19 · GENESIS proven low-CFG profile. GROK legacy Phr00t numbers stay separate/reference-only (7 steps, CFG 4.5, Euler/Normal).", label="Main vs Grok reference", interactive=False)

        with gr.Row():
            prompt_strength = gr.Slider(0.5,2.0,value=1.0,step=0.05,label="Written Prompt Strength")
            pose_strength = gr.Slider(0.5,2.0,value=1.0,step=0.05,label="Pose / Skeleton Strength")
            identity_strength = gr.Slider(0.5,2.0,value=1.2,step=0.05,label="Identity Lock Strength")
            negative_strength = gr.Slider(0.0,2.0,value=1.0,step=0.05,label="Negative Strength")

        with gr.Row():
            stage1_width = gr.Number(value=768, precision=0, label="Width")
            stage1_height = gr.Number(value=1152, precision=0, label="Height")
            stage1_seed = gr.Number(value=-1, precision=0, label="Seed (-1 random)")
            stage1_steps = gr.Number(value=6, precision=0, label="Steps")
            stage1_cfg = gr.Number(value=1.0, label="CFG")
        with gr.Row():
            stage1_sampler = gr.Dropdown(choices=["er_sde","euler","dpmpp_2m","dpmpp_2m_sde"], value="er_sde", allow_custom_value=True, label="Sampler")
            stage1_scheduler = gr.Dropdown(choices=["beta","normal","karras","simple"], value="beta", allow_custom_value=True, label="Scheduler")
            vram_status = gr.Textbox(value="BALANCED · 768×1152", label="VRAM preset", interactive=False)

        with gr.Accordion("POSE GEOMETRY CHECK", open=False):
            gr.Markdown("Use this before a long generation to confirm an uploaded photo converts cleanly to pose geometry. Pose Library entries are already skeleton maps.")
            with gr.Row():
                preview_pose_btn = gr.Button("PREVIEW / VERIFY POSE GEOMETRY", elem_classes="sec-btn")
                pose_geometry_status = gr.Textbox(label="Pose geometry status", interactive=False, scale=3)
            pose_geometry_preview = gr.Image(label="Geometry sent to Stage 1", type="pil", height=300)

    with gr.Accordion("STAGE 2 CONFIG — Reusable Flux / 9B / Lustify Refine", open=False, elem_classes="config-accordion"):
        gr.Markdown("Stage 2 accepts the current Stage 1 image. You can also copy any Model Tester output into the Stage 1 slot, then refine it here. Model-specific LoRA choices update automatically.")
        stage2_workflow = gr.Dropdown(choices=STAGE2_WORKFLOWS, value=GENESIS_TESTER_FLUXUP_GGUF, label="Stage 2 workflow / model family")
        stage2_model = gr.Textbox(value="fluxedUpFluxNSFW_40Q4KSGguf.gguf", label="Stage 2 model")
        stage2_profile_info = gr.Textbox(value=TESTER_MODEL_PROFILES[GENESIS_TESTER_FLUXUP_GGUF]["summary"], label="Active model-specific profile", interactive=False)
        stage2_positive = gr.Textbox(value=STAGE2_POSITIVE, label="Positive Prompt — Stage 2", lines=3)
        stage2_negative = gr.Textbox(value=STAGE2_NEGATIVE, label="Negative Prompt — Stage 2", lines=3)
        with gr.Row():
            stage2_width = gr.Number(value=768, precision=0, label="Width")
            stage2_height = gr.Number(value=1152, precision=0, label="Height")
            stage2_seed = gr.Number(value=-1, precision=0, label="Seed (-1 random)")
            stage2_steps = gr.Number(value=5, precision=0, label="Steps")
            stage2_cfg = gr.Number(value=1.2, label="CFG / Guidance")
            stage2_denoise = gr.Slider(0.05,1.0,value=0.35,step=0.01,label="Refinement strength / denoise")
        with gr.Row():
            stage2_sampler = gr.Dropdown(choices=["euler","dpmpp_2m","dpmpp_2m_sde","res_multistep"], value="euler", allow_custom_value=True, label="Sampler")
            stage2_scheduler = gr.Dropdown(choices=["normal","karras","beta","simple"], value="normal", allow_custom_value=True, label="Scheduler")
        with gr.Row():
            stage2_lora1_name = gr.Dropdown(choices=FLUX1_TEST_LORAS, value="None", label="Compatible LoRA 1", scale=3)
            stage2_lora1_strength = gr.Slider(0.0,1.5,value=0.0,step=0.05,label="LoRA 1 strength", scale=2)
        with gr.Row():
            stage2_lora2_name = gr.Dropdown(choices=FLUX1_TEST_LORAS, value="None", label="Compatible LoRA 2", scale=3)
            stage2_lora2_strength = gr.Slider(0.0,1.5,value=0.0,step=0.05,label="LoRA 2 strength", scale=2)

    with gr.Accordion("STAGE 3 CONFIG — ReActor Face Lock", open=False, elem_classes="config-accordion"):
        with gr.Row():
            swap_model = gr.Textbox(value="inswapper_128.onnx", label="Swap model")
            detector = gr.Textbox(value="retinaface_resnet50", label="Face detector")
        with gr.Row():
            source_face_index = gr.Number(value=0, precision=0, label="Source face index")
            target_face_index = gr.Number(value=0, precision=0, label="Target face index")
            face_restore = gr.Checkbox(False, label="Face restore")
        with gr.Row():
            restore_model = gr.Textbox(value="CodeFormer", label="Restore model")
            restore_visibility = gr.Slider(0.0,1.0,value=1.0,step=0.05,label="Restore visibility")
            codeformer_weight = gr.Slider(0.0,1.0,value=0.5,step=0.05,label="CodeFormer weight")

    with gr.Accordion("GLOBAL CONFIG — Memory / Backend", open=False, elem_classes="config-accordion"):
        memory_guard_gib = gr.Slider(2.0,8.0,value=4.0,step=0.5,label="Minimum available RAM before each stage (GiB)")
        gr.Markdown("ComfyUI backend is **ON-DEMAND**. GENESIS can start with ComfyUI OFF. The RX 9060 XT profile uses one asynchronous offload stream plus 1 GiB DynamicVRAM working headroom.", elem_classes="memory-guard-box")
        with gr.Row():
            test_btn = gr.Button("TEST COMFYUI CONNECTION", elem_classes="sec-btn")
            node_btn = gr.Button("CHECK REQUIRED / OPTIONAL NODES", elem_classes="sec-btn")
        test_status = gr.Textbox(label="Connection status", interactive=False)
        node_status = gr.Textbox(label="Custom-node health", interactive=False, lines=8)
        test_btn.click(connection_test, outputs=test_status)
        node_btn.click(custom_node_report, outputs=node_status, queue=False, show_progress="hidden")

    with gr.Row():
        generate_btn = gr.Button("GENERATE FULL PIPELINE", elem_id="generate-btn", scale=3)
        generate_stage1_btn = gr.Button("GENERATE STAGE 1", elem_classes="sec-btn", scale=2)
        cancel_btn = gr.Button("CANCEL RUN", elem_classes="cancel-btn", scale=1)
        restore_ex_btn = gr.Button("Restore example images", elem_classes="sec-btn", scale=1)
    cancel_status = gr.Textbox(value="", label="Cancel status", interactive=False)

    with gr.Accordion("MODEL TESTER — KLEIN / AISHA / PERSEPHONE / FLUXUP", open=False):
        gr.Markdown(
            "Model testing with optional Pose Library control. When enabled, GENESIS first renders the selected skeleton/photo through the existing geometry-first Phr00t route, then refines that result with Klein, Aisha, or FluxUp."
        )

        tester_model = gr.Dropdown(
            choices=[
                GENESIS_TESTER_KLEIN,
                GENESIS_TESTER_AISHA,
                GENESIS_TESTER_PERSEPHONE,
                GENESIS_TESTER_FLUXUP_FP8,
                GENESIS_TESTER_FLUXUP_GGUF,
            ],
            value=GENESIS_TESTER_KLEIN,
            label="Tester model",
        )

        with gr.Row():
            tester_use_pose = gr.Checkbox(
                True,
                label="Use selected Pose Library / uploaded pose",
                scale=2,
            )
            tester_refine_denoise = gr.Slider(
                0.05,
                1.0,
                value=0.45,
                step=0.05,
                label="Model refinement strength",
                info="Lower preserves the Phr00t pose render; higher lets the selected model reshape it.",
                scale=3,
            )

        gr.Markdown(
            "**LoRA compatibility:** `FK_sloppydeepthroat` and `FK_teeththroat` are the Klein/Aisha 9B test pair. Persephone and FluxUp use the FLUX.1 stack; use a FLUX.1 LoRA there, or set strength to 0 for a clean baseline."
        )

        tester_profile_info = gr.Textbox(
            value=TESTER_MODEL_PROFILES[GENESIS_TESTER_KLEIN]["summary"],
            label="Active model-specific fast profile",
            interactive=False,
        )

        with gr.Row():
            tester_lora1_name = gr.Dropdown(
                choices=KLEIN_9B_TEST_LORAS,
                value="FK_sloppydeepthroat_epoch_10.safetensors",
                label="Tester LoRA 1",
                scale=3,
            )
            tester_lora1_strength = gr.Slider(
                0.0, 1.5, value=0.5, step=0.05,
                label="LoRA 1 strength",
                scale=2,
            )

        with gr.Row():
            tester_lora2_name = gr.Dropdown(
                choices=KLEIN_9B_TEST_LORAS,
                value="FK_teeththroat.safetensors",
                label="Tester LoRA 2",
                scale=3,
            )
            tester_lora2_strength = gr.Slider(
                0.0, 1.5, value=0.5, step=0.05,
                label="LoRA 2 strength",
                scale=2,
            )

        with gr.Row():
            run_tester_btn = gr.Button(
                "RUN SELECTED TESTER",
                elem_classes="sec-btn",
                scale=2,
            )
            open_tester_image_btn = gr.Button(
                "OPEN TESTER IMAGE",
                elem_classes="sec-btn",
                scale=1,
            )
            open_output_folder_btn = gr.Button(
                "OPEN OUTPUT FOLDER",
                elem_classes="sec-btn",
                scale=1,
            )

        with gr.Row():
            tester_to_stage1_btn = gr.Button("USE TESTER OUTPUT AS STAGE 1 SOURCE", elem_classes="sec-btn")
            tester_to_stage2_btn = gr.Button("USE TESTER OUTPUT AS STAGE 2 SOURCE", elem_classes="sec-btn")

        tester_output = gr.Image(
            label="TESTER OUTPUT",
            type="pil",
            height=420,
        )

        tester_state = gr.HTML(
            _stage_badge("READY", "Model tester"),
            elem_id="tester-status",
        )

        tester_status = gr.Textbox(
            label="Tester status / output path",
            lines=5,
            interactive=False,
        )

    with gr.Row(equal_height=True):
        with gr.Column(scale=1, min_width=300, elem_classes="gen-card", elem_id="stage1-card"):
            stage1_state = gr.HTML(_stage_badge("READY"), elem_id="stage1-status")
            out1 = gr.Image(label="STAGE 1 IMAGE — Phr00t or imported tester output", type="pil", height=340)
            open_stage1_image_btn = gr.Button("OPEN STAGE 1 IMAGE", elem_classes="sec-btn")

        with gr.Column(scale=1, min_width=300, elem_classes="gen-card", elem_id="stage2-card"):
            stage2_state = gr.HTML(_stage_badge("READY"), elem_id="stage2-status")
            out2 = gr.Image(label="STAGE 2 IMAGE — selected refinement workflow", type="pil", height=340)
            open_stage2_image_btn = gr.Button("OPEN STAGE 2 IMAGE", elem_classes="sec-btn")

        with gr.Column(scale=1, min_width=300, elem_classes="gen-card", elem_id="stage3-card"):
            stage3_state = gr.HTML(_stage_badge("READY"), elem_id="stage3-status")
            out3 = gr.Image(label="STAGE 3 OUTPUT — ReActor", type="pil", height=340)
            open_stage3_image_btn = gr.Button("OPEN STAGE 3 IMAGE", elem_classes="sec-btn")

    with gr.Row():
        verify_stage1_btn = gr.Button("VERIFY STAGE 1", elem_classes="sec-btn")
        verify_stage2_btn = gr.Button("VERIFY STAGE 2", elem_classes="sec-btn")
        verify_stage3_btn = gr.Button("VERIFY STAGE 3", elem_classes="sec-btn")
    verify_status = gr.Textbox(value="", label="Verification status", interactive=False)

    with gr.Row():
        run_stage2_existing_btn = gr.Button("RUN STAGE 2 FROM CURRENT STAGE 1", elem_classes="sec-btn")
        run_stage3_existing_btn = gr.Button("RUN STAGE 3 FROM CURRENT STAGE 2", elem_classes="sec-btn")

    status = gr.Textbox(label="Run log", lines=6, interactive=False, elem_id="status-box")

    # Quick preset wiring.
    for label, btn in preset_btns:
        btn.click(fn=lambda l=label: load_preset(l), outputs=[pose_prompt, preset_status], queue=False, show_progress="hidden")

    tester_model.change(
        tester_model_profile_update,
        inputs=tester_model,
        outputs=[
            tester_lora1_name,
            tester_lora1_strength,
            tester_lora2_name,
            tester_lora2_strength,
            tester_refine_denoise,
            tester_profile_info,
        ],
        queue=False,
        show_progress="hidden",
    )

    # Lazy library wiring.
    lib_outputs = [pose_library_gallery, pose_library_page_state, pose_library_status, pose_library_items_state]
    pose_library_category.change(pose_library_first, [pose_library_category, pose_library_search, pose_library_page_size], lib_outputs, queue=False, show_progress="hidden")
    pose_library_search.submit(pose_library_first, [pose_library_category, pose_library_search, pose_library_page_size], lib_outputs, queue=False, show_progress="hidden")
    pose_library_page_size.change(pose_library_first, [pose_library_category, pose_library_search, pose_library_page_size], lib_outputs, queue=False, show_progress="hidden")
    pose_library_prev_btn.click(pose_library_prev, [pose_library_category, pose_library_search, pose_library_page_state, pose_library_page_size], lib_outputs, queue=False, show_progress="hidden")
    pose_library_next_btn.click(pose_library_next, [pose_library_category, pose_library_search, pose_library_page_state, pose_library_page_size], lib_outputs, queue=False, show_progress="hidden")
    pose_library_gallery.select(select_library_pose, [pose_library_items_state, pose_prompt_mode, pose_prompt], [pose, pose_prompt, preset_status, pose_source_kind], queue=False, show_progress="hidden")
    pose_prompt_preset.change(load_pose_prompt_preset, inputs=pose_prompt_preset, outputs=[pose_prompt, preset_status], queue=False, show_progress="hidden")

    # A manual upload is a photo unless a Pose Library selection explicitly marks it as a skeleton.
    pose.input(lambda: "photo", outputs=pose_source_kind, queue=False, show_progress="hidden")
    for route_component in (pose, pose_source_kind, pose_mode):
        route_component.change(pose_route_status, inputs=[pose, pose_source_kind, pose_mode], outputs=pose_route, queue=False, show_progress="hidden")

    strength_profile.change(
        apply_stage1_strength_profile,
        inputs=[strength_profile, stage1_model, stage1_steps, stage1_cfg, prompt_strength, pose_strength, identity_strength, negative_strength],
        outputs=[stage1_steps, stage1_cfg, prompt_strength, pose_strength, identity_strength, negative_strength, model_profile_info],
        queue=False, show_progress="hidden"
    )
    stage1_model.change(model_profile_status, inputs=stage1_model, outputs=model_profile_info, queue=False, show_progress="hidden")

    preview_pose_btn.click(
        preview_pose_geometry,
        inputs=[pose, pose_source_kind, pose_mode, on_demand_backend, memory_guard_gib],
        outputs=[pose_geometry_preview, pose_geometry_status],
        show_progress="hidden"
    )

    verify_stage1_btn.click(verify_stage1, inputs=out1, outputs=[verify_status, stage1_state], queue=False, show_progress="hidden")
    verify_stage2_btn.click(verify_stage2, inputs=out2, outputs=[verify_status, stage2_state], queue=False, show_progress="hidden")
    verify_stage3_btn.click(verify_stage3, inputs=out3, outputs=[verify_status, stage3_state], queue=False, show_progress="hidden")

    vram_mode.change(apply_vram_mode, vram_mode, [stage1_width, stage1_height, vram_status], queue=False, show_progress="hidden")

    stage2_workflow.change(
        stage2_model_profile_update,
        inputs=stage2_workflow,
        outputs=[
            stage2_model,
            stage2_lora1_name, stage2_lora1_strength,
            stage2_lora2_name, stage2_lora2_strength,
            stage2_denoise, stage2_steps, stage2_cfg,
            stage2_sampler, stage2_scheduler, stage2_profile_info,
        ],
        queue=False,
        show_progress="hidden",
    )

    tester_to_stage1_btn.click(lambda image: image, inputs=tester_output, outputs=out1, queue=False, show_progress="hidden")
    tester_to_stage2_btn.click(lambda image: image, inputs=tester_output, outputs=out2, queue=False, show_progress="hidden")

    # Cancel must bypass the generation queue.
    cancel_btn.click(cancel_run, outputs=cancel_status, queue=False, show_progress="hidden")

    generate_stage1_btn.click(
        generate_stage1_only,
        inputs=[
            source, pose, pose_prompt, stage1_negative, pose_mode, pose_source_kind,
            strength_profile, prompt_strength, pose_strength, identity_strength,
            negative_strength, strict_identity_lock,
            stage1_model, stage1_width, stage1_height, stage1_seed,
            stage1_steps, stage1_cfg, stage1_sampler, stage1_scheduler,
            on_demand_backend, memory_guard_gib,
        ],
        outputs=[
            out1,
            status,
            stage1_state,
        ],
        show_progress="hidden",
    )

    run_tester_btn.click(
        run_selected_tester,
        inputs=[
            tester_model,
            pose_prompt,
            stage1_negative,
            stage1_width,
            stage1_height,
            stage1_seed,
            tester_use_pose,
            tester_refine_denoise,
            tester_lora1_name,
            tester_lora1_strength,
            tester_lora2_name,
            tester_lora2_strength,
            source,
            pose,
            pose_mode,
            pose_source_kind,
            strict_identity_lock,
            stage1_model,
            strength_profile,
            prompt_strength,
            pose_strength,
            identity_strength,
            negative_strength,
            stage1_steps,
            stage1_cfg,
            stage1_sampler,
            stage1_scheduler,
            memory_safe_restart,
            on_demand_backend,
            memory_guard_gib,
        ],
        outputs=[
            tester_output,
            tester_status,
            tester_state,
        ],
        show_progress="hidden",
    )

    open_output_folder_btn.click(
        open_genesis_output_folder,
        outputs=tester_status,
        queue=False,
        show_progress="hidden",
    )

    open_tester_image_btn.click(
        open_tester_image,
        inputs=tester_model,
        outputs=tester_status,
        queue=False,
        show_progress="hidden",
    )

    tester_output.select(
        open_tester_image,
        inputs=tester_model,
        outputs=tester_status,
        queue=False,
        show_progress="hidden",
    )

    open_stage1_image_btn.click(
        open_stage1_image,
        outputs=status,
        queue=False,
        show_progress="hidden",
    )

    open_stage2_image_btn.click(
        open_stage2_image,
        outputs=status,
        queue=False,
        show_progress="hidden",
    )

    open_stage3_image_btn.click(
        open_stage3_image,
        outputs=status,
        queue=False,
        show_progress="hidden",
    )

    generate_btn.click(
        generate,
        inputs=[
            source, pose, pose_prompt, stage1_negative, pose_mode, pose_source_kind,
            strength_profile, prompt_strength, pose_strength, identity_strength, negative_strength, strict_identity_lock,
            use_stage2, use_stage3,
            stage1_model, stage1_width, stage1_height, stage1_seed, stage1_steps, stage1_cfg, stage1_sampler, stage1_scheduler,
            stage2_workflow, stage2_model, stage2_width, stage2_height,
            stage2_seed, stage2_denoise, stage2_positive, stage2_negative, stage2_steps, stage2_cfg, stage2_sampler, stage2_scheduler,
            stage2_lora1_name, stage2_lora1_strength, stage2_lora2_name, stage2_lora2_strength,
            swap_model, detector, source_face_index, target_face_index, face_restore, restore_model, restore_visibility, codeformer_weight,
            memory_safe_restart, on_demand_backend, memory_guard_gib,
        ],
        outputs=[out1,out2,out3,status,stage1_state,stage2_state,stage3_state],
        show_progress="hidden",
    )

    run_stage2_existing_btn.click(
        run_stage2_from_existing,
        inputs=[out1, stage2_workflow, stage2_model, stage2_width, stage2_height,
                stage2_seed, stage2_denoise, stage2_positive, stage2_negative,
                stage2_steps, stage2_cfg, stage2_sampler, stage2_scheduler,
                stage2_lora1_name, stage2_lora1_strength, stage2_lora2_name, stage2_lora2_strength,
                memory_safe_restart, on_demand_backend, memory_guard_gib],
        outputs=[out2,status,stage2_state],
        show_progress="hidden",
    )

    run_stage3_existing_btn.click(
        run_stage3_from_existing,
        inputs=[out2, source, swap_model, detector, source_face_index, target_face_index,
                face_restore, restore_model, restore_visibility, codeformer_weight,
                memory_safe_restart, on_demand_backend, memory_guard_gib],
        outputs=[out3,status,stage3_state],
        show_progress="hidden",
    )

    restore_ex_btn.click(load_examples, outputs=[source, pose, pose_prompt, pose_source_kind], queue=False)
    restore_ex_btn.click(lambda: STAGE2_NEGATIVE, outputs=stage2_negative, queue=False)


def _find_ui_port() -> int:
    preferred = int(os.environ.get("GENESIS_PORT", "7861"))
    for port in [preferred] + [p for p in range(7860, 7871) if p != preferred]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise OSError("No free GENESIS UI port found in 7860-7870")


if __name__ == "__main__":
    ui_port = _find_ui_port()
    print(f"GENESIS Pose Maker V14: http://127.0.0.1:{ui_port}")
    demo.queue(default_concurrency_limit=1)
    demo.launch(
        server_name="127.0.0.1",
        server_port=ui_port,
        inbrowser=True,
        show_error=True,
        css=CSS,
        js=GENESIS_JS,
        theme=gr.themes.Base(
            primary_hue="yellow",
            neutral_hue="slate",
            font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
        ).set(
            body_background_fill="#0B0E12",
            body_background_fill_dark="#0B0E12",
            block_background_fill="#0C0C0D",
            block_background_fill_dark="#0C0C0D",
            block_border_color="#4A4028",
            block_border_color_dark="#4A4028",
            block_label_text_color="#AAA39A",
            block_label_text_color_dark="#AAA39A",
            body_text_color="#F4EFE6",
            body_text_color_dark="#F4EFE6",
            button_primary_background_fill="#B78A45",
            button_primary_background_fill_dark="#B78A45",
            button_primary_background_fill_hover="#C99A4D",
            button_primary_background_fill_hover_dark="#C99A4D",
            button_primary_text_color="#F4EFE6",
            button_primary_text_color_dark="#F4EFE6",
            button_secondary_background_fill="#101011",
            button_secondary_background_fill_dark="#101011",
            input_background_fill="#1C232C",
            input_background_fill_dark="#1C232C",
            border_color_primary="#4A4028",
            border_color_primary_dark="#4A4028",
        ),
        allowed_paths=[str(BASE_DIR / "assets"), str(BASE_DIR / "sample_images"), str(THUMB_CACHE_DIR)],
    )
