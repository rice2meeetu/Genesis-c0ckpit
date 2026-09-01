from pathlib import Path
from datetime import datetime

from PIL import Image


from genesis.database import DB, connect


def update_metadata(db_path: str | Path | None = None):
    connection = connect(db_path)
    cur = connection.cursor()

    cur.execute("""
        SELECT id, path
        FROM photos
    """)

    photos = cur.fetchall()

    total = len(photos)
    updated = 0
    failed = 0

    print("Photos found:", total)

    for photo_id, path_string in photos:

        path = Path(path_string)

        try:
            stat = path.stat()

            width = None
            height = None

            with Image.open(path) as img:
                width = img.width
                height = img.height

            modified = datetime.fromtimestamp(
                stat.st_mtime
            ).isoformat()

            cur.execute("""
                UPDATE photos
                SET
                    width=?,
                    height=?,
                    file_size=?,
                    modified_date=?
                WHERE id=?
            """, (
                width,
                height,
                stat.st_size,
                modified,
                photo_id
            ))

            updated += 1

            if updated % 100 == 0:
                print(
                    "Updated:",
                    updated,
                    "/",
                    total
                )

        except Exception as e:
            failed += 1
            print("Failed:", path, e)


    connection.commit()
    connection.close()

    print()
    print("====================")
    print("METADATA MIGRATION COMPLETE")
    print("Updated:", updated)
    print("Failed:", failed)
    print("====================")

    return {"updated": updated, "failed": failed}


if __name__ == "__main__":
    update_metadata()
