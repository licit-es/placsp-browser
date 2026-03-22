import uuid
from decimal import Decimal

from pydantic import BaseModel


class AwardingCriteriaWrite(BaseModel):
    contract_folder_status_id: uuid.UUID
    lot_id: uuid.UUID | None = None
    criteria_type_code: str | None = None
    criteria_sub_type_code: str | None = None
    description: str | None = None
    weight_numeric: Decimal | None = None
    note: str | None = None


class AwardingCriteriaRead(AwardingCriteriaWrite):
    id: uuid.UUID
