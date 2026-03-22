import uuid

from pydantic import BaseModel


class RealizedLocationWrite(BaseModel):
    lot_id: uuid.UUID
    nuts_code: str | None = None
    country_subentity: str | None = None
    country_code: str | None = None
    city_name: str | None = None
    postal_zone: str | None = None
    street_name: str | None = None


class RealizedLocationRead(RealizedLocationWrite):
    id: uuid.UUID
