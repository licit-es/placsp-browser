"""Parser for ProcurementProjectLot elements.

Composes ProcurementProjectParser (lot-level) and TenderingTermsParser
to produce one LotBundle per lot found in the ContractFolderStatus.

Zero lots -> empty list. No virtual lots.
"""

from dataclasses import dataclass, field

from lxml import etree

from shared.codice.xml_helpers import find_all, find_children, find_first, text
from etl.parsers.procurement_project import LotProjectFields, ProcurementProjectParser
from etl.parsers.tendering_terms import (
    CriteriaData,
    RequirementData,
    TenderingTermsParser,
)


@dataclass
class LocationData:
    """Raw realized-location data from a lot's Address element."""

    nuts_code: str | None = None
    country_subentity: str | None = None
    country_code: str | None = None
    city_name: str | None = None
    postal_zone: str | None = None
    street_name: str | None = None


@dataclass
class LotBundle:
    """Complete parsed output for a single lot."""

    lot_number: str
    project: LotProjectFields
    cpv_codes: list[str] = field(default_factory=list)
    criteria: list[CriteriaData] = field(default_factory=list)
    requirements: list[RequirementData] = field(default_factory=list)
    locations: list[LocationData] = field(default_factory=list)


class LotParser:
    def __init__(
        self,
        project: ProcurementProjectParser,
        terms: TenderingTermsParser,
    ) -> None:
        self._project = project
        self._terms = terms

    def parse(self, folder_elem: etree._Element) -> list[LotBundle]:
        bundles: list[LotBundle] = []

        for lot_elem in find_children(folder_elem, "ProcurementProjectLot"):
            lot_number = self._extract_lot_number(lot_elem)
            if lot_number is None:
                continue

            project_fields = self._project.parse_lot(lot_elem)

            terms_bundle = self._terms.parse(lot_elem, is_lot=True)

            cpv_codes = project_fields.cpv_codes or []

            locations = self._parse_locations(lot_elem)

            bundles.append(
                LotBundle(
                    lot_number=lot_number,
                    project=project_fields,
                    cpv_codes=cpv_codes,
                    criteria=terms_bundle.criteria,
                    requirements=terms_bundle.requirements,
                    locations=locations,
                )
            )

        return bundles

    def _extract_lot_number(self, lot_elem: etree._Element) -> str | None:
        for child in lot_elem:
            if not isinstance(child.tag, str):
                continue
            local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if local == "ID":
                return text(child)
        return None

    def _parse_locations(self, lot_elem: etree._Element) -> list[LocationData]:
        locations: list[LocationData] = []
        pp = find_first(lot_elem, "ProcurementProject")
        if pp is None:
            return locations

        for rl in find_all(pp, "RealizedLocation"):
            address = find_first(rl, "Address")
            if address is None:
                continue

            locations.append(
                LocationData(
                    nuts_code=text(find_first(address, "CountrySubentityCode")),
                    country_subentity=text(find_first(address, "CountrySubentity")),
                    country_code=text(find_first(address, "IdentificationCode")),
                    city_name=text(find_first(address, "CityName")),
                    postal_zone=text(find_first(address, "PostalZone")),
                    street_name=text(find_first(address, "Line")),
                )
            )

        return locations
