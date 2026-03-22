import uuid

from pydantic import BaseModel


class DocumentReferenceWrite(BaseModel):
    contract_folder_status_id: uuid.UUID
    publication_status_id: uuid.UUID | None = None
    source_type: str
    filename: str | None = None
    uri: str | None = None
    document_hash: str | None = None
    document_type_code: str | None = None


class DocumentReferenceRead(DocumentReferenceWrite):
    id: uuid.UUID
