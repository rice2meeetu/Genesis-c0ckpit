#!/usr/bin/env python3
import fcntl, tempfile, uuid
try:
    from genesis.runpod_model_cache import validate_weight
except ModuleNotFoundError:
    from runpod_model_cache import validate_weight

import argparse, json, os, pathlib, shutil, signal, subprocess, sys, time, urllib.request

CACHE = pathlib.Path("/opt/genesis-qwen-v23")
MODELS = CACHE / "models"
RUNTIME = pathlib.Path("/opt/genesis-comfy-runtime")
LAUNCHER = RUNTIME / "launch-paul-local.py"
PYTHON = pathlib.Path("/opt/genesis-comfy-env/bin/python")
LOG = RUNTIME / "paul.log"
MASTER = pathlib.Path("/workspace/ComfyUI/models")
RESERVE = 2 * 1024**3

PROFILES = {
    "phr00t-v23": [
        ("unet/Qwen-Rapid-NSFW-v23_Q8_0.gguf", "unet/Qwen-Rapid-NSFW-v23_Q8_0.gguf"),
        ("text_encoders/Qwen2.5-VL-7B-Instruct-Q8_0.gguf", "text_encoders/Qwen2.5-VL-7B-Instruct-Q8_0.gguf"),
        ("text_encoders/Qwen2.5-VL-7B-Instruct-mmproj-f16.gguf", "text_encoders/Qwen2.5-VL-7B-Instruct-mmproj-f16.gguf"),
        ("vae/qwen_image_vae.safetensors", "vae/qwen_image_vae.safetensors"),
    ],
    "phr00t-v19": [
        ("unet/Qwen-Rapid-AIO-NSFW-v19_Q8_0.gguf", "unet/Qwen-Rapid-AIO-NSFW-v19_Q8_0.gguf"),
        ("text_encoders/Qwen2.5-VL-7B-Instruct-Q8_0.gguf", "text_encoders/Qwen2.5-VL-7B-Instruct-Q8_0.gguf"),
        ("text_encoders/Qwen2.5-VL-7B-Instruct-mmproj-f16.gguf", "text_encoders/Qwen2.5-VL-7B-Instruct-mmproj-f16.gguf"),
        ("vae/qwen_image_vae.safetensors", "vae/qwen_image_vae.safetensors"),
    ],    "aisha": [
        ("diffusion_models/aisha_nsfw_beta_v9_7_distilled_bf16.safetensors", "diffusion_models/aisha_nsfw_beta_v9_7_distilled_bf16.safetensors"),
        ("text_encoders/qwen_3_8b_fp8mixed.safetensors", "text_encoders/qwen_3_8b_fp8mixed.safetensors"),
        ("vae/flux2-vae.safetensors", "vae/flux2-vae.safetensors"),
    ],
    "miraclein": [
        ("diffusion_models/miracleinNSFWGeneration_20FP8.safetensors", "diffusion_models/miracleinNSFWGeneration_20FP8.safetensors"),
        ("text_encoders/qwen_3_8b_fp8mixed.safetensors", "text_encoders/qwen_3_8b_fp8mixed.safetensors"),
        ("vae/flux2-vae.safetensors", "vae/flux2-vae.safetensors"),
    ],
}

def human(n):
    return f"{n / 1024**3:.2f} GiB"

