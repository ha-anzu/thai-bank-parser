from pathlib import Path

from thai_bank_parser.models import OcrBox
from thai_bank_parser.templates.krungsri import KrungsriTemplate, parse_left_anchor


def box(text, x0, y0, x1=None, y1=None, confidence=0.99):
    return OcrBox(
        page=1,
        text=text,
        confidence=confidence,
        x0=float(x0),
        y0=float(y0),
        x1=float(x1 if x1 is not None else x0 + 50),
        y1=float(y1 if y1 is not None else y0 + 20),
    )


def test_parse_left_anchor_reads_exact_datetime_and_transaction():
    parsed = parse_left_anchor("01/01/2026 09:08:07 Transfer Deposit")
    assert parsed == ("01/01/2026", "09:08:07", "Transfer Deposit")


def test_parse_left_anchor_rejects_missing_time():
    assert parse_left_anchor("01/01/2026 Transfer Deposit") is None


def test_positional_amount_split_and_schema():
    template = KrungsriTemplate()
    rows = template.parse(
        [
            box("01/01/2026 09:00:00 Transfer Deposit", 20, 100, 420, 124),
            box("1,000.00", 710, 102, 810, 124),
            box("5,000.00", 850, 102, 950, 124),
            box("MOBILE", 990, 102, 1070, 124),
            box("Synthetic sender", 1100, 102, 1300, 124),
            box("01/01/2026 10:00:00 Transfer Withd...", 20, 150, 420, 174),
            box("250.00", 570, 152, 660, 174),
            box("4,750.00", 850, 152, 950, 174),
            box("MOBILE", 990, 152, 1070, 174),
            box("Synthetic receiver", 1100, 152, 1300, 174),
        ],
        Path("sample.pdf"),
    )

    assert len(rows) == 2
    assert rows[0].direction == "in"
    assert rows[0].deposit == "1,000.00"
    assert rows[0].withdrawal == ""
    assert rows[0].datetime_iso == "2026-01-01 09:00:00"
    assert rows[1].direction == "out"
    assert rows[1].withdrawal == "250.00"
    assert rows[1].deposit == ""
    assert rows[1].balance == "4,750.00"
