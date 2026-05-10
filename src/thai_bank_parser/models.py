from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class OcrBox:
    page: int
    text: str
    confidence: float
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass
class StatementRow:
    bank: str
    template: str
    source_file: str
    page: int
    date: str
    time: str
    datetime: str
    datetime_iso: str
    transaction: str
    direction: str
    amount: str
    withdrawal: str
    deposit: str
    balance: str
    channel: str
    description: str
    ocr_confidence: str
    amount_source: str

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


CSV_COLUMNS = list(StatementRow.__dataclass_fields__)


@dataclass(frozen=True)
class ValidationResult:
    rows: int
    missing_times: int
    missing_iso_datetimes: int
    missing_amounts: int
    bad_balance_deltas: int
    deposits: int
    withdrawals: int

    @property
    def ok(self) -> bool:
        return (
            self.rows > 0
            and self.missing_times == 0
            and self.missing_iso_datetimes == 0
            and self.missing_amounts == 0
            and self.bad_balance_deltas == 0
        )
