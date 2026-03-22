"""Tests for ModificationParser."""

from decimal import Decimal
from pathlib import Path

import pytest

from etl.parsers.modification import ModificationParser
from shared.codice.xml_helpers import find_first, get_entries, parse_xml

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _folder_elem(fixture: str) -> object:
    root = parse_xml(_load(fixture))
    entries = get_entries(root)
    return find_first(entries[0], "ContractFolderStatus")


@pytest.fixture
def parser() -> ModificationParser:
    return ModificationParser()


class TestFullEntryModifications:
    def test_returns_one_modification(self, parser: ModificationParser) -> None:
        folder = _folder_elem("full_entry.xml")
        mods = parser.parse(folder)
        assert len(mods) == 1

    def test_modification_number(self, parser: ModificationParser) -> None:
        folder = _folder_elem("full_entry.xml")
        mods = parser.parse(folder)
        assert mods[0].modification_number == "MOD-001"

    def test_contract_id(self, parser: ModificationParser) -> None:
        folder = _folder_elem("full_entry.xml")
        mods = parser.parse(folder)
        assert mods[0].contract_id == "CTR-2024-001"

    def test_note(self, parser: ModificationParser) -> None:
        folder = _folder_elem("full_entry.xml")
        mods = parser.parse(folder)
        assert "Ampliación de plazo" in mods[0].note

    def test_modification_duration(self, parser: ModificationParser) -> None:
        folder = _folder_elem("full_entry.xml")
        mods = parser.parse(folder)
        assert mods[0].modification_duration_measure == 3
        assert mods[0].modification_duration_unit_code == "MON"

    def test_final_duration(self, parser: ModificationParser) -> None:
        folder = _folder_elem("full_entry.xml")
        mods = parser.parse(folder)
        assert mods[0].final_duration_measure == 15
        assert mods[0].final_duration_unit_code == "MON"

    def test_modification_amount(self, parser: ModificationParser) -> None:
        folder = _folder_elem("full_entry.xml")
        mods = parser.parse(folder)
        assert mods[0].modification_tax_exclusive_amount == Decimal("10000.00")

    def test_final_amount(self, parser: ModificationParser) -> None:
        folder = _folder_elem("full_entry.xml")
        mods = parser.parse(folder)
        assert mods[0].final_tax_exclusive_amount == Decimal("160000.00")

    def test_currency(self, parser: ModificationParser) -> None:
        folder = _folder_elem("full_entry.xml")
        mods = parser.parse(folder)
        assert mods[0].currency_id == "EUR"


class TestMinimalEntry:
    def test_no_modifications(self, parser: ModificationParser) -> None:
        folder = _folder_elem("minimal_entry.xml")
        mods = parser.parse(folder)
        assert mods == []
