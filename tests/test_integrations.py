import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from genesis import integrations


class IntegrationTests(unittest.TestCase):
    def test_first_existing_prefers_first_available_runtime(self):
        candidates = (Path("/missing/preferred"), Path("/available/fallback"))
        with patch.object(Path, "exists", autospec=True) as exists:
            exists.side_effect = lambda path: str(path) == "/available/fallback"
            self.assertEqual(
                integrations.first_existing(candidates),
                Path("/available/fallback"),
            )

    def test_user_systemd_env_supplies_remote_session_bus(self):
        with patch.dict("os.environ", {}, clear=True), patch("os.getuid", return_value=1000):
            env = integrations._user_systemd_env()
        self.assertEqual(env["XDG_RUNTIME_DIR"], "/run/user/1000")
        self.assertEqual(env["DBUS_SESSION_BUS_ADDRESS"], "unix:path=/run/user/1000/bus")

    def test_start_user_service_does_not_duplicate_online_service(self):
        with patch("genesis.integrations.subprocess.run") as run:
            result = integrations.start_user_service(
                "genesis-comfyui.service",
                already_online=True,
            )
        self.assertEqual(result, (True, "Already running — no duplicate started."))
        run.assert_not_called()

    @patch("genesis.integrations.service_state", return_value="inactive")
    @patch("genesis.integrations.mount_is_writable", return_value=False)
    @patch("genesis.integrations.shutil.which", return_value="/usr/bin/flatpak")
    @patch("genesis.integrations.endpoint_online", return_value=False)
    def test_diagnostics_report_offline_without_starting_services(
        self,
        endpoint_online,
        which,
        mount_is_writable,
        service_state,
    ):
        with patch.object(Path, "is_file", return_value=True), patch.object(
            Path, "exists", return_value=False
        ):
            diagnostics = integrations.integration_diagnostics()

        self.assertEqual(
            set(diagnostics),
            {
                "ComfyUI",
                "llama.cpp",
                "Qwen Assistant",
                "Jellyfin",
                "go2rtc",
                "LM Studio",
                "FaceFusion",
                "SwarmUI",
            },
        )
        self.assertFalse(any(item["online"] for item in diagnostics.values()))

    @patch("genesis.integrations.integration_diagnostics")
    @patch("genesis.integrations._request_json")
    @patch("genesis.integrations.process_running", return_value=False)
    @patch("genesis.integrations.mount_is_writable", return_value=True)
    @patch("genesis.integrations.service_state", return_value="inactive")
    def test_status_snapshot_keeps_existing_public_fields(
        self,
        service_state,
        mount_is_writable,
        process_running,
        request_json,
        diagnostics,
    ):
        request_json.return_value = {}
        diagnostics.return_value = {
            name: {"online": False}
            for name in (
                "ComfyUI",
                "llama.cpp",
                "Qwen Assistant",
                "Jellyfin",
                "go2rtc",
            )
        }
        snapshot = integrations.status_snapshot()
        required = {
            "jellyfin_server",
            "llama_online",
            "qwen_online",
            "comfy_online",
            "go2rtc_online",
            "integrations",
        }
        self.assertTrue(required.issubset(snapshot))

    @patch("genesis.integrations.service_state", return_value="inactive")
    @patch("genesis.integrations.time.sleep")
    def test_gpu_service_start_has_cooldown(self, sleep, service_state):
        with patch("genesis.integrations.subprocess.run") as run:
            run.return_value.returncode = 0
            result = integrations.start_user_service(integrations.COMFYUI_SERVICE)
        self.assertEqual(result, (True, "Start requested."))
        sleep.assert_any_call(integrations.GPU_TRANSITION_COOLDOWN_SECONDS)

    def test_gpu_service_start_refuses_overlap(self):
        def state(name):
            return "active" if name == integrations.QWEN_SERVICE else "inactive"
        with patch("genesis.integrations.service_state", side_effect=state), patch(
            "genesis.integrations.subprocess.run"
        ) as run:
            ok, detail = integrations.start_user_service(integrations.COMFYUI_SERVICE)
        self.assertFalse(ok)
        self.assertIn(integrations.QWEN_SERVICE, detail)
        run.assert_not_called()

    def test_ai_model_volume_accepts_existing_read_only_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            mount = Path(tmp) / "Ai"
            required = mount / "AI-Models/diffusion_models/model.safetensors"
            required.parent.mkdir(parents=True)
            required.touch()
            with patch.object(integrations, "AI_MODEL_MOUNT", mount), patch(
                "genesis.integrations.mount_is_writable", return_value=False
            ), patch("genesis.integrations.subprocess.run") as run:
                ok, detail = integrations.ensure_ai_model_volume_readonly(required)
        self.assertTrue(ok)
        self.assertIn("ready read-only", detail)
        run.assert_not_called()

    def test_ai_model_volume_mounts_by_label_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            device = root / "Ai-device"
            device.touch()
            mount = root / "Ai"
            required = mount / "AI-Models/diffusion_models/model.safetensors"

            def mounted(command, **kwargs):
                required.parent.mkdir(parents=True, exist_ok=True)
                required.touch()
                return subprocess.CompletedProcess(command, 0, stdout="mounted", stderr="")

            with patch.object(integrations, "AI_MODEL_VOLUME", device), patch.object(
                integrations, "AI_MODEL_MOUNT", mount
            ), patch("genesis.integrations.shutil.which", return_value="/usr/bin/udisksctl"), patch(
                "genesis.integrations.mount_is_writable", return_value=False
            ), patch("genesis.integrations.subprocess.run", side_effect=mounted) as run:
                ok, detail = integrations.ensure_ai_model_volume_readonly(required)
        self.assertTrue(ok)
        self.assertIn("Mounted Ai model volume read-only", detail)
        command = run.call_args.args[0]
        self.assertEqual(command[:3], ["udisksctl", "mount", "-b"])
        self.assertEqual(command[-2:], ["--options", "ro"])

    def test_ai_model_volume_refuses_existing_read_write_mount(self):
        with tempfile.TemporaryDirectory() as tmp:
            mount = Path(tmp) / "Ai"
            required = mount / "model.safetensors"
            mount.mkdir()
            required.touch()
            with patch.object(integrations, "AI_MODEL_MOUNT", mount), patch(
                "genesis.integrations.mount_is_writable", return_value=True
            ):
                ok, detail = integrations.ensure_ai_model_volume_readonly(required)
        self.assertFalse(ok)
        self.assertIn("read-write", detail)

    def test_gpu_kernel_preflight_is_clean_without_svm_warning(self):
        with patch("genesis.integrations.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "normal kernel output"
            self.assertEqual(
                integrations.gpu_kernel_preflight(),
                (True, "GPU kernel preflight clean."),
            )

    def test_gpu_kernel_preflight_latches_after_svm_warning(self):
        with patch("genesis.integrations.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "workqueue: svm_range_restore_work [amdgpu] hogged CPU"
            ok, detail = integrations.gpu_kernel_preflight()
        self.assertFalse(ok)
        self.assertIn("reboot required", detail)
        self.assertIn("svm_range_restore_work", detail)


if __name__ == "__main__":
    unittest.main()
