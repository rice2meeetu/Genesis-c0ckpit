import unittest

from genesis.model_compatibility import (
    compatible_loras,
    is_compatible,
    model_family,
)


class ModelCompatibilityTests(unittest.TestCase):
    def test_model_families_are_distinct(self):
        self.assertEqual(model_family("flux-2-klein-4b.safetensors"), "flux2_klein_4b")
        self.assertEqual(model_family("flux-2-klein-9b-kv-fp8.safetensors"), "flux2_klein_9b_kv")
        self.assertEqual(model_family("flux-2-klein-base-9b.safetensors"), "flux2_klein_9b_base")

    def test_four_b_and_nine_b_loras_do_not_cross(self):
        model = "flux-2-klein-4b.safetensors"
        self.assertTrue(is_compatible(model, "hina_flux2klein4b_asianMix_v4.0-lora.safetensors"))
        self.assertFalse(is_compatible(model, "Klein_Anatomy_Revamped.safetensors"))

    def test_kv_rejects_unverified_regular_nine_b_lora(self):
        model = "flux-2-klein-9b-kv-fp8.safetensors"
        self.assertFalse(is_compatible(model, "Flux Klein - NSFW v2.safetensors"))
        self.assertEqual(compatible_loras(model, ["Flux Klein - NSFW v2.safetensors"]), [])

    def test_workflow_default_is_always_safe(self):
        self.assertTrue(is_compatible("unknown", "Use workflow default"))

    def test_aisha_has_no_implicitly_compatible_klein_lora(self):
        self.assertFalse(is_compatible(
            "aisha_nsfw_beta_v8_fp8.safetensors",
            "Flux Klein - NSFW v2.safetensors",
        ))

    def test_known_sdxl_checkpoint_accepts_sdxl_adapter(self):
        self.assertTrue(is_compatible(
            "juggernautXL_ragnarokBy.safetensors",
            "add-detail-xl.safetensors",
        ))


if __name__ == "__main__":
    unittest.main()
