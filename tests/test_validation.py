from thai_bank_parser.models import StatementRow
from thai_bank_parser.validation import validate_rows


def row(direction, amount, balance):
    return StatementRow(
        bank="Synthetic",
        template="synthetic",
        source_file="sample.pdf",
        page=1,
        date="01/01/2026",
        time="09:00:00",
        datetime="01/01/2026 09:00:00",
        datetime_iso="2026-01-01 09:00:00",
        transaction="Synthetic",
        direction=direction,
        amount=amount,
        withdrawal=amount if direction == "out" else "",
        deposit=amount if direction == "in" else "",
        balance=balance,
        channel="MOBILE",
        description="Synthetic",
        ocr_confidence="0.990",
        amount_source="ocr",
    )


def test_validation_passes_clean_rows():
    result = validate_rows([row("in", "100.00", "1,100.00"), row("out", "50.00", "1,050.00")])
    assert result.ok
    assert result.deposits == 1
    assert result.withdrawals == 1


def test_validation_catches_bad_balance_delta():
    result = validate_rows([row("in", "100.00", "1,100.00"), row("out", "50.00", "1,000.00")])
    assert not result.ok
    assert result.bad_balance_deltas == 1
