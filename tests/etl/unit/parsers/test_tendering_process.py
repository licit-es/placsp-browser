"""Tests for TenderingProcessParser."""

from datetime import date, time
from pathlib import Path

import pytest

from shared.codice.xml_helpers import find_first, get_entries, parse_xml
from etl.parsers.tendering_process import TenderingProcessParser

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _folder_elem(fixture: str) -> object:
    root = parse_xml(_load(fixture))
    entries = get_entries(root)
    return find_first(entries[0], "ContractFolderStatus")


@pytest.fixture
def parser() -> TenderingProcessParser:
    return TenderingProcessParser()


class TestTenderingProcessFullEntry:
    def test_parses_procedure_code(self, parser: TenderingProcessParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.procedure_code == "1"

    def test_parses_urgency_code(self, parser: TenderingProcessParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.urgency_code == "1"

    def test_parses_submission_method(self, parser: TenderingProcessParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.submission_method_code == "1"

    def test_parses_submission_deadline(self, parser: TenderingProcessParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.submission_deadline_date == date(2024, 7, 1)
        assert result.submission_deadline_time == time(14, 0, 0)
        assert result.submission_deadline_description == "Plazo de presentación"

    def test_parses_document_availability(self, parser: TenderingProcessParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.document_availability_end_date == date(2024, 6, 30)
        assert result.document_availability_end_time == time(23, 59, 59)

    def test_parses_contracting_system(self, parser: TenderingProcessParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.contracting_system_code == "0"

    def test_parses_part_presentation(self, parser: TenderingProcessParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.part_presentation_code == "1"

    def test_parses_auction_indicator(self, parser: TenderingProcessParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.auction_constraint_indicator is False

    def test_parses_lot_quantities(self, parser: TenderingProcessParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.max_lot_presentation_quantity == 2
        assert result.max_tenderer_awarded_lots_qty == 1

    def test_parses_lots_combination_rights(
        self, parser: TenderingProcessParser
    ) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.lots_combination_rights == "Reservado el derecho"

    def test_parses_over_threshold(self, parser: TenderingProcessParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.over_threshold_indicator is True


class TestTenderingProcessMinimal:
    def test_minimal_has_procedure_code(self, parser: TenderingProcessParser) -> None:
        folder = _folder_elem("minimal_entry.xml")
        result = parser.parse(folder)
        assert result.procedure_code == "1"

    def test_minimal_has_no_deadlines(self, parser: TenderingProcessParser) -> None:
        folder = _folder_elem("minimal_entry.xml")
        result = parser.parse(folder)
        assert result.submission_deadline_date is None
        assert result.submission_deadline_time is None
