import os
import tempfile
import time
import unittest
from pathlib import Path

from PIL import Image

from genesis.visual_browser import ThumbnailCache, folder_entries, read_preview
from genesis.send_to import SendDestination, build_send_to_menu


class VisualBrowserTests(unittest.TestCase):
    def make_image(self, path, colour, size=(48, 32)):
        Image.new("RGB", size, colour).save(path)

    def test_folder_entries_stays_in_selected_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "nested"
            nested.mkdir()
            self.make_image(root / "b.png", "blue")
            self.make_image(root / "A.jpg", "red")
            self.make_image(nested / "hidden.png", "green")
            (root / "notes.txt").write_text("neutral fixture", encoding="utf-8")

            folder, folders, files = folder_entries(root)

            self.assertEqual(folder, root.resolve())
            self.assertEqual([path.resolve() for path in folders], [nested.resolve()])
            self.assertEqual([path.name for path in files], ["A.jpg", "b.png"])

    def test_newest_sort_uses_source_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            older = root / "older.png"
            newer = root / "newer.png"
            self.make_image(older, "red")
            self.make_image(newer, "blue")
            now = time.time_ns()
            os.utime(older, ns=(now - 2_000_000_000, now - 2_000_000_000))
            os.utime(newer, ns=(now, now))

            _, _, files = folder_entries(root, newest=True)

            self.assertEqual(
                [path.resolve() for path in files],
                [newer.resolve(), older.resolve()],
            )

    def test_thumbnail_cache_refreshes_when_source_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.png"
            self.make_image(source, "red")
            cache = ThumbnailCache(limit=4)
            first = cache.get(source, 32)
            self.make_image(source, "blue", size=(49, 32))
            second = cache.get(source, 32)

            self.assertNotEqual(first.getpixel((0, 0)), second.getpixel((0, 0)))

    def test_read_preview_does_not_modify_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.png"
            self.make_image(source, "purple", size=(120, 80))
            before = source.read_bytes()

            preview, dimensions, _ = read_preview(source, 40)

            self.assertEqual(dimensions, (120, 80))
            self.assertLessEqual(max(preview.size), 40)
            self.assertEqual(source.read_bytes(), before)

    def test_send_to_destinations_require_unique_stable_keys(self):
        with self.assertRaisesRegex(ValueError, "unique"):
            build_send_to_menu(
                None,
                (SendDestination("viewer", "Viewer"), SendDestination("viewer", "Again")),
                lambda _key: None,
            )


if __name__ == "__main__":
    unittest.main()
