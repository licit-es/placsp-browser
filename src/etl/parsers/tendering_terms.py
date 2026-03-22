"""Parser for TenderingTerms — handles criteria, requirements, guarantees, etc.

Respects E11: lot-level TenderingTerms only get criteria + requirements.
Folder-level gets everything: criteria, requirements, guarantees,
classifications, conditions, and scalar fields.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from lxml import etree

from shared.codice.xml_helpers import (
    attr,
    find_all,
    find_child,
    find_first,
    text,
    text_bool,
    text_decimal,
    text_int,
)


@dataclass
class TenderingTermsFields:
    """Scalar fields from folder-level TenderingTerms inlined into CFS."""

    required_curricula_indicator: bool | None = None
    procurement_legislation_id: str | None = None
    variant_constraint_indicator: bool | None = None
    price_revision_formula: str | None = None
    funding_program_code: str | None = None
    funding_program_name: str | None = None
    funding_program_description: str | None = None
    received_appeal_quantity: int | None = None
    tender_recipient_endpoint_id: str | None = None
    allowed_subcontract_rate: Decimal | None = None
    allowed_subcontract_description: str | None = None
    national_legislation_code: str | None = None


@dataclass
class CriteriaData:
    """Raw criteria data before FK assignment."""

    criteria_type_code: str | None = None
    criteria_sub_type_code: str | None = None
    description: str | None = None
    weight_numeric: Decimal | None = None
    note: str | None = None


@dataclass
class RequirementData:
    """Raw requirement data before FK assignment."""

    origin_type: str
    evaluation_criteria_type_code: str | None = None
    description: str | None = None
    threshold_quantity: Decimal | None = None
    personal_situation: str | None = None
    operating_years_quantity: int | None = None
    employee_quantity: int | None = None


@dataclass
class GuaranteeData:
    """Raw guarantee data before FK assignment."""

    guarantee_type_code: str | None = None
    amount_rate: Decimal | None = None
    liability_amount: Decimal | None = None
    currency_id: str | None = None


@dataclass
class ClassificationData:
    """Raw business classification data."""

    code_value: str


@dataclass
class ConditionData:
    """Raw execution condition data."""

    name: str | None = None
    execution_requirement_code: str | None = None
    description: str | None = None


@dataclass
class TenderingTermsBundle:
    """Complete parsed output from TenderingTerms."""

    scalar_fields: TenderingTermsFields | None = None
    criteria: list[CriteriaData] = field(default_factory=list)
    requirements: list[RequirementData] = field(default_factory=list)
    guarantees: list[GuaranteeData] = field(default_factory=list)
    classifications: list[ClassificationData] = field(default_factory=list)
    conditions: list[ConditionData] = field(default_factory=list)


class TenderingTermsParser:
    def parse(
        self,
        parent_elem: etree._Element,
        is_lot: bool = False,
    ) -> TenderingTermsBundle:
        tt = find_child(parent_elem, "TenderingTerms")
        if tt is None:
            return TenderingTermsBundle()

        criteria = self._parse_criteria(tt)
        requirements = self._parse_requirements(tt)

        if is_lot:
            return TenderingTermsBundle(
                criteria=criteria,
                requirements=requirements,
            )

        scalar_fields = self._parse_scalar_fields(tt)
        guarantees = self._parse_guarantees(tt)
        classifications = self._parse_classifications(tt)
        conditions = self._parse_conditions(tt)

        return TenderingTermsBundle(
            scalar_fields=scalar_fields,
            criteria=criteria,
            requirements=requirements,
            guarantees=guarantees,
            classifications=classifications,
            conditions=conditions,
        )

    def _parse_scalar_fields(self, tt: etree._Element) -> TenderingTermsFields:
        funding_code_elem = find_first(tt, "FundingProgramCode")
        appeal_terms = find_first(tt, "AppealTerms")
        recipient = find_first(tt, "TenderRecipientParty")
        subcontract = find_first(tt, "AllowedSubcontractTerms")
        legislation = find_first(tt, "ProcurementLegislationDocumentReference")
        funding_program = find_first(tt, "FundingProgram")

        return TenderingTermsFields(
            required_curricula_indicator=text_bool(
                find_child(tt, "RequiredCurriculaIndicator")
            ),
            procurement_legislation_id=text(find_first(legislation, "ID"))
            if legislation is not None
            else None,
            variant_constraint_indicator=text_bool(
                find_child(tt, "VariantConstraintIndicator")
            ),
            price_revision_formula=text(find_child(tt, "PriceRevisionFormulaID")),
            funding_program_code=text(funding_code_elem),
            funding_program_name=attr(funding_code_elem, "name"),
            funding_program_description=text(find_first(funding_program, "Description"))
            if funding_program is not None
            else None,
            received_appeal_quantity=text_int(
                find_first(appeal_terms, "ReceivedAppealQuantity")
            )
            if appeal_terms is not None
            else None,
            tender_recipient_endpoint_id=text(find_first(recipient, "EndpointID"))
            if recipient is not None
            else None,
            allowed_subcontract_rate=text_decimal(find_first(subcontract, "Rate"))
            if subcontract is not None
            else None,
            allowed_subcontract_description=text(find_first(subcontract, "Description"))
            if subcontract is not None
            else None,
            national_legislation_code=text(find_child(tt, "NationalLegislationCode")),
        )

    def _parse_criteria(self, tt: etree._Element) -> list[CriteriaData]:
        criteria: list[CriteriaData] = []
        awarding_terms = find_first(tt, "AwardingTerms")
        if awarding_terms is None:
            return criteria

        for ac in find_all(awarding_terms, "AwardingCriteria"):
            type_code_elem = find_first(ac, "AwardingCriteriaTypeCode")
            type_code = text(type_code_elem)

            sub_type_elems = find_all(ac, "AwardingCriteriaTypeCode")
            sub_type_code = None
            for elem in sub_type_elems:
                val = text(elem)
                if val and val != type_code:
                    sub_type_code = val
                    break
                if val and val in ("1", "2", "3", "4", "5", "01", "02", "99"):
                    sub_type_code = val

            criteria.append(
                CriteriaData(
                    criteria_type_code=type_code,
                    criteria_sub_type_code=sub_type_code,
                    description=text(find_first(ac, "Description")),
                    weight_numeric=text_decimal(find_first(ac, "WeightNumeric")),
                    note=text(find_first(ac, "Note")),
                )
            )
        return criteria

    def _parse_requirements(self, tt: etree._Element) -> list[RequirementData]:
        requirements: list[RequirementData] = []

        for tqr in find_all(tt, "TendererQualificationRequest"):
            personal_situation = text(find_first(tqr, "PersonalSituation"))

            requirements.extend(
                RequirementData(
                    origin_type="TECHNICAL",
                    evaluation_criteria_type_code=text(
                        find_first(tec, "EvaluationCriteriaTypeCode")
                    ),
                    description=text(find_first(tec, "Description")),
                    threshold_quantity=text_decimal(
                        find_first(tec, "ThresholdQuantity")
                    ),
                    personal_situation=personal_situation,
                    operating_years_quantity=text_int(
                        find_first(tec, "OperatingYearsQuantity")
                    ),
                    employee_quantity=text_int(find_first(tec, "EmployeeQuantity")),
                )
                for tec in find_all(tqr, "TechnicalEvaluationCriteria")
            )

            requirements.extend(
                RequirementData(
                    origin_type="FINANCIAL",
                    evaluation_criteria_type_code=text(
                        find_first(fec, "EvaluationCriteriaTypeCode")
                    ),
                    description=text(find_first(fec, "Description")),
                    threshold_quantity=text_decimal(
                        find_first(fec, "ThresholdQuantity")
                    ),
                    personal_situation=personal_situation,
                )
                for fec in find_all(tqr, "FinancialEvaluationCriteria")
            )

            requirements.extend(
                RequirementData(
                    origin_type="DECLARATION",
                    evaluation_criteria_type_code=text(
                        find_first(str_elem, "RequirementTypeCode")
                    ),
                    personal_situation=personal_situation,
                )
                for str_elem in find_all(tqr, "SpecificTendererRequirement")
            )

        return requirements

    def _parse_guarantees(self, tt: etree._Element) -> list[GuaranteeData]:
        guarantees: list[GuaranteeData] = []
        for rfg in find_all(tt, "RequiredFinancialGuarantee"):
            liability = find_first(rfg, "LiabilityAmount")
            guarantees.append(
                GuaranteeData(
                    guarantee_type_code=text(find_first(rfg, "GuaranteeTypeCode")),
                    amount_rate=text_decimal(find_first(rfg, "AmountRate")),
                    liability_amount=text_decimal(liability),
                    currency_id=attr(liability, "currencyID"),
                )
            )
        return guarantees

    def _parse_classifications(self, tt: etree._Element) -> list[ClassificationData]:
        classifications: list[ClassificationData] = []
        for rbc in find_all(tt, "RequiredBusinessClassification"):
            code = text(find_first(rbc, "ClassificationCategoryCode"))
            if code:
                classifications.append(ClassificationData(code_value=code))
        return classifications

    def _parse_conditions(self, tt: etree._Element) -> list[ConditionData]:
        return [
            ConditionData(
                name=text(find_first(cer, "Name")),
                execution_requirement_code=text(
                    find_first(cer, "ExecutionRequirementCode")
                ),
                description=text(find_first(cer, "Description")),
            )
            for cer in find_all(tt, "ContractExecutionRequirement")
        ]
