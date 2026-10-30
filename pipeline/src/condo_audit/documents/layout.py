"""Page layout model shared by the native-text and OCR paths.

Both paths produce positioned words with a confidence; everything after this
module (classification, extraction) is agnostic to where the text came from.
"""

from __future__ import annotations

import bisect
import itertools
import re
from dataclasses import dataclass, field
from statistics import median
from typing import Literal

TextSource = Literal["native", "ocr"]

DATE_FRAGMENT = re.compile(r"\d{1,2}[/.]\d{1,2}[/.]\d{2,4}")


@dataclass(frozen=True, slots=True)
class Word:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    confidence: float = 1.0

    @property
    def y_center(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def height(self) -> float:
        return self.y1 - self.y0


@dataclass(frozen=True, slots=True)
class Line:
    words: tuple[Word, ...]

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def confidence(self) -> float:
        return round(sum(w.confidence for w in self.words) / len(self.words), 3) if self.words else 0.0

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return (
            min(w.x0 for w in self.words),
            min(w.y0 for w in self.words),
            max(w.x1 for w in self.words),
            max(w.y1 for w in self.words),
        )


@dataclass(slots=True)
class PageLayout:
    number: int
    source: TextSource
    width: float
    height: float
    lines: list[Line] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)

    @property
    def mean_confidence(self) -> float:
        words = [w for line in self.lines for w in line.words]
        return round(sum(w.confidence for w in words) / len(words), 3) if words else 0.0


def group_lines(words: list[Word]) -> list[Line]:
    """Words → lines.

    Tables (bank statements) are clustered around their date column: each
    transaction row starts with exactly one date, so the vertical midpoints
    between consecutive dates are the row boundaries. This copes with uneven
    row spacing and slightly rotated scans, where a single distance threshold
    glues neighbouring rows together. Pages without a date column fall back
    to clustering by vertical proximity.
    """
    if not words:
        return []
    anchors = _date_anchors(words)
    rows = _rows_by_anchor(words, anchors) if len(anchors) >= 3 else _rows_by_proximity(words)
    return [Line(tuple(sorted(row, key=lambda w: w.x0))) for row in rows if row]


def _date_anchors(words: list[Word]) -> list[Word]:
    candidates = [w for w in words if DATE_FRAGMENT.fullmatch(w.text.strip(".,;:"))]
    if len(candidates) < 3:
        return []
    # The date column is the left-most one; dates further right are
    # references inside a description ("venc. 05/01") and must not split rows.
    left = min(w.x0 for w in candidates)
    tolerance = max(30.0, median(w.height for w in candidates) * 3)
    return sorted((w for w in candidates if w.x0 <= left + tolerance), key=lambda w: w.y_center)


def _rows_by_anchor(words: list[Word], anchors: list[Word]) -> list[list[Word]]:
    heights = [w.height for w in anchors]
    half = median(heights) * 0.9
    first_top = anchors[0].y_center - half
    last_bottom = anchors[-1].y_center + half
    above = [w for w in words if w.y_center < first_top]
    below = [w for w in words if w.y_center > last_bottom]
    inside = [w for w in words if first_top <= w.y_center <= last_bottom]

    boundaries = [(a.y_center + b.y_center) / 2 for a, b in itertools.pairwise(anchors)]
    rows: list[list[Word]] = [[] for _ in anchors]
    for w in inside:
        rows[bisect.bisect_left(boundaries, w.y_center)].append(w)
    return [*_rows_by_proximity(above), *rows, *_rows_by_proximity(below)]


def _rows_by_proximity(words: list[Word]) -> list[list[Word]]:
    if not words:
        return []
    threshold = max(median(w.height for w in words) * 0.6, 2.0)
    rows: list[list[Word]] = []
    current: list[Word] = []
    last_y: float | None = None
    for w in sorted(words, key=lambda w: w.y_center):
        if last_y is not None and abs(w.y_center - last_y) > threshold:
            rows.append(current)
            current = []
        current.append(w)
        last_y = w.y_center
    rows.append(current)
    return rows
