"""Tests for FeedReaderService with faked repositories."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
import respx
from lxml import etree

from shared.config import Settings
from shared.models.etl import EntryResult, EtlSyncStateRead
from shared.models.parsed_page import ParsedPage
from etl.parsers.page import PageParser
from etl.services.feed_reader import FeedReaderService
from tests.etl.builders.entities import build_deleted_entry, build_parsed_entry

_NOW = datetime.now(UTC)
_LATER = _NOW + timedelta(hours=1)
_FIXTURES = Path(__file__).parent.parent.parent / "fixtures"

_SETTINGS = Settings(
    database_url="postgresql://test:test@localhost/test",
    environment="test",
    feed_reader_max_concurrent_entries=10,
    http_max_retries=2,
    http_retry_delay=0.0,
)


# ------------------------------------------------------------------ Fakes
class FakeEntryRepo:
    def __init__(self, results: dict[str, str] | None = None):
        self._results = results or {}
        self.processed: list[str] = []

    async def process_entry(self, entry) -> EntryResult:
        eid = entry.envelope.entry_id
        self.processed.append(eid)
        status = self._results.get(eid, "ok")
        if status == "raise":
            msg = "DB connection lost"
            raise RuntimeError(msg)
        return EntryResult(status=status)


class FakeSyncRepo:
    def __init__(self, resume_url: str | None = None):
        self._resume_url = resume_url
        self.states: dict[str, EtlSyncStateRead] = {}
        self.updates: list[tuple] = []

    async def get_or_create(
        self, feed_type: str, year: int, page_url: str
    ) -> EtlSyncStateRead:
        key = f"{feed_type}:{year}:{page_url}"
        if key not in self.states:
            self.states[key] = EtlSyncStateRead(
                id=uuid.uuid4(),
                feed_type=feed_type,
                year=year,
                page_url=page_url,
                status="pending",
            )
        return self.states[key]

    async def update_status(
        self,
        sync_id: uuid.UUID,
        status: str,
        entry_count: int,
        error_count: int,
    ) -> None:
        self.updates.append((sync_id, status, entry_count, error_count))

    async def find_resume_point(self, _feed_type: str, _year: int) -> str | None:
        return self._resume_url


class FakeFailedRepo:
    def __init__(self):
        self.failures: list[dict] = []

    async def record_failure(
        self,
        feed_type: str,
        entry_id: str,
        _entry_updated,
        _page_url: str,
        error_type: str,
        error_message: str,
    ) -> None:
        self.failures.append(
            {
                "feed_type": feed_type,
                "entry_id": entry_id,
                "error_type": error_type,
                "error_message": error_message,
            }
        )

    async def mark_resolved(self, _feed_type: str, _entry_id: str) -> None:
        pass


class FakeParser:
    def __init__(self, pages: list[ParsedPage]):
        self._pages = iter(pages)

    def parse(self, _content: bytes, _feed_type: str) -> ParsedPage:
        return next(self._pages)


class _DummyTransport(httpx.AsyncBaseTransport):
    """Returns empty 200 for any request — content ignored by FakeParser."""

    async def handle_async_request(self, _request):
        return httpx.Response(200, content=b"<dummy/>")


# ------------------------------------------------------------ Helpers
def _make_service(
    entry_repo=None,
    sync_repo=None,
    failed_repo=None,
    parser=None,
    http_client=None,
    config=None,
):
    return FeedReaderService(
        entry_repo=entry_repo or FakeEntryRepo(),
        sync_repo=sync_repo or FakeSyncRepo(),
        failed_repo=failed_repo or FakeFailedRepo(),
        parser=parser or PageParser(),
        http_client=http_client or httpx.AsyncClient(transport=_DummyTransport()),
        config=config or _SETTINGS,
    )


def _page(
    n_entries: int = 0,
    n_deleted: int = 0,
    next_link: str | None = None,
    entry_ids: list[str] | None = None,
) -> ParsedPage:
    ids = entry_ids or [f"test://entry_{i}" for i in range(n_entries)]
    entries = []
    for eid in ids:
        e = build_parsed_entry()
        e.envelope.entry_id = eid
        entries.append(e)

    deleted = [build_deleted_entry() for _ in range(n_deleted)]
    return ParsedPage(
        entries=entries,
        deleted_entries=deleted,
        next_link=next_link,
    )


# ------------------------------------------------------------ Tests
class TestSinglePage:
    @pytest.mark.asyncio
    async def test_processes_entries(self) -> None:
        entry_repo = FakeEntryRepo()
        page = _page(n_entries=3)
        parser = FakeParser([page])

        svc = _make_service(
            entry_repo=entry_repo,
            parser=parser,
        )
        result = await svc.sync(
            "outsiders",
            start_url="https://example.com/feed",
        )
        assert result.processed == 3
        assert result.pages == 1
        assert len(entry_repo.processed) == 3

    @pytest.mark.asyncio
    async def test_no_entries(self) -> None:
        page = _page(n_entries=0)
        parser = FakeParser([page])

        svc = _make_service(parser=parser)
        result = await svc.sync(
            "outsiders",
            start_url="https://example.com/feed",
        )
        assert result.processed == 0
        assert result.pages == 1


class TestDeletedEntries:
    @pytest.mark.asyncio
    async def test_deleted_entries_not_processed(self) -> None:
        entry_repo = FakeEntryRepo()
        page = _page(n_entries=0, n_deleted=3)
        parser = FakeParser([page])

        svc = _make_service(
            entry_repo=entry_repo,
            parser=parser,
        )
        result = await svc.sync(
            "outsiders",
            start_url="https://example.com/feed",
        )
        assert result.processed == 0
        assert len(entry_repo.processed) == 0
        assert result.pages == 1


class TestStaleEntries:
    @pytest.mark.asyncio
    async def test_stale_counted_separately(self) -> None:
        page = _page(entry_ids=["test://ok", "test://stale"])
        entry_repo = FakeEntryRepo(results={"test://stale": "stale"})
        parser = FakeParser([page])
        failed_repo = FakeFailedRepo()

        svc = _make_service(
            entry_repo=entry_repo,
            parser=parser,
            failed_repo=failed_repo,
        )
        result = await svc.sync(
            "outsiders",
            start_url="https://example.com/feed",
        )
        assert result.processed == 1
        assert result.skipped_stale == 1
        assert result.failed == 0
        assert len(failed_repo.failures) == 0


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_persist_error_recorded(self) -> None:
        page = _page(entry_ids=["test://fail"])
        entry_repo = FakeEntryRepo(results={"test://fail": "raise"})
        failed_repo = FakeFailedRepo()
        parser = FakeParser([page])

        svc = _make_service(
            entry_repo=entry_repo,
            parser=parser,
            failed_repo=failed_repo,
        )
        result = await svc.sync(
            "outsiders",
            start_url="https://example.com/feed",
        )
        assert result.failed == 1
        assert result.processed == 0
        assert len(failed_repo.failures) == 1
        assert failed_repo.failures[0]["error_type"] == "persist_error"

    @pytest.mark.asyncio
    async def test_mixed_results(self) -> None:
        page = _page(
            entry_ids=[
                "test://ok1",
                "test://stale1",
                "test://err1",
            ]
        )
        entry_repo = FakeEntryRepo(
            results={
                "test://stale1": "stale",
                "test://err1": "raise",
            }
        )
        failed_repo = FakeFailedRepo()
        parser = FakeParser([page])

        svc = _make_service(
            entry_repo=entry_repo,
            parser=parser,
            failed_repo=failed_repo,
        )
        result = await svc.sync(
            "outsiders",
            start_url="https://example.com/feed",
        )
        assert result.processed == 1
        assert result.skipped_stale == 1
        assert result.failed == 1


class TestPagination:
    @pytest.mark.asyncio
    async def test_follows_next_link(self) -> None:
        page1 = _page(
            n_entries=2,
            next_link="https://example.com/feed?page=2",
        )
        page2 = _page(n_entries=1)
        entry_repo = FakeEntryRepo()
        parser = FakeParser([page1, page2])

        svc = _make_service(
            entry_repo=entry_repo,
            parser=parser,
        )
        result = await svc.sync(
            "outsiders",
            start_url="https://example.com/feed",
        )
        assert result.pages == 2
        assert result.processed == 3


class TestEndDateFilter:
    @pytest.mark.asyncio
    async def test_filters_by_end_date(self) -> None:
        entries = []
        for i, ts in enumerate([_NOW, _LATER]):
            e = build_parsed_entry()
            e.envelope.entry_id = f"test://e{i}"
            e.envelope.updated = ts
            entries.append(e)

        page = ParsedPage(
            entries=entries,
            deleted_entries=[],
            next_link=None,
        )
        entry_repo = FakeEntryRepo()
        parser = FakeParser([page])

        cutoff = _NOW + timedelta(minutes=30)
        svc = _make_service(
            entry_repo=entry_repo,
            parser=parser,
        )
        result = await svc.sync(
            "outsiders",
            start_url="https://example.com/feed",
            end_date=cutoff,
        )
        assert result.processed == 1
        assert len(entry_repo.processed) == 1


class TestResumePoint:
    @pytest.mark.asyncio
    async def test_uses_resume_url(self) -> None:
        page = _page(n_entries=1)
        sync_repo = FakeSyncRepo(resume_url="https://example.com/feed?page=5")
        parser = FakeParser([page])

        svc = _make_service(
            sync_repo=sync_repo,
            parser=parser,
        )
        result = await svc.sync("outsiders")
        assert result.pages == 1
        key = "outsiders:0:https://example.com/feed?page=5"
        assert key in sync_repo.states


class TestSyncStateUpdates:
    @pytest.mark.asyncio
    async def test_marks_in_progress_then_completed(
        self,
    ) -> None:
        page = _page(n_entries=2)
        sync_repo = FakeSyncRepo()
        parser = FakeParser([page])

        svc = _make_service(
            sync_repo=sync_repo,
            parser=parser,
        )
        await svc.sync(
            "outsiders",
            start_url="https://example.com/feed",
        )
        statuses = [u[1] for u in sync_repo.updates]
        assert statuses == ["in_progress", "completed"]


class TestHttpFetch:
    @pytest.mark.asyncio
    @respx.mock
    async def test_fetches_real_page(self) -> None:
        xml_bytes = (_FIXTURES / "minimal_entry.xml").read_bytes()
        url = "https://example.com/feed"

        respx.get(url).respond(200, content=xml_bytes)

        async with httpx.AsyncClient() as client:
            svc = _make_service(
                http_client=client,
                parser=PageParser(),
            )
            result = await svc.sync(
                "insiders",
                start_url=url,
            )
        assert result.pages == 1
        assert result.processed == 1


class TestFallbackToBaseUrl:
    """When no start_url and no resume point, uses the feed base URL."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_resolves_default_outsiders_url(self) -> None:
        xml_bytes = (_FIXTURES / "minimal_entry.xml").read_bytes()
        base = (
            "https://contrataciondelsectorpublico.gob.es"
            "/sindicacion/sindicacion_1044"
            "/PlataformasAgregadasSinMenores.atom"
        )
        respx.get(base).respond(200, content=xml_bytes)

        async with httpx.AsyncClient() as client:
            svc = _make_service(
                http_client=client,
                sync_repo=FakeSyncRepo(resume_url=None),
                parser=PageParser(),
            )
            result = await svc.sync("outsiders")

        assert result.pages == 1


