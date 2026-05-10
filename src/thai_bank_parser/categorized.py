from __future__ import annotations

import csv
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


CATEGORIZED_COLUMNS = [
    "tt number",
    "date",
    "time",
    "datetime",
    "datetime_iso",
    "transaction",
    "direction",
    "amount",
    "withdrawal",
    "deposit",
    "balance",
    "channel",
    "description",
    "Type",
    "Main_Category",
    "Sub_Category",
    "Sub2_Category",
    "Sub3_Category",
    "From",
    "To",
    "Column1",
    "Memo / Note",
    "Additional_Info",
    "Reference_No",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_rows(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CATEGORIZED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def money_plain(value: str) -> str:
    if not value:
        return ""
    cleaned = value.replace(",", "").strip()
    try:
        decimal = Decimal(cleaned)
    except InvalidOperation:
        return cleaned
    if decimal == decimal.to_integral_value():
        return str(int(decimal))
    return f"{decimal:.2f}"


def parse_dt(row: dict[str, str]) -> datetime | None:
    iso = row.get("datetime_iso", "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        if iso:
            try:
                return datetime.strptime(iso, fmt)
            except ValueError:
                pass
    raw = f"{row.get('date', '').strip()} {row.get('time', '').strip()}".strip()
    if raw:
        try:
            return datetime.strptime(raw, "%d/%m/%Y %H:%M:%S")
        except ValueError:
            return None
    return None


def classify(row: dict[str, str]) -> tuple[str, str, str, str]:
    text = " ".join(
        [
            row.get("transaction", ""),
            row.get("channel", ""),
            row.get("description", ""),
        ]
    ).lower()
    direction = row.get("direction", "")

    if direction == "in":
        tx_type = "Fund Transfer"
        main = "Income"
    elif "qr" in text or "spending" in text or "card" in text or row.get("channel", "").upper() == "POS":
        tx_type = "Purchase"
        main = "Expense"
    elif "bill" in text:
        tx_type = "Bill Payment"
        main = "Expense"
    elif "withdraw" in text or "atm" in text:
        tx_type = "Withdrawal"
        main = "Cash"
    else:
        tx_type = "Fund Transfer" if "transfer" in text or "promptpay" in text else "Uncategorized"
        main = "Transfer" if direction == "out" else "Uncategorized"

    sub = "Uncategorized"
    if "e-wallet" in text:
        sub = "E-wallet"
    elif "promptpay" in text:
        sub = "PromptPay"
    elif "atm" in text:
        sub = "ATM"
    elif "card" in text or row.get("channel", "").upper() == "POS":
        sub = "Card"
    elif "interest" in text:
        sub = "Interest"
    elif "bill" in text:
        sub = "Bills"

    return tx_type, main, sub, ""


def extract_counterparty(description: str) -> str:
    text = re.sub(r"\s+", " ", description or "").strip()
    if not text:
        return ""
    patterns = [
        r"^(?:To|From)\s+(.+?)(?:\s+Acc\s+No\.?|\s+PromptPay\s+ID|\s*:\s*X|$)",
        r"^(Transfer to E-wallet)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip(" .:")
    return text


def reference_number(row_number: int, dt: datetime | None) -> str:
    if dt is None:
        return f"REF{row_number:08d}"
    return f"REF{dt:%y%m%d}{row_number:06d}"


def to_categorized_rows(
    rows: list[dict[str, str]],
    account_label: str = "Account",
    additional_info: str = "",
) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=1):
        dt = parse_dt(row)
        tx_type, main, sub, sub2 = classify(row)
        counterparty = extract_counterparty(row.get("description", ""))
        direction = row.get("direction", "")

        if direction == "in":
            from_value = counterparty
            to_value = account_label
        elif direction == "out":
            from_value = account_label
            to_value = counterparty
        else:
            from_value = ""
            to_value = counterparty

        display_dt = dt.strftime("%d/%m/%Y %H:%M") if dt else row.get("datetime", "")
        iso_dt = dt.strftime("%Y-%m-%dT%H:%M:00") if dt else row.get("datetime_iso", "")

        output.append(
            {
                "tt number": str(index),
                "date": row.get("date", ""),
                "time": row.get("time", ""),
                "datetime": display_dt,
                "datetime_iso": iso_dt,
                "transaction": row.get("transaction", ""),
                "direction": direction,
                "amount": money_plain(row.get("amount", "")),
                "withdrawal": money_plain(row.get("withdrawal", "")),
                "deposit": money_plain(row.get("deposit", "")),
                "balance": row.get("balance", ""),
                "channel": row.get("channel", ""),
                "description": row.get("description", ""),
                "Type": tx_type,
                "Main_Category": main,
                "Sub_Category": sub,
                "Sub2_Category": sub2,
                "Sub3_Category": "",
                "From": from_value,
                "To": to_value,
                "Column1": "",
                "Memo / Note": "",
                "Additional_Info": additional_info,
                "Reference_No": reference_number(index, dt),
            }
        )
    return output


def convert_to_categorized(
    input_csv: Path,
    output_csv: Path,
    account_label: str = "Account",
    additional_info: str = "",
) -> list[dict[str, str]]:
    rows = to_categorized_rows(read_rows(input_csv), account_label, additional_info)
    write_rows(rows, output_csv)
    return rows
