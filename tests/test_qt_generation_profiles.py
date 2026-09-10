import unittest

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

    def test_single_lora_is_inserted(self):
        prompt = {"model": {"inputs": {}}, "sampler": {"inputs": {}}}
        insert_model_only_loras(
            prompt, "model", "sampler", "model", ["one.safetensors"]
        )
        self.assertEqual(prompt["genesis_lora_1"]["inputs"]["model"], ["model", 0])
        self.assertEqual(prompt["sampler"]["inputs"]["model"], ["genesis_lora_1", 0])

    def test_lora_stacking_is_rejected(self):
        prompt = {"model": {"inputs": {}}, "sampler": {"inputs": {}}}
        with self.assertRaisesRegex(Exception, "stacking is blocked"):
            insert_model_only_loras(
                prompt, "model", "sampler", "model", ["one.safetensors", "two.safetensors"]
            )


if __name__ == "__main__":
    unittest.main()
