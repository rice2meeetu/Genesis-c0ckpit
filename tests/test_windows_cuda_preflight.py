"""Offline regression tests for GENESIS Windows CUDA readiness (no GPU required)."""
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from windows.nvidia_preflight import cuda_preflight


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit):
        return self.data


class WindowsCudaPreflightTests(unittest.TestCase):
    def test_cuda_backend_ready(self):
        payload = {"devices": [{"type": "cuda", "name": "cuda:0 NVIDIA GeForce RTX 5060 Ti"}]}
        with patch("windows.nvidia_preflight.urlopen", return_value=FakeResponse(json.dumps(payload).encode())):
            ready, detail = cuda_preflight()
        self.assertTrue(ready)
        self.assertIn("RTX 5060 Ti", detail)

    def test_cpu_backend_is_not_ready(self):
        payload = {"devices": [{"type": "cpu", "name": "cpu"}]}
        with patch("windows.nvidia_preflight.urlopen", return_value=FakeResponse(json.dumps(payload).encode())):
            ready, detail = cuda_preflight()
        self.assertFalse(ready)
        self.assertIn("without a CUDA GPU", detail)

    def test_offline_backend_is_not_ready(self):
        with patch("windows.nvidia_preflight.urlopen", side_effect=URLError("offline")):
            ready, detail = cuda_preflight()
        self.assertFalse(ready)
        self.assertIn("offline", detail)

    def test_remote_backend_cannot_masquerade_as_local(self):
        with patch("windows.nvidia_preflight.urlopen") as opener:
            ready, detail = cuda_preflight("https://example.com")
        self.assertFalse(ready)
        opener.assert_not_called()
        self.assertIn("loopback", detail)

    def test_corrupt_response_does_not_enable_local(self):
        with patch("windows.nvidia_preflight.urlopen", return_value=FakeResponse(b"invalid")):
            ready, _detail = cuda_preflight()
        self.assertFalse(ready)

    def test_bad_device_payload_does_not_enable_local(self):
        with patch("windows.nvidia_preflight.urlopen", return_value=FakeResponse(b'{"devices": {}}')):
            ready, _detail = cuda_preflight()
        self.assertFalse(ready)


if __name__ == "__main__":
    unittest.main()
