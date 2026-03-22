"""Typed test builders per domain entity with CODICE-valid defaults.

Each builder returns a Write model with sensible defaults, so tests only
specify the fields they care about.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from shared.models.awarding_criteria import AwardingCriteriaWrite
from shared.models.business_classification import BusinessClassificationWrite
from shared.models.contract import ContractWrite
from shared.models.contract_folder_status import ContractFolderStatusWrite
from shared.models.contract_modification import ContractModificationWrite
from shared.models.contracting_party import ContractingPartyWrite
from shared.models.cpv_classification import CpvClassificationWrite
from shared.models.document_reference import DocumentReferenceWrite
from shared.models.execution_condition import ExecutionConditionWrite
from shared.models.financial_guarantee import FinancialGuaranteeWrite
from shared.models.parsed_page import (
    DeletedEntry,
    EntryEnvelope,
    LotGroup,
    NoticeGroup,
    ParsedEntry,
    PublicationStatusGroup,
    ResultGroup,
)
from shared.models.procurement_project_lot import ProcurementProjectLotWrite
from shared.models.publication_status import PublicationStatusWrite
from shared.models.qualification_requirement import QualificationRequirementWrite
from shared.models.realized_location import RealizedLocationWrite
from shared.models.status_change import StatusChangeWrite
from shared.models.tender_result import TenderResultWrite
from shared.models.valid_notice_info import ValidNoticeInfoWrite
from shared.models.winning_party import WinningPartyWrite


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(UTC)


def build_contracting_party(**overrides: Any) -> ContractingPartyWrite:
    defaults: dict[str, Any] = {
        "name": "Ayuntamiento de Test",
        "dir3": "EA0003089",
        "nif": "S2800011H",
        "platform_id": "PLAT001",
    }
    defaults.update(overrides)
    return ContractingPartyWrite(**defaults)


def build_contract_folder_status(**overrides: Any) -> ContractFolderStatusWrite:
    defaults: dict[str, Any] = {
        "entry_id": f"https://example.com/entry_{_uuid().hex[:8]}",
        "title": "Expediente de prueba",
        "summary": "Resumen del expediente",
        "link": "https://example.com/detail",
        "updated": _now(),
        "feed_type": "outsiders",
        "contract_folder_id": "2024/001",
        "status_code": "PUB",
        "name": "Servicio de prueba",
        "type_code": "2",
        "procedure_code": "1",
    }
    defaults.update(overrides)
    return ContractFolderStatusWrite(**defaults)


def build_procurement_project_lot(**overrides: Any) -> ProcurementProjectLotWrite:
    defaults: dict[str, Any] = {
        "contract_folder_status_id": _uuid(),
        "lot_number": "1",
        "name": "Lote 1",
        "total_amount": Decimal("100000.00"),
        "tax_exclusive_amount": Decimal("82644.63"),
        "currency_id": "EUR",
    }
    defaults.update(overrides)
    return ProcurementProjectLotWrite(**defaults)


def build_cpv_classification(**overrides: Any) -> CpvClassificationWrite:
    defaults: dict[str, Any] = {
        "contract_folder_status_id": _uuid(),
        "item_classification_code": "30200000",
    }
    defaults.update(overrides)
    return CpvClassificationWrite(**defaults)


def build_realized_location(**overrides: Any) -> RealizedLocationWrite:
    defaults: dict[str, Any] = {
        "lot_id": _uuid(),
        "nuts_code": "ES300",
        "country_subentity": "Madrid",
    }
    defaults.update(overrides)
    return RealizedLocationWrite(**defaults)


def build_tender_result(**overrides: Any) -> TenderResultWrite:
    defaults: dict[str, Any] = {
        "contract_folder_status_id": _uuid(),
        "result_code": "8",
        "award_date": "2024-08-01",
        "received_tender_quantity": 5,
    }
    defaults.update(overrides)
    return TenderResultWrite(**defaults)


def build_winning_party(**overrides: Any) -> WinningPartyWrite:
    defaults: dict[str, Any] = {
        "tender_result_id": _uuid(),
        "name": "TechCorp S.L.",
        "identifier": "B12345678",
        "identifier_scheme": "NIF",
    }
    defaults.update(overrides)
    return WinningPartyWrite(**defaults)


def build_contract(**overrides: Any) -> ContractWrite:
    defaults: dict[str, Any] = {
        "tender_result_id": _uuid(),
        "contract_number": "CTR-2024-001",
        "issue_date": "2024-09-01",
    }
    defaults.update(overrides)
    return ContractWrite(**defaults)


def build_awarding_criteria(**overrides: Any) -> AwardingCriteriaWrite:
    defaults: dict[str, Any] = {
        "contract_folder_status_id": _uuid(),
        "criteria_type_code": "OBJ",
        "criteria_sub_type_code": "1",
        "description": "Precio",
        "weight_numeric": Decimal("60"),
    }
    defaults.update(overrides)
    return AwardingCriteriaWrite(**defaults)


def build_financial_guarantee(**overrides: Any) -> FinancialGuaranteeWrite:
    defaults: dict[str, Any] = {
        "contract_folder_status_id": _uuid(),
        "guarantee_type_code": "1",
        "amount_rate": Decimal("5"),
        "liability_amount": Decimal("7500.00"),
        "currency_id": "EUR",
    }
    defaults.update(overrides)
    return FinancialGuaranteeWrite(**defaults)


def build_qualification_requirement(**overrides: Any) -> QualificationRequirementWrite:
    defaults: dict[str, Any] = {
        "contract_folder_status_id": _uuid(),
        "origin_type": "TECHNICAL",
        "evaluation_criteria_type_code": "1",
        "description": "Experiencia en el sector",
    }
    defaults.update(overrides)
    return QualificationRequirementWrite(**defaults)


def build_business_classification(**overrides: Any) -> BusinessClassificationWrite:
    defaults: dict[str, Any] = {
        "contract_folder_status_id": _uuid(),
        "code_value": "C3-1",
    }
    defaults.update(overrides)
    return BusinessClassificationWrite(**defaults)


def build_execution_condition(**overrides: Any) -> ExecutionConditionWrite:
    defaults: dict[str, Any] = {
        "contract_folder_status_id": _uuid(),
        "name": "Condición medioambiental",
        "execution_requirement_code": "3",
        "description": "Cumplimiento normativa medioambiental",
    }
    defaults.update(overrides)
    return ExecutionConditionWrite(**defaults)


def build_document_reference(**overrides: Any) -> DocumentReferenceWrite:
    defaults: dict[str, Any] = {
        "contract_folder_status_id": _uuid(),
        "source_type": "LEGAL",
        "filename": "pliego.pdf",
        "uri": "https://example.com/pliego.pdf",
    }
    defaults.update(overrides)
    return DocumentReferenceWrite(**defaults)


def build_valid_notice_info(**overrides: Any) -> ValidNoticeInfoWrite:
    defaults: dict[str, Any] = {
        "contract_folder_status_id": _uuid(),
        "notice_type_code": "DOC_CN",
        "notice_issue_date": "2024-06-01",
    }
    defaults.update(overrides)
    return ValidNoticeInfoWrite(**defaults)


def build_publication_status(**overrides: Any) -> PublicationStatusWrite:
    defaults: dict[str, Any] = {
        "valid_notice_info_id": _uuid(),
        "publication_media_name": "Perfil del Contratante",
    }
    defaults.update(overrides)
    return PublicationStatusWrite(**defaults)


def build_contract_modification(**overrides: Any) -> ContractModificationWrite:
    defaults: dict[str, Any] = {
        "contract_folder_status_id": _uuid(),
        "modification_number": "MOD-001",
        "contract_id": "CTR-2024-001",
        "note": "Ampliación de plazo",
    }
    defaults.update(overrides)
    return ContractModificationWrite(**defaults)


def build_status_change(**overrides: Any) -> StatusChangeWrite:
    defaults: dict[str, Any] = {
        "contract_folder_status_id": _uuid(),
        "status_code": "PUB",
        "updated": _now(),
    }
    defaults.update(overrides)
    return StatusChangeWrite(**defaults)


def build_entry_envelope(**overrides: Any) -> EntryEnvelope:
    defaults: dict[str, Any] = {
        "entry_id": f"https://example.com/entry_{_uuid().hex[:8]}",
        "title": "Expediente test",
        "summary": "Resumen",
        "link": "https://example.com/detail",
        "updated": _now(),
        "feed_type": "outsiders",
    }
    defaults.update(overrides)
    return EntryEnvelope(**defaults)


def build_deleted_entry(**overrides: Any) -> DeletedEntry:
    defaults: dict[str, Any] = {
        "ref": f"https://example.com/entry_deleted_{_uuid().hex[:8]}",
        "when": _now(),
    }
    defaults.update(overrides)
    return DeletedEntry(**defaults)


def build_lot_group(**overrides: Any) -> LotGroup:
    defaults: dict[str, Any] = {
        "lot": build_procurement_project_lot(),
        "cpv_codes": [],
        "criteria": [],
        "requirements": [],
        "locations": [],
    }
    defaults.update(overrides)
    return LotGroup(**defaults)


def build_result_group(**overrides: Any) -> ResultGroup:
    defaults: dict[str, Any] = {
        "result": build_tender_result(),
        "winning_parties": [],
        "contract": None,
    }
    defaults.update(overrides)
    return ResultGroup(**defaults)


def build_publication_status_group(
    **overrides: Any,
) -> PublicationStatusGroup:
    defaults: dict[str, Any] = {
        "status": build_publication_status(),
        "documents": [],
    }
    defaults.update(overrides)
    return PublicationStatusGroup(**defaults)


def build_notice_group(**overrides: Any) -> NoticeGroup:
    defaults: dict[str, Any] = {
        "notice": build_valid_notice_info(),
        "statuses": [],
    }
    defaults.update(overrides)
    return NoticeGroup(**defaults)


def build_parsed_entry(**overrides: Any) -> ParsedEntry:
    folder_id = _uuid()
    envelope = build_entry_envelope()
    folder = build_contract_folder_status(
        entry_id=envelope.entry_id,
        updated=envelope.updated,
        feed_type=envelope.feed_type,
    )
    defaults: dict[str, Any] = {
        "envelope": envelope,
        "folder": folder,
        "contracting_party": build_contracting_party(),
        "lot_groups": [],
        "result_groups": [],
        "cpv_folder": [
            build_cpv_classification(
                contract_folder_status_id=folder_id,
            )
        ],
        "criteria_folder": [],
        "guarantees": [],
        "requirements_folder": [],
        "classifications": [],
        "conditions": [],
        "direct_documents": [],
        "notice_groups": [],
        "modifications": [],
        "status_changes": [],
    }
    defaults.update(overrides)
    return ParsedEntry(**defaults)
