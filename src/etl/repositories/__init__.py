"""ETL repository implementations and protocols."""

from etl.repositories.catalog_repo import PgCatalogRepository
from etl.repositories.entry_repo import PgEntryRepository
from etl.repositories.failed_entry_repo import PgFailedEntryRepository
from etl.repositories.protocols import (
    CatalogRepository,
    EntryRepository,
    FailedEntryRepository,
    SyncStateRepository,
)
from etl.repositories.sync_state_repo import PgSyncStateRepository

__all__ = [
    "CatalogRepository",
    "EntryRepository",
    "FailedEntryRepository",
    "PgCatalogRepository",
    "PgEntryRepository",
    "PgFailedEntryRepository",
    "PgSyncStateRepository",
    "SyncStateRepository",
]
