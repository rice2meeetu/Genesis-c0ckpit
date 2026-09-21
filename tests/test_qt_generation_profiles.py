import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from qt_cockpit import build_generation_profiles, insert_model_only_loras


class QtGenerationProfileTests(unittest.TestCase):
    def test_regular_and_kv_klein_loras_remain_separate(self):
        report = {
            "profiles": [
                {
                    "name": "FLUX.2 Klein 9B-KV FP8",
                    "ready": True,
                    "evidence": {"MODEL": "/models/flux-2-klein-9b-kv-fp8.safetensors"},
                },
                {
                    "name": "FLUX.2 Klein 9B Base",
                    "ready": True,
                    "evidence": {"MODEL": "/models/flux-2-klein-base-9b-Q4_K_M.gguf"},
                },
            ]
        }
        profiles = build_generation_profiles(report, [
            "Flux Klein - NSFW v2.safetensors",
            "Klein_Anatomy_Revamped.safetensors",
        ])
        self.assertEqual(profiles[0]["label"], "FLUX.2 Klein 9B Base")
        self.assertEqual(profiles[0]["loras"], [
            "None", "Flux Klein - NSFW v2.safetensors", "Klein_Anatomy_Revamped.safetensors",
        ])
        self.assertEqual(profiles[1]["loras"], ["None"])
        self.assertTrue(profiles[0]["runnable"])
        self.assertTrue(profiles[1]["runnable"])

    def test_phroot_is_runnable_but_explicitly_requires_source(self):
        report = {"profiles": [{
            "name": "Phr00t / QwenRapid AIO",
            "ready": True,
            "evidence": {"MODEL": "/models/Qwen-Rapid-AIO-NSFW-v19.safetensors"},
        }]}
        profile = build_generation_profiles(report, [])[0]
        self.assertTrue(profile["runnable"])
        self.assertTrue(profile["sourceRequired"])

    def test_unavailable_models_are_not_exposed(self):
        report = {"profiles": [{"name": "Missing", "ready": False, "evidence": {"MODEL": None}}]}
        self.assertEqual(build_generation_profiles(report, []), [])

    def test_compatible_lora_trigger_words_are_exposed_to_qml(self):
        report = {
            "profiles": [{
                "name": "FLUX.2 Klein 9B Base",
                "ready": True,
                "evidence": {"MODEL": "/models/flux-2-klein-base-9b-Q4_K_M.gguf"},
            }]
        }
        profiles = build_generation_profiles(
            report,
            ["flux2klein_body_version_a.safetensors"],
            {"flux2klein_body_version_a.safetensors": ["woman"]},
        )
        self.assertEqual(
            profiles[0]["triggers"]["flux2klein_body_version_a.safetensors"],
            ["woman"],
        )

    def test_unvalidated_inventory_model_is_visible_but_not_runnable(self):
        report = {"profiles": [{
            "name": "Aisha 9B",
            "ready": True,
            "evidence": {"MODEL": "/models/aisha-9b.safetensors"},
        }]}
        profile = build_generation_profiles(report, [])[0]
        self.assertTrue(profile["ready"])
        self.assertFalse(profile["runnable"])
        self.assertIn("not yet validated", profile["note"])

    def test_legacy_generate_forwards_original_pose_contract(self):
        from qt_cockpit import GenerationBridge, FOUR_B_MODEL
        class Recorder:
            def queueGenerate(self, *args):
                self.args = args
        recorder = Recorder()
        GenerationBridge.queueGenerateLegacy(
            recorder, "A ceramic vase", "", 512, 512, FOUR_B_MODEL,
            "None", "None", "file:///source.png", "file:///pose.png",
            False, False, False,
        )
        self.assertEqual(len(recorder.args), 16)
        self.assertEqual(recorder.args[7:11], ("None", 0.5, 0.5, 0.5))
        self.assertEqual(recorder.args[11:13], ("file:///source.png", "file:///pose.png"))

    def test_generate_exposes_both_qml_signatures(self):
        from qt_cockpit import GenerationBridge
        meta = GenerationBridge.staticMetaObject
        counts = {
            meta.method(i).parameterCount()
            for i in range(meta.methodOffset(), meta.methodCount())
            if bytes(meta.method(i).name()) == b"queueGenerate"
        }
        self.assertEqual(counts, {12, 16})

    def test_single_lora_is_inserted(self):
        prompt = {"model": {"inputs": {}}, "sampler": {"inputs": {}}}
        insert_model_only_loras(
            prompt, "model", "sampler", "model", ["one.safetensors"]
        )
        self.assertEqual(prompt["genesis_lora_1"]["inputs"]["model"], ["model", 0])
        self.assertEqual(prompt["sampler"]["inputs"]["model"], ["genesis_lora_1", 0])

    def test_lora_stacking_chains_in_selection_order(self):
        prompt = {"model": {"inputs": {}}, "sampler": {"inputs": {}}}
        insert_model_only_loras(
            prompt, "model", "sampler", "model", ["one.safetensors", "two.safetensors"]
        )
        self.assertEqual(prompt["genesis_lora_2"]["inputs"]["model"], ["genesis_lora_1", 0])
        self.assertEqual(prompt["sampler"]["inputs"]["model"], ["genesis_lora_2", 0])

    def test_lora_stacking_preserves_individual_strengths(self):
        prompt = {"model": {"inputs": {}}, "sampler": {"inputs": {}}}
        insert_model_only_loras(
            prompt, "model", "sampler", "model",
            ["one.safetensors", "two.safetensors"], [0.35, 0.8],
        )
        self.assertEqual(prompt["genesis_lora_1"]["inputs"]["strength_model"], 0.35)
        self.assertEqual(prompt["genesis_lora_2"]["inputs"]["strength_model"], 0.8)

    def test_duplicate_lora_is_rejected(self):
        prompt = {"model": {"inputs": {}}, "sampler": {"inputs": {}}}
        with self.assertRaisesRegex(Exception, "only once"):
            insert_model_only_loras(
                prompt, "model", "sampler", "model",
                ["one.safetensors", "one.safetensors"], [0.5, 0.7],
            )

    def test_on_demand_comfy_connector_starts_guarded_backend(self):
        from qt_cockpit import GenerationBridge
        client = Mock()
        client.system_stats.return_value = {"devices": []}
        with patch("qt_cockpit.integrations.gpu_kernel_preflight", return_value=(True, "clean")), \
             patch("qt_cockpit.integrations.endpoint_online", return_value=False), \
             patch("qt_cockpit.integrations.start_user_service", return_value=(True, "Start requested.")) as start, \
             patch("qt_cockpit.workflow_lab.ComfyClient", return_value=client), \
             patch("qt_cockpit.workflow_lab.gpu_acceleration_available", return_value=True):
            resolved, stats = GenerationBridge._connect_comfyui(object())
        self.assertIs(resolved, client)
        self.assertEqual(stats, {"devices": []})
        start.assert_called_once()

    def test_on_demand_comfy_connector_obeys_kernel_latch_before_start(self):
        from qt_cockpit import GenerationBridge, workflow_lab
        with patch(
            "qt_cockpit.integrations.gpu_kernel_preflight",
            return_value=(False, "GPU safety latch: reboot required"),
        ), patch("qt_cockpit.integrations.start_user_service") as start:
            with self.assertRaisesRegex(workflow_lab.ComfyError, "reboot required"):
                GenerationBridge._connect_comfyui(object())
        start.assert_not_called()

    def test_two_image_face_swap_route_is_exposed(self):
        from qt_cockpit import GenerationBridge
        meta = GenerationBridge.staticMetaObject
        counts = {
            meta.method(i).parameterCount()
            for i in range(meta.methodOffset(), meta.methodCount())
            if bytes(meta.method(i).name()) == b"queueFaceSwap"
        }
        self.assertEqual(counts, {2})
        root = Path(__file__).resolve().parents[1]
        qml = (root / "genesis/qt_ui/MainPremiumLinux.qml").read_text(encoding="utf-8")
        self.assertIn('{title:"Face Swap"', qml)
        self.assertIn('mediaCard.actionKey === "face swap"', qml)
        self.assertIn("faceSwapTarget", qml)
        self.assertIn("faceSwapSource", qml)
        self.assertIn("genesisBridge.queueFaceSwap", qml)

    def test_module_pages_route_buttons_through_qt_bridge(self):
        root = Path(__file__).resolve().parents[1]
        qml = (root / "genesis/qt_ui/Main.qml").read_text(encoding="utf-8")
        python = (root / "qt_cockpit.py").read_text(encoding="utf-8")
        self.assertIn("moduleBridge.triggerAction(modelData.action)", qml)
        self.assertIn("moduleBridge.triggerAction(modelData)", qml)
        self.assertIn('setContextProperty("moduleBridge", module_bridge)', python)
        self.assertNotIn(
            'GoldButton { Layout.fillWidth: true; text: modelData.action; enabled: false }',
            qml,
        )


if __name__ == "__main__":
    unittest.main()