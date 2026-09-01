import os
import hashlib
from pathlib import Path
from datetime import datetime
from PIL import Image

from genesis.database import DB, session

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".tiff"
}

def file_hash(path, chunk=1024*1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            data = f.read(chunk)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def get_image_metadata(path):
    metadata = {
        "width": None,
        "height": None,
        "filesize": None,
        "modified": None
    }

    try:
        stat = path.stat()

        metadata["filesize"] = stat.st_size
        metadata["modified"] = datetime.fromtimestamp(
            stat.st_mtime
        ).isoformat()

        with Image.open(path) as img:
            metadata["width"] = img.width
            metadata["height"] = img.height

    except Exception as e:
        print("Metadata error:", path, e)

    return metadata


def init_db(db_path: str | Path | None = None):
    """Initialize the canonical schema and return its path."""
    with session(db_path):
        pass
    return Path(db_path).expanduser().resolve() if db_path else DB


def scan_folder(folder, db_path: str | Path | None = None):
    """Scan a folder into the canonical photo library schema."""

    count = 0
    skipped = 0

    folder = Path(folder)

    print("Scanning:")
    print(folder)

    with session(db_path) as con:
        cur = con.cursor()

        for root, dirs, files in os.walk(folder):

            for name in files:

                path = Path(root) / name

                if path.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue

                try:

                    h = file_hash(path)
                    meta = get_image_metadata(path)

                    cur.execute(
                        """
                        INSERT INTO photos
                        (
                            path, filename, hash, created_at, width, height,
                            file_size, modified_date
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(path) DO UPDATE SET
                            filename = excluded.filename,
                            hash = excluded.hash,
                            width = excluded.width,
                            height = excluded.height,
                            file_size = excluded.file_size,
                            modified_date = excluded.modified_date
                        """,
                        (
                            str(path.resolve()),
                            name,
                            h,
                            datetime.now().isoformat(),
                            meta["width"],
                            meta["height"],
                            meta["filesize"],
                            meta["modified"],
                        ),
                    )

                    if cur.rowcount:
                        count += 1
                    else:
                        skipped += 1

                except Exception as e:
                    print("ERROR:", path, e)
                    skipped += 1

    print("====================")
    print("SCAN COMPLETE")
    print("Added:", count)
    print("Skipped:", skipped)
    print("====================")

    return {"processed": count, "skipped": skipped}


if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("python3 genesis/scanner.py /path/to/photos")
        exit()

    scan_folder(sys.argv[1])
