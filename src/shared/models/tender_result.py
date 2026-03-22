import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class TenderResultWrite(BaseModel):
    contract_folder_status_id: uuid.UUID
    lot_id: uuid.UUID | None = None
    result_code: str | None = None
    description: str | None = None
    award_date: date | None = None
    received_tender_quantity: int | None = None
    lower_tender_amount: Decimal | None = None
    higher_tender_amount: Decimal | None = None
    sme_awarded_indicator: bool | None = None
    abnormally_low_tenders_indicator: bool | None = None
    start_date: date | None = None
    smes_received_tender_quantity: int | None = None
    eu_nationals_received_quantity: int | None = None
    non_eu_nationals_received_qty: int | None = None
    awarded_owner_nationality_code: str | None = None
    subcontract_rate: Decimal | None = None
    subcontract_description: str | None = None
    awarded_tax_exclusive_amount: Decimal | None = None
    awarded_payable_amount: Decimal | None = None
    awarded_currency_id: str | None = None
    awarded_lot_number: str | None = None


class TenderResultRead(TenderResultWrite):
    id: uuid.UUID
