import uuid

from pydantic import BaseModel


class WinningPartyWrite(BaseModel):
    tender_result_id: uuid.UUID
    identifier: str | None = None
    identifier_scheme: str | None = None
    name: str
    nuts_code: str | None = None
    city_name: str | None = None
    postal_zone: str | None = None
    country_code: str | None = None
    company_type_code: str | None = None


class WinningPartyRead(WinningPartyWrite):
    id: uuid.UUID
