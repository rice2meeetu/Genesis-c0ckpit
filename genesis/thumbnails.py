from pathlib import Path
import hashlib
from PIL import Image

from genesis.database import DB, PROJECT_ROOT, session


CACHE = PROJECT_ROOT / "cache" / "thumbnails"

SIZE = (320, 320)


def create_cache():

    CACHE.mkdir(parents=True, exist_ok=True)



def generate_thumbnail(image_path, cache_dir: str | Path | None = None):

    image_path = Path(image_path)

    try:
        stat = image_path.stat()
        # Include the source revision and thumbnail geometry, not just its path.
        revision = f"{image_path.resolve()}:{stat.st_mtime_ns}:{stat.st_ctime_ns}:{stat.st_size}:{SIZE}"
        key = hashlib.sha256(revision.encode("utf-8")).hexdigest()[:20]
        name = f"{image_path.stem}-{key}.jpg"
        output = Path(cache_dir) / name if cache_dir else CACHE / name
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            return output

        with Image.open(image_path) as img:

            img.thumbnail(SIZE)

            img.convert("RGB").save(
                output,
                "JPEG",
                quality=85
            )

        return output


    except Exception as e:

        print("Thumbnail error:")
        print(image_path)
        print(e)

        return None



def process_library(db_path: str | Path | None = None):

    create_cache()

    with session(db_path) as con:
        photos = con.execute("SELECT id, path FROM photos").fetchall()

    total = len(photos)

    done = 0


    print("Images found:", total)


    with session(db_path) as con:
        for row in photos:

            result = generate_thumbnail(row["path"])

            if result:
                done += 1
                con.execute(
                    "UPDATE photos SET thumbnail_path = ? WHERE id = ?",
                    (str(result), row["id"]),
                )

            if done and done % 100 == 0:
                print(
                    "Processed:",
                    done,
                    "/",
                    total
                )


    print()
    print("====================")
    print("THUMBNAIL COMPLETE")
    print("Created:", done)
    print("====================")

    return {"created": done, "total": total}



if __name__ == "__main__":

    process_library()
