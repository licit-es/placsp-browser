"""Parser for ContractingParty from LocatedContractingParty element."""

from typing import Any

from lxml import etree

from shared.codice.xml_helpers import attr, find_all, find_child, find_first, text
from shared.models.contracting_party import ContractingPartyWrite


class ContractingPartyParser:
    def parse(self, folder_elem: etree._Element) -> ContractingPartyWrite:
        lcp = find_first(folder_elem, "LocatedContractingParty")
        if lcp is None:
            msg = "Missing LocatedContractingParty"
            raise ValueError(msg)

        party = find_first(lcp, "Party")
        if party is None:
            msg = "Missing Party in LocatedContractingParty"
            raise ValueError(msg)

        party_name_elem = find_first(party, "PartyName")
        name_elem = (
            find_first(party_name_elem, "Name") if party_name_elem is not None else None
        )
        name = text(name_elem, "")
        if not name:
            msg = "Missing PartyName/Name"
            raise ValueError(msg)

        dir3, nif, platform_id = self._parse_identifications(party)

        cpt_code = find_child(lcp, "ContractingPartyTypeCode")
        activity = find_child(lcp, "ActivityCode")

        address = find_first(party, "PostalAddress")
        contact = find_first(party, "Contact")

        agent_party = find_first(party, "AgentParty")
        agent_id = None
        agent_name = None
        if agent_party is not None:
            agent_id_elem = find_first(agent_party, "ID")
            agent_id = text(agent_id_elem)
            agent_name_elem = find_first(agent_party, "Name")
            agent_name = text(agent_name_elem)

        buyer_profile = find_first(lcp, "BuyerProfileURIID")

        parent_hierarchy = self._parse_hierarchy(lcp)

        return ContractingPartyWrite(
            name=name,
            dir3=dir3,
            nif=nif,
            platform_id=platform_id,
            website_uri=text(find_first(party, "WebsiteURI")),
            contracting_party_type_code=text(cpt_code),
            activity_code=text(activity),
            buyer_profile_uri=text(buyer_profile),
            contact_name=text(find_first(contact, "Name"))
            if contact is not None
            else None,
            contact_telephone=text(find_first(contact, "Telephone"))
            if contact is not None
            else None,
            contact_telefax=text(find_first(contact, "Telefax"))
            if contact is not None
            else None,
            contact_email=text(find_first(contact, "ElectronicMail"))
            if contact is not None
            else None,
            city_name=text(find_first(address, "CityName"))
            if address is not None
            else None,
            postal_zone=text(find_first(address, "PostalZone"))
            if address is not None
            else None,
            address_line=text(find_first(address, "Line"))
            if address is not None
            else None,
            country_code=text(find_first(address, "IdentificationCode"))
            if address is not None
            else None,
            agent_party_id=agent_id,
            agent_party_name=agent_name,
            parent_hierarchy=parent_hierarchy,
        )

    def _parse_identifications(
        self, party: etree._Element
    ) -> tuple[str | None, str | None, str | None]:
        dir3 = None
        nif = None
        platform_id = None

        for pi in find_all(party, "PartyIdentification"):
            id_elem = find_first(pi, "ID")
            if id_elem is None:
                continue
            scheme = attr(id_elem, "schemeName")
            value = text(id_elem)
            if not value:
                continue

            if scheme == "DIR3":
                dir3 = value
            elif scheme == "NIF":
                nif = value
            elif scheme == "ID_PLATAFORMA" or (
                scheme == "ID_OC_PLAT" and platform_id is None
            ):
                platform_id = value

        return dir3, nif, platform_id

    def _parse_hierarchy(self, lcp: etree._Element) -> list[dict[str, Any]] | None:
        hierarchy: list[dict[str, Any]] = []
        level = 1
        current = find_child(lcp, "ParentLocatedParty")

        while current is not None:
            party_name = find_first(current, "PartyName")
            name = (
                text(find_first(party_name, "Name")) if party_name is not None else None
            )

            pi = find_first(current, "PartyIdentification")
            dir3 = None
            if pi is not None:
                id_elem = find_first(pi, "ID")
                if id_elem is not None and attr(id_elem, "schemeName") == "DIR3":
                    dir3 = text(id_elem)

            entry: dict[str, Any] = {"level": level}
            if name:
                entry["name"] = name
            if dir3:
                entry["dir3"] = dir3
            hierarchy.append(entry)

            level += 1
            current = find_child(current, "ParentLocatedParty")

        return hierarchy if hierarchy else None
