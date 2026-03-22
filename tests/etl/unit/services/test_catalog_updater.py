"""Tests for CatalogUpdaterService with faked dependencies."""

from __future__ import annotations

import httpx
import pytest
import respx

from shared.config import Settings
from etl.services.catalog_updater import (
    CatalogUpdaterService,
    _extract_gc_links,
    _parse_genericode,
)

_SETTINGS = Settings(
    database_url="postgresql://test:test@localhost/test",
    environment="test",
    s3_bucket_documents="test-bucket",
    scraper_batch_size=10,
    scraper_max_concurrent=5,
    http_timeout=5.0,
)

_ROOT_URL = "https://example.com/codice/cl/"

_DIRECTORY_HTML = """
<html><body>
<a href="SyndicationContractFolderStatusCode-2.3.gc">Status</a>
<a href="TenderResultCode-2.3.gc">Results</a>
</body></html>
"""

_GC_NS = "http://docs.oasis-open.org/codelist/ns/genericode/1.0/"

_GC_XML = f"""\
<?xml version="1.0" encoding="UTF-8"?>
<gc:CodeList xmlns:gc="{_GC_NS}">
  <gc:SimpleCodeList>
    <gc:Row>
      <gc:Value ColumnRef="code"><gc:SimpleValue>RES</gc:SimpleValue></gc:Value>
      <gc:Value ColumnRef="name"><gc:SimpleValue>Resolved</gc:SimpleValue></gc:Value>
    </gc:Row>
    <gc:Row>
      <gc:Value ColumnRef="code"><gc:SimpleValue>PND</gc:SimpleValue></gc:Value>
      <gc:Value ColumnRef="name"><gc:SimpleValue>Pending</gc:SimpleValue></gc:Value>
    </gc:Row>
  </gc:SimpleCodeList>
</gc:CodeList>
""".encode()


# ------------------------------------------------------------------ Fakes
class FakeCatalogRepo:
    def __init__(self, pending: dict[str, list[str]] | None = None):
        self._pending = pending or {}
        self.activated: list[dict] = []

    async def get_pending_codes(self, table: str) -> list[str]:
        return self._pending.get(table, [])

    async def activate_codes(self, table: str, codes: dict[str, str]) -> int:
        self.activated.append({"table": table, "codes": codes})
        return len(codes)

    async def ensure_code(self, table: str, code: str) -> None:
        pass


def _make_service(catalog_repo=None, http_client=None, config=None):
    return CatalogUpdaterService(
        catalog_repo=catalog_repo or FakeCatalogRepo(),
        http_client=http_client or httpx.AsyncClient(),
        config=config or _SETTINGS,
    )


# ------------------------------------------------------------ Unit: helpers
class TestParseGenericode:
    def test_parses_rows(self) -> None:
        codes = _parse_genericode(_GC_XML)
        assert codes == {"RES": "Resolved", "PND": "Pending"}

    def test_empty_xml(self) -> None:
        xml = f'<gc:CodeList xmlns:gc="{_GC_NS}"></gc:CodeList>'.encode()
        assert _parse_genericode(xml) == {}


class TestExtractGcLinks:
    def test_extracts_gc_hrefs(self) -> None:
        links = _extract_gc_links(_DIRECTORY_HTML)
        assert len(links) == 2
        assert "SyndicationContractFolderStatusCode-2.3.gc" in links
        assert "TenderResultCode-2.3.gc" in links

    def test_no_links(self) -> None:
        assert _extract_gc_links("<html></html>") == []


# ----------------------------------------------------- Integration: service
class TestNoPending:
    @pytest.mark.asyncio
    async def test_returns_early_when_nothing_pending(self) -> None:
        repo = FakeCatalogRepo()
        svc = _make_service(catalog_repo=repo)
        result = await svc.sync(root_url=_ROOT_URL)
        assert result.tables_checked == 6
        assert result.pending_found == 0
        assert result.updated == 0
        assert result.not_found == 0


