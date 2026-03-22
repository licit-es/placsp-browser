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
