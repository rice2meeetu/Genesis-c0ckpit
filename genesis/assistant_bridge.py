"""Qt bridge for the local GENESIS assistant.

GENESIS keeps two mutually-exclusive llama.cpp services on the local GPU:
Rocinante for general private conversation and Qwen3-Coder for coding/build work.
The bridge starts the requested service on demand and talks to llama.cpp's
OpenAI-compatible chat-completions endpoint without sending prompts off-device.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from genesis import integrations


class AssistantBridge(QObject):
    statusChanged = pyqtSignal()
    busyChanged = pyqtSignal()
    transcriptChanged = pyqtSignal()
    modeChanged = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._status = "Ready · choose CHAT, BUILD or STUDIO"
        self._busy = False
        self._transcript = "GENESIS AI\nLocal. Private. On-device.\n"
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

    @pyqtProperty(str, notify=modeChanged)
    def activeModel(self) -> str:
        if self._mode == "CHAT":
            return "Rocinante-X-12B · Q5_K_M"
        return "Qwen3-Coder-30B-A3B · Q3_K_XL"

    def _set_status(self, value: str) -> None:
        self._status = value
        self.statusChanged.emit()

    def _set_busy(self, value: bool) -> None:
        self._busy = value
        self.busyChanged.emit()

    def _append(self, role: str, text: str) -> None:
        label = "YOU" if role == "user" else "GENESIS"
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
        self._set_status(f"{mode} selected · {self.activeModel}")

    @pyqtSlot()
    def clearChat(self) -> None:
        self._history.clear()
        self._transcript = "GENESIS AI\nLocal. Private. On-device.\n"
        self.transcriptChanged.emit()
        self._set_status("Conversation cleared")

    @pyqtSlot(str)
    def sendMessage(self, text: str) -> None:
        message = text.strip()
        if not message or self._busy:
            return
        self._append("user", message)
        self._history.append({"role": "user", "content": message})
        self._set_busy(True)
        self._set_status(f"Starting {self._mode} assistant…")
        threading.Thread(target=self._run_chat, daemon=True).start()

    def _route(self):
        if self._mode == "CHAT":
            return (
                integrations.LLAMA_URL,
                integrations.LLAMA_SERVICE,
                integrations.LLAMA_MODEL.name,
                "You are GENESIS AI, Paul's private local assistant inside GENESIS c0ckpit. "
                "Be concise, practical and conversational. You run locally and should not claim cloud access.",
            )
        if self._mode == "BUILD":
            return (
                integrations.QWEN_URL,
                integrations.QWEN_SERVICE,
                "genesis-qwen",
                "You are GENESIS BUILD, the local coding and engineering assistant for GENESIS c0ckpit. "
                "Prioritize concrete implementation, debugging, tests, Linux/ROCm, Qt/QML and ComfyUI integration.",
            )
        return (
            integrations.QWEN_URL,
            integrations.QWEN_SERVICE,
            "genesis-qwen",
            "You are GENESIS STUDIO, the local creative-workflow assistant for GENESIS c0ckpit. "
            "Help with prompts, models, LoRAs, pose workflows, ComfyUI graphs and image-pipeline decisions.",
        )

    def _run_chat(self) -> None:
        try:
            base_url, service, model, system_prompt = self._route()
            online = integrations.endpoint_online(base_url, "/health", timeout=0.8)
            ok, detail = integrations.start_user_service(service, already_online=online)
            if not ok:
                raise RuntimeError(detail)

            if not online:
                self._set_status(f"Loading {self.activeModel}…")
                import time
                for _ in range(80):
                    if integrations.endpoint_online(base_url, "/health", timeout=0.8):
                        online = True
                        break
                    time.sleep(0.5)
            if not online:
                raise RuntimeError("Local assistant service did not become ready.")

            messages = [{"role": "system", "content": system_prompt}, *self._history[-18:]]
            payload = json.dumps({
                "model": model,
                "messages": messages,
                "temperature": 0.7 if self._mode == "CHAT" else 0.25,
                "max_tokens": 1200,
                "stream": False,
            }).encode("utf-8")
            request = urllib.request.Request(
                base_url.rstrip("/") + "/v1/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "GENESIS-c0ckpit/1.0"},
                method="POST",
            )
            self._set_status(f"{self._mode} · thinking locally…")
            with urllib.request.urlopen(request, timeout=300) as response:
                result = json.loads(response.read().decode("utf-8", "replace"))
            choices = result.get("choices") or []
            if not choices:
                raise RuntimeError("The local model returned no response.")
            answer = str((choices[0].get("message") or {}).get("content") or "").strip()
            if not answer:
                raise RuntimeError("The local model returned an empty response.")
            self._history.append({"role": "assistant", "content": answer})
            self._append("assistant", answer)
            self._set_status(f"{self._mode} · {self.activeModel} · ready")
        except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
            self._append("assistant", f"Local assistant error: {exc}")
            self._set_status(f"Assistant unavailable · {exc}")
        finally:
            self._set_busy(False)
