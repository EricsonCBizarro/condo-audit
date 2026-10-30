from __future__ import annotations

from condo_audit.documents.layout import Word, group_lines


def _w(text: str, x: float, y: float) -> Word:
    return Word(text, x, y - 5, x + 8 * len(text), y + 5, 0.9)


def test_rows_are_split_at_the_midpoint_between_dates_even_with_uneven_spacing() -> None:
    words = [
        _w("01/03/2025", 40, 100),
        _w("SALDO", 120, 101),
        _w("100,00", 400, 99),
        _w("05/03/2025", 40, 118),
        _w("PAGTO", 120, 119),
        _w("-50,00", 340, 118),
        _w("50,00", 400, 117),
        # this row was rendered with extra spacing above and a slight skew
        _w("09/03/2025", 40, 150),
        _w("TED", 120, 152),
        _w("10,00", 340, 151),
        _w("60,00", 400, 149),
    ]
    lines = group_lines(words)
    assert [ln.text for ln in lines] == [
        "01/03/2025 SALDO 100,00",
        "05/03/2025 PAGTO -50,00 50,00",
        "09/03/2025 TED 10,00 60,00",
    ]


def test_a_second_date_inside_the_description_does_not_split_the_row() -> None:
    words = [
        _w("01/03/2025", 40, 100),
        _w("A", 120, 100),
        _w("02/03/2025", 40, 120),
        _w("BOLETO", 120, 120),
        _w("venc.", 180, 121),
        _w("05/04/2025", 230, 123),
        _w("03/03/2025", 40, 140),
        _w("C", 120, 140),
    ]
    texts = [ln.text for ln in group_lines(words)]
    assert texts[1] == "02/03/2025 BOLETO venc. 05/04/2025"
    assert len(texts) == 3


def test_pages_without_a_date_column_are_grouped_by_proximity() -> None:
    words = [_w("Valor:", 40, 100), _w("R$", 90, 101), _w("10,00", 110, 100), _w("Pagador:", 40, 130)]
    assert [ln.text for ln in group_lines(words)] == ["Valor: R$ 10,00", "Pagador:"]
