import unittest

from genesis.generation_pipeline import (
    GenerationState,
    adapt_prompt,
    build_pipeline_plan,
    compatible_selection,
)


class GenerationPipelineTests(unittest.TestCase):
    def test_source_and_preset_are_order_independent(self):
        initial = GenerationState(model="flux-2-klein-base-9b-Q4_K_M.gguf")
        source_first = initial.with_changes(source_image="person.png").with_changes(
            preset_id="grok-12", prompt="lying pose"
        )
        preset_first = initial.with_changes(preset_id="grok-12", prompt="lying pose").with_changes(
            source_image="person.png"
        )
        self.assertEqual(source_first, preset_first)

    def test_klein_adapter_keeps_user_text_and_adds_narrative_sections(self):
        result = adapt_prompt("rear three-quarter pose", "flux-2-klein-base-9b-Q4_K_M.gguf")
        self.assertIn("Subject: rear three-quarter pose", result)
        self.assertIn("Setting:", result)
        self.assertIn("Composition:", result)
        self.assertIn("Lighting:", result)
        self.assertIn("Texture:", result)

    def test_qwen_adapter_prioritises_identity_for_source_edits(self):
        result = adapt_prompt("turn toward camera", "Qwen-Rapid-AIO-NSFW-v19.safetensors", source_image=True)
        self.assertIn("Preserve the same person", result)
        self.assertIn("turn toward camera", result)

    def test_incompatible_lora_is_blocked(self):
        with self.assertRaisesRegex(ValueError, "Incompatible"):
            compatible_selection(
                "flux-2-klein-base-9b-Q4_K_M.gguf",
                ["hina_flux2klein4b_asianMix_v4.0-lora.safetensors"],
            )

    def test_each_enabled_stage_consumes_previous_output(self):
        state = GenerationState(
            source_image="person.png",
            prompt="standing pose",
            model="Qwen-Rapid-AIO-NSFW-v19.safetensors",
            use_stage2=True,
            use_stage3=True,
            use_upscale=True,
        )
        plan = build_pipeline_plan(state, "/workflows")
        self.assertEqual([stage.number for stage in plan], [1, 2, 3, 4])
        self.assertEqual(plan[1].input_source, "stage1.output")
        self.assertEqual(plan[2].input_source, "stage2.output")
        self.assertEqual(plan[3].input_source, "stage3.output")

    def test_stage_three_requires_original_source(self):
        state = GenerationState(prompt="portrait", model="flux-2-klein-base-9b-Q4_K_M.gguf", use_stage3=True)
        with self.assertRaisesRegex(ValueError, "original source image"):
            build_pipeline_plan(state)


if __name__ == "__main__":
    unittest.main()
