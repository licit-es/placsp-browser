import uuid
from datetime import date

from pydantic import BaseModel


class ContractWrite(BaseModel):
    tender_result_id: uuid.UUID
    contract_number: str | None = None
    issue_date: date | None = None


class ContractRead(ContractWrite):
    id: uuid.UUID
