"""Repository protocol definitions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Protocol

from shared.models.etl import EntryResult, EtlSyncStateRead
from shared.models.parsed_page import ParsedEntry


class EntryRepository(Protocol):
    async def process_entry(
        self,
        entry: ParsedEntry,
    ) -> EntryResult: ...


class SyncStateRepository(Protocol):
    async def get_or_create(
        self,
        feed_type: str,
        year: int,
        page_url: str,
    ) -> EtlSyncStateRead: ...

    async def update_status(
        self,
        sync_id: uuid.UUID,
        status: str,
        entry_count: int,
        error_count: int,
    ) -> None: ...

    async def find_resume_point(
        self,
        feed_type: str,
        year: int,
    ) -> str | None: ...


class FailedEntryRepository(Protocol):
    async def record_failure(
        self,
        feed_type: str,
        entry_id: str,
        entry_updated: datetime | None,
        page_url: str,
        error_type: str,
        error_message: str,
    ) -> None: ...

    async def mark_resolved(
        self,
        feed_type: str,
        entry_id: str,
    ) -> None: ...


class CatalogRepository(Protocol):
    async def get_pending_codes(
        self,
        table: str,
    ) -> list[str]: ...

    async def activate_codes(
        self,
        table: str,
        codes: dict[str, str],
    ) -> int: ...

    async def ensure_code(
        self,
        table: str,
        code: str,
    ) -> None: ...
