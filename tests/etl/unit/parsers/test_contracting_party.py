"""Tests for ContractingPartyParser."""

from pathlib import Path

import pytest

from shared.codice.xml_helpers import find_first, get_entries, parse_xml
from etl.parsers.contracting_party import ContractingPartyParser

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _folder_elem(fixture: str) -> object:
    root = parse_xml(_load(fixture))
    entries = get_entries(root)
    entry = entries[0]
    return find_first(entry, "ContractFolderStatus")


@pytest.fixture
def parser() -> ContractingPartyParser:
    return ContractingPartyParser()


class TestContractingPartyParserFullEntry:
    def test_parses_name(self, parser: ContractingPartyParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.name == "Ayuntamiento de Test"

    def test_parses_dir3(self, parser: ContractingPartyParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.dir3 == "EA0003089"

    def test_parses_nif(self, parser: ContractingPartyParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.nif == "S2800011H"

    def test_parses_platform_id(self, parser: ContractingPartyParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.platform_id == "PLAT001"

    def test_parses_website(self, parser: ContractingPartyParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.website_uri == "http://www.ayto-test.es"

    def test_parses_contact(self, parser: ContractingPartyParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.contact_name == "Juan García"
        assert result.contact_telephone == "910000001"
        assert result.contact_telefax == "910000002"
        assert result.contact_email == "contratacion@test.es"

    def test_parses_address(self, parser: ContractingPartyParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.city_name == "Madrid"
        assert result.postal_zone == "28001"
        assert result.address_line == "Calle Mayor 1"
        assert result.country_code == "ES"

    def test_parses_agent_party(self, parser: ContractingPartyParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.agent_party_id == "121"
        assert result.agent_party_name == "Comunidad de Madrid"

    def test_parses_parent_hierarchy(self, parser: ContractingPartyParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.parent_hierarchy is not None
        assert len(result.parent_hierarchy) == 3
        assert result.parent_hierarchy[0]["name"] == "Ayuntamiento de Test"
        assert result.parent_hierarchy[0]["level"] == 1
        assert result.parent_hierarchy[2]["name"] == "Comunidad de Madrid"

    def test_parses_contracting_party_type_code(
        self, parser: ContractingPartyParser
    ) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.contracting_party_type_code == "2"

    def test_parses_buyer_profile_uri(self, parser: ContractingPartyParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.buyer_profile_uri is not None
        assert "perfilContratante" in result.buyer_profile_uri


class TestContractingPartyParserMinimalEntry:
    def test_minimal_party_has_name(self, parser: ContractingPartyParser) -> None:
        folder = _folder_elem("minimal_entry.xml")
        result = parser.parse(folder)
        assert result.name == "Organismo mínimo"

    def test_minimal_party_has_no_identifiers(
        self, parser: ContractingPartyParser
    ) -> None:
        folder = _folder_elem("minimal_entry.xml")
        result = parser.parse(folder)
        assert result.dir3 is None
        assert result.nif is None
        assert result.platform_id is None

    def test_minimal_party_has_no_hierarchy(
        self, parser: ContractingPartyParser
    ) -> None:
        folder = _folder_elem("minimal_entry.xml")
        result = parser.parse(folder)
        assert result.parent_hierarchy is None


class TestPlatformIdNormalization:
    def test_id_oc_plat_used_as_fallback(self, parser: ContractingPartyParser) -> None:
        folder = _folder_elem("multi_lot_with_terms.xml")
        result = parser.parse(folder)
        assert result.platform_id == "PLAT_OC_002"

    def test_hierarchy_with_dir3(self, parser: ContractingPartyParser) -> None:
        folder = _folder_elem("multi_lot_with_terms.xml")
        result = parser.parse(folder)
        assert result.parent_hierarchy is not None
        assert result.parent_hierarchy[0].get("dir3") == "EA0008416"
