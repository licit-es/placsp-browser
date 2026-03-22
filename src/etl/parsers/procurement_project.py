"""Parser for ProcurementProject at folder and lot levels."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from lxml import etree

from shared.codice.xml_helpers import (
    attr,
    find_all,
    find_child,
    find_first,
    text,
    text_bool,
    text_date,
    text_decimal,
    text_int,
)


@dataclass
class FolderProjectFields:
    """Fields extracted from folder-level ProcurementProject."""

    name: str | None = None
    type_code: str | None = None
    sub_type_code: str | None = None
    estimated_overall_contract_amount: Decimal | None = None
    total_amount: Decimal | None = None
    tax_exclusive_amount: Decimal | None = None
    currency_id: str | None = None
    nuts_code: str | None = None
    country_subentity: str | None = None
    duration_measure: int | None = None
    duration_unit_code: str | None = None
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    option_validity_description: str | None = None
    options_description: str | None = None
    mix_contract_indicator: bool | None = None
    cpv_codes: list[str] | None = None


@dataclass
class LotProjectFields:
    """Fields extracted from lot-level ProcurementProject.

    Does NOT have estimated_overall_contract_amount (E3).
    """

    name: str | None = None
    total_amount: Decimal | None = None
    tax_exclusive_amount: Decimal | None = None
    currency_id: str | None = None
    nuts_code: str | None = None
    country_subentity: str | None = None
    cpv_codes: list[str] | None = None


class ProcurementProjectParser:
    def parse_folder(self, folder_elem: etree._Element) -> FolderProjectFields:
        pp = find_child(folder_elem, "ProcurementProject")
        if pp is None:
            return FolderProjectFields()

        budget = find_first(pp, "BudgetAmount")
        location = find_first(pp, "RealizedLocation")
        period = find_first(pp, "PlannedPeriod")
        extension = find_first(pp, "ContractExtension")

        currency_id = None
        if budget is not None:
            for amount_tag in [
                "EstimatedOverallContractAmount",
                "TotalAmount",
                "TaxExclusiveAmount",
            ]:
                amount_elem = find_first(budget, amount_tag)
                if amount_elem is not None:
                    currency_id = attr(amount_elem, "currencyID")
                    if currency_id:
                        break

        duration_elem = (
            find_first(period, "DurationMeasure") if period is not None else None
        )

        cpv_codes = self._extract_cpv_codes(pp)

        return FolderProjectFields(
            name=text(find_child(pp, "Name")),
            type_code=text(find_child(pp, "TypeCode")),
            sub_type_code=text(find_child(pp, "SubTypeCode")),
            estimated_overall_contract_amount=text_decimal(
                find_first(budget, "EstimatedOverallContractAmount")
            )
            if budget is not None
            else None,
            total_amount=text_decimal(find_first(budget, "TotalAmount"))
            if budget is not None
            else None,
            tax_exclusive_amount=text_decimal(find_first(budget, "TaxExclusiveAmount"))
            if budget is not None
            else None,
            currency_id=currency_id,
            nuts_code=text(find_first(location, "CountrySubentityCode"))
            if location is not None
            else None,
            country_subentity=text(find_first(location, "CountrySubentity"))
            if location is not None
            else None,
            duration_measure=text_int(duration_elem),
            duration_unit_code=attr(duration_elem, "unitCode"),
            planned_start_date=text_date(find_first(period, "StartDate"))
            if period is not None
            else None,
            planned_end_date=text_date(find_first(period, "EndDate"))
            if period is not None
            else None,
            option_validity_description=text(
                find_first(extension, "OptionsDescription")
            )
            if extension is not None
            else None,
            options_description=text(find_first(extension, "OptionsDescription"))
            if extension is not None
            else None,
            mix_contract_indicator=text_bool(find_child(pp, "MixContractIndicator")),
            cpv_codes=cpv_codes,
        )

    def parse_lot(self, lot_elem: etree._Element) -> LotProjectFields:
        pp = find_child(lot_elem, "ProcurementProject")
        if pp is None:
            return LotProjectFields()

        budget = find_first(pp, "BudgetAmount")
        location = find_first(pp, "RealizedLocation")

        currency_id = None
        if budget is not None:
            for amount_tag in ["TotalAmount", "TaxExclusiveAmount"]:
                amount_elem = find_first(budget, amount_tag)
                if amount_elem is not None:
                    currency_id = attr(amount_elem, "currencyID")
                    if currency_id:
                        break

        cpv_codes = self._extract_cpv_codes(pp)

        return LotProjectFields(
            name=text(find_child(pp, "Name")),
            total_amount=text_decimal(find_first(budget, "TotalAmount"))
            if budget is not None
            else None,
            tax_exclusive_amount=text_decimal(find_first(budget, "TaxExclusiveAmount"))
            if budget is not None
            else None,
            currency_id=currency_id,
            nuts_code=text(find_first(location, "CountrySubentityCode"))
            if location is not None
            else None,
            country_subentity=text(find_first(location, "CountrySubentity"))
            if location is not None
            else None,
            cpv_codes=cpv_codes,
        )

    def _extract_cpv_codes(self, pp: etree._Element) -> list[str] | None:
        codes = []
        for cc in find_all(pp, "RequiredCommodityClassification"):
            code_elem = find_first(cc, "ItemClassificationCode")
            code = text(code_elem)
            if code:
                codes.append(code)
        return codes if codes else None
