import json
from pathlib import Path
import unittest

from genesis.pose_prompt_profiles import PosePromptMap, template_id

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "genesis" / "reference" / "prompt_maps" / "GENESIS_POSE_PROMPTS_KLEIN_v1.json"


class PosePromptProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prompt_map = PosePromptMap.load(MAP)

    def test_grok_source_shape_matches_audit(self):
        self.assertEqual(len(self.prompt_map.records), 485)
        self.assertEqual(self.prompt_map.template_count, 28)
        self.assertEqual(self.prompt_map.source_negative_count, 1)
        self.assertTrue(self.prompt_map.negative_review_required)

    def test_known_486th_pose_uses_explicit_fallback(self):
        missing = "lying/768512/lying009"
        with self.assertRaises(KeyError):
            self.prompt_map.record_for(missing)
        record = self.prompt_map.record_for(missing, fallback_prompt="generic lying pose fallback")
        self.assertEqual(record.source, "AUTO_FALLBACK")
        self.assertEqual(record.pose_id, missing)

    def test_qwen_profile_zeroes_negative_conditioning(self):
        record = next(iter(self.prompt_map.records.values()))
        mode, negative = self.prompt_map.negative_for_model(record, "Qwen-Rapid-AIO-NSFW-v19.safetensors")
        self.assertEqual(mode, "zeroed")
        self.assertEqual(negative, "")

    def test_regular_klein_profile_keeps_paired_negative(self):
        record = next(iter(self.prompt_map.records.values()))
        mode, negative = self.prompt_map.negative_for_model(record, "flux-2-klein-base-9b-Q4_K_M.gguf")
        self.assertEqual(mode, "paired")
        self.assertEqual(negative, record.negative_prompt)

    def test_community_cross_family_recommendations_are_available_for_klein9b(self):
        names = [x["name"] for x in self.prompt_map.filtered_lora_recommendations("flux-2-klein-base-9b-Q4_K_M.gguf")]
        self.assertIn("snofs_krea_v1_3D.safetensors", names)
        self.assertIn("lenovo_krea2_2.safetensors", names)
        self.assertIn("Klein_Anatomy_Revamped.safetensors", names)
        self.assertIn("Flux Klein - NSFW v2.safetensors", names)
        self.assertNotIn("FLUX2_KLEIN_UNLOCKED_V1.safetensors", names)

    def test_negative_override_is_template_scoped(self):
        original = next(iter(self.prompt_map.records.values()))
        updated = PosePromptMap(self.prompt_map.payload, {original.prompt_template_id: "template-specific negative"})
        replacement = updated.record_for(original.pose_id)
        self.assertEqual(replacement.negative_prompt, "template-specific negative")
        self.assertEqual(replacement.prompt_template_id, template_id(original.prompt))


if __name__ == "__main__":
    unittest.main()
