"""Prevent embedded ComfyUI workflow/prompt leaks in published UI artwork."""
from pathlib import Path
from PIL import Image


def test_published_ui_artwork_has_no_embedded_comfy_prompts():
    repo=Path(__file__).resolve().parents[1]
    assets=repo/'genesis'/'assets'
    roots=(assets/'home_buttons',assets/'lunacy_banner',assets/'ui')
    pictures=[p for root in roots if root.exists() for p in root.rglob('*')
              if p.suffix.lower() in {'.png','.jpg','.jpeg','.webp'}]
    assert pictures, 'GENESIS UI artwork is unexpectedly missing'
    for path in pictures:
        with Image.open(path) as image:
            fields={key.lower():value for key,value in image.info.items()}
            assert not any(key in fields for key in ('prompt','workflow','parameters')),(path,sorted(fields))
            # Existing, unrelated reference artwork may have ordinary EXIF.
            # Newly added public UI assets must never contain private EXIF.
            if path.name in {
                'AIPG_Image_00391_.png','AIPG_Image_00403_.png',
                'AIPG_Image_00405_.png','AIPG_Image_00443_.png',
                'Phr00t_Img2Img_Q4_K_M_00042_.png',
            }:
                assert 'exif' not in fields, (path,sorted(fields))
