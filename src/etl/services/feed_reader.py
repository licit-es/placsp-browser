"""FeedReaderService — orchestrates ATOM feed pagination and entry processing."""

from __future__ import annotations

import asyncio
from datetime import datetime

import httpx

from etl.parsers.page import PageParser
from etl.repositories.protocols import (
    EntryRepository,
    FailedEntryRepository,
    SyncStateRepository,
)
from shared.config import Settings
from shared.logger import get_logger
from shared.models.etl import EntryResult, SyncResult
from shared.models.parsed_page import ParsedEntry, ParsedPage

logger = get_logger(__name__)

_FEED_BASE_URLS: dict[str, str] = {
    "outsiders": (
        "https://contrataciondelsectorpublico.gob.es"
        "/sindicacion/sindicacion_1044"
        "/PlataformasAgregadasSinMenores.atom"
    ),
    "insiders": (
        "https://contrataciondelsectorpublico.gob.es"
        "/sindicacion/sindicacion_643"
        "/licitacionesPerfilesContratanteCompleto3.atom"
    ),
}


class FeedReaderService:
    def __init__(
        self,
        entry_repo: EntryRepository,
        sync_repo: SyncStateRepository,
        failed_repo: FailedEntryRepository,
        parser: PageParser,
        http_client: httpx.AsyncClient,
        config: Settings,
    ) -> None:
        self._entry_repo = entry_repo
        self._sync_repo = sync_repo
        self._failed_repo = failed_repo
        self._parser = parser
        self._http = http_client
        self._config = config
        self._semaphore = asyncio.Semaphore(
            config.feed_reader_max_concurrent_entries,
        )

    async def sync(
        self,
        feed_type: str,
        year: int = 0,
        start_url: str | None = None,
        end_date: datetime | None = None,
        *,
        skip_stale_check: bool = False,
    ) -> SyncResult:
        logger.info("Sync start feed_type=%s year=%d", feed_type, year)
        try:
            return await self._sync_loop(
                feed_type, year, start_url, end_date, skip_stale_check
            )
        except Exception:
            logger.error(
                "Sync failed feed_type=%s year=%d", feed_type, year, exc_info=True
            )
            raise

    async def _sync_loop(
        self,
        feed_type: str,
        year: int,
        start_url: str | None,
        end_date: datetime | None,
        skip_stale_check: bool = False,
    ) -> SyncResult:
        url: str | None = await self._resolve_start_url(feed_type, year, start_url)

        processed = 0
        skipped_stale = 0
        failed = 0
        pages = 0
        consecutive_stale_pages = 0
        max_stale_pages = 0 if skip_stale_check else 3

        while url:
            logger.info("Page fetch url=%s", url)
            content = await self._fetch_page(url)
            page = self._parser.parse(content, feed_type)

            entries = self._filter_entries(page, end_date)

            sync_state = await self._sync_repo.get_or_create(feed_type, year, url)
            await self._sync_repo.update_status(sync_state.id, "in_progress", 0, 0)

            for pf in page.parse_failures:
                await self._failed_repo.record_failure(
                    feed_type,
                    pf.entry_id or f"unknown:{url}",
                    None,
                    url,
                    "parse_error",
                    pf.error_message,
                )
            failed += len(page.parse_failures)

            page_ok, page_stale, page_failed = await self._process_entries(
                entries, feed_type, url
            )
            processed += page_ok
            skipped_stale += page_stale
            failed += page_failed

            for deleted in page.deleted_entries:
                logger.debug(
                    "Deleted entry ref=%s when=%s",
                    deleted.ref,
                    deleted.when,
                )

            logger.info(
                "Page summary entries=%d parse_failed=%d"
                " deleted=%d ok=%d stale=%d failed=%d",
                len(entries),
                len(page.parse_failures),
                len(page.deleted_entries),
                page_ok,
                page_stale,
                page_failed,
            )

            await self._sync_repo.update_status(
                sync_state.id,
                "completed",
                page_ok + page_stale,
                page_failed,
            )
            pages += 1

            if page_ok > 0:
                consecutive_stale_pages = 0
            else:
                consecutive_stale_pages += 1

            if not page.next_link:
                logger.info("Pagination stop reason=no_next_link")
                url = None
            elif max_stale_pages and consecutive_stale_pages >= max_stale_pages:
                logger.info(
                    "Pagination stop reason=all_stale consecutive_pages=%d",
                    consecutive_stale_pages,
                )
                url = None
            else:
                url = page.next_link

        logger.info(
            "Sync end feed_type=%s year=%d processed=%d failed=%d pages=%d",
            feed_type,
            year,
            processed,
            failed,
            pages,
        )
        return SyncResult(
            processed=processed,
            skipped_stale=skipped_stale,
            failed=failed,
            pages=pages,
        )

    async def _resolve_start_url(
        self,
        feed_type: str,
        year: int,
        start_url: str | None,
    ) -> str:
        if start_url:
            return start_url
        resume = await self._sync_repo.find_resume_point(feed_type, year)
        if resume:
            logger.info(
                "Sync resume feed_type=%s year=%d cursor_url=%s",
                feed_type,
                year,
                resume,
            )
            return resume
        return _FEED_BASE_URLS[feed_type]

    async def _fetch_page(self, url: str) -> bytes:
        last_err: Exception | None = None
        for attempt in range(self._config.http_max_retries):
            try:
                resp = await self._http.get(
                    url,
                    timeout=self._config.http_timeout,
                )
                resp.raise_for_status()
            except (httpx.HTTPError, httpx.TimeoutException) as exc:
                last_err = exc
                logger.warning(
                    "HTTP attempt %d/%d failed for %s: %s",
                    attempt + 1,
                    self._config.http_max_retries,
                    url,
                    exc,
                )
                if attempt < self._config.http_max_retries - 1:
                    await asyncio.sleep(self._config.http_retry_delay * (attempt + 1))
            else:
                return resp.content
        msg = f"Failed to fetch {url} after {self._config.http_max_retries} attempts"
        raise httpx.HTTPError(msg) from last_err

    def _filter_entries(
        self, page: ParsedPage, end_date: datetime | None
    ) -> list[ParsedEntry]:
        if end_date is None:
            return list(page.entries)
        return [e for e in page.entries if e.envelope.updated < end_date]

    async def _process_entries(
        self,
        entries: list[ParsedEntry],
        feed_type: str,
        page_url: str,
    ) -> tuple[int, int, int]:
        ok = 0
        stale = 0
        failed = 0

        async def _handle(entry: ParsedEntry) -> EntryResult:
            async with self._semaphore:
                return await self._process_one(entry, feed_type, page_url)

        results = await asyncio.gather(
            *[_handle(e) for e in entries],
            return_exceptions=True,
        )

        for entry, r in zip(entries, results, strict=True):
            if isinstance(r, BaseException):
                failed += 1
                try:
                    await self._failed_repo.record_failure(
                        feed_type,
                        entry.envelope.entry_id,
                        entry.envelope.updated,
                        page_url,
                        "unexpected_error",
                        str(r),
                    )
                except Exception:
                    logger.warning(
                        "Could not record failure entry_id=%s",
                        entry.envelope.entry_id,
                        exc_info=True,
                    )
            elif r.status == "ok":
                ok += 1
            elif r.status == "stale":
                stale += 1
            else:
                failed += 1

        return ok, stale, failed

    async def _process_one(
        self,
        entry: ParsedEntry,
        feed_type: str,
        page_url: str,
    ) -> EntryResult:
        try:
            result = await self._entry_repo.process_entry(entry)
        except Exception as exc:
            logger.warning(
                "Entry upsert failed entry_id=%s error=%s",
                entry.envelope.entry_id,
                exc,
                exc_info=True,
            )
            await self._failed_repo.record_failure(
                feed_type,
                entry.envelope.entry_id,
                entry.envelope.updated,
                page_url,
                "persist_error",
                str(exc),
            )
            return EntryResult(status="persist_error")

        if result.status == "stale":
            logger.debug("Stale entry: %s", entry.envelope.entry_id)
        elif result.status not in ("ok", "stale"):
            logger.warning(
                "Entry processing failed entry_id=%s status=%s",
                entry.envelope.entry_id,
                result.status,
            )
            await self._failed_repo.record_failure(
                feed_type,
                entry.envelope.entry_id,
                entry.envelope.updated,
                page_url,
                result.status,
                f"Entry processing returned {result.status}",
            )

        return result
