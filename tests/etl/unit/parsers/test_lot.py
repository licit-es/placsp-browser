"""Tests for LotParser."""

from decimal import Decimal
from pathlib import Path

import pytest

from etl.parsers.lot import LotParser
from etl.parsers.procurement_project import ProcurementProjectParser
from etl.parsers.tendering_terms import TenderingTermsParser
from shared.codice.xml_helpers import find_first, get_entries, parse_xml

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _folder_elem(fixture: str) -> object:
    root = parse_xml(_load(fixture))
    entries = get_entries(root)
    return find_first(entries[0], "ContractFolderStatus")


@pytest.fixture
def parser() -> LotParser:
    return LotParser(
        project=ProcurementProjectParser(),
        terms=TenderingTermsParser(),
    )


class TestFullEntryLots:
    def test_returns_two_lots(self, parser: LotParser) -> None:
        folder = _folder_elem("full_entry.xml")
        lots = parser.parse(folder)
        assert len(lots) == 2

    def test_lot_numbers(self, parser: LotParser) -> None:
        folder = _folder_elem("full_entry.xml")
        lots = parser.parse(folder)
        assert lots[0].lot_number == "1"
        assert lots[1].lot_number == "2"

    def test_lot1_project_name(self, parser: LotParser) -> None:
        folder = _folder_elem("full_entry.xml")
        lots = parser.parse(folder)
        assert lots[0].project.name == "Lote 1: Ordenadores portátiles"

    def test_lot1_project_amounts(self, parser: LotParser) -> None:
        folder = _folder_elem("full_entry.xml")
        lots = parser.parse(folder)
        assert lots[0].project.total_amount == Decimal("90000.00")
        assert lots[0].project.tax_exclusive_amount == Decimal("74380.17")

    def test_lot1_cpv_codes(self, parser: LotParser) -> None:
        folder = _folder_elem("full_entry.xml")
        lots = parser.parse(folder)
        assert lots[0].cpv_codes == ["30213100"]

    def test_lot1_has_criteria(self, parser: LotParser) -> None:
        folder = _folder_elem("full_entry.xml")
        lots = parser.parse(folder)
        assert len(lots[0].criteria) == 1
        assert lots[0].criteria[0].criteria_type_code == "OBJ"
        assert lots[0].criteria[0].weight_numeric == Decimal("70")

    def test_lot1_has_requirements(self, parser: LotParser) -> None:
        folder = _folder_elem("full_entry.xml")
        lots = parser.parse(folder)
        assert len(lots[0].requirements) == 1
        assert lots[0].requirements[0].origin_type == "TECHNICAL"

    def test_lot2_has_no_terms(self, parser: LotParser) -> None:
        folder = _folder_elem("full_entry.xml")
        lots = parser.parse(folder)
        assert lots[1].criteria == []
        assert lots[1].requirements == []

    def test_lot2_has_location_with_address(self, parser: LotParser) -> None:
        folder = _folder_elem("full_entry.xml")
        lots = parser.parse(folder)
        assert len(lots[1].locations) == 1
        loc = lots[1].locations[0]
        assert loc.city_name == "Madrid"
        assert loc.postal_zone == "28001"
        assert loc.country_code == "ES"
        assert loc.street_name == "Calle Test 5"

    def test_lot1_has_no_address_locations(self, parser: LotParser) -> None:
        folder = _folder_elem("full_entry.xml")
        lots = parser.parse(folder)
        assert lots[0].locations == []

    def test_lot_project_has_no_estimated_overall(self, parser: LotParser) -> None:
        folder = _folder_elem("full_entry.xml")
        lots = parser.parse(folder)
        assert not hasattr(lots[0].project, "estimated_overall_contract_amount")


class TestMultiLotFixture:
    def test_returns_three_lots(self, parser: LotParser) -> None:
        folder = _folder_elem("multi_lot_with_terms.xml")
        lots = parser.parse(folder)
        assert len(lots) == 3

    def test_lot_numbers(self, parser: LotParser) -> None:
        folder = _folder_elem("multi_lot_with_terms.xml")
        lots = parser.parse(folder)
        numbers = [lot.lot_number for lot in lots]
        assert numbers == ["1", "2", "3"]

    def test_lot1_has_two_criteria(self, parser: LotParser) -> None:
        folder = _folder_elem("multi_lot_with_terms.xml")
        lots = parser.parse(folder)
        assert len(lots[0].criteria) == 2

    def test_lot1_criteria_types(self, parser: LotParser) -> None:
        folder = _folder_elem("multi_lot_with_terms.xml")
        lots = parser.parse(folder)
        types = [c.criteria_type_code for c in lots[0].criteria]
        assert "OBJ" in types
        assert "SUBJ" in types

    def test_lot2_has_one_criterion(self, parser: LotParser) -> None:
        folder = _folder_elem("multi_lot_with_terms.xml")
        lots = parser.parse(folder)
        assert len(lots[1].criteria) == 1

    def test_lot3_has_no_criteria(self, parser: LotParser) -> None:
        folder = _folder_elem("multi_lot_with_terms.xml")
        lots = parser.parse(folder)
        assert lots[2].criteria == []
        assert lots[2].requirements == []

    def test_lot_amounts(self, parser: LotParser) -> None:
        folder = _folder_elem("multi_lot_with_terms.xml")
        lots = parser.parse(folder)
        assert lots[0].project.total_amount == Decimal("200000.00")
        assert lots[1].project.total_amount == Decimal("180000.00")
        assert lots[2].project.total_amount == Decimal("120000.00")

    def test_lot_cpv_codes(self, parser: LotParser) -> None:
        folder = _folder_elem("multi_lot_with_terms.xml")
        lots = parser.parse(folder)
        assert lots[0].cpv_codes == ["90911200"]
        assert lots[1].cpv_codes == ["90911200"]
        assert lots[2].cpv_codes == ["90911200"]


class TestMinimalEntry:
    def test_no_lots_returns_empty_list(self, parser: LotParser) -> None:
        folder = _folder_elem("minimal_entry.xml")
        lots = parser.parse(folder)
        assert lots == []
