"""Qt bridge for Feefee, the GENESIS AI assistant.

Feefee is the user-facing assistant identity. The backend is deliberately
swappable: a dedicated local Qwen model is used today, the heavier Qwen3-Coder
route is available for BUILD work, and an OpenAI-compatible cloud endpoint
(such as RunPod) can be enabled later without changing the Feefee persona.

Rocinante is intentionally excluded from this bridge; it is reserved for
external persona/chat frontends.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from genesis import integrations


class AssistantBridge(QObject):
    statusChanged = pyqtSignal()
    busyChanged = pyqtSignal()
    transcriptChanged = pyqtSignal()
    modeChanged = pyqtSignal()
    providerChanged = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        provider = os.environ.get("GENESIS_AI_PROVIDER", "AUTO").strip().upper()
        self._provider = provider if provider in {"AUTO", "LOCAL", "CLOUD"} else "AUTO"
        self._status = "Feefee ready · AUTO hybrid routing"
        self._busy = False
        self._transcript = "FEEFEE · GENESIS AI\nYour private GENESIS assistant.\n"
        self._mode = "CHAT"
        self._history: list[dict[str, str]] = []

    @pyqtProperty(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @pyqtProperty(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @pyqtProperty(str, notify=transcriptChanged)
    def transcript(self) -> str:
        return self._transcript

    @pyqtProperty(str, notify=modeChanged)
    def mode(self) -> str:
        return self._mode

    @pyqtProperty(str, notify=providerChanged)
    def provider(self) -> str:
        return self._provider

    @pyqtProperty(bool, notify=providerChanged)
    def cloudConfigured(self) -> bool:
        return bool(self._cloud_base_url() and self._cloud_model())

    @pyqtProperty(str, notify=modeChanged)
    def localModel(self) -> str:
        if self._mode == "BUILD":
            return "Qwen3-Coder-30B-A3B · Q3_K_XL"
        return "Qwen2.5-Coder-14B-Instruct · Q4_K_M"

    @pyqtProperty(str, notify=modeChanged)
    def activeModel(self) -> str:
        if self._provider == "CLOUD":
            return self._cloud_model() or "Cloud endpoint not configured"
        if self._provider == "AUTO" and self.cloudConfigured:
            return f"AUTO · {self._cloud_model()} / {self.localModel}"
        return self.localModel

    def _cloud_base_url(self) -> str:
        return os.environ.get("GENESIS_CLOUD_BASE_URL", "").strip().rstrip("/")

    def _cloud_api_key(self) -> str:
        return os.environ.get("GENESIS_CLOUD_API_KEY", "").strip()

    def _cloud_model(self) -> str:
        return os.environ.get("GENESIS_CLOUD_MODEL", "").strip()

    def _set_status(self, value: str) -> None:
        self._status = value
        self.statusChanged.emit()

    def _set_busy(self, value: bool) -> None:
        self._busy = value
        self.busyChanged.emit()

    def _append(self, role: str, text: str) -> None:
        label = "YOU" if role == "user" else "FEEFEE"
        self._transcript = self._transcript.rstrip() + f"\n\n{label}\n{text.strip()}\n"
        self.transcriptChanged.emit()

    @pyqtSlot(str)
    def setMode(self, mode: str) -> None:
        mode = mode.strip().upper()
        if mode not in {"CHAT", "BUILD", "STUDIO"}:
            return
        if self._mode != mode:
            self._mode = mode
            self.modeChanged.emit()
        self._set_status(f"Feefee · {mode} · {self.activeModel}")

    @pyqtSlot(str)
    def setProvider(self, provider: str) -> None:
        provider = provider.strip().upper()
        if provider not in {"AUTO", "LOCAL", "CLOUD"}:
            return
        self._provider = provider
        self.providerChanged.emit()
        self.modeChanged.emit()
        if provider == "CLOUD" and not self.cloudConfigured:
            self._set_status("Cloud mode selected · configure GENESIS_CLOUD_BASE_URL and GENESIS_CLOUD_MODEL")
        else:
            self._set_status(f"Feefee · {provider} · {self.activeModel}")

    @pyqtSlot()
    def clearChat(self) -> None:
        self._history.clear()
        self._transcript = "FEEFEE · GENESIS AI\nYour private GENESIS assistant.\n"
        self.transcriptChanged.emit()
        self._set_status("Feefee · conversation cleared")

    @pyqtSlot(str)
    def sendMessage(self, text: str) -> None:
        message = text.strip()
        if not message or self._busy:
            return
        self._append("user", message)
        self._history.append({"role": "user", "content": message})
        self._set_busy(True)
        self._set_status(f"Feefee · starting {self._mode}…")
        threading.Thread(target=self._run_chat, daemon=True).start()

    def _system_prompt(self) -> str:
        base = (
            "You are Feefee, Paul's GENESIS AI assistant inside GENESIS c0ckpit. "
            "Your visual identity is his real cat Feefee. Be warm, sharp, concise, practical and loyal. "
            "A little dry cat-like personality is welcome, but do not overdo roleplay or constant meowing. "
            "Never claim you are using a cloud provider unless the active route actually is cloud. "
        )
        if self._mode == "BUILD":
            return base + (
                "You are in BUILD mode. Prioritize concrete implementation, debugging, tests, Linux/ROCm, "
                "Qt/QML, Python, Git and ComfyUI integration. Prefer actionable fixes over general advice."
            )
        if self._mode == "STUDIO":
            return base + (
                "You are in STUDIO mode. Help with image-generation prompts, model/LoRA selection, poses, "
                "ComfyUI workflows, creative tools and GENESIS production decisions."
            )
        return base + "You are in CHAT mode. Be a capable general-purpose personal assistant."

    def _local_route(self):
        if self._mode == "BUILD":
            return (
                integrations.QWEN_URL,
                integrations.QWEN_SERVICE,
                "genesis-qwen",
            )
        return (
            integrations.ASSISTANT_URL,
            integrations.ASSISTANT_SERVICE,
            "genesis-assistant",
        )

    def _request_completion(self, base_url: str, model: str, headers: dict[str, str], route_label: str) -> str:
        messages = [{"role": "system", "content": self._system_prompt()}, *self._history[-18:]]
        payload = json.dumps({
            "model": model,
            "messages": messages,
            "temperature": 0.62 if self._mode == "CHAT" else 0.28,
            "max_tokens": 1400,
            "stream": False,
        }).encode("utf-8")
        request_headers = {
            "Content-Type": "application/json",
            "User-Agent": "GENESIS-c0ckpit/1.0",
            **headers,
        }
        request = urllib.request.Request(
            base_url.rstrip("/") + "/v1/chat/completions",
            data=payload,
            headers=request_headers,
            method="POST",
        )
        self._set_status(f"Feefee · {route_label} · thinking…")
        with urllib.request.urlopen(request, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8", "replace"))
        choices = result.get("choices") or []
        if not choices:
            raise RuntimeError(f"{route_label} returned no response.")
        answer = str((choices[0].get("message") or {}).get("content") or "").strip()
        if not answer:
            raise RuntimeError(f"{route_label} returned an empty response.")
        return answer

    def _run_cloud(self) -> str:
        base_url = self._cloud_base_url()
        model = self._cloud_model()
        if not base_url or not model:
            raise RuntimeError("Cloud endpoint is not configured.")
        headers: dict[str, str] = {}
        api_key = self._cloud_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return self._request_completion(base_url, model, headers, "CLOUD")

    def _run_local(self) -> str:
        base_url, service, model = self._local_route()
        online = integrations.endpoint_online(base_url, "/health", timeout=0.8)
        ok, detail = integrations.start_user_service(service, already_online=online)
        if not ok:
            raise RuntimeError(detail)
        if not online:
            self._set_status(f"Feefee · loading {self.localModel}…")
            for _ in range(80):
                if integrations.endpoint_online(base_url, "/health", timeout=0.8):
                    online = True
                    break
                time.sleep(0.5)
        if not online:
            raise RuntimeError("Local GENESIS AI service did not become ready.")
        return self._request_completion(base_url, model, {}, "LOCAL")

    def _run_chat(self) -> None:
        try:
            answer = ""
            route = "LOCAL"
            if self._provider == "CLOUD":
                answer = self._run_cloud()
                route = "CLOUD"
            elif self._provider == "LOCAL":
                answer = self._run_local()
            elif self.cloudConfigured:
                try:
                    answer = self._run_cloud()
                    route = "CLOUD"
                except Exception as cloud_error:
                    self._set_status(f"Cloud unavailable ({cloud_error}) · falling back to local…")
                    answer = self._run_local()
                    route = "LOCAL"
            else:
                answer = self._run_local()

            self._history.append({"role": "assistant", "content": answer})
            self._append("assistant", answer)
            self._set_status(f"Feefee · {route} · {self.activeModel} · ready")
        except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
            self._append("assistant", f"I couldn't answer that: {exc}")
            self._set_status(f"Feefee unavailable · {exc}")
        finally:
            self._set_busy(False)
