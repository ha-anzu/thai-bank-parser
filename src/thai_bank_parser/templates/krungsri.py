from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..models import OcrBox, StatementRow
from ..template import StatementTemplate, TemplateInfo


DATE_TIME_RE = re.compile(
    r"(?P<date>\d{1,2}/\d{2}/\d{4})\s*"
    r"(?P<time>\d{1,2}[:.]\d{2}[:.]\d{2})?\s*"
    r"(?P<transaction>.*)"
)
MONEY_RE = re.compile(r"^\d[\d,]*\.\d{2}$")


def normalize_date(raw: str) -> str:
    day, month, year = raw.split("/")
    return f"{int(day):02d}/{month}/{year}"


def normalize_time(raw: str) -> str:
    return raw.replace(".", ":")


def iso_datetime(date_text: str, time_text: str) -> str:
    return datetime.strptime(f"{date_text} {time_text}", "%d/%m/%Y %H:%M:%S").strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def clean_transaction(text: str) -> str:
    replacements = {
        "Dep0sit": "Deposit",
        "TransferWithd": "Transfer Withd",
        "TransferPromp": "Transfer Promp",
        "BillPayment": "Bill Payment",
        "Payment-QR": "Payment - QR",
        "Payment-QRP": "Payment - QR P",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.strip(" -")


def clean_money(text: str) -> str:
    normalized = text.replace("O", "0").replace("o", "0").replace(" ", "")
    return normalized if MONEY_RE.match(normalized) else ""


def money_decimal(text: str) -> Decimal | None:
    if not text:
        return None
    try:
        return Decimal(text.replace(",", ""))
    except InvalidOperation:
        return None


def money_text(value: Decimal) -> str:
    return f"{value:,.2f}"


def join_text(items: list[OcrBox]) -> str:
    return " ".join(item.text for item in sorted(items, key=lambda item: (item.y0, item.x0))).strip()


def boxes_in(items: list[OcrBox], x0: float, x1: float, y0: float, y1: float) -> list[OcrBox]:
    return [item for item in items if x0 <= item.x0 < x1 and y0 <= item.y0 <= y1]


def parse_left_anchor(text: str) -> tuple[str, str, str] | None:
    match = DATE_TIME_RE.search(text)
    if not match:
        return None
    date = normalize_date(match.group("date"))
    time = normalize_time(match.group("time") or "")
    transaction = clean_transaction(match.group("transaction") or "")
    if not time:
        return None
    return date, time, transaction


class KrungsriTemplate(StatementTemplate):
    info = TemplateInfo(
        key="krungsri",
        bank="Krungsri",
        name="Krungsri savings account statement",
        status="implemented",
        description="Scanned Krungsri statement table with positional withdrawal/deposit amount band.",
    )

    render_scale = 2.5
    table_crop = (35, 180, 1460, 1885)

    def parse(self, boxes: list[OcrBox], source_file: Path) -> list[StatementRow]:
        rows: list[StatementRow] = []
        by_page: dict[int, list[OcrBox]] = {}
        for box in boxes:
            by_page.setdefault(box.page, []).append(box)

        for page in sorted(by_page):
            page_boxes = by_page[page]
            anchors: list[tuple[OcrBox, str, str, str]] = []
            for item in page_boxes:
                if item.x0 > 430 or item.y0 < 80:
                    continue
                parsed = parse_left_anchor(item.text)
                if parsed:
                    anchors.append((item, *parsed))
            anchors.sort(key=lambda item: item[0].y0)

            for index, (anchor, date, time, transaction) in enumerate(anchors):
                next_y = anchors[index + 1][0].y0 if index + 1 < len(anchors) else 1700
                line_y0 = anchor.y0 - 14
                line_y1 = anchor.y1 + 12
                desc_y1 = min(next_y - 5, anchor.y0 + 78)

                withdrawal = clean_money(join_text(boxes_in(page_boxes, 540, 690, line_y0, line_y1)))
                deposit = clean_money(join_text(boxes_in(page_boxes, 690, 825, line_y0, line_y1)))
                balance = clean_money(join_text(boxes_in(page_boxes, 825, 970, line_y0, line_y1)))
                channel = join_text(boxes_in(page_boxes, 970, 1085, line_y0, line_y1))
                description = join_text(boxes_in(page_boxes, 1085, 1430, line_y0, desc_y1))

                direction = ""
                amount = ""
                if deposit:
                    direction = "in"
                    amount = deposit
                    withdrawal = ""
                elif withdrawal:
                    direction = "out"
                    amount = withdrawal

                confidence_values = [anchor.confidence]
                confidence_values.extend(item.confidence for item in boxes_in(page_boxes, 540, 1085, line_y0, line_y1))
                confidence = min(confidence_values) if confidence_values else anchor.confidence

                rows.append(
                    StatementRow(
                        bank=self.info.bank,
                        template=self.info.key,
                        source_file=source_file.name,
                        page=page,
                        date=date,
                        time=time,
                        datetime=f"{date} {time}",
                        datetime_iso=iso_datetime(date, time),
                        transaction=transaction,
                        direction=direction,
                        amount=amount,
                        withdrawal=withdrawal,
                        deposit=deposit,
                        balance=balance,
                        channel=channel,
                        description=description,
                        ocr_confidence=f"{confidence:.3f}",
                        amount_source="ocr",
                    )
                )

        self._repair_missing_amounts(rows)
        return rows

    def _repair_missing_amounts(self, rows: list[StatementRow]) -> None:
        previous_balance: Decimal | None = None
        previous_had_balance = False
        for row in rows:
            balance = money_decimal(row.balance)
            withdrawal = money_decimal(row.withdrawal)
            deposit = money_decimal(row.deposit)
            if previous_had_balance and previous_balance is not None and balance is not None:
                delta = balance - previous_balance
                expected = abs(delta)
                if expected != 0 and withdrawal is None and deposit is None:
                    row.amount = money_text(expected)
                    row.amount_source = "balance_delta"
                    if delta > 0:
                        row.direction = "in"
                        row.deposit = row.amount
                    else:
                        row.direction = "out"
                        row.withdrawal = row.amount

            if balance is not None:
                previous_balance = balance
                previous_had_balance = True
            else:
                previous_had_balance = False
