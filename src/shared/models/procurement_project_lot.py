import uuid
from decimal import Decimal

from pydantic import BaseModel


class ProcurementProjectLotWrite(BaseModel):
    contract_folder_status_id: uuid.UUID
    lot_number: str
    name: str | None = None
    total_amount: Decimal | None = None
    tax_exclusive_amount: Decimal | None = None
    currency_id: str | None = None
    nuts_code: str | None = None
    country_subentity: str | None = None


class ProcurementProjectLotRead(ProcurementProjectLotWrite):
    id: uuid.UUID
