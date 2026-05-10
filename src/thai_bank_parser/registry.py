from __future__ import annotations

from .template import PlaceholderTemplate, StatementTemplate
from .templates.krungsri import KrungsriTemplate


_TEMPLATES: dict[str, StatementTemplate] = {
    "krungsri": KrungsriTemplate(),
    "kbank": PlaceholderTemplate("kbank", "KBank"),
    "bangkok-bank": PlaceholderTemplate("bangkok-bank", "Bangkok Bank"),
    "scb": PlaceholderTemplate("scb", "SCB"),
}


def get_template(key: str) -> StatementTemplate:
    normalized = key.strip().lower()
    try:
        return _TEMPLATES[normalized]
    except KeyError as exc:
        known = ", ".join(sorted(_TEMPLATES))
        raise KeyError(f"Unknown template '{key}'. Known templates: {known}") from exc


def list_templates() -> list[StatementTemplate]:
    return [_TEMPLATES[key] for key in sorted(_TEMPLATES)]