def current_pid():
    found = []
    for p in pathlib.Path("/proc").glob("[0-9]*"):
        try:
            argv = (p / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        if str(LAUNCHER).encode() in argv and b"paul" in argv:
            found.append(int(p.name))
    if len(found) > 1:
        raise RuntimeError("Multiple Paul processes; refusing to choose a PID")
    return found[0] if found else None


def queue_empty():
    # Connection errors and malformed responses must never authorize a stop.
    with urllib.request.urlopen("http://127.0.0.1:8188/queue", timeout=3) as r:
        q = json.load(r)
    if not isinstance(q, dict) or any(not isinstance(q.get(k), list) for k in ("queue_running", "queue_pending")):
        raise RuntimeError("8188 queue state is unknown")
    return not q["queue_running"] and not q["queue_pending"]

def cache_bytes():
    total = 0
    for p in MODELS.rglob("*"):
        if p.is_file() and not p.is_symlink():
            total += p.stat().st_size
    return total

def profile_sizes(name):
    rows = []
    for src_rel, dst_rel in PROFILES[name]:
        src = MASTER / src_rel
        if not src.is_file():
            raise FileNotFoundError(src)
        rows.append((src, MODELS / dst_rel, src.stat().st_size))
    return rows

def stop_paul():
    pid = current_pid()
    if not pid:
        return
    if not queue_empty():
        raise RuntimeError("8188 has a running or pending job; refusing to switch cache")
    os.kill(pid, signal.SIGTERM)
    for _ in range(60):
        if not pathlib.Path(f"/proc/{pid}").exists():
            return
        time.sleep(0.5)
    raise RuntimeError("Paul/8188 did not stop cleanly")

def stage(name):
    """Prepare the complete existing profile without reclaiming active files."""
    if CACHE.resolve() != pathlib.Path("/opt/genesis-qwen-v23"):
        raise RuntimeError("Unexpected cache root")
    rows = profile_sizes(name)
    need = sum(x[2] for x in rows)
    free = shutil.disk_usage(CACHE).free
    if need + RESERVE > free:
        raise RuntimeError(f"{name} needs {human(need + RESERVE)} staging space; {human(free)} free. Active cache retained.")
    staged = pathlib.Path(tempfile.mkdtemp(prefix=".staging-", dir=CACHE))
    manifest = []
    try:
        for src, dst, size in rows:
            if MASTER.resolve() not in src.resolve(strict=True).parents:
                raise RuntimeError("Source escapes master model root")
            if src.stat().st_dev == CACHE.stat().st_dev:
                raise RuntimeError("Cache and master must use different filesystems")
            before = src.stat()
            validate_weight(src)
            target = staged / "models" / dst.relative_to(MODELS)
            target.parent.mkdir(parents=True, exist_ok=True)
            import hashlib
            digest = hashlib.sha256()
            with src.open("rb") as fi, target.open("xb") as fo:
                while block := fi.read(16 * 1024 * 1024):
                    digest.update(block)
                    fo.write(block)
                fo.flush()
                os.fsync(fo.fileno())
            after = src.stat()
            if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                raise RuntimeError("Master changed while copying")
            validate_weight(target)
            manifest.append({"source": str(src), "destination": str(dst), "bytes": size,
                             "sha256": digest.hexdigest(), "profile": name})
        (staged / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (staged / "profile.json").write_text(json.dumps({"profile": name, "updated": time.time()}) + "\n")
        return staged
    except Exception:
        shutil.rmtree(staged)
        raise


def switch(name):
    """Serialize switches; stage first, then stop only idle Paul and roll back."""
    with (CACHE / '.switch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not current_pid() or not queue_empty():
            raise RuntimeError("Paul/8188 must be running and idle before switching")
        staged = stage(name)
        backup = CACHE / ('.previous-' + uuid.uuid4().hex)
        moved = []
        published = []
        stopped = False
        try:
            # Recheck after staging. A new job prevents activation.
            stop_paul()
            stopped = True
            backup.mkdir()
            for item in ('models', 'manifest.json', 'profile.json'):
                old = CACHE / item
                if old.exists():
                    old.rename(backup / item)
                    moved.append(item)
                (staged / item).rename(old)
                published.append(item)
            start_paul()
        except Exception:
            if stopped:
                # A new process that failed readiness must stop before rollback.
                if current_pid():
                    stop_paul()
                for item in reversed(published):
                    (CACHE / item).rename(staged / item)
                for item in reversed(moved):
                    (backup / item).rename(CACHE / item)
                start_paul()
            raise
        finally:
            # Retain old cache for recovery; delete only our unpublished staging.
            if staged.exists():
                shutil.rmtree(staged)

def start_paul():
    with LOG.open("ab", buffering=0) as log:
        subprocess.Popen([str(PYTHON), "-B", str(LAUNCHER), "paul"], stdout=log, stderr=subprocess.STDOUT,
                         cwd=str(CACHE), start_new_session=True)
    for _ in range(90):
        try:
            urllib.request.urlopen("http://127.0.0.1:8188/queue", timeout=2).read()
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("8188 did not come back up")

def status():
    prof = "phr00t-v23"
    pf = CACHE / "profile.json"
    if pf.exists():
        prof = json.loads(pf.read_text()).get("profile", prof)
    print(f"active profile: {prof}")
    print(f"8188 pid: {current_pid()}")
    print(f"local cache: {human(cache_bytes())}")
    print(f"root free: {human(shutil.disk_usage('/').free)}")
    for name in PROFILES:
        try:
            size = sum(x[2] for x in profile_sizes(name))
            print(f"{name}: {human(size)} master OK")
        except Exception as e:
            print(f"{name}: unavailable: {e}")

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sw = sub.add_parser("switch")
    sw.add_argument("profile", choices=sorted(PROFILES))
    args = ap.parse_args()
    if args.cmd == "status":
        status()
        return
    print(f"switching Paul/8188 to {args.profile}")
    switch(args.profile)
    status()

if __name__ == "__main__":
    main()
