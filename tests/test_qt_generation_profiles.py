import unittest

from qt_cockpit import build_generation_profiles


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

    def test_unavailable_models_are_not_exposed(self):
        report = {"profiles": [{"name": "Missing", "ready": False, "evidence": {"MODEL": None}}]}
        self.assertEqual(build_generation_profiles(report, []), [])


if __name__ == "__main__":
    unittest.main()
