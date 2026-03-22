"""CatalogUpdaterService — syncs CODICE genericode code lists to catalog tables."""

from __future__ import annotations

import re

import httpx
from lxml import etree

from shared.config import Settings
from shared.logger import get_logger
from shared.models.etl import CatalogUpdateResult
from etl.repositories.protocols import CatalogRepository

logger = get_logger(__name__)

_DEFAULT_ROOT = "https://contrataciondelestado.es/codice/cl/"

_TABLE_TO_GC: dict[str, str] = {
    "cat_status_code": "SyndicationContractFolderStatusCode",
    "cat_type_code": "SyndicationContractCode",
    "cat_procedure_code": "SyndicationTenderingProcessCode",
    "cat_urgency_code": "DiligenceTypeCode",
    "cat_result_code": "TenderResultCode",
    "cat_contracting_system": "ContractingSystemTypeCode",
}

_GC_NS = "http://docs.oasis-open.org/codelist/ns/genericode/1.0/"


def _parse_genericode(content: bytes) -> dict[str, str]:
    root = etree.fromstring(content)
    rows = root.findall(f".//{{{_GC_NS}}}Row")
    codes: dict[str, str] = {}
    for row in rows:
        values = row.findall(f"{{{_GC_NS}}}Value")
        code = None
        description = ""
        for val in values:
            col_ref = val.get("ColumnRef", "")
            simple = val.find(f"{{{_GC_NS}}}SimpleValue")
            text = simple.text if simple is not None and simple.text else ""
            if col_ref.lower() in ("code", "code_value"):
                code = text
            elif not description and col_ref.lower() in (
                "name",
                "description",
                "name_es",
                "descripcion",
            ):
                description = text
        if code:
            codes[code] = description
    return codes


def _extract_gc_links(html: str) -> list[str]:
    return re.findall(r'href="([^"]*\.gc)"', html, re.IGNORECASE)


class CatalogUpdaterService:
    def __init__(
        self,
        catalog_repo: CatalogRepository,
        http_client: httpx.AsyncClient,
        config: Settings,
    ) -> None:
        self._catalog_repo = catalog_repo
        self._http = http_client
        self._config = config

    async def sync(
        self,
        root_url: str | None = None,
    ) -> CatalogUpdateResult:
        url = root_url or _DEFAULT_ROOT
        tables_checked = 0
        pending_found = 0
        updated = 0
        not_found = 0

        needed: dict[str, list[tuple[str, list[str]]]] = {}
        for table, gc_base in _TABLE_TO_GC.items():
            tables_checked += 1
            pending = await self._catalog_repo.get_pending_codes(table)
            if not pending:
                continue
            pending_found += len(pending)
            needed.setdefault(gc_base, []).append((table, pending))

        if not needed:
            return CatalogUpdateResult(
                tables_checked=tables_checked,
                pending_found=0,
                updated=0,
                not_found=0,
            )

        gc_urls = await self._resolve_gc_urls(url)

        for gc_base, table_entries in needed.items():
            gc_url = gc_urls.get(gc_base)
            if not gc_url:
                for _table, codes in table_entries:
                    not_found += len(codes)
                    logger.warning("No genericode URL for %s", gc_base)
                continue

            try:
                resp = await self._http.get(
                    gc_url,
                    timeout=self._config.http_timeout,
                )
                resp.raise_for_status()
                gc_codes = _parse_genericode(resp.content)
            except (
                httpx.HTTPError,
                etree.XMLSyntaxError,
            ) as exc:
                logger.warning("Failed to process %s: %s", gc_url, exc)
                for _table, codes in table_entries:
                    not_found += len(codes)
                continue

            for table, pending_codes in table_entries:
                matched = {c: gc_codes[c] for c in pending_codes if c in gc_codes}
                if matched:
                    count = await self._catalog_repo.activate_codes(table, matched)
                    updated += count
                unmatched = len(pending_codes) - len(matched)
                not_found += unmatched

        return CatalogUpdateResult(
            tables_checked=tables_checked,
            pending_found=pending_found,
            updated=updated,
            not_found=not_found,
        )

    async def _resolve_gc_urls(self, root_url: str) -> dict[str, str]:
        try:
            resp = await self._http.get(
                root_url,
                timeout=self._config.http_timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError:
            logger.warning(
                "Failed to crawl CODICE directory at %s",
                root_url,
            )
            return {}

        links = _extract_gc_links(resp.text)
        gc_map: dict[str, str] = {}
        for link in links:
            for gc_base in _TABLE_TO_GC.values():
                if gc_base in link:
                    full_url = (
                        link
                        if link.startswith("http")
                        else f"{root_url.rstrip('/')}/{link}"
                    )
                    gc_map[gc_base] = full_url
        return gc_map
