"""PDF → PageLayout per page: native text layer when present, OCR otherwise."""

from __future__ import annotations

import io
from collections.abc import Iterator
from typing import Protocol

import pymupdf
from PIL import Image

from condo_audit.documents.layout import PageLayout, Word, group_lines

MIN_NATIVE_WORDS = 5


class OcrEngine(Protocol):
    def words(self, image: Image.Image, scale: float) -> list[Word]:
        """Words in PDF coordinates (points). `scale` = pixels per point."""
        ...


class TesseractEngine:
    def __init__(self, language: str = "por", psm: int = 6) -> None:
        self._language = language
        self._config = f"--psm {psm}"

    def words(self, image: Image.Image, scale: float) -> list[Word]:
        import pytesseract  # noqa: PLC0415 - optional at import time (tests without the binary)

        data = pytesseract.image_to_data(
            image, lang=self._language, config=self._config, output_type=pytesseract.Output.DICT
        )
        words: list[Word] = []
        for text, conf, left, top, width, height in zip(
            data["text"], data["conf"], data["left"], data["top"], data["width"], data["height"], strict=True
        ):
            confidence = float(conf)
            if not str(text).strip() or confidence < 0:
                continue
            words.append(
                Word(
                    str(text),
                    left / scale,
                    top / scale,
                    (left + width) / scale,
                    (top + height) / scale,
                    round(confidence / 100, 3),
                )
            )
        return words


class DocumentReader:
    def __init__(self, ocr: OcrEngine, dpi: int = 300) -> None:
        self._ocr = ocr
        self._dpi = dpi

    def pages(self, pdf: bytes) -> Iterator[PageLayout]:
        with pymupdf.open(stream=pdf, filetype="pdf") as doc:
            for index, page in enumerate(doc, start=1):
                native = [
                    Word(text, x0, y0, x1, y1)
                    for x0, y0, x1, y1, text, *_ in page.get_text("words")
                    if str(text).strip()
                ]
                if len(native) >= MIN_NATIVE_WORDS:
                    yield PageLayout(index, "native", page.rect.width, page.rect.height, group_lines(native))
                    continue
                scale = self._dpi / 72
                pix = page.get_pixmap(dpi=self._dpi, colorspace=pymupdf.csGRAY)
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                words = self._ocr.words(image, scale)
                yield PageLayout(index, "ocr", page.rect.width, page.rect.height, group_lines(words))
