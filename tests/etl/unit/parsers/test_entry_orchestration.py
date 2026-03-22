"""Tests for EntryParser orchestration."""

from decimal import Decimal
from pathlib import Path

import pytest

from etl.parsers.entry import EntryParser
from shared.codice.xml_helpers import get_entries, parse_xml

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _entry_elem(fixture: str, index: int = 0) -> object:
    root = parse_xml(_load(fixture))
    return get_entries(root)[index]


@pytest.fixture
def parser() -> EntryParser:
    return EntryParser()


class TestFullEntryOrchestration:
    def test_envelope_id(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert "entry_001" in result.envelope.entry_id

    def test_envelope_feed_type(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert result.envelope.feed_type == "outsiders"

    def test_envelope_title(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert "Material informático" in result.envelope.title

    def test_envelope_updated(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert result.envelope.updated.year == 2024

    def test_envelope_link(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert "detalle_licitacion" in result.envelope.link

    def test_folder_status_code(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert result.folder.status_code == "ADJ"

    def test_folder_contract_id(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert result.folder.contract_folder_id == "2024/001"

    def test_folder_project_fields(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert result.folder.name == "Material informático para oficinas"
        assert result.folder.type_code == "1"
        assert result.folder.total_amount == Decimal("181500.00")

    def test_folder_process_fields(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert result.folder.procedure_code == "1"
        assert result.folder.max_lot_presentation_quantity == 2

    def test_folder_terms_scalars(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert result.folder.funding_program_code == "NO-EU"
        assert result.folder.national_legislation_code == "LCSP"

    def test_folder_ted_uuid(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert result.folder.ted_uuid == "ted-uuid-001"

    def test_contracting_party(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert result.contracting_party.name == "Ayuntamiento de Test"
        assert result.contracting_party.dir3 == "EA0003089"

    def test_lot_groups(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert len(result.lot_groups) == 2
        assert result.lot_groups[0].lot.lot_number == "1"
        assert result.lot_groups[1].lot.lot_number == "2"

    def test_cpv_folder(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        codes = [c.item_classification_code for c in result.cpv_folder]
        assert "30200000" in codes
        assert "30230000" in codes

    def test_cpv_lot(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        total_cpv = sum(len(lg.cpv_codes) for lg in result.lot_groups)
        assert total_cpv == 2

    def test_criteria_folder(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert len(result.criteria_folder) == 2

    def test_criteria_lot(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        total = sum(len(lg.criteria) for lg in result.lot_groups)
        assert total == 1

    def test_guarantees(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert len(result.guarantees) == 1

    def test_requirements_folder(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert len(result.requirements_folder) == 3

    def test_requirements_lot(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        total = sum(len(lg.requirements) for lg in result.lot_groups)
        assert total == 1

    def test_classifications(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert len(result.classifications) == 2

    def test_conditions(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert len(result.conditions) == 1

    def test_result_groups(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert len(result.result_groups) == 2

    def test_winning_parties(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        total = sum(len(rg.winning_parties) for rg in result.result_groups)
        assert total == 2

    def test_contracts(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        contracts = [rg.contract for rg in result.result_groups if rg.contract]
        assert len(contracts) == 1

    def test_documents(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        source_types = {d.source_type for d in result.direct_documents}
        assert "LEGAL" in source_types
        assert "TECHNICAL" in source_types
        # PUBLICATION docs are inside notice_groups
        pub_docs = [
            doc
            for ng in result.notice_groups
            for sg in ng.statuses
            for doc in sg.documents
        ]
        assert any(d.source_type == "PUBLICATION" for d in pub_docs)

    def test_notice_groups(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert len(result.notice_groups) == 2

    def test_publication_statuses(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        total = sum(len(ng.statuses) for ng in result.notice_groups)
        assert total == 3

    def test_modifications(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert len(result.modifications) == 1

    def test_status_changes(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        assert len(result.status_changes) == 1
        assert result.status_changes[0].status_code == "ADJ"

    def test_locations(self, parser: EntryParser) -> None:
        entry = _entry_elem("full_entry.xml")
        result = parser.parse(entry, "outsiders")
        all_locations = [loc for lg in result.lot_groups for loc in lg.locations]
        assert len(all_locations) == 1
        assert all_locations[0].city_name == "Madrid"


class TestMinimalEntryOrchestration:
    def test_minimal_has_empty_lots(self, parser: EntryParser) -> None:
        entry = _entry_elem("minimal_entry.xml")
        result = parser.parse(entry, "insiders")
        assert result.lot_groups == []

    def test_minimal_has_no_results(self, parser: EntryParser) -> None:
        entry = _entry_elem("minimal_entry.xml")
        result = parser.parse(entry, "insiders")
        assert result.result_groups == []

    def test_minimal_has_status_change(self, parser: EntryParser) -> None:
        entry = _entry_elem("minimal_entry.xml")
        result = parser.parse(entry, "insiders")
        assert len(result.status_changes) == 1


class TestMultiLotOrchestration:
    def test_three_lots(self, parser: EntryParser) -> None:
        entry = _entry_elem("multi_lot_with_terms.xml")
        result = parser.parse(entry, "outsiders")
        assert len(result.lot_groups) == 3

    def test_lot_level_criteria(self, parser: EntryParser) -> None:
        entry = _entry_elem("multi_lot_with_terms.xml")
        result = parser.parse(entry, "outsiders")
        total = sum(len(lg.criteria) for lg in result.lot_groups)
        assert total == 3
