import uuid
from datetime import datetime

from pydantic import BaseModel


class EtlSyncStateWrite(BaseModel):
    feed_type: str
    year: int = 0
    page_url: str
    status: str
    entry_count: int | None = None
    error_count: int | None = None
    processed_at: datetime | None = None


class EtlSyncStateRead(EtlSyncStateWrite):
    id: uuid.UUID


class EtlFailedEntryWrite(BaseModel):
    feed_type: str
    entry_id: str
    entry_updated: datetime | None = None
    page_url: str | None = None
    error_type: str
    error_message: str
    first_failed_at: datetime
    last_failed_at: datetime
    retry_count: int = 1
    resolved_at: datetime | None = None


class EtlFailedEntryRead(EtlFailedEntryWrite):
    id: uuid.UUID


class EntryResult(BaseModel):
    status: str


class SyncResult(BaseModel):
    processed: int
    skipped_stale: int
    failed: int
    pages: int


class CatalogUpdateResult(BaseModel):
    tables_checked: int
    pending_found: int
    updated: int
    not_found: int
