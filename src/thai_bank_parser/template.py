from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from .models import OcrBox, StatementRow


@dataclass(frozen=True)
class TemplateInfo:
    key: str
    bank: str
    name: str
    status: str
    description: str


class StatementTemplate(ABC):
    info: TemplateInfo

    @abstractmethod
    def parse(self, boxes: list[OcrBox], source_file: Path) -> list[StatementRow]:
        """Convert OCR boxes into normalized statement rows."""


class PlaceholderTemplate(StatementTemplate):
    def __init__(self, key: str, bank: str) -> None:
        self.info = TemplateInfo(
            key=key,
            bank=bank,
            name=f"{bank} statement",
            status="planned",
            description="Template slot reserved for a future bank layout.",
        )

    def parse(self, boxes: list[OcrBox], source_file: Path) -> list[StatementRow]:
        raise NotImplementedError(f"Template '{self.info.key}' is planned but not implemented yet.")
