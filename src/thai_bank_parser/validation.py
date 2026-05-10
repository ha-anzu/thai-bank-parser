from __future__ import annotations

from decimal import Decimal, InvalidOperation

from .models import StatementRow, ValidationResult


def decimal_money(text: str | None) -> Decimal | None:
    if not text:
        return None
    try:
        return Decimal(text.replace(",", ""))
    except InvalidOperation:
        return None


def validate_rows(rows: list[StatementRow] | list[dict[str, str]]) -> ValidationResult:
    missing_times = 0
    missing_iso = 0
    missing_amounts = 0
    bad_balance_deltas = 0
    deposits = 0
    withdrawals = 0
    previous_balance: Decimal | None = None

    for row in rows:
        getter = row.get if isinstance(row, dict) else lambda key, default="": getattr(row, key, default)
        direction = str(getter("direction", ""))
        amount = str(getter("amount", ""))
        balance = str(getter("balance", ""))

        if not getter("time", ""):
            missing_times += 1
        if not getter("datetime_iso", ""):
            missing_iso += 1
        if not amount:
            missing_amounts += 1
        if direction == "in":
            deposits += 1
        if direction == "out":
            withdrawals += 1

        amount_value = decimal_money(amount)
        balance_value = decimal_money(balance)
        if previous_balance is not None and amount_value is not None and balance_value is not None:
            expected = previous_balance + amount_value if direction == "in" else previous_balance - amount_value
            if abs(expected - balance_value) > Decimal("0.01"):
                bad_balance_deltas += 1
        if balance_value is not None:
            previous_balance = balance_value

    return ValidationResult(
        rows=len(rows),
        missing_times=missing_times,
        missing_iso_datetimes=missing_iso,
        missing_amounts=missing_amounts,
        bad_balance_deltas=bad_balance_deltas,
        deposits=deposits,
        withdrawals=withdrawals,
    )
