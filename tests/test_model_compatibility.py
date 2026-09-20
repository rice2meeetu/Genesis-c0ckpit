import unittest

from genesis.model_registry import MODEL_PROFILES
from genesis.model_compatibility import (
    compatible_loras,
    is_compatible,
    lora_family,
    lora_trigger,
    model_family,
)


class ModelCompatibilityTests(unittest.TestCase):
    def test_klein4b_readiness_does_not_require_blocked_adapter(self):
        profile = next(item for item in MODEL_PROFILES if item["name"] == "FLUX.2 Klein 4B")
        self.assertEqual(profile["lora"], ())

    def test_model_families_are_distinct(self):
        self.assertEqual(model_family("flux-2-klein-4b.safetensors"), "flux2_klein_4b")
        self.assertEqual(model_family("flux-2-klein-9b-kv-fp8.safetensors"), "flux2_klein_9b_kv")
        self.assertEqual(model_family("flux-2-klein-base-9b-Q4_K_M.gguf"), "flux2_klein_9b_base")

    def test_four_b_and_nine_b_loras_do_not_cross(self):
        model = "flux-2-klein-4b.safetensors"
        self.assertTrue(is_compatible(model, "hina_flux2klein4b_asianMix_v4.0-lora.safetensors"))
        self.assertTrue(is_compatible(model, "klein4b-deepthroat-22epoc-k3nk.safetensors"))
        self.assertFalse(is_compatible("flux-2-klein-base-9b-Q4_K_M.gguf", "klein4b-deepthroat-22epoc-k3nk.safetensors"))
        self.assertFalse(is_compatible(model, "Klein_Anatomy_Revamped.safetensors"))

    def test_kv_rejects_unverified_regular_nine_b_lora(self):
        model = "flux-2-klein-9b-kv-fp8.safetensors"
        self.assertFalse(is_compatible(model, "Flux Klein - NSFW v2.safetensors"))
        self.assertEqual(compatible_loras(model, ["Flux Klein - NSFW v2.safetensors"]), [])

    def test_workflow_default_is_always_safe(self):
        self.assertTrue(is_compatible("unknown", "Use workflow default"))

    def test_aisha_has_no_implicitly_compatible_klein_lora(self):
        self.assertFalse(is_compatible("aisha_nsfw_beta_v8_fp8.safetensors", "Flux Klein - NSFW v2.safetensors"))

    def test_known_sdxl_checkpoint_accepts_sdxl_adapter(self):
        self.assertTrue(is_compatible("juggernautXL_ragnarokBy.safetensors", "add-detail-xl.safetensors"))

    def test_local_krea2_loras_keep_native_family_but_are_community_allowed_on_klein9b(self):
        model = "flux-2-klein-base-9b-Q4_K_M.gguf"
        for name in ("snofs_krea_v1_3D.safetensors", "lenovo_krea2_2.safetensors"):
            self.assertEqual(lora_family(name), "krea2")
            self.assertTrue(is_compatible(model, name))

    def test_only_metadata_verified_regular_9b_loras_are_enabled(self):
        model = "flux-2-klein-base-9b-Q4_K_M.gguf"
        verified = [
            "Flux Klein - NSFW v2.safetensors",
            "Klein_Anatomy_Revamped.safetensors",
            "flux2klein_body_version_a.safetensors",
        ]
        self.assertEqual(compatible_loras(model, verified), verified)

    def test_metadata_audit_enables_verified_4b_and_regular_9b_loras(self):
        four_b = "flux-2-klein-4b.safetensors"
        regular_nine_b = "flux-2-klein-base-9b-Q4_K_M.gguf"
        self.assertTrue(is_compatible(four_b, "f2k_4B_consist_20260314.safetensors"))
        for name in (
            "flux2klein_tocowgirl.safetensors",
            "FK_sloppydeepthroat_epoch_10.safetensors",
            "FK_teeththroat.safetensors",
        ):
            self.assertTrue(is_compatible(regular_nine_b, name))
            self.assertFalse(is_compatible(four_b, name))

    def test_metadata_triggers_are_exposed_but_not_invented(self):
        self.assertEqual(lora_trigger("F2K4BBabe_Engel_v1.0.safetensors"), "F2K4BBabe_Engel_v1.0")
        self.assertEqual(lora_trigger("FK_sloppydeepthroat_epoch_10.safetensors"), "FK_sloppydeepthroat")
        self.assertEqual(lora_trigger("FK_teeththroat.safetensors"), "FK_strappadoblowjob")
        self.assertEqual(lora_trigger("flux2klein_tocowgirl.safetensors"), "")

    def test_explicit_unverified_names_stay_blocked_even_if_filename_matches(self):
        self.assertFalse(is_compatible("flux-2-klein-base-9b-Q4_K_M.gguf", "FLUX2_KLEIN_UNLOCKED_V1.safetensors"))

    def test_community_krea_loras_are_exposed_for_regular_klein9b_only(self):
        regular = "flux-2-klein-base-9b-Q4_K_M.gguf"
        kv = "flux-2-klein-9b-kv-fp8.safetensors"
        for name in ("snofs_krea_v1_3D.safetensors", "lenovo_krea2_2.safetensors"):
            self.assertTrue(is_compatible(regular, name))
            self.assertFalse(is_compatible(kv, name))


if __name__ == "__main__":
    unittest.main()
