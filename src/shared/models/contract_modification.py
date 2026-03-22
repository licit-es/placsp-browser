import uuid
from decimal import Decimal

from pydantic import BaseModel


class ContractModificationWrite(BaseModel):
    contract_folder_status_id: uuid.UUID
    modification_number: str | None = None
    contract_id: str | None = None
    note: str | None = None
    modification_duration_measure: int | None = None
    modification_duration_unit_code: str | None = None
    final_duration_measure: int | None = None
    final_duration_unit_code: str | None = None
    modification_tax_exclusive_amount: Decimal | None = None
    final_tax_exclusive_amount: Decimal | None = None
    currency_id: str | None = None


class ContractModificationRead(ContractModificationWrite):
    id: uuid.UUID
