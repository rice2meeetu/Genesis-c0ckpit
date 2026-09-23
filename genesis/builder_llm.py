from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from genesis import integrations


class LocalLLM:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.base_url = (base_url or integrations.BUILDER_URL).rstrip("/")
        self.model = model or str(integrations.BUILDER_MODEL)

    def _ensure_ready(self) -> None:
        online = integrations.endpoint_online(self.base_url, "/health", timeout=0.8)
        if not online:
            # A BUILD request explicitly switches FeeFee's own local coding route.
            # Do not auto-stop image generation or unrelated local LLM workloads.
            for service in (integrations.ASSISTANT_SERVICE, integrations.QWEN_SERVICE):
                if integrations.service_state(service) == "active":
                    stopped, detail = integrations.stop_user_service(service)
                    if not stopped:
                        raise RuntimeError(detail)
        ok, detail = integrations.start_user_service(
            integrations.BUILDER_SERVICE, already_online=online
        )
        if not ok:
            raise RuntimeError(detail)
        if online:
            return
        for _ in range(180):
            if integrations.endpoint_online(self.base_url, "/health", timeout=0.8):
                return
            time.sleep(0.5)
        raise RuntimeError("GENESIS Builder service did not become ready")

    def chat(
        self,
        system: str,
        user: str,
        temperature: float = 0.0,
        max_tokens: int = 1400,
    ) -> str:
        self._ensure_ready()

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        req = urllib.request.Request(
            self.base_url + "/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                result = json.loads(r.read().decode("utf-8"))

        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"LOCAL LLM HTTP {exc.code}\n{body}"
            ) from exc

        return result["choices"][0]["message"]["content"]
