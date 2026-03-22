"""Tests for feed reader handler — parallel feed orchestration."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from shared.enums import ROOT_FILENAMES
from etl.handlers.feed_reader import (
    LocalFeedTransport,
    _build_event,
    parse_args,
    resolve_pairs,
    run_feeds_parallel,
)
from shared.models.etl import SyncResult


class TestResolvePairsOnline:
    def test_online_mode_returns_both_feeds(self) -> None:
        pairs = resolve_pairs(local_dir=None, years=None)
        assert pairs == [("outsiders", 0), ("insiders", 0)]

    def test_online_mode_honors_single_feed_type(self) -> None:
        pairs = resolve_pairs(local_dir=None, years=None, feed_types=["outsiders"])
        assert pairs == [("outsiders", 0)]

    def test_years_without_local_raises(self) -> None:
        with pytest.raises(ValueError, match="--years requires --local"):
            resolve_pairs(local_dir=None, years=[2020])


def _make_sync_fn(result: SyncResult | None = None):
    """Return a fake sync callable that returns a fixed result."""
    r = result or SyncResult(processed=5, skipped_stale=1, failed=0, pages=2)

    async def _sync(_feed_type: str, _year: int) -> SyncResult:
        return r

    return _sync


class TestResultAggregation:
    @pytest.mark.asyncio
    async def test_sums_results_from_multiple_feeds(self) -> None:
        pairs = [("outsiders", 0), ("insiders", 0)]
        sync_fn = _make_sync_fn(
            SyncResult(processed=10, skipped_stale=2, failed=1, pages=3),
        )

        agg = await run_feeds_parallel(pairs, sync_fn, max_concurrent=4)

        assert agg["processed"] == 20
        assert agg["skipped_stale"] == 4
        assert agg["failed"] == 2
        assert agg["pages"] == 6
        assert agg["success"] is True


class TestSemaphoreThrottling:
    @pytest.mark.asyncio
    async def test_limits_concurrency(self) -> None:
        max_concurrent_seen = 0
        current = 0
        lock = asyncio.Lock()

        async def _sync(_feed_type: str, _year: int) -> SyncResult:
            nonlocal max_concurrent_seen, current
            async with lock:
                current += 1
                max_concurrent_seen = max(max_concurrent_seen, current)
            await asyncio.sleep(0.01)
            async with lock:
                current -= 1
            return SyncResult(processed=1, skipped_stale=0, failed=0, pages=1)

        pairs = [
            ("outsiders", 2020),
            ("outsiders", 2021),
            ("insiders", 2020),
            ("insiders", 2021),
        ]

        await run_feeds_parallel(pairs, _sync, max_concurrent=2)

        assert max_concurrent_seen <= 2


class TestErrorIsolation:
    @pytest.mark.asyncio
    async def test_failing_feed_does_not_affect_others(self) -> None:
        async def _sync(feed_type: str, _year: int) -> SyncResult:
            if feed_type == "outsiders":
                msg = "boom"
                raise RuntimeError(msg)
            return SyncResult(processed=10, skipped_stale=0, failed=0, pages=5)

        pairs = [("outsiders", 0), ("insiders", 0)]

        agg = await run_feeds_parallel(pairs, _sync, max_concurrent=4)

        assert agg["success"] is False
        assert agg["processed"] == 10
        assert agg["pages"] == 5

    @pytest.mark.asyncio
    async def test_failure_propagates_status_code(self) -> None:
        async def _sync(_ft: str, _yr: int) -> SyncResult:
            msg = "boom"
            raise RuntimeError(msg)

        agg = await run_feeds_parallel([("outsiders", 0)], _sync, max_concurrent=4)

        assert agg["success"] is False
        assert agg["processed"] == 0


def _build_local_dir(tmp_path: Path, layout: dict[str, list[int]]) -> Path:
    """Create a local feed directory with root entry files.

    layout: {"outsiders": [2020, 2021], "insiders": [2020]}
    """
    for feed_type, years in layout.items():
        root_name = ROOT_FILENAMES[feed_type]
        for year in years:
            year_dir = tmp_path / feed_type / str(year)
            year_dir.mkdir(parents=True)
            (year_dir / root_name).write_text("<feed/>")
    return tmp_path


class TestResolvePairsLocal:
    def test_seeding_mode_produces_four_pairs(self, tmp_path: Path) -> None:
        local_dir = _build_local_dir(
            tmp_path, {"outsiders": [2020, 2021], "insiders": [2020, 2021]}
        )
        pairs = resolve_pairs(local_dir=str(local_dir), years=[2020, 2021])
        assert len(pairs) == 4
        assert ("outsiders", 2021) in pairs
        assert ("outsiders", 2020) in pairs
        assert ("insiders", 2021) in pairs
        assert ("insiders", 2020) in pairs

    def test_newest_year_first(self, tmp_path: Path) -> None:
        local_dir = _build_local_dir(tmp_path, {"outsiders": [2018, 2021, 2020]})
        pairs = resolve_pairs(local_dir=str(local_dir), years=None)
        outsider_years = [yr for ft, yr in pairs if ft == "outsiders"]
        assert outsider_years == [2021, 2020, 2018]

    def test_filters_by_years(self, tmp_path: Path) -> None:
        local_dir = _build_local_dir(tmp_path, {"outsiders": [2018, 2020, 2021]})
        pairs = resolve_pairs(local_dir=str(local_dir), years=[2020])
        assert pairs == [("outsiders", 2020)]

    def test_skips_directory_without_root_file(self, tmp_path: Path) -> None:
        (tmp_path / "outsiders" / "2020").mkdir(parents=True)
        _build_local_dir(tmp_path, {"outsiders": [2021]})

        pairs = resolve_pairs(local_dir=str(tmp_path), years=None)
        outsider_years = [yr for ft, yr in pairs if ft == "outsiders"]
        assert outsider_years == [2021]

    def test_skips_non_numeric_directories(self, tmp_path: Path) -> None:
        _build_local_dir(tmp_path, {"outsiders": [2020]})
        (tmp_path / "outsiders" / "latest").mkdir()
        (tmp_path / "outsiders" / "latest" / ROOT_FILENAMES["outsiders"]).write_text(
            "<feed/>"
        )

        pairs = resolve_pairs(local_dir=str(tmp_path), years=None)
        outsider_years = [yr for ft, yr in pairs if ft == "outsiders"]
        assert outsider_years == [2020]


class TestBuildEvent:
    def test_naive_end_date_gets_utc(self) -> None:
        args = parse_args(["--end-date", "2024-06-15T00:00:00"])
        event = _build_event(args)
        assert event["end_date"].tzinfo is UTC

    def test_aware_end_date_preserved(self) -> None:
        args = parse_args(["--end-date", "2024-06-15T00:00:00+02:00"])
        event = _build_event(args)
        assert event["end_date"] == datetime.fromisoformat("2024-06-15T00:00:00+02:00")


class TestParseCLIArgs:
    def test_local_with_years(self) -> None:
        args = parse_args(["--local", "/data/feeds", "--years", "2020", "2021"])
        assert args.local == "/data/feeds"
        assert args.years == [2020, 2021]
        assert args.end_date is None

    def test_local_without_years(self) -> None:
        args = parse_args(["--local", "/data/feeds"])
        assert args.local == "/data/feeds"
        assert args.years is None

    def test_end_date(self) -> None:
        args = parse_args(["--end-date", "2024-06-15T00:00:00"])
        assert args.end_date == "2024-06-15T00:00:00"

    def test_defaults(self) -> None:
        args = parse_args([])
        assert args.local is None
        assert args.years is None
        assert args.end_date is None


class TestLocalFeedTransport:
    @pytest.mark.asyncio
    async def test_reads_local_file(self, tmp_path: Path) -> None:
        content = b"<feed><entry>test</entry></feed>"
        (tmp_path / "root.atom").write_bytes(content)

        transport = LocalFeedTransport()
        base = tmp_path.as_uri() + "/"
        async with httpx.AsyncClient(base_url=base, transport=transport) as client:
            resp = await client.get("root.atom")

        assert resp.status_code == 200
        assert resp.content == content

    @pytest.mark.asyncio
    async def test_missing_file_returns_empty_feed(self, tmp_path: Path) -> None:
        transport = LocalFeedTransport()
        base = tmp_path.as_uri() + "/"
        async with httpx.AsyncClient(base_url=base, transport=transport) as client:
            resp = await client.get("nonexistent.atom")

        assert resp.status_code == 200
        assert b"<feed" in resp.content

    @pytest.mark.asyncio
    async def test_resolves_relative_next_link(self, tmp_path: Path) -> None:
        (tmp_path / "page1.atom").write_bytes(b"<page1/>")
        (tmp_path / "page2.atom").write_bytes(b"<page2/>")

        transport = LocalFeedTransport()
        base = tmp_path.as_uri() + "/"
        async with httpx.AsyncClient(base_url=base, transport=transport) as client:
            r1 = await client.get("page1.atom")
            assert r1.content == b"<page1/>"
            r2 = await client.get("page2.atom")
            assert r2.content == b"<page2/>"
