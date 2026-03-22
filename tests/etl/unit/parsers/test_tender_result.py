"""Tests for TenderResultParser."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from etl.parsers.tender_result import TenderResultParser
from shared.codice.xml_helpers import find_first, get_entries, parse_xml

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _folder_elem(fixture: str) -> object:
    root = parse_xml(_load(fixture))
    entries = get_entries(root)
    return find_first(entries[0], "ContractFolderStatus")


@pytest.fixture
def parser() -> TenderResultParser:
    return TenderResultParser()


class TestFullEntryResults:
    def test_returns_two_results(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("full_entry.xml")
        bundles = parser.parse(folder)
        assert len(bundles) == 2

    def test_first_result_code(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("full_entry.xml")
        bundles = parser.parse(folder)
        assert bundles[0].result.result_code == "8"

    def test_first_result_description(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("full_entry.xml")
        bundles = parser.parse(folder)
        assert bundles[0].result.description == "Adjudicación definitiva"

    def test_first_result_award_date(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("full_entry.xml")
        bundles = parser.parse(folder)
        assert bundles[0].result.award_date == date(2024, 8, 1)

    def test_first_result_quantities(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("full_entry.xml")
        bundles = parser.parse(folder)
        r = bundles[0].result
        assert r.received_tender_quantity == 5
        assert r.lower_tender_amount == Decimal("80000.00")
        assert r.higher_tender_amount == Decimal("140000.00")

    def test_first_result_sme_fields(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("full_entry.xml")
        bundles = parser.parse(folder)
        r = bundles[0].result
        assert r.sme_awarded_indicator is True
        assert r.abnormally_low_tenders_indicator is False
        assert r.smes_received_tender_quantity == 3

    def test_first_result_eu_fields(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("full_entry.xml")
        bundles = parser.parse(folder)
        r = bundles[0].result
        assert r.eu_nationals_received_quantity == 1
        assert r.non_eu_nationals_received_qty == 1

    def test_first_result_start_date(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("full_entry.xml")
        bundles = parser.parse(folder)
        assert bundles[0].result.start_date == date(2024, 9, 1)

    def test_first_result_awarded_lot(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("full_entry.xml")
        bundles = parser.parse(folder)
        assert bundles[0].result.awarded_lot_number == "1"

    def test_first_result_awarded_amounts(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("full_entry.xml")
        bundles = parser.parse(folder)
        r = bundles[0].result
        assert r.awarded_tax_exclusive_amount == Decimal("72000.00")
        assert r.awarded_payable_amount == Decimal("87120.00")
        assert r.awarded_currency_id == "EUR"

    def test_first_result_subcontract(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("full_entry.xml")
        bundles = parser.parse(folder)
        r = bundles[0].result
        assert r.subcontract_rate == Decimal("15.00")
        assert r.subcontract_description == "Subcontratación parcial"


class TestWinningParties:
    def test_first_result_has_two_parties(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("full_entry.xml")
        bundles = parser.parse(folder)
        assert len(bundles[0].winning_parties) == 2

    def test_first_party_identifier(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("full_entry.xml")
        bundles = parser.parse(folder)
        wp = bundles[0].winning_parties[0]
        assert wp.identifier == "B12345678"
        assert wp.identifier_scheme == "NIF"
        assert wp.name == "TechCorp S.L."

    def test_first_party_address(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("full_entry.xml")
        bundles = parser.parse(folder)
        wp = bundles[0].winning_parties[0]
        assert wp.city_name == "Barcelona"
        assert wp.postal_zone == "08001"
        assert wp.nuts_code == "ES511"
        assert wp.country_code == "ES"

    def test_second_party_has_no_address(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("full_entry.xml")
        bundles = parser.parse(folder)
        wp = bundles[0].winning_parties[1]
        assert wp.name == "InfoSystems S.A."
        assert wp.city_name is None

    def test_second_result_has_no_parties(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("full_entry.xml")
        bundles = parser.parse(folder)
        assert bundles[1].winning_parties == []


class TestContracts:
    def test_first_result_has_contract(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("full_entry.xml")
        bundles = parser.parse(folder)
        assert bundles[0].contract is not None
        assert bundles[0].contract.contract_number == "CTR-2024-001"
        assert bundles[0].contract.issue_date == date(2024, 9, 1)

    def test_second_result_has_no_contract(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("full_entry.xml")
        bundles = parser.parse(folder)
        assert bundles[1].contract is None


class TestMinimalEntry:
    def test_no_results(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("minimal_entry.xml")
        bundles = parser.parse(folder)
        assert bundles == []


class TestMultiLotEntry:
    def test_no_results(self, parser: TenderResultParser) -> None:
        folder = _folder_elem("multi_lot_with_terms.xml")
        bundles = parser.parse(folder)
        assert bundles == []
