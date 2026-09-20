import unittest

from pathlib import Path
from tempfile import TemporaryDirectory

from genesis.asset_inventory import inventory_records, unavailable_local_assets


class AssetInventoryTests(unittest.TestCase):
    def test_inventory_normalizes_names_without_opening_assets(self):
        records = inventory_records({
            "diffusion_models": ["model-b.safetensors", "model-a.safetensors"],
            "checkpoints": ["checkpoint.safetensors"],
            "loras": ["style.safetensors", "style.safetensors", ""],
            "vaes": ["vae.safetensors"],
        })
        self.assertEqual(
            [(record.kind, record.name) for record in records],
            [
                ("Checkpoint", "checkpoint.safetensors"),
                ("LoRA", "style.safetensors"),
                ("Model", "model-a.safetensors"),
                ("Model", "model-b.safetensors"),
                ("VAE", "vae.safetensors"),
            ],
        )

    def test_inventory_ignores_unknown_or_non_list_payloads(self):
        self.assertEqual(inventory_records({"loras": "not-a-list", "unknown": ["x"]}), [])

    def test_broken_loader_link_is_reported_before_submit(self):
        with TemporaryDirectory() as root:
            root_path = Path(root)
            model_dir = root_path / "text_encoders"
            model_dir.mkdir()
            broken = model_dir / "encoder.safetensors"
            broken.symlink_to(root_path / "missing.safetensors")
            prompt = {
                "clip": {
                    "class_type": "CLIPLoader",
                    "inputs": {"clip_name": "encoder.safetensors"},
                }
            }
            issues = unavailable_local_assets(prompt, (root_path,))
            self.assertEqual(len(issues), 1)
            self.assertIn("broken link", issues[0])


if __name__ == "__main__":
    unittest.main()
