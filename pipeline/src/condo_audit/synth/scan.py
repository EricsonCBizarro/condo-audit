"""Make a clean PDF look scanned: raster only (no text layer), slight
rotation, speckles, blur and JPEG compression. This forces the OCR path."""

from __future__ import annotations

import io
import random

import pymupdf
from PIL import Image, ImageDraw, ImageFilter


def scanned(pdf: bytes, rng: random.Random, dpi: int = 200) -> bytes:
    source = pymupdf.open(stream=pdf, filetype="pdf")
    out = pymupdf.open()
    for page in source:
        pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
        img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
        img = img.rotate(rng.uniform(-0.35, 0.35), resample=Image.Resampling.BICUBIC, fillcolor=255)
        draw = ImageDraw.Draw(img)
        for _ in range(int(pix.width * pix.height / 9000)):
            x, y = rng.randrange(pix.width), rng.randrange(pix.height)
            shade = rng.randint(90, 200)
            draw.point((x, y), fill=shade)
        img = img.filter(ImageFilter.GaussianBlur(radius=0.6))
        jpeg = io.BytesIO()
        img.save(jpeg, format="JPEG", quality=72, optimize=False)
        new_page = out.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(new_page.rect, stream=jpeg.getvalue())
    out.set_metadata({"producer": "condo-audit synthetic scanner", "creator": "condo-audit"})
    data: bytes = out.tobytes(garbage=3, deflate=True, no_new_id=True)
    return data
