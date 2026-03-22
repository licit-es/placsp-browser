import uuid
from decimal import Decimal

from pydantic import BaseModel


class FinancialGuaranteeWrite(BaseModel):
    contract_folder_status_id: uuid.UUID
    guarantee_type_code: str | None = None
    amount_rate: Decimal | None = None
    liability_amount: Decimal | None = None
    currency_id: str | None = None


class FinancialGuaranteeRead(FinancialGuaranteeWrite):
    id: uuid.UUID