class TestMatchingCodes:
    @pytest.mark.asyncio
    @respx.mock
    async def test_activates_matched_codes(self) -> None:
        repo = FakeCatalogRepo(
            pending={"cat_status_code": ["RES", "PND"]},
        )

        respx.get(_ROOT_URL).respond(200, text=_DIRECTORY_HTML)
        respx.get(f"{_ROOT_URL}SyndicationContractFolderStatusCode-2.3.gc").respond(
            200, content=_GC_XML
        )

        async with httpx.AsyncClient() as client:
            svc = _make_service(catalog_repo=repo, http_client=client)
            result = await svc.sync(root_url=_ROOT_URL)

        assert result.updated == 2
        assert result.not_found == 0
        assert len(repo.activated) == 1
        assert repo.activated[0]["table"] == "cat_status_code"


class TestUnmatchedCodes:
    @pytest.mark.asyncio
    @respx.mock
    async def test_counts_unmatched_as_not_found(self) -> None:
        repo = FakeCatalogRepo(
            pending={"cat_status_code": ["RES", "UNKNOWN"]},
        )

        respx.get(_ROOT_URL).respond(200, text=_DIRECTORY_HTML)
        respx.get(f"{_ROOT_URL}SyndicationContractFolderStatusCode-2.3.gc").respond(
            200, content=_GC_XML
        )

        async with httpx.AsyncClient() as client:
            svc = _make_service(catalog_repo=repo, http_client=client)
            result = await svc.sync(root_url=_ROOT_URL)

        assert result.updated == 1
        assert result.not_found == 1


class TestDirectoryCrawlError:
    @pytest.mark.asyncio
    @respx.mock
    async def test_marks_all_not_found_on_crawl_failure(self) -> None:
        repo = FakeCatalogRepo(
            pending={"cat_status_code": ["RES"]},
        )

        respx.get(_ROOT_URL).respond(500)

        async with httpx.AsyncClient() as client:
            svc = _make_service(catalog_repo=repo, http_client=client)
            result = await svc.sync(root_url=_ROOT_URL)

        assert result.not_found == 1
        assert result.updated == 0
        assert len(repo.activated) == 0


class TestGcFileError:
    @pytest.mark.asyncio
    @respx.mock
    async def test_marks_not_found_on_gc_download_error(self) -> None:
        repo = FakeCatalogRepo(
            pending={"cat_status_code": ["RES"]},
        )

        respx.get(_ROOT_URL).respond(200, text=_DIRECTORY_HTML)
        respx.get(f"{_ROOT_URL}SyndicationContractFolderStatusCode-2.3.gc").respond(500)

        async with httpx.AsyncClient() as client:
            svc = _make_service(catalog_repo=repo, http_client=client)
            result = await svc.sync(root_url=_ROOT_URL)

        assert result.not_found == 1
        assert result.updated == 0


class TestGcXmlParseError:
    @pytest.mark.asyncio
    @respx.mock
    async def test_marks_not_found_on_invalid_xml(self) -> None:
        repo = FakeCatalogRepo(
            pending={"cat_status_code": ["RES"]},
        )

        respx.get(_ROOT_URL).respond(200, text=_DIRECTORY_HTML)
        respx.get(f"{_ROOT_URL}SyndicationContractFolderStatusCode-2.3.gc").respond(
            200, content=b"<not valid xml"
        )

        async with httpx.AsyncClient() as client:
            svc = _make_service(catalog_repo=repo, http_client=client)
            result = await svc.sync(root_url=_ROOT_URL)

        assert result.not_found == 1
        assert result.updated == 0


class TestNoGcUrlForTable:
    @pytest.mark.asyncio
    @respx.mock
    async def test_no_gc_link_in_directory(self) -> None:
        repo = FakeCatalogRepo(
            pending={"cat_urgency_code": ["URG"]},
        )

        # Directory has no DiligenceTypeCode link
        respx.get(_ROOT_URL).respond(200, text=_DIRECTORY_HTML)

        async with httpx.AsyncClient() as client:
            svc = _make_service(catalog_repo=repo, http_client=client)
            result = await svc.sync(root_url=_ROOT_URL)

        assert result.not_found == 1
        assert result.updated == 0
