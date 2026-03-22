"""Tests for ProcurementProjectParser."""

from decimal import Decimal
from pathlib import Path

import pytest

from etl.parsers.procurement_project import ProcurementProjectParser
from shared.codice.xml_helpers import find_children, find_first, get_entries, parse_xml

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _folder_elem(fixture: str) -> object:
    root = parse_xml(_load(fixture))
    entries = get_entries(root)
    return find_first(entries[0], "ContractFolderStatus")


@pytest.fixture
def parser() -> ProcurementProjectParser:
    return ProcurementProjectParser()


class TestFolderLevelProject:
    def test_parses_name(self, parser: ProcurementProjectParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse_folder(folder)
        assert result.name == "Material informático para oficinas"

    def test_parses_type_code(self, parser: ProcurementProjectParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse_folder(folder)
        assert result.type_code == "1"

    def test_parses_sub_type_code(self, parser: ProcurementProjectParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse_folder(folder)
        assert result.sub_type_code == "1.1"

    def test_parses_estimated_overall_amount(
        self, parser: ProcurementProjectParser
    ) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse_folder(folder)
        assert result.estimated_overall_contract_amount == Decimal("150000.00")

    def test_parses_total_amount(self, parser: ProcurementProjectParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse_folder(folder)
        assert result.total_amount == Decimal("181500.00")

    def test_parses_tax_exclusive_amount(
        self, parser: ProcurementProjectParser
    ) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse_folder(folder)
        assert result.tax_exclusive_amount == Decimal("150000.00")

    def test_parses_currency(self, parser: ProcurementProjectParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse_folder(folder)
        assert result.currency_id == "EUR"

    def test_parses_location(self, parser: ProcurementProjectParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse_folder(folder)
        assert result.nuts_code == "ES300"
        assert result.country_subentity == "Madrid"

    def test_parses_duration(self, parser: ProcurementProjectParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse_folder(folder)
        assert result.duration_measure == 12
        assert result.duration_unit_code == "MON"

    def test_parses_planned_dates(self, parser: ProcurementProjectParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse_folder(folder)
        assert result.planned_start_date is not None
        assert str(result.planned_start_date) == "2024-07-01"
        assert str(result.planned_end_date) == "2025-06-30"

    def test_parses_mix_contract_indicator(
        self, parser: ProcurementProjectParser
    ) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse_folder(folder)
        assert result.mix_contract_indicator is False

    def test_parses_cpv_codes(self, parser: ProcurementProjectParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse_folder(folder)
        assert result.cpv_codes is not None
        assert "30200000" in result.cpv_codes
        assert "30230000" in result.cpv_codes


class TestFolderLevelMinimal:
    def test_minimal_has_name_and_type(self, parser: ProcurementProjectParser) -> None:
        folder = _folder_elem("minimal_entry.xml")
        result = parser.parse_folder(folder)
        assert result.name == "Servicio básico"
        assert result.type_code == "2"

    def test_minimal_has_no_budget(self, parser: ProcurementProjectParser) -> None:
        folder = _folder_elem("minimal_entry.xml")
        result = parser.parse_folder(folder)
        assert result.estimated_overall_contract_amount is None
        assert result.total_amount is None


class TestLotLevelProject:
    def test_lot_has_no_estimated_overall_amount(
        self, parser: ProcurementProjectParser
    ) -> None:
        root = parse_xml(_load("full_entry.xml"))
        entry = get_entries(root)[0]
        folder = find_first(entry, "ContractFolderStatus")
        lots = find_children(folder, "ProcurementProjectLot")
        result = parser.parse_lot(lots[0])
        assert not hasattr(result, "estimated_overall_contract_amount")

    def test_lot_parses_amounts(self, parser: ProcurementProjectParser) -> None:
        root = parse_xml(_load("full_entry.xml"))
        entry = get_entries(root)[0]
        folder = find_first(entry, "ContractFolderStatus")
        lots = find_children(folder, "ProcurementProjectLot")
        result = parser.parse_lot(lots[0])
        assert result.total_amount == Decimal("90000.00")
        assert result.tax_exclusive_amount == Decimal("74380.17")

    def test_lot_parses_cpv(self, parser: ProcurementProjectParser) -> None:
        root = parse_xml(_load("full_entry.xml"))
        entry = get_entries(root)[0]
        folder = find_first(entry, "ContractFolderStatus")
        lots = find_children(folder, "ProcurementProjectLot")
        result = parser.parse_lot(lots[0])
        assert result.cpv_codes == ["30213100"]
