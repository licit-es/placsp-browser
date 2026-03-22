import uuid
from typing import Any

from pydantic import BaseModel


class ContractingPartyWrite(BaseModel):
    name: str
    dir3: str | None = None
    nif: str | None = None
    platform_id: str | None = None
    website_uri: str | None = None
    contracting_party_type_code: str | None = None
    activity_code: str | None = None
    buyer_profile_uri: str | None = None
    contact_name: str | None = None
    contact_telephone: str | None = None
    contact_telefax: str | None = None
    contact_email: str | None = None
    city_name: str | None = None
    postal_zone: str | None = None
    address_line: str | None = None
    country_code: str | None = None
    agent_party_id: str | None = None
    agent_party_name: str | None = None
    parent_hierarchy: list[dict[str, Any]] | None = None


class ContractingPartyRead(ContractingPartyWrite):
    id: uuid.UUID
