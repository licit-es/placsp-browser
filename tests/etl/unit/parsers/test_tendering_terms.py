"""Tests for TenderingTermsParser."""

from decimal import Decimal
from pathlib import Path

import pytest

from etl.parsers.tendering_terms import TenderingTermsParser
from shared.codice.xml_helpers import find_children, find_first, get_entries, parse_xml

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _folder_elem(fixture: str) -> object:
    root = parse_xml(_load(fixture))
    entries = get_entries(root)
    return find_first(entries[0], "ContractFolderStatus")


@pytest.fixture
def parser() -> TenderingTermsParser:
    return TenderingTermsParser()


class TestFolderLevelScalarFields:
    def test_required_curricula_indicator(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.scalar_fields is not None
        assert result.scalar_fields.required_curricula_indicator is False

    def test_procurement_legislation_id(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.scalar_fields is not None
        assert result.scalar_fields.procurement_legislation_id == "2014/24/EU"

    def test_variant_constraint_indicator(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.scalar_fields is not None
        assert result.scalar_fields.variant_constraint_indicator is False

    def test_price_revision_formula(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.scalar_fields is not None
        assert result.scalar_fields.price_revision_formula == "Formula revisión"

    def test_funding_program_code(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.scalar_fields is not None
        assert result.scalar_fields.funding_program_code == "NO-EU"

    def test_funding_program_name(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.scalar_fields is not None
        assert (
            result.scalar_fields.funding_program_name
            == "No hay financiación con fondos de la UE"
        )

    def test_funding_program_description(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.scalar_fields is not None
        assert (
            result.scalar_fields.funding_program_description
            == "Sin financiación europea"
        )

    def test_received_appeal_quantity(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.scalar_fields is not None
        assert result.scalar_fields.received_appeal_quantity == 0

    def test_tender_recipient_endpoint_id(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.scalar_fields is not None
        assert result.scalar_fields.tender_recipient_endpoint_id == "endpoint001"

    def test_allowed_subcontract_rate(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.scalar_fields is not None
        assert result.scalar_fields.allowed_subcontract_rate == Decimal("30.00")

    def test_allowed_subcontract_description(
        self, parser: TenderingTermsParser
    ) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.scalar_fields is not None
        assert (
            result.scalar_fields.allowed_subcontract_description
            == "Subcontratación permitida hasta el 30%"
        )

    def test_national_legislation_code(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.scalar_fields is not None
        assert result.scalar_fields.national_legislation_code == "LCSP"


class TestFolderLevelCriteria:
    def test_folder_has_two_criteria(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert len(result.criteria) == 2

    def test_first_criteria_type_code(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.criteria[0].criteria_type_code == "OBJ"

    def test_first_criteria_sub_type(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.criteria[0].criteria_sub_type_code == "1"

    def test_first_criteria_description(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.criteria[0].description == "Precio"

    def test_first_criteria_weight(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.criteria[0].weight_numeric == Decimal("60")

    def test_second_criteria_has_note(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.criteria[1].note == "Valoración según baremo"


class TestFolderLevelRequirements:
    def test_folder_has_three_requirements(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert len(result.requirements) == 3

    def test_technical_requirement(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        tech = [r for r in result.requirements if r.origin_type == "TECHNICAL"]
        assert len(tech) == 1
        assert tech[0].evaluation_criteria_type_code == "1"
        assert (
            tech[0].description == "Experiencia en suministro de material informático"
        )
        assert tech[0].personal_situation == "Capacidad de obrar"

    def test_financial_requirement(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        fin = [r for r in result.requirements if r.origin_type == "FINANCIAL"]
        assert len(fin) == 1
        assert fin[0].threshold_quantity == Decimal("100000")
        assert fin[0].personal_situation == "Capacidad de obrar"

    def test_declaration_requirement(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        decl = [r for r in result.requirements if r.origin_type == "DECLARATION"]
        assert len(decl) == 1
        assert decl[0].evaluation_criteria_type_code == "1"


class TestFolderLevelGuarantees:
    def test_folder_has_one_guarantee(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert len(result.guarantees) == 1

    def test_guarantee_type_code(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.guarantees[0].guarantee_type_code == "1"

    def test_guarantee_amount_rate(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.guarantees[0].amount_rate == Decimal("5")

    def test_guarantee_liability_amount(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.guarantees[0].liability_amount == Decimal("7500.00")

    def test_guarantee_currency(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert result.guarantees[0].currency_id == "EUR"


class TestFolderLevelClassifications:
    def test_folder_has_two_classifications(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert len(result.classifications) == 2

    def test_classification_codes(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        codes = [c.code_value for c in result.classifications]
        assert "C3-1" in codes
        assert "G*-2" in codes


class TestFolderLevelConditions:
    def test_folder_has_one_condition(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        assert len(result.conditions) == 1

    def test_condition_fields(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("full_entry.xml")
        result = parser.parse(folder)
        cond = result.conditions[0]
        assert cond.name == "Condición medioambiental"
        assert cond.execution_requirement_code == "3"
        assert cond.description == "Cumplimiento normativa medioambiental"


class TestLotLevelTerms:
    def test_lot_terms_have_no_scalar_fields(
        self, parser: TenderingTermsParser
    ) -> None:
        root = parse_xml(_load("full_entry.xml"))
        entry = get_entries(root)[0]
        folder = find_first(entry, "ContractFolderStatus")
        lots = find_children(folder, "ProcurementProjectLot")
        result = parser.parse(lots[0], is_lot=True)
        assert result.scalar_fields is None

    def test_lot_terms_have_no_guarantees(self, parser: TenderingTermsParser) -> None:
        root = parse_xml(_load("full_entry.xml"))
        entry = get_entries(root)[0]
        folder = find_first(entry, "ContractFolderStatus")
        lots = find_children(folder, "ProcurementProjectLot")
        result = parser.parse(lots[0], is_lot=True)
        assert result.guarantees == []

    def test_lot_terms_have_no_classifications(
        self, parser: TenderingTermsParser
    ) -> None:
        root = parse_xml(_load("full_entry.xml"))
        entry = get_entries(root)[0]
        folder = find_first(entry, "ContractFolderStatus")
        lots = find_children(folder, "ProcurementProjectLot")
        result = parser.parse(lots[0], is_lot=True)
        assert result.classifications == []

    def test_lot_terms_have_no_conditions(self, parser: TenderingTermsParser) -> None:
        root = parse_xml(_load("full_entry.xml"))
        entry = get_entries(root)[0]
        folder = find_first(entry, "ContractFolderStatus")
        lots = find_children(folder, "ProcurementProjectLot")
        result = parser.parse(lots[0], is_lot=True)
        assert result.conditions == []

    def test_lot_has_criteria(self, parser: TenderingTermsParser) -> None:
        root = parse_xml(_load("full_entry.xml"))
        entry = get_entries(root)[0]
        folder = find_first(entry, "ContractFolderStatus")
        lots = find_children(folder, "ProcurementProjectLot")
        result = parser.parse(lots[0], is_lot=True)
        assert len(result.criteria) == 1
        assert result.criteria[0].criteria_type_code == "OBJ"
        assert result.criteria[0].weight_numeric == Decimal("70")

    def test_lot_has_requirements(self, parser: TenderingTermsParser) -> None:
        root = parse_xml(_load("full_entry.xml"))
        entry = get_entries(root)[0]
        folder = find_first(entry, "ContractFolderStatus")
        lots = find_children(folder, "ProcurementProjectLot")
        result = parser.parse(lots[0], is_lot=True)
        assert len(result.requirements) == 1
        assert result.requirements[0].origin_type == "TECHNICAL"

    def test_lot_without_terms_returns_empty(
        self, parser: TenderingTermsParser
    ) -> None:
        root = parse_xml(_load("full_entry.xml"))
        entry = get_entries(root)[0]
        folder = find_first(entry, "ContractFolderStatus")
        lots = find_children(folder, "ProcurementProjectLot")
        result = parser.parse(lots[1], is_lot=True)
        assert result.criteria == []
        assert result.requirements == []


class TestMultiLotFixture:
    def test_folder_terms_have_funding_code(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("multi_lot_with_terms.xml")
        result = parser.parse(folder)
        assert result.scalar_fields is not None
        assert result.scalar_fields.funding_program_code == "FEDER"

    def test_folder_terms_have_guarantee(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("multi_lot_with_terms.xml")
        result = parser.parse(folder)
        assert len(result.guarantees) == 1
        assert result.guarantees[0].guarantee_type_code == "1"
        assert result.guarantees[0].amount_rate == Decimal("5")

    def test_lot1_has_two_criteria(self, parser: TenderingTermsParser) -> None:
        root = parse_xml(_load("multi_lot_with_terms.xml"))
        entry = get_entries(root)[0]
        folder = find_first(entry, "ContractFolderStatus")
        lots = find_children(folder, "ProcurementProjectLot")
        result = parser.parse(lots[0], is_lot=True)
        assert len(result.criteria) == 2

    def test_lot1_has_technical_requirement(self, parser: TenderingTermsParser) -> None:
        root = parse_xml(_load("multi_lot_with_terms.xml"))
        entry = get_entries(root)[0]
        folder = find_first(entry, "ContractFolderStatus")
        lots = find_children(folder, "ProcurementProjectLot")
        result = parser.parse(lots[0], is_lot=True)
        assert len(result.requirements) == 1
        assert (
            result.requirements[0].description == "Experiencia en limpieza industrial"
        )

    def test_lot3_has_no_terms(self, parser: TenderingTermsParser) -> None:
        root = parse_xml(_load("multi_lot_with_terms.xml"))
        entry = get_entries(root)[0]
        folder = find_first(entry, "ContractFolderStatus")
        lots = find_children(folder, "ProcurementProjectLot")
        result = parser.parse(lots[2], is_lot=True)
        assert result.criteria == []
        assert result.requirements == []


class TestMinimalEntry:
    def test_minimal_has_no_terms(self, parser: TenderingTermsParser) -> None:
        folder = _folder_elem("minimal_entry.xml")
        result = parser.parse(folder)
        assert result.scalar_fields is None
        assert result.criteria == []
        assert result.requirements == []
        assert result.guarantees == []
        assert result.classifications == []
        assert result.conditions == []
