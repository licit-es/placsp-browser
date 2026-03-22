"""Schema drift test: ensures Pydantic model fields match DB columns exactly.

Queries information_schema.columns for every table and asserts the column set
matches the model fields. Runs against the local Supabase instance.
"""

import asyncio
from collections.abc import Generator

import asyncpg
import pytest

from shared.models.awarding_criteria import AwardingCriteriaWrite
from shared.models.business_classification import BusinessClassificationWrite
from shared.models.contract import ContractWrite
from shared.models.contract_folder_status import ContractFolderStatusWrite
from shared.models.contract_modification import ContractModificationWrite
from shared.models.contracting_party import ContractingPartyWrite
from shared.models.cpv_classification import CpvClassificationWrite
from shared.models.document_reference import DocumentReferenceWrite
from shared.models.etl import EtlFailedEntryWrite, EtlSyncStateWrite
from shared.models.execution_condition import ExecutionConditionWrite
from shared.models.financial_guarantee import FinancialGuaranteeWrite
from shared.models.procurement_project_lot import ProcurementProjectLotWrite
from shared.models.publication_status import PublicationStatusWrite
from shared.models.qualification_requirement import QualificationRequirementWrite
from shared.models.realized_location import RealizedLocationWrite
from shared.models.status_change import StatusChangeWrite
from shared.models.tender_result import TenderResultWrite
from shared.models.valid_notice_info import ValidNoticeInfoWrite
from shared.models.winning_party import WinningPartyWrite

DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"

# Mapping: table_name -> (WriteModel, set of DB-generated columns to exclude from Write)
TABLE_MODEL_MAP: dict[str, tuple[type, set[str]]] = {
    "contracting_party": (ContractingPartyWrite, {"id"}),
    "contract_folder_status": (ContractFolderStatusWrite, {"id", "created_at", "search_vector"}),
    "procurement_project_lot": (ProcurementProjectLotWrite, {"id"}),
    "cpv_classification": (CpvClassificationWrite, {"id"}),
    "realized_location": (RealizedLocationWrite, {"id"}),
    "tender_result": (TenderResultWrite, {"id"}),
    "winning_party": (WinningPartyWrite, {"id"}),
    "contract": (ContractWrite, {"id"}),
    "awarding_criteria": (AwardingCriteriaWrite, {"id"}),
    "financial_guarantee": (FinancialGuaranteeWrite, {"id"}),
    "qualification_requirement": (QualificationRequirementWrite, {"id"}),
    "business_classification": (BusinessClassificationWrite, {"id"}),
    "execution_condition": (ExecutionConditionWrite, {"id"}),
    "valid_notice_info": (ValidNoticeInfoWrite, {"id"}),
    "publication_status": (PublicationStatusWrite, {"id"}),
    "document_reference": (DocumentReferenceWrite, {"id"}),
    "contract_modification": (ContractModificationWrite, {"id"}),
    "status_change": (StatusChangeWrite, {"id", "recorded_at"}),
    "etl_sync_state": (EtlSyncStateWrite, {"id"}),
    "etl_failed_entries": (EtlFailedEntryWrite, {"id"}),
}


@pytest.fixture(scope="module")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def db_columns(event_loop: asyncio.AbstractEventLoop) -> dict[str, set[str]]:
    async def _fetch() -> dict[str, set[str]]:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            rows = await conn.fetch(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = ANY($1::text[])
                ORDER BY table_name, ordinal_position
                """,
                list(TABLE_MODEL_MAP.keys()),
            )
            result: dict[str, set[str]] = {}
            for row in rows:
                table = row["table_name"]
                col = row["column_name"]
                result.setdefault(table, set()).add(col)
            return result
        finally:
            await conn.close()

    return event_loop.run_until_complete(_fetch())


class TestSchemaDrift:
    @pytest.mark.parametrize("table_name", sorted(TABLE_MODEL_MAP.keys()))
    def test_model_fields_match_db_columns(
        self,
        table_name: str,
        db_columns: dict[str, set[str]],
    ) -> None:
        model_cls, generated_cols = TABLE_MODEL_MAP[table_name]
        model_fields = set(model_cls.model_fields.keys())
        db_cols = db_columns.get(table_name, set())

        # DB columns minus generated ones should equal model fields
        db_non_generated = db_cols - generated_cols

        missing_in_model = db_non_generated - model_fields
        extra_in_model = model_fields - db_non_generated

        assert not missing_in_model, (
            f"Table '{table_name}' has DB columns not in model: {missing_in_model}"
        )
        assert not extra_in_model, (
            f"Table '{table_name}' model has fields not in DB: {extra_in_model}"
        )
