from enum import StrEnum


class StatusCode(StrEnum):
    """SyndicationContractFolderStatusCode -- contract_folder_status.status_code"""

    ADJ = "ADJ"
    ANUL = "ANUL"
    BORR = "BORR"
    CERR = "CERR"
    EV = "EV"
    PRE = "PRE"
    PUB = "PUB"
    RES = "RES"


class TypeCode(StrEnum):
    """ContractCode -- contract_folder_status.type_code"""

    SUPPLIES = "1"
    SERVICES = "2"
    WORKS = "3"
    PUBLIC_WORKS_CONCESSION = "7"
    SERVICE_CONCESSION = "8"
    COLLABORATION = "21"
    SPECIAL = "22"
    PATRIMONIAL = "50"


class ProcedureCode(StrEnum):
    """SyndicationTenderingProcessCode -- contract_folder_status.procedure_code"""

    OPEN = "1"
    RESTRICTED = "2"
    NEGOTIATED_WITH_PUBLICITY = "3"
    NEGOTIATED_WITHOUT_PUBLICITY = "4"
    COMPETITIVE_DIALOGUE = "7"
    INNOVATION_PARTNERSHIP = "9"
    BASED_ON_FRAMEWORK = "100"
    OTHER = "999"


class ResultCode(StrEnum):
    """TenderResultCode -- tender_result.result_code"""

    PROVISIONAL_AWARD = "2"
    DESERTED = "3"
    ANNULLED = "4"
    WAIVED = "5"
    DEFINITIVE_AWARD = "8"
    FORMALIZED = "9"
    PARTIALLY_AWARDED = "10"


class SourceType(StrEnum):
    """document_reference.source_type"""

    LEGAL = "LEGAL"
    TECHNICAL = "TECHNICAL"
    ADDITIONAL = "ADDITIONAL"
    GENERAL = "GENERAL"
    PUBLICATION = "PUBLICATION"


class FeedType(StrEnum):
    """etl_sync_state.feed_type / contract_folder_status.feed_type"""

    OUTSIDERS = "outsiders"
    INSIDERS = "insiders"


ROOT_FILENAMES: dict[str, str] = {
    FeedType.OUTSIDERS: "PlataformasAgregadasSinMenores.atom",
    FeedType.INSIDERS: "licitacionesPerfilesContratanteCompleto3.atom",
}


class ErrorType(StrEnum):
    """etl_failed_entries.error_type"""

    PARSE_ERROR = "parse_error"
    PERSIST_ERROR = "persist_error"
    CONSTRAINT_ERROR = "constraint_error"


class SyncStatus(StrEnum):
    """etl_sync_state.status"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class EntryResultStatus(StrEnum):
    """EntryResult.status"""

    OK = "ok"
    STALE = "stale"
    PARSE_ERROR = "parse_error"
    PERSIST_ERROR = "persist_error"
    CONSTRAINT_ERROR = "constraint_error"


class QualificationOriginType(StrEnum):
    """qualification_requirement.origin_type"""

    TECHNICAL = "TECHNICAL"
    FINANCIAL = "FINANCIAL"
    DECLARATION = "DECLARATION"
