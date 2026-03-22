import uuid

from pydantic import BaseModel


class BusinessClassificationWrite(BaseModel):
    contract_folder_status_id: uuid.UUID
    code_value: str


class BusinessClassificationRead(BusinessClassificationWrite):
    id: uuid.UUID
