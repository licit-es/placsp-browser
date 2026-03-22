"""Parser for ContractModification elements."""

from dataclasses import dataclass
from decimal import Decimal

from lxml import etree

from shared.codice.xml_helpers import (
    attr,
    find_children,
    find_first,
    text,
    text_decimal,
    text_int,
)


@dataclass
class ModificationData:
    """Raw contract modification data before FK assignment."""

    modification_number: str | None = None
    contract_id: str | None = None
    note: str | None = None
    modification_duration_measure: int | None = None
    modification_duration_unit_code: str | None = None
    final_duration_measure: int | None = None
    final_duration_unit_code: str | None = None
    modification_tax_exclusive_amount: Decimal | None = None
    final_tax_exclusive_amount: Decimal | None = None
    currency_id: str | None = None


class ModificationParser:
    def parse(self, folder_elem: etree._Element) -> list[ModificationData]:
        modifications: list[ModificationData] = []

        for cm in find_children(folder_elem, "ContractModification"):
            mod_duration = find_first(cm, "ContractModificationDuration")
            final_duration = find_first(cm, "FinalContractDuration")
            mod_budget = find_first(cm, "ContractModificationBudget")
            final_budget = find_first(cm, "FinalContractBudget")

            mod_dur_elem = (
                find_first(mod_duration, "DurationMeasure")
                if mod_duration is not None
                else None
            )
            final_dur_elem = (
                find_first(final_duration, "DurationMeasure")
                if final_duration is not None
                else None
            )

            mod_amount_elem = (
                find_first(mod_budget, "TaxExclusiveAmount")
                if mod_budget is not None
                else None
            )
            final_amount_elem = (
                find_first(final_budget, "TaxExclusiveAmount")
                if final_budget is not None
                else None
            )

            currency_id = None
            for amount_elem in [mod_amount_elem, final_amount_elem]:
                if amount_elem is not None:
                    currency_id = attr(amount_elem, "currencyID")
                    if currency_id:
                        break

            modifications.append(
                ModificationData(
                    modification_number=text(find_first(cm, "ID")),
                    contract_id=text(find_first(cm, "ContractID")),
                    note=text(find_first(cm, "Note")),
                    modification_duration_measure=text_int(mod_dur_elem),
                    modification_duration_unit_code=attr(mod_dur_elem, "unitCode"),
                    final_duration_measure=text_int(final_dur_elem),
                    final_duration_unit_code=attr(final_dur_elem, "unitCode"),
                    modification_tax_exclusive_amount=text_decimal(mod_amount_elem),
                    final_tax_exclusive_amount=text_decimal(final_amount_elem),
                    currency_id=currency_id,
                )
            )

        return modifications