class TestHttpRetryExhausted:
    """After exhausting retries, _fetch_page raises httpx.HTTPError."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_raises_after_max_retries(self) -> None:
        url = "https://example.com/feed"
        respx.get(url).mock(side_effect=httpx.TimeoutException("timed out"))

        async with httpx.AsyncClient() as client:
            svc = _make_service(
                http_client=client,
                parser=FakeParser([]),
            )
            with pytest.raises(httpx.HTTPError, match="Failed to fetch"):
                await svc.sync("outsiders", start_url=url)


class TestNonOkStatusRecordsFailure:
    """Entry status not in (ok, stale) is recorded as a failure."""

    @pytest.mark.asyncio
    async def test_constraint_error_recorded(self) -> None:
        page = _page(entry_ids=["test://constraint"])
        entry_repo = FakeEntryRepo(results={"test://constraint": "constraint_error"})
        failed_repo = FakeFailedRepo()
        parser = FakeParser([page])

        svc = _make_service(
            entry_repo=entry_repo,
            parser=parser,
            failed_repo=failed_repo,
        )
        result = await svc.sync("outsiders", start_url="https://example.com/feed")

        assert result.failed == 1
        assert len(failed_repo.failures) == 1
        assert failed_repo.failures[0]["error_type"] == "constraint_error"


class TestSyncExceptionPropagation:
    """Exception from _sync_loop is logged and re-raised."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_exception_propagates(self) -> None:
        url = "https://example.com/feed"
        respx.get(url).respond(200, content=b"<invalid")

        async with httpx.AsyncClient() as client:
            svc = _make_service(
                http_client=client,
                parser=PageParser(),
            )
            with pytest.raises(etree.XMLSyntaxError):
                await svc.sync("outsiders", start_url=url)
