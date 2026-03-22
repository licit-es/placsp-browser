from datetime import datetime

from pydantic import BaseModel

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
from shared.models.procurement_project_lot import ProcurementProjectLotWrite
from shared.models.publication_status import PublicationStatusWrite
from shared.models.qualification_requirement import QualificationRequirementWrite
from shared.models.realized_location import RealizedLocationWrite
from shared.models.status_change import StatusChangeWrite
from shared.models.tender_result import TenderResultWrite
from shared.models.valid_notice_info import ValidNoticeInfoWrite
from shared.models.winning_party import WinningPartyWrite


class EntryEnvelope(BaseModel):
    entry_id: str
    title: str | None = None
    summary: str | None = None
    link: str | None = None
    updated: datetime
    feed_type: str


class LotGroup(BaseModel):
    lot: ProcurementProjectLotWrite
    cpv_codes: list[CpvClassificationWrite]
    criteria: list[AwardingCriteriaWrite]
    requirements: list[QualificationRequirementWrite]
    locations: list[RealizedLocationWrite]


class ResultGroup(BaseModel):
    result: TenderResultWrite
    winning_parties: list[WinningPartyWrite]
    contract: ContractWrite | None = None


class PublicationStatusGroup(BaseModel):
    status: PublicationStatusWrite
    documents: list[DocumentReferenceWrite]


class NoticeGroup(BaseModel):
    notice: ValidNoticeInfoWrite
    statuses: list[PublicationStatusGroup]


class ParsedEntry(BaseModel):
    envelope: EntryEnvelope
    folder: ContractFolderStatusWrite
    contracting_party: ContractingPartyWrite
    lot_groups: list[LotGroup]
    result_groups: list[ResultGroup]
    cpv_folder: list[CpvClassificationWrite]
    criteria_folder: list[AwardingCriteriaWrite]
    guarantees: list[FinancialGuaranteeWrite]
    requirements_folder: list[QualificationRequirementWrite]
    classifications: list[BusinessClassificationWrite]
    conditions: list[ExecutionConditionWrite]
    direct_documents: list[DocumentReferenceWrite]
    notice_groups: list[NoticeGroup]
    modifications: list[ContractModificationWrite]
    status_changes: list[StatusChangeWrite]


class DeletedEntry(BaseModel):
    ref: str
    when: datetime | None = None


class ParseFailure(BaseModel):
    entry_id: str | None = None
    error_message: str


class ParsedPage(BaseModel):
    entries: list[ParsedEntry]
    deleted_entries: list[DeletedEntry]
    parse_failures: list[ParseFailure] = []
    next_link: str | None = None
