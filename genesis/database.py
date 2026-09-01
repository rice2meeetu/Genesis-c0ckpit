"""Canonical SQLite schema and connection helpers for GENESIS.

The project historically used two names for several photo metadata fields.
The canonical API uses ``file_size``, ``modified_date`` and ``created_at``.
Legacy columns remain synchronized so older standalone tools keep working while
they are migrated to this module.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB = PROJECT_ROOT / "database" / "genesis.db"
SCHEMA_VERSION = 1


PHOTO_COLUMNS = {
    "filename": "TEXT",
    "hash": "TEXT",
    "person_id": "INTEGER",
    "processed": "INTEGER NOT NULL DEFAULT 0",
    "width": "INTEGER",
    "height": "INTEGER",
    "file_size": "INTEGER DEFAULT 0",
    "modified_date": "TEXT",
    "created_at": "TEXT",
    "thumbnail_path": "TEXT",
    "face_count": "INTEGER NOT NULL DEFAULT 0",
    "face_data": "TEXT",
    "filesize": "INTEGER",
    "modified": "TEXT",
    "created": "TEXT",
}

JOB_COLUMNS = {
    "created_at": "TEXT",
    "updated_at": "TEXT",
    "error": "TEXT",
    "progress": "REAL NOT NULL DEFAULT 0",
    "detail": "TEXT",
    "workflow": "TEXT",
    "outputs": "TEXT",
}


def resolve_db_path(db_path: str | Path | None = None) -> Path:
    """Return an absolute database path independent of the process CWD."""
    return Path(db_path).expanduser().resolve() if db_path else DB


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        str(row[1])
        for row in connection.execute(f'PRAGMA table_info("{table}")')
    }


def _add_missing_photo_columns(connection: sqlite3.Connection) -> None:
    existing = _columns(connection, "photos")
    for name, declaration in PHOTO_COLUMNS.items():
        if name not in existing:
            connection.execute(
                f'ALTER TABLE photos ADD COLUMN "{name}" {declaration}'
            )


def _add_missing_job_columns(connection: sqlite3.Connection) -> None:
    existing = _columns(connection, "jobs")
    for name, declaration in JOB_COLUMNS.items():
        if name not in existing:
            connection.execute(
                f'ALTER TABLE jobs ADD COLUMN "{name}" {declaration}'
            )


def _backfill_compatibility_columns(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        UPDATE photos
        SET file_size = COALESCE(NULLIF(file_size, 0), filesize, 0),
            modified_date = COALESCE(modified_date, modified),
            created_at = COALESCE(created_at, created),
            filesize = COALESCE(filesize, file_size, 0),
            modified = COALESCE(modified, modified_date),
            created = COALESCE(created, created_at)
        """
    )


def _create_compatibility_triggers(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TRIGGER IF NOT EXISTS photos_sync_after_insert
        AFTER INSERT ON photos
        BEGIN
            UPDATE photos
            SET file_size = COALESCE(NULLIF(NEW.file_size, 0), NEW.filesize, 0),
                filesize = COALESCE(NEW.filesize, NEW.file_size, 0),
                modified_date = COALESCE(NEW.modified_date, NEW.modified),
                modified = COALESCE(NEW.modified, NEW.modified_date),
                created_at = COALESCE(NEW.created_at, NEW.created),
                created = COALESCE(NEW.created, NEW.created_at)
            WHERE id = NEW.id;
        END;

        CREATE TRIGGER IF NOT EXISTS photos_sync_legacy_after_update
        AFTER UPDATE OF filesize, modified, created ON photos
        BEGIN
            UPDATE photos
            SET file_size = COALESCE(NEW.filesize, 0),
                modified_date = NEW.modified,
                created_at = NEW.created
            WHERE id = NEW.id;
        END;

        CREATE TRIGGER IF NOT EXISTS photos_sync_canonical_after_update
        AFTER UPDATE OF file_size, modified_date, created_at ON photos
        BEGIN
            UPDATE photos
            SET filesize = COALESCE(NEW.file_size, 0),
                modified = NEW.modified_date,
                created = NEW.created_at
            WHERE id = NEW.id;
        END;
        """
    )


def migrate(connection: sqlite3.Connection) -> None:
    """Bring an open database to the current non-destructive schema version."""
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            filename TEXT,
            hash TEXT,
            person_id INTEGER,
            processed INTEGER NOT NULL DEFAULT 0,
            width INTEGER,
            height INTEGER,
            file_size INTEGER DEFAULT 0,
            modified_date TEXT,
            created_at TEXT,
            thumbnail_path TEXT,
            face_count INTEGER NOT NULL DEFAULT 0,
            face_data TEXT,
            filesize INTEGER,
            modified TEXT,
            created TEXT
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY,
            photo_id INTEGER,
            operation TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT,
            updated_at TEXT,
            error TEXT,
            progress REAL NOT NULL DEFAULT 0,
            detail TEXT,
            workflow TEXT,
            outputs TEXT,
            FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS face_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            encoding BLOB NOT NULL,
            image_path TEXT,
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS face_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            face_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            location_top INTEGER,
            location_right INTEGER,
            location_bottom INTEGER,
            location_left INTEGER,
            confidence REAL,
            created_at TEXT,
            FOREIGN KEY (face_id) REFERENCES face_data(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS photo_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            photo_path TEXT NOT NULL,
            person_name TEXT NOT NULL,
            confidence REAL,
            location_top INTEGER,
            location_right INTEGER,
            location_bottom INTEGER,
            location_left INTEGER,
            created_at TEXT,
            UNIQUE(photo_path, person_name)
        );
        """
    )
    _add_missing_photo_columns(connection)
    _add_missing_job_columns(connection)
    _backfill_compatibility_columns(connection)
    _create_compatibility_triggers(connection)
    connection.executescript(
        """
        CREATE INDEX IF NOT EXISTS idx_photos_hash ON photos(hash);
        CREATE INDEX IF NOT EXISTS idx_photos_modified ON photos(modified_date);
        CREATE INDEX IF NOT EXISTS idx_photos_filename ON photos(filename);
        CREATE INDEX IF NOT EXISTS idx_photo_tags_person ON photo_tags(person_name);
        CREATE INDEX IF NOT EXISTS idx_photo_tags_photo ON photo_tags(photo_path);
        CREATE INDEX IF NOT EXISTS idx_face_data_name ON face_data(name);
        CREATE INDEX IF NOT EXISTS idx_face_assignments_image
            ON face_assignments(image_path);
        """
    )
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


def connect(
    db_path: str | Path | None = None,
    *,
    initialize: bool = True,
) -> sqlite3.Connection:
    """Open a configured connection and optionally apply schema migrations."""
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=5)
    connection.row_factory = sqlite3.Row
    if initialize:
        with connection:
            migrate(connection)
    return connection


@contextmanager
def session(
    db_path: str | Path | None = None,
    *,
    initialize: bool = True,
) -> Iterator[sqlite3.Connection]:
    """Yield a connection with commit/rollback and guaranteed close semantics."""
    connection = connect(db_path, initialize=initialize)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def create_database(db_path: str | Path | None = None) -> Path:
    """Create or non-destructively migrate the Genesis database."""
    path = resolve_db_path(db_path)
    with session(path):
        pass
    return path


if __name__ == "__main__":
    print("Database upgraded:")
    print(create_database())
