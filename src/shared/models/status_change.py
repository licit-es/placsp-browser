import uuid
from datetime import datetime

from pydantic import BaseModel


class StatusChangeWrite(BaseModel):
    contract_folder_status_id: uuid.UUID
    status_code: str
    updated: datetime


class StatusChangeRead(StatusChangeWrite):
    id: uuid.UUID
    recorded_at: datetime
