"""Filesystem-only model and workflow readiness for the GENESIS cockpit."""

from __future__ import annotations

import getpass
import os
import tkinter as tk
from pathlib import Path


BG = "#06080c"
PANEL = "#0c1420"
PANEL_2 = "#111d2d"
BORDER = "#2b3d56"
GOLD = "#d6a84b"
TEXT = "#f4ead5"
MUTED = "#9da9b8"
GREEN = "#4fd18b"
RED = "#d16a6a"
BLUE = "#1c3656"


_DEFAULT_COMFYUI_ROOT = Path(os.environ.get("GENESIS_COMFYUI_ROOT") or os.environ.get("COMFYUI_ROOT") or (Path.home() / ("ComfyUI" if os.name == "nt" else "AI/ComfyUI")))

MODEL_ROOTS = tuple(dict.fromkeys([
    *([Path(os.environ["GENESIS_MODEL_ROOT"]).expanduser()] if os.environ.get("GENESIS_MODEL_ROOT") else []),
    _DEFAULT_COMFYUI_ROOT / "models",
    Path.home() / "Documents" / "ComfyUI" / "models",
    Path.home() / "Desktop" / "ComfyUI" / "models",
    Path("/mnt/AI-Storage/ComfyUI/models"),
    Path.home() / "AI" / "ComfyUI" / "models",
    Path.home() / "AI" / "AI-Models",
    Path("/run/media") / getpass.getuser() / "Ai" / "AI-Models",
]))

WORKFLOW_ROOTS = (
    _DEFAULT_COMFYUI_ROOT / "user" / "default" / "workflows",
    _DEFAULT_COMFYUI_ROOT / "workflows",
    Path("/mnt/AI-Storage/ComfyUI/workflows"),
    Path.home() / "AI" / "ComfyUI" / "user" / "default" / "workflows",
    Path.home() / "AI" / "GENESIS_POSE_MAKER" / "workflows",
    Path(__file__).resolve().parent / "reference" / "pose_workflows",
)

MODEL_PROFILES = (
    {
        "name": "Aisha 9B FP8",
        "model": ("aisha",),
        "lora": (),
        "vae": ("flux2-vae", "ae.safetensors"),
        "encoder": ("qwen_3_8b", "qwen3_8b"),
        "workflow": ("aisha",),
    },
    {
        "name": "FLUX.2 Klein 9B Base",
        "model": ("flux-2-klein-base-9b", "klein-base-9b"),
        "lora": ("Flux Klein - NSFW v2", "Klein_Anatomy_Revamped", "flux2klein_body_version_a"),
        "vae": ("flux2-vae", "ae.safetensors"),
        "encoder": ("qwen_3_8b", "qwen3_8b"),
        "workflow": ("Flux.2 Klein 9b Text To Image", "klein-base-9b"),
    },
    {
        "name": "FLUX.2 Klein 9B-KV FP8",
        "model": ("klein9bkv", "klein-9b-kv", "klein_9b_kv"),
        "lora": (),
        "vae": ("flux2-vae", "ae.safetensors"),
        "encoder": ("qwen_3_8b", "qwen3_8b"),
        "workflow": ("KLEIN_9B_KV", "klein9bkv", "klein-9b-kv", "klein_9b_kv"),
    },
    {
        "name": "FLUX.2 Klein 4B",
        "model": ("klein-4b", "klein_4b", "klein 4b"),
        # 4B baseline generation does not require an adapter. Experimental
        # adapters are surfaced separately by model_compatibility.py.
        "lora": (),
        "vae": ("flux2-vae", "ae.safetensors"),
        "encoder": ("qwen_3_4b", "qwen3_4b"),
        "workflow": ("klein_img", "klein_4b", "klein-4b", "klein 4b"),
    },
    {
        "name": "FluxedUp",
        "model": ("fluxedup", "fluxup"),
        "lora": (),
        "vae": ("flux2-vae", "ae.safetensors"),
        "encoder": (),
        "workflow": ("fluxedup", "fluxup"),
    },
    {
        "name": "Phr00t / QwenRapid AIO",
        "model": ("phroot", "phr00t", "qwen-rapid", "qwenrapid"),
        "lora": (),
        "vae": (),
        "encoder": (),
        "workflow": ("phroot", "phr00t", "qwenrapid", "qwen_rapid"),
    },
)


def _files(roots: tuple[Path, ...], suffixes: set[str]) -> list[Path]:
    found: dict[str, Path] = {}
    for root in roots:
        if not root.is_dir():
            continue
        try:
            candidates = root.rglob("*")
            for path in candidates:
                try:
                    if not path.is_file() or path.suffix.lower() not in suffixes:
                        continue
                except OSError:
                    continue
                try:
                    if ".cache" in path.parts or path.stat().st_size == 0:
                        continue
                except OSError:
                    continue
                found[str(path.resolve())] = path
        except OSError:
            continue
    return sorted(found.values(), key=lambda value: value.name.lower())


def _match(paths: list[Path], tokens: tuple[str, ...]) -> Path | None:
    if not tokens:
        return None
    lowered = tuple(token.lower() for token in tokens)
    return next(
        (path for path in paths if any(token in path.name.lower() for token in lowered)),
        None,
    )


