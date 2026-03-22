"""Tests for DocumentParser."""

from pathlib import Path

import pytest

from shared.codice.xml_helpers import find_first, get_entries, parse_xml
from etl.parsers.document import DocumentParser

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _folder_elem(fixture: str) -> object:
    root = parse_xml(_load(fixture))
    entries = get_entries(root)
    return find_first(entries[0], "ContractFolderStatus")


@pytest.fixture
def parser() -> DocumentParser:
    return DocumentParser()


class TestFullEntryDocuments:
    def test_total_document_count(self, parser: DocumentParser) -> None:
        folder = _folder_elem("full_entry.xml")
        docs = parser.parse(folder)
        assert len(docs) == 4

    def test_legal_document(self, parser: DocumentParser) -> None:
        folder = _folder_elem("full_entry.xml")
        docs = parser.parse(folder)
        legal = [d for d in docs if d.source_type == "LEGAL"]
        assert len(legal) == 1
        assert legal[0].filename == "pliego_clausulas.pdf"
        assert "pliego_clausulas.pdf" in legal[0].uri
        assert legal[0].document_hash == "abc123hash"

    def test_technical_document(self, parser: DocumentParser) -> None:
        folder = _folder_elem("full_entry.xml")
        docs = parser.parse(folder)
        tech = [d for d in docs if d.source_type == "TECHNICAL"]
        assert len(tech) == 1
        assert tech[0].filename == "pliego_tecnico.pdf"
        assert tech[0].document_hash == "def456hash"

    def test_additional_document(self, parser: DocumentParser) -> None:
        folder = _folder_elem("full_entry.xml")
        docs = parser.parse(folder)
        add = [d for d in docs if d.source_type == "ADDITIONAL"]
        assert len(add) == 1
        assert add[0].filename == "anexo_i.pdf"
        assert add[0].document_hash is None

    def test_general_document(self, parser: DocumentParser) -> None:
        folder = _folder_elem("full_entry.xml")
        docs = parser.parse(folder)
        gen = [d for d in docs if d.source_type == "GENERAL"]
        assert len(gen) == 1
        assert gen[0].filename == "acta_mesa_contratacion.pdf"
        assert gen[0].document_type_code == "2"
        assert "acta_mesa.pdf" in gen[0].uri


class TestMultiLotDocuments:
    def test_has_one_legal_doc(self, parser: DocumentParser) -> None:
        folder = _folder_elem("multi_lot_with_terms.xml")
        docs = parser.parse(folder)
        legal = [d for d in docs if d.source_type == "LEGAL"]
        assert len(legal) == 1

    def test_total_count(self, parser: DocumentParser) -> None:
        folder = _folder_elem("multi_lot_with_terms.xml")
        docs = parser.parse(folder)
        assert len(docs) == 1


class TestMinimalEntry:
    def test_no_documents(self, parser: DocumentParser) -> None:
        folder = _folder_elem("minimal_entry.xml")
        docs = parser.parse(folder)
        assert docs == []
