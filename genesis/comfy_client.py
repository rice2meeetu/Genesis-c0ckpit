"""Small dependency-free ComfyUI client used by GENESIS Workflow Lab."""

from __future__ import annotations

import json
import mimetypes
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable


class ComfyError(RuntimeError):
    """Raised when ComfyUI rejects a request or returns malformed data."""


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value).encode("utf-8")


@dataclass
class PromptResult:
    prompt_id: str
    status: str
    outputs: list[dict] = field(default_factory=list)
    history: dict = field(default_factory=dict)
    elapsed: float = 0.0
    error: str | None = None


class ComfyClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8188",
        *,
        timeout: float = 20.0,
        opener=None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client_id = f"genesis-{uuid.uuid4()}"
        self.opener = opener or urllib.request.urlopen

    def _request(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: Any = None,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        expect_json: bool = True,
    ):
        url = self.base_url + "/" + path.lstrip("/")
        request_headers = {"User-Agent": "GENESIS-Workflow-Lab/2.0"}
        if headers:
            request_headers.update(headers)
        if payload is not None:
            data = _json_bytes(payload)
            request_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            url,
            data=data,
            headers=request_headers,
            method=method,
        )
        try:
            with self.opener(request, timeout=timeout or self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise ComfyError(f"ComfyUI HTTP {exc.code}: {detail}") from exc
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            raise ComfyError(f"ComfyUI unavailable: {exc}") from exc
        if not expect_json:
            return raw
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8", "replace"))
        except json.JSONDecodeError as exc:
            raise ComfyError("ComfyUI returned invalid JSON") from exc

    def system_stats(self) -> dict:
        value = self._request("/system_stats", timeout=max(5.0, self.timeout))
        return value if isinstance(value, dict) else {}

    def object_info(self) -> dict:
        value = self._request("/object_info", timeout=max(30.0, self.timeout))
        return value if isinstance(value, dict) else {}

    def queue(self) -> dict:
        value = self._request("/queue", timeout=max(5.0, self.timeout))
        return value if isinstance(value, dict) else {}

    def history(self, prompt_id: str | None = None, max_items: int = 100) -> dict:
        path = f"/history/{urllib.parse.quote(prompt_id)}" if prompt_id else f"/history?max_items={max_items}"
        value = self._request(path, timeout=max(10.0, self.timeout))
        return value if isinstance(value, dict) else {}

    def submit(self, prompt: dict, *, extra_data: dict | None = None) -> str:
        body = {"prompt": prompt, "client_id": self.client_id}
        if extra_data:
            body["extra_data"] = extra_data
        value = self._request("/prompt", method="POST", payload=body, timeout=30)
        if not isinstance(value, dict) or not value.get("prompt_id"):
            raise ComfyError(f"ComfyUI rejected prompt: {value}")
        return str(value["prompt_id"])

    def interrupt(self) -> None:
        self._request("/interrupt", method="POST", payload={})

    def cancel(self, prompt_ids: Iterable[str]) -> None:
        ids = [str(value) for value in prompt_ids if value]
        if ids:
            self._request("/queue", method="POST", payload={"delete": ids})

    def clear_queue(self) -> None:
        self._request("/queue", method="POST", payload={"clear": True})

    def upload_image(
        self,
        path: str | Path,
        *,
        filename: str | None = None,
        subfolder: str = "genesis",
        overwrite: bool = True,
    ) -> dict:
        path = Path(path)
        return self.upload_image_bytes(
            path.read_bytes(),
            filename=filename or path.name,
            content_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            subfolder=subfolder,
            overwrite=overwrite,
        )

    def upload_image_bytes(
        self,
        data: bytes,
        *,
        filename: str,
        content_type: str = "image/png",
        subfolder: str = "genesis",
        overwrite: bool = True,
    ) -> dict:
        boundary = f"----Genesis{uuid.uuid4().hex}"
        parts: list[bytes] = []

        def field(name: str, value: str):
            parts.extend([
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode(),
                b"\r\n",
            ])

        parts.extend([
            f"--{boundary}\r\n".encode(),
            (
                'Content-Disposition: form-data; name="image"; '
                f'filename="{filename}"\r\n'
            ).encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            data,
            b"\r\n",
        ])
        field("type", "input")
        field("subfolder", subfolder)
        field("overwrite", "true" if overwrite else "false")
        parts.append(f"--{boundary}--\r\n".encode())
        value = self._request(
            "/upload/image",
            method="POST",
            data=b"".join(parts),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            timeout=60,
        )
        if not isinstance(value, dict) or not value.get("name"):
            raise ComfyError(f"Image upload failed: {value}")
        return value

    def view(self, output: dict) -> bytes:
        query = urllib.parse.urlencode({
            "filename": output.get("filename", ""),
            "subfolder": output.get("subfolder", ""),
            "type": output.get("type", "output"),
        })
        return self._request(f"/view?{query}", expect_json=False, timeout=30)

    def wait(
        self,
        prompt_id: str,
        *,
        poll_interval: float = 0.75,
        timeout: float = 1800,
        progress: Callable[[dict], None] | None = None,
        abort_check: Callable[[], str | None] | None = None,
    ) -> PromptResult:
        started = time.monotonic()
        missing_since: float | None = None
        while True:
            elapsed = time.monotonic() - started
            reason = abort_check() if abort_check else None
            if reason:
                try:
                    self.interrupt()
                except ComfyError:
                    pass
                try:
                    self.cancel([prompt_id])
                except ComfyError:
                    pass
                return PromptResult(prompt_id, "interrupted", elapsed=elapsed, error=reason)
            if elapsed > timeout:
                return PromptResult(prompt_id, "timeout", elapsed=elapsed, error="Timed out")
            history = self.history(prompt_id)
            record = history.get(prompt_id) if isinstance(history, dict) else None
            if isinstance(record, dict):
                outputs = collect_outputs(record)
                status_data = record.get("status") or {}
                completed = status_data.get("completed")
                status = "completed" if completed is not False else "error"
                messages = status_data.get("messages") or []
                error = None if status == "completed" else json.dumps(messages, default=str)
                if progress:
                    progress({"status": status, "elapsed": elapsed, "prompt_id": prompt_id})
                return PromptResult(prompt_id, status, outputs, record, elapsed, error)
            queue = self.queue()
            state = prompt_queue_state(queue, prompt_id)
            if progress:
                progress({"status": state, "elapsed": elapsed, "prompt_id": prompt_id})
            if state == "missing":
                if missing_since is None:
                    missing_since = time.monotonic()
                elif time.monotonic() - missing_since > 30.0:
                    return PromptResult(
                        prompt_id,
                        "missing",
                        elapsed=elapsed,
                        error="Prompt left queue without history after 30s grace period",
                    )
            else:
                missing_since = None
            time.sleep(poll_interval)


def prompt_queue_state(queue: dict, prompt_id: str) -> str:
    for item in queue.get("queue_running") or []:
        if len(item) > 1 and str(item[1]) == str(prompt_id):
            return "running"
    for item in queue.get("queue_pending") or []:
        if len(item) > 1 and str(item[1]) == str(prompt_id):
            return "pending"
    return "missing"


def collect_outputs(history_record: dict) -> list[dict]:
    found: list[dict] = []
    for node_id, value in (history_record.get("outputs") or {}).items():
        if not isinstance(value, dict):
            continue
        for kind in ("images", "gifs", "audio"):
            for item in value.get(kind) or []:
                if isinstance(item, dict):
                    found.append({"node_id": str(node_id), "kind": kind, **item})
    return found
