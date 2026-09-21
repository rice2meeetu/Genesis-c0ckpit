"""Regression checks for the saved RX 9060 XT launch profile (no GPU jobs)."""

import configparser
import shlex
import unittest
from pathlib import Path


class ComfyRuntimeProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        # systemd permits repeated directives such as ConditionPathExists.
        unit = configparser.ConfigParser(interpolation=None, strict=False)
        unit.read(root / "systemd/genesis-comfyui.service")
        cls.command = shlex.split(unit["Service"]["ExecStart"])
        cls.flags = cls.command[2:]

    def test_keeps_benchmarked_memory_flags(self):
        for flag in ("--lowvram", "--force-fp16", "--cache-none"):
            self.assertIn(flag, self.flags)
        self.assertEqual(self.flags[self.flags.index("--preview-method") + 1], "none")

    def test_async_offload_is_explicitly_disabled(self):
        self.assertIn("--disable-async-offload", self.flags)
        self.assertFalse(any(flag.startswith("--async-offload") for flag in self.flags))

    def test_rx9060_svm_memory_workarounds_are_enabled(self):
        for flag in ("--disable-pinned-memory", "--disable-dynamic-vram", "--disable-mmap"):
            self.assertIn(flag, self.flags)

    def test_does_not_force_gpu_residency_or_cpu_only_execution(self):
        for flag in ("--highvram", "--gpu-only", "--cpu", "--cache-classic"):
            self.assertNotIn(flag, self.flags)

    def test_pose_maker_uses_same_mmap_workaround(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "genesis/reference/pose_maker_app.py").read_text(encoding="utf-8")
        self.assertIn("--disable-mmap", source)
        self.assertIn("--disable-pinned-memory", source)
        self.assertIn("--disable-dynamic-vram", source)

    def test_runtime_and_local_endpoint_are_preserved(self):
        self.assertEqual(self.command[:2], [
            "%h/miniforge3/envs/comfyui-reactor-rocm/bin/python",
            "%h/AI/ComfyUI/main.py",
        ])
        self.assertEqual(self.flags[self.flags.index("--listen") + 1], "127.0.0.1")
        self.assertEqual(self.flags[self.flags.index("--port") + 1], "8188")


if __name__ == "__main__":
    unittest.main()
