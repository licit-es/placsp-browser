import uuid
from datetime import date

from pydantic import BaseModel


class ValidNoticeInfoWrite(BaseModel):
    contract_folder_status_id: uuid.UUID
    notice_type_code: str | None = None
    notice_issue_date: date | None = None


class ValidNoticeInfoRead(ValidNoticeInfoWrite):
    id: uuid.UUID