def readiness_report() -> dict:
    model_files = _files(MODEL_ROOTS, {".safetensors", ".gguf", ".ckpt", ".pt"})
    workflows = _files(WORKFLOW_ROOTS, {".json"})
    loras = [path for path in model_files if {"lora", "loras"} & {
        part.lower() for part in path.parts
    }]
    vaes = [path for path in model_files if "vae" in {part.lower() for part in path.parts}]
    encoders = [path for path in model_files if any(
        part.lower() in {"text_encoders", "clip"} for part in path.parts
    )]
    base_models = [path for path in model_files if path not in loras + vaes + encoders]

    profiles = []
    for spec in MODEL_PROFILES:
        evidence = {
            "MODEL": _match(base_models, spec["model"]),
            "LORA": _match(loras, spec["lora"]),
            "VAE": _match(vaes, spec["vae"]),
            "ENCODER": _match(encoders, spec["encoder"]),
            "WORKFLOW": _match(workflows, spec["workflow"]),
        }
        required = {
            key for key, source in (
                ("MODEL", spec["model"]), ("LORA", spec["lora"]),
                ("VAE", spec["vae"]), ("ENCODER", spec["encoder"]),
                ("WORKFLOW", spec["workflow"]),
            ) if source
        }
        missing = [key for key in required if evidence[key] is None]
        profiles.append({
            "name": spec["name"],
            "ready": not missing,
            "missing": missing,
            "evidence": evidence,
            "required": required,
        })

    return {
        "profiles": profiles,
        "counts": {
            "models": len(base_models), "loras": len(loras), "vaes": len(vaes),
            "encoders": len(encoders), "workflows": len(workflows),
        },
        "roots": [str(root) for root in MODEL_ROOTS + WORKFLOW_ROOTS if root.exists()],
    }


class ModelManager(tk.Toplevel):
    def __init__(self, parent: tk.Misc):
        super().__init__(parent)
        self.title("GENESIS · Workflow / Model Manager")
        self.geometry("1120x680")
        self.minsize(900, 560)
        self.configure(bg=BG)
        self._build()
        self.refresh()

    def _build(self) -> None:
        header = tk.Frame(self, bg=PANEL, highlightthickness=1,
                          highlightbackground=BORDER)
        header.pack(fill="x", padx=12, pady=(12, 8))
        title = tk.Frame(header, bg=PANEL)
        title.pack(side="left", padx=14, pady=10)
        tk.Label(title, text="WORKFLOW / MODEL MANAGER", bg=PANEL, fg=GOLD,
                 font=("Sans", 16, "bold")).pack(anchor="w")
        tk.Label(title, text="Filesystem readiness · LOCAL ONLY · no automatic downloads",
                 bg=PANEL, fg=MUTED, font=("Sans", 9)).pack(anchor="w", pady=(2, 0))
        tk.Button(header, text="REFRESH LOCAL STATUS", command=self.refresh,
                  bg=BLUE, fg=TEXT, activebackground=GOLD,
                  activeforeground="#000000", relief="flat", bd=0,
                  padx=12, pady=7, font=("Sans", 8, "bold")).pack(
                      side="right", padx=12)

        self.summary = tk.Label(self, bg=BG, fg=MUTED, anchor="w",
                                font=("Sans", 9))
        self.summary.pack(fill="x", padx=18, pady=(2, 8))
        self.rows = tk.Frame(self, bg=BG)
        self.rows.pack(fill="both", expand=True, padx=12)
        self.footer = tk.Label(self, bg=PANEL, fg=MUTED, anchor="w",
                               justify="left", padx=10, pady=7,
                               font=("Sans", 8))
        self.footer.pack(fill="x", padx=12, pady=(8, 12))

    def refresh(self) -> None:
        report = readiness_report()
        for child in self.rows.winfo_children():
            child.destroy()
        counts = report["counts"]
        ready_count = sum(1 for profile in report["profiles"] if profile["ready"])
        self.summary.configure(text=(
            f"{ready_count}/{len(report['profiles'])} launch profiles ready   ·   "
            f"{counts['models']} models   ·   {counts['loras']} LoRAs   ·   "
            f"{counts['vaes']} VAEs   ·   {counts['encoders']} encoders   ·   "
            f"{counts['workflows']} workflows"
        ))
        for profile in report["profiles"]:
            self._profile_row(profile)
        roots = "   •   ".join(report["roots"])
        self.footer.configure(text=f"Scanned local roots: {roots or 'No configured roots found'}")

    def _profile_row(self, profile: dict) -> None:
        row = tk.Frame(self.rows, bg=PANEL, highlightthickness=1,
                       highlightbackground=BORDER)
        row.pack(fill="x", pady=4)
        name_wrap = tk.Frame(row, bg=PANEL, width=250)
        name_wrap.pack(side="left", fill="y", padx=12, pady=10)
        name_wrap.pack_propagate(False)
        tk.Label(name_wrap, text=profile["name"], bg=PANEL, fg=TEXT,
                 font=("Sans", 11, "bold"), anchor="w").pack(fill="x")
        status = "READY" if profile["ready"] else f"{profile['missing'][0]} MISSING"
        tk.Label(name_wrap, text=status, bg=PANEL,
                 fg=GREEN if profile["ready"] else RED,
                 font=("Sans", 9, "bold"), anchor="w").pack(fill="x", pady=(4, 0))

        chips = tk.Frame(row, bg=PANEL)
        chips.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=8)
        for index, key in enumerate(("MODEL", "LORA", "VAE", "ENCODER", "WORKFLOW")):
            required = key in profile["required"]
            path = profile["evidence"][key]
            if not required:
                text = f"{key}\nOPTIONAL"
                fg = MUTED
                bg = PANEL_2
            elif path:
                text = f"{key}\n{path.name}"
                fg = GREEN
                bg = "#10251f"
            else:
                text = f"{key}\nMISSING"
                fg = RED
                bg = "#2a1518"
            chip = tk.Label(chips, text=text, bg=bg, fg=fg, justify="left",
                            anchor="w", padx=8, pady=6, font=("Sans", 8))
            chip.grid(row=0, column=index, sticky="nsew", padx=2)
            chips.grid_columnconfigure(index, weight=1, uniform="chips")


def open_model_manager(parent: tk.Misc) -> ModelManager:
    return ModelManager(parent)
