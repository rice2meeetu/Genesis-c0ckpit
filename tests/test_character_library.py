import tempfile
import unittest
from pathlib import Path
from genesis.character_library import add_reference, character_items, load_characters, preferred_reference, save_character

class CharacterLibraryTests(unittest.TestCase):
    def test_save_and_reload_character_reference(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); image=root/"person.png"; image.write_bytes(b"png")
            index=root/"characters.json"
            row=save_character("Studio Character", str(image), adult_confirmed=True, path=index)
            self.assertEqual(row["name"], "Studio Character")
            self.assertEqual(load_characters(index)[0]["primary_image"], str(image.resolve()))
            self.assertEqual(character_items(index)[0]["referenceCount"], 1)
    def test_adult_confirmation_required(self):
        with tempfile.TemporaryDirectory() as td:
            image=Path(td)/"person.png"; image.write_bytes(b"png")
            with self.assertRaisesRegex(ValueError, "18"):
                save_character("Character", str(image), adult_confirmed=False, path=Path(td)/"characters.json")

if __name__ == "__main__": unittest.main()


def test_add_reference_builds_anchor_set(tmp_path):
    index = tmp_path / "characters.json"
    primary = tmp_path / "primary.png"; primary.write_bytes(b"p")
    second = tmp_path / "full-body.png"; second.write_bytes(b"r")
    row = save_character("Nova", str(primary), adult_confirmed=True, path=index)
    updated = add_reference(row["id"], str(second), role="full-body", path=index)
    assert updated["references"] == [str(primary.resolve()), str(second.resolve())]
    assert updated["reference_roles"][str(second.resolve())] == "full-body"
    items = character_items(index)
    assert items[0]["referenceCount"] == 2
    assert len(items[0]["references"]) == 2


def test_preferred_reference_keeps_primary_identity(tmp_path):
    index = tmp_path / "characters.json"
    primary = tmp_path / "primary.png"; primary.write_bytes(b"p")
    generated = tmp_path / "approved-full.png"; generated.write_bytes(b"g")
    row = save_character("Nova", str(primary), adult_confirmed=True, path=index)
    add_reference(row["id"], str(generated), role="full-body", path=index)
    assert preferred_reference(row["id"], path=index) == str(primary.resolve())
    assert preferred_reference(row["id"], "full-body", path=index) == str(generated.resolve())


def test_reference_items_expose_roles(tmp_path):
    index = tmp_path / "characters.json"
    primary = tmp_path / "primary.png"; primary.write_bytes(b"p")
    side = tmp_path / "side.png"; side.write_bytes(b"s")
    row = save_character("Iris", str(primary), adult_confirmed=True, path=index)
    add_reference(row["id"], str(side), role="side", path=index)
    item = character_items(index)[0]
    assert item["referenceItems"][0]["role"] == "primary"
    assert item["referenceItems"][1]["role"] == "side"
    assert preferred_reference(row["id"], "side", index) == str(side.resolve())
