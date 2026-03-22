import uuid

from pydantic import BaseModel


class CpvClassificationWrite(BaseModel):
    contract_folder_status_id: uuid.UUID
    lot_id: uuid.UUID | None = None
    item_classification_code: str


class CpvClassificationRead(CpvClassificationWrite):
    id: uuid.UUID
