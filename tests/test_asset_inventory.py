import unittest

from genesis.asset_inventory import inventory_records


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


if __name__ == "__main__":
    unittest.main()
