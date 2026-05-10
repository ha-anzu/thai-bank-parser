import pytest

from thai_bank_parser.registry import get_template, list_templates


def test_registry_lists_implemented_and_planned_templates():
    keys = [template.info.key for template in list_templates()]
    assert keys == ["bangkok-bank", "kbank", "krungsri", "scb"]


def test_get_template_returns_krungsri():
    template = get_template("krungsri")
    assert template.info.bank == "Krungsri"
    assert template.info.status == "implemented"


def test_unknown_template_raises_clear_error():
    with pytest.raises(KeyError, match="Unknown template"):
        get_template("unknown")
