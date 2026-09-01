import json
import tempfile
import unittest
from pathlib import Path

from genesis import workflow_lab


class WorkflowLabTests(unittest.TestCase):
    def test_gpu_acceleration_rejects_cpu_mode(self):
        stats = {
            "system": {"argv": ["main.py", "--cpu"]},
            "devices": [{"name": "cpu", "type": "cpu"}],
        }
        self.assertFalse(workflow_lab.gpu_acceleration_available(stats))

    def test_gpu_acceleration_accepts_rocm_device(self):
        stats = {
            "system": {"argv": ["main.py", "--force-fp16"]},
            "devices": [{"name": "AMD Radeon RX 9060 XT", "type": "cuda"}],
        }
        self.assertTrue(workflow_lab.gpu_acceleration_available(stats))

    def test_workflow_browser_ignores_index_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflow = {
                "1": {"class_type": "KSampler", "inputs": {}},
            }
            (root / "render.json").write_text(json.dumps(workflow), encoding="utf-8")
            (root / ".index.json").write_text(json.dumps(workflow), encoding="utf-8")

            found = workflow_lab.workflow_browser([root])
            paths = {Path(item["path"]).name for item in found}

        self.assertIn("render.json", paths)
        self.assertNotIn(".index.json", paths)

    def test_negative_prompt_gets_separate_conditioning(self):
        prompt = {
            "4": {
                "class_type": "DualCLIPLoaderGGUF",
                "inputs": {"clip_name1": "encoder.safetensors"},
            },
            "5": {
                "class_type": "CLIPTextEncode",
                "inputs": {"clip": ["4", 0], "text": "positive"},
                "_meta": {"title": "Positive Prompt"},
            },
            "6": {
                "class_type": "KSampler",
                "inputs": {"positive": ["5", 0]},
            },
        }

        negative_id = workflow_lab.apply_negative_prompt(prompt, "blur, artifacts")

        self.assertIsNotNone(negative_id)
        self.assertNotEqual(negative_id, "5")
        self.assertEqual(prompt[negative_id]["inputs"]["text"], "blur, artifacts")
        self.assertEqual(prompt[negative_id]["inputs"]["clip"], ["4", 0])
        self.assertEqual(prompt["6"]["inputs"]["negative"], [negative_id, 0])
        self.assertEqual(prompt["5"]["inputs"]["text"], "positive")

    def test_loader_widget_values_survive_stale_model_inventory(self):
        workflow = {
            "nodes": [{
                "id": 1,
                "type": "UNETLoader",
                "widgets_values": ["flux-2-klein-9b-kv-fp8.safetensors", "default"],
                "inputs": [],
            }],
            "links": [],
        }
        info = {
            "UNETLoader": {"input": {"required": {
                "unet_name": [["another-model.safetensors"]],
                "weight_dtype": [["default", "fp8_e4m3fn"]],
            }}},
        }

        prompt = workflow_lab.workflow_to_prompt(workflow, info)

        self.assertEqual(
            prompt["1"]["inputs"],
            {"unet_name": "flux-2-klein-9b-kv-fp8.safetensors", "weight_dtype": "default"},
        )

    def test_load_image_widget_is_mapped_for_phroot_workflows(self):
        workflow = {
            "nodes": [{
                "id": 2,
                "type": "LoadImage",
                "widgets_values": ["face_reference.png", "image"],
                "inputs": [],
            }],
            "links": [],
        }
        info = {"LoadImage": {"input": {"required": {"image": ["IMAGE"]}}}}

        prompt = workflow_lab.workflow_to_prompt(workflow, info)

        self.assertEqual(prompt["2"]["inputs"]["image"], "face_reference.png")

    def test_phroot_resize_widget_is_not_mapped_as_third_image(self):
        workflow = {
            "nodes": [{
                "id": 4,
                "type": "TextEncodeQwenImageEditPlus",
                "widgets_values": ["preserve identity", 896],
                "inputs": [],
            }],
            "links": [],
        }
        info = {"TextEncodeQwenImageEditPlus": {"input": {
            "required": {"clip": ["CLIP"], "prompt": ["STRING"]},
            "optional": {"image3": ["IMAGE"]},
        }}}

        prompt = workflow_lab.workflow_to_prompt(workflow, info)

        self.assertEqual(prompt["4"]["inputs"], {"prompt": "preserve identity"})


if __name__ == "__main__":
    unittest.main()
