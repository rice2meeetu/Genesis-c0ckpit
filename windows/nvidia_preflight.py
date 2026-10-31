"""Read-only local Windows ComfyUI CUDA readiness probe.

The cockpit UI environment may intentionally lack torch. Probe the *running
ComfyUI backend* instead; do not mistake a working NVIDIA display driver or
nvidia-smi for a working CUDA image-generation backend.
"""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def cuda_preflight(base_url: str = "http://127.0.0.1:8188", timeout: float = 2.5):
    """Return (ready, explanation), without starting services or changing settings."""
    try:
        parsed = urlsplit(base_url)
        if (parsed.scheme != "http"
                or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
                or parsed.username or parsed.password
                or not parsed.port or parsed.path not in {"", "/"}
                or parsed.query or parsed.fragment):
            return False, "LOCAL requires a loopback ComfyUI HTTP endpoint; check its URL."
        url = base_url.rstrip("/") + "/system_stats"
        request = Request(url, headers={"User-Agent": "GENESIS-Windows-CUDA-Preflight"})
        with urlopen(request, timeout=timeout) as response:
            # Avoid unbounded responses from a misconfigured service.
            raw = response.read(256 * 1024 + 1)
        if len(raw) > 256 * 1024:
            return False, "Local ComfyUI returned an oversized system report."
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return False, "Local ComfyUI system report has an unexpected format."
        devices = payload.get("devices", [])
        if not isinstance(devices, list):
            return False, "Local ComfyUI did not provide a valid device list."
        for device in devices:
            if not isinstance(device, dict):
                continue
            kind = str(device.get("type", "")).lower()
            name = str(device.get("name", "")).strip()
            if kind == "cuda" or kind.startswith("cuda:"):
                return True, "Local ComfyUI CUDA ready: " + (name or "CUDA device")
        return False, (
            "Local ComfyUI is running without a CUDA GPU. Check the ComfyUI "
            "Python/PyTorch CUDA installation before choosing LOCAL."
        )
    except (OSError, HTTPError, URLError, TimeoutError):
        return False, "Local ComfyUI is offline at port 8188; start its NVIDIA CUDA backend."
    except (ValueError, TypeError, json.JSONDecodeError):
        return False, "Local ComfyUI CUDA status could not be validated."
