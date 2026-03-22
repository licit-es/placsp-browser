"""Tests for codice/xml_helpers.py — namespace-agnostic element search."""

from datetime import date, time
from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree

from shared.codice.xml_helpers import (
    attr,
    extract_next_link,
    find_all,
    find_child,
    find_children,
    find_first,
    get_deleted_entries,
    get_entries,
    parse_xml,
    text,
    text_bool,
    text_date,
    text_decimal,
    text_int,
    text_time,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class TestParseXml:
    def test_parses_valid_xml(self) -> None:
        root = parse_xml(b"<root><child>text</child></root>")
        assert root.tag == "root"

    def test_raises_on_invalid_xml(self) -> None:
        with pytest.raises(etree.XMLSyntaxError):
            parse_xml(b"<broken>")


class TestFindFirst:
    def test_finds_nested_element(self) -> None:
        root = parse_xml(_load("full_entry.xml"))
        elem = find_first(root, "ContractFolderID")
        assert elem is not None
        assert text(elem) == "2024/001"

    def test_returns_none_when_missing(self) -> None:
        root = parse_xml(b"<root><a/></root>")
        assert find_first(root, "nonexistent") is None


class TestFindAll:
    def test_finds_multiple_elements(self) -> None:
        root = parse_xml(_load("full_entry.xml"))
        cpvs = find_all(root, "ItemClassificationCode")
        assert len(cpvs) >= 2

    def test_returns_empty_for_missing(self) -> None:
        root = parse_xml(b"<root/>")
        assert find_all(root, "nope") == []


class TestFindChild:
    def test_finds_direct_child(self) -> None:
        root = parse_xml(b'<root xmlns:a="urn:test"><a:child>yes</a:child></root>')
        assert find_child(root, "child") is not None

    def test_ignores_deeper_descendants(self) -> None:
        root = parse_xml(b"<root><a><deep>v</deep></a></root>")
        assert find_child(root, "deep") is None


class TestFindChildren:
    def test_finds_all_direct_children_by_name(self) -> None:
        root = parse_xml(b"<root><item>1</item><item>2</item><other>3</other></root>")
        assert len(find_children(root, "item")) == 2


class TestText:
    def test_extracts_text(self) -> None:
        root = parse_xml(b"<a>hello</a>")
        assert text(root) == "hello"

    def test_returns_default_for_none(self) -> None:
        assert text(None, "fallback") == "fallback"

    def test_strips_whitespace(self) -> None:
        root = parse_xml(b"<a>  spaced  </a>")
        assert text(root) == "spaced"

    def test_returns_default_for_empty(self) -> None:
        root = parse_xml(b"<a>  </a>")
        assert text(root, "def") == "def"


class TestTextInt:
    def test_parses_integer(self) -> None:
        root = parse_xml(b"<a>42</a>")
        assert text_int(root) == 42

    def test_returns_none_for_non_numeric(self) -> None:
        root = parse_xml(b"<a>abc</a>")
        assert text_int(root) is None

    def test_returns_none_for_none(self) -> None:
        assert text_int(None) is None


class TestTextDecimal:
    def test_parses_decimal(self) -> None:
        root = parse_xml(b"<a>150000.00</a>")
        assert text_decimal(root) == Decimal("150000.00")

    def test_returns_none_for_invalid(self) -> None:
        root = parse_xml(b"<a>not-a-number</a>")
        assert text_decimal(root) is None


class TestTextBool:
    def test_true(self) -> None:
        root = parse_xml(b"<a>true</a>")
        assert text_bool(root) is True

    def test_false(self) -> None:
        root = parse_xml(b"<a>false</a>")
        assert text_bool(root) is False

    def test_none(self) -> None:
        assert text_bool(None) is None


class TestTextDate:
    def test_parses_date(self) -> None:
        root = parse_xml(b"<a>2024-07-01</a>")
        assert text_date(root) == date(2024, 7, 1)

    def test_returns_none_for_invalid(self) -> None:
        root = parse_xml(b"<a>not-a-date</a>")
        assert text_date(root) is None


class TestTextTime:
    def test_parses_time(self) -> None:
        root = parse_xml(b"<a>14:00:00</a>")
        assert text_time(root) == time(14, 0, 0)

    def test_parses_short_time(self) -> None:
        root = parse_xml(b"<a>14:00</a>")
        assert text_time(root) == time(14, 0)


class TestAttr:
    def test_extracts_attribute(self) -> None:
        root = parse_xml(b'<a currencyID="EUR">100</a>')
        assert attr(root, "currencyID") == "EUR"

    def test_returns_none_for_missing(self) -> None:
        root = parse_xml(b"<a>100</a>")
        assert attr(root, "missing") is None

    def test_returns_none_for_none_element(self) -> None:
        assert attr(None, "key") is None


class TestGetEntries:
    def test_finds_entries_in_feed(self) -> None:
        root = parse_xml(_load("full_entry.xml"))
        entries = get_entries(root)
        assert len(entries) == 1

    def test_no_entries_in_deleted_only(self) -> None:
        root = parse_xml(_load("deleted_entries_only.xml"))
        assert get_entries(root) == []


class TestGetDeletedEntries:
    def test_finds_deleted_entries(self) -> None:
        root = parse_xml(_load("deleted_entries_only.xml"))
        deleted = get_deleted_entries(root)
        assert len(deleted) == 3

    def test_no_deleted_in_regular_feed(self) -> None:
        root = parse_xml(_load("minimal_entry.xml"))
        assert get_deleted_entries(root) == []


class TestExtractNextLink:
    def test_finds_next_link(self) -> None:
        root = parse_xml(_load("full_entry.xml"))
        assert extract_next_link(root) == "https://example.com/feed?page=2"

    def test_returns_none_when_no_next(self) -> None:
        root = parse_xml(_load("minimal_entry.xml"))
        assert extract_next_link(root) is None

    def test_next_link_in_deleted_only(self) -> None:
        root = parse_xml(_load("deleted_entries_only.xml"))
        assert extract_next_link(root) == "https://example.com/feed?page=3"


class TestFixturesParseable:
    @pytest.mark.parametrize(
        "fixture",
        [
            "full_entry.xml",
            "minimal_entry.xml",
            "deleted_entries_only.xml",
            "multi_lot_with_terms.xml",
        ],
    )
    def test_fixture_parses_without_error(self, fixture: str) -> None:
        root = parse_xml(_load(fixture))
        assert root is not None
