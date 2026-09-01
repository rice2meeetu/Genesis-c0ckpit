import sqlite3
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from genesis.database import SCHEMA_VERSION, create_database, session
from genesis.scanner import scan_folder
from genesis.thumbnails import generate_thumbnail


class DatabaseMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "genesis.db"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_new_database_has_canonical_schema(self):
        create_database(self.db_path)
        with session(self.db_path) as connection:
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(photos)")
            }
            self.assertTrue(
                {
                    "path",
                    "file_size",
                    "modified_date",
                    "created_at",
                    "thumbnail_path",
                    "filesize",
                    "modified",
                    "created",
                }.issubset(columns)
            )
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            self.assertEqual(version, SCHEMA_VERSION)
            job_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(jobs)")
            }
            self.assertTrue({"created_at", "updated_at", "error"}.issubset(job_columns))

    def test_migrates_original_schema_without_losing_rows(self):
        connection = sqlite3.connect(self.db_path)
        connection.executescript(
            """
            CREATE TABLE photos (
                id INTEGER PRIMARY KEY,
                path TEXT UNIQUE,
                filename TEXT,
                hash TEXT,
                created TEXT,
                processed INTEGER DEFAULT 0,
                width INTEGER,
                height INTEGER,
                filesize INTEGER,
                modified TEXT,
                thumbnail_path TEXT
            );
            INSERT INTO photos (
                path, filename, filesize, modified, created
            ) VALUES (
                '/photos/one.jpg', 'one.jpg', 123, '2026-01-02', '2026-01-01'
            );
            """
        )
        connection.commit()
        connection.close()

        create_database(self.db_path)

        with session(self.db_path) as migrated:
            row = migrated.execute(
                "SELECT * FROM photos WHERE path = '/photos/one.jpg'"
            ).fetchone()
            self.assertEqual(row["file_size"], 123)
            self.assertEqual(row["modified_date"], "2026-01-02")
            self.assertEqual(row["created_at"], "2026-01-01")

    def test_legacy_and_canonical_writes_stay_compatible(self):
        with session(self.db_path) as connection:
            connection.execute(
                """
                INSERT INTO photos (path, file_size, modified_date, created_at)
                VALUES ('/photos/new.jpg', 456, 'new-modified', 'new-created')
                """
            )
            canonical = connection.execute(
                "SELECT * FROM photos WHERE path = '/photos/new.jpg'"
            ).fetchone()
            self.assertEqual(canonical["filesize"], 456)
            self.assertEqual(canonical["modified"], "new-modified")
            self.assertEqual(canonical["created"], "new-created")

            connection.execute(
                """
                INSERT INTO photos (path, filesize, modified, created)
                VALUES ('/photos/legacy.jpg', 789, 'old-modified', 'old-created')
                """
            )
            legacy = connection.execute(
                "SELECT * FROM photos WHERE path = '/photos/legacy.jpg'"
            ).fetchone()
            self.assertEqual(legacy["file_size"], 789)
            self.assertEqual(legacy["modified_date"], "old-modified")
            self.assertEqual(legacy["created_at"], "old-created")

    def test_scanner_writes_canonical_metadata(self):
        library = Path(self.temp_dir.name) / "library"
        library.mkdir()
        image_path = library / "sample.png"
        Image.new("RGB", (32, 24), "navy").save(image_path)

        result = scan_folder(library, self.db_path)

        self.assertEqual(result, {"processed": 1, "skipped": 0})
        with session(self.db_path) as connection:
            row = connection.execute(
                "SELECT * FROM photos WHERE path = ?",
                (str(image_path.resolve()),),
            ).fetchone()
            self.assertEqual((row["width"], row["height"]), (32, 24))
            self.assertGreater(row["file_size"], 0)
            self.assertEqual(row["file_size"], row["filesize"])

    def test_thumbnail_names_do_not_collide_for_same_basename(self):
        first_dir = Path(self.temp_dir.name) / "a"
        second_dir = Path(self.temp_dir.name) / "b"
        first_dir.mkdir()
        second_dir.mkdir()
        first = first_dir / "same.png"
        second = second_dir / "same.png"
        Image.new("RGB", (10, 10), "red").save(first)
        Image.new("RGB", (10, 10), "blue").save(second)

        cache_dir = Path(self.temp_dir.name) / "thumbs"
        first_thumb = generate_thumbnail(first, cache_dir)
        second_thumb = generate_thumbnail(second, cache_dir)

        self.assertNotEqual(first_thumb, second_thumb)


if __name__ == "__main__":
    unittest.main()
