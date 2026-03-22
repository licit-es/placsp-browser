"""Tests for PageParser."""

from pathlib import Path

import pytest

from etl.parsers.page import PageParser

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


@pytest.fixture
def parser() -> PageParser:
    return PageParser()


class TestFullEntryPage:
    def test_parses_one_entry(self, parser: PageParser) -> None:
        page = parser.parse(_load("full_entry.xml"), "outsiders")
        assert len(page.entries) == 1

    def test_no_deleted_entries(self, parser: PageParser) -> None:
        page = parser.parse(_load("full_entry.xml"), "outsiders")
        assert page.deleted_entries == []

    def test_next_link(self, parser: PageParser) -> None:
        page = parser.parse(_load("full_entry.xml"), "outsiders")
        assert page.next_link == "https://example.com/feed?page=2"


class TestMinimalEntryPage:
    def test_parses_one_entry(self, parser: PageParser) -> None:
        page = parser.parse(_load("minimal_entry.xml"), "insiders")
        assert len(page.entries) == 1

    def test_feed_type_propagated(self, parser: PageParser) -> None:
        page = parser.parse(_load("minimal_entry.xml"), "insiders")
        assert page.entries[0].envelope.feed_type == "insiders"


class TestDeletedEntriesPage:
    def test_no_regular_entries(self, parser: PageParser) -> None:
        page = parser.parse(_load("deleted_entries_only.xml"), "outsiders")
        assert page.entries == []

    def test_three_deleted_entries(self, parser: PageParser) -> None:
        page = parser.parse(_load("deleted_entries_only.xml"), "outsiders")
        assert len(page.deleted_entries) == 3

    def test_deleted_entry_ref(self, parser: PageParser) -> None:
        page = parser.parse(_load("deleted_entries_only.xml"), "outsiders")
        refs = [de.ref for de in page.deleted_entries]
        assert any("entry_deleted_001" in r for r in refs)

    def test_deleted_entry_when(self, parser: PageParser) -> None:
        page = parser.parse(_load("deleted_entries_only.xml"), "outsiders")
        assert page.deleted_entries[0].when is not None
        assert page.deleted_entries[0].when.year == 2024

    def test_next_link(self, parser: PageParser) -> None:
        page = parser.parse(_load("deleted_entries_only.xml"), "outsiders")
        assert page.next_link is not None
        assert "page=3" in page.next_link


class TestMultiLotPage:
    def test_parses_one_entry(self, parser: PageParser) -> None:
        page = parser.parse(_load("multi_lot_with_terms.xml"), "outsiders")
        assert len(page.entries) == 1

    def test_entry_has_three_lots(self, parser: PageParser) -> None:
        page = parser.parse(_load("multi_lot_with_terms.xml"), "outsiders")
        assert len(page.entries[0].lot_groups) == 3


class TestParseFailureIsolation:
    """A broken entry must not prevent parsing the rest of the page."""

    _FEED_WITH_BAD_ENTRY = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<feed xmlns="http://www.w3.org/2005/Atom"'
        b"  xmlns:cac-place-ext="
        b'"urn:dgpe:names:draft:codice-place-ext:schema:xsd:'
        b'CommonAggregateComponents-2"'
        b"  xmlns:cbc-place-ext="
        b'"urn:dgpe:names:draft:codice-place-ext:schema:xsd:'
        b'CommonBasicComponents-2"'
        b"  xmlns:cac="
        b'"urn:dgpe:names:draft:codice:schema:xsd:'
        b'CommonAggregateComponents-2"'
        b"  xmlns:cbc="
        b'"urn:dgpe:names:draft:codice:schema:xsd:'
        b'CommonBasicComponents-2">'
        # Entry 1 — missing ContractFolderStatus → parse error
        b"<entry>"
        b"<id>broken_entry_001</id>"
        b"<updated>2024-01-01T00:00:00+00:00</updated>"
        b"</entry>"
        # Entry 2 — valid minimal entry
        b"<entry>"
        b"<id>good_entry_002</id>"
        b"<updated>2024-01-01T00:00:00+00:00</updated>"
        b"<title>OK</title>"
        b"<cac-place-ext:ContractFolderStatus>"
        b"<cbc-place-ext:ContractFolderStatusCode>"
        b"PUB"
        b"</cbc-place-ext:ContractFolderStatusCode>"
        b"<cac-place-ext:LocatedContractingParty>"
        b"<cac:Party>"
        b"<cac:PartyName><cbc:Name>Test</cbc:Name></cac:PartyName>"
        b"</cac:Party>"
        b"</cac-place-ext:LocatedContractingParty>"
        b"<cac:ProcurementProject>"
        b"<cbc:Name>Test</cbc:Name>"
        b"<cbc:TypeCode>1</cbc:TypeCode>"
        b"</cac:ProcurementProject>"
        b"<cac:TenderingProcess>"
        b"<cbc:ProcedureCode>1</cbc:ProcedureCode>"
        b"</cac:TenderingProcess>"
        b"</cac-place-ext:ContractFolderStatus>"
        b"</entry>"
        b"</feed>"
    )

    def test_good_entry_still_parsed(self, parser: PageParser) -> None:
        page = parser.parse(self._FEED_WITH_BAD_ENTRY, "outsiders")
        assert len(page.entries) == 1
        assert page.entries[0].envelope.entry_id == "good_entry_002"

    def test_bad_entry_recorded_as_failure(self, parser: PageParser) -> None:
        page = parser.parse(self._FEED_WITH_BAD_ENTRY, "outsiders")
        assert len(page.parse_failures) == 1
        assert page.parse_failures[0].entry_id == "broken_entry_001"

    def test_failure_has_error_message(self, parser: PageParser) -> None:
        page = parser.parse(self._FEED_WITH_BAD_ENTRY, "outsiders")
        assert "ContractFolderStatus" in page.parse_failures[0].error_message
