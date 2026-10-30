"""Builders for hand-made test inputs."""

from __future__ import annotations

from condo_audit.documents.layout import Line, PageLayout, Word, group_lines


def page_from_lines(lines: list[str], number: int = 1, confidence: float = 1.0) -> PageLayout:
    """A page whose lines are exactly the given strings (one word per token)."""
    words = []
    for row, text in enumerate(lines):
        x = 40.0
        for token in text.split():
            width = 6.0 * len(token)
            words.append(Word(token, x, 100 + row * 20, x + width, 110 + row * 20, confidence))
            x += width + 5
    return PageLayout(number, "native", 595, 842, group_lines(words))


def line(text: str, confidence: float = 1.0) -> Line:
    return page_from_lines([text], confidence=confidence).lines[0]
