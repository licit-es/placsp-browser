import uuid
from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel


class ContractFolderStatusWrite(BaseModel):
    # ATOM envelope
    entry_id: str
    title: str | None = None
    summary: str | None = None
    link: str | None = None
    updated: datetime
    feed_type: str

    # ContractFolderStatus
    contract_folder_id: str | None = None
    status_code: str
    contracting_party_id: uuid.UUID | None = None

    name: str | None = None
    type_code: str | None = None
    sub_type_code: str | None = None
    estimated_overall_contract_amount: Decimal | None = None
    total_amount: Decimal | None = None
    tax_exclusive_amount: Decimal | None = None
    currency_id: str | None = None
    nuts_code: str | None = None
    country_subentity: str | None = None
    duration_measure: int | None = None
    duration_unit_code: str | None = None
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    option_validity_description: str | None = None
    options_description: str | None = None
    mix_contract_indicator: bool | None = None

    procedure_code: str | None = None
    urgency_code: str | None = None
    submission_method_code: str | None = None
    submission_deadline_date: date | None = None
    submission_deadline_time: time | None = None
    submission_deadline_description: str | None = None
    document_availability_end_date: date | None = None
    document_availability_end_time: time | None = None
    contracting_system_code: str | None = None
    part_presentation_code: str | None = None
    auction_constraint_indicator: bool | None = None
    max_lot_presentation_quantity: int | None = None
    max_tenderer_awarded_lots_qty: int | None = None
    lots_combination_rights: str | None = None
    over_threshold_indicator: bool | None = None
    participation_request_end_date: date | None = None
    participation_request_end_time: time | None = None
    short_list_limitation_description: str | None = None
    short_list_min_quantity: int | None = None
    short_list_expected_quantity: int | None = None
    short_list_max_quantity: int | None = None

    # TenderingTerms scalar fields (inlined)
    required_curricula_indicator: bool | None = None
    procurement_legislation_id: str | None = None
    variant_constraint_indicator: bool | None = None
    price_revision_formula: str | None = None
    funding_program_code: str | None = None
    funding_program_name: str | None = None
    funding_program_description: str | None = None
    received_appeal_quantity: int | None = None
    tender_recipient_endpoint_id: str | None = None
    allowed_subcontract_rate: Decimal | None = None
    allowed_subcontract_description: str | None = None
    national_legislation_code: str | None = None

    # Infrastructure
    ted_uuid: str | None = None


class ContractFolderStatusRead(ContractFolderStatusWrite):
    id: uuid.UUID
    created_at: datetime
