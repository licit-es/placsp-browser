"""Integration tests for PgEntryRepository against local Supabase."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import asyncpg
import pytest
import pytest_asyncio

from shared.models.cpv_classification import CpvClassificationWrite
from shared.models.document_reference import DocumentReferenceWrite
from shared.models.parsed_page import (
    LotGroup,
    NoticeGroup,
    PublicationStatusGroup,
    ResultGroup,
)
from shared.models.procurement_project_lot import ProcurementProjectLotWrite
from shared.models.publication_status import PublicationStatusWrite
from shared.models.tender_result import TenderResultWrite
from shared.models.valid_notice_info import ValidNoticeInfoWrite
from shared.models.winning_party import WinningPartyWrite
from etl.repositories.entry_repo import PgEntryRepository
from tests.etl.builders.entities import (
    build_contract_folder_status,
    build_contracting_party,
    build_entry_envelope,
    build_parsed_entry,
)

DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"

_PH = uuid.UUID(int=0)
_NOW = datetime.now(UTC)
_LATER = _NOW + timedelta(hours=1)


@pytest_asyncio.fixture
async def pool():
    p = await asyncpg.create_pool(DATABASE_URL)
    yield p
    await p.execute('TRUNCATE contract_folder_status, contracting_party CASCADE')
    await p.close()


@pytest.fixture
def repo(pool) -> PgEntryRepository:
    return PgEntryRepository(pool)


def _entry(
    entry_id: str = "test://entry_1",
    updated: datetime | None = None,
    **overrides,
):
    ts = updated or _NOW
    envelope = build_entry_envelope(entry_id=entry_id, updated=ts)
    folder = build_contract_folder_status(
        entry_id=entry_id,
        updated=ts,
        feed_type="outsiders",
    )
    defaults = {
        "envelope": envelope,
        "folder": folder,
        "contracting_party": build_contracting_party(),
        "lot_groups": [],
        "result_groups": [],
        "cpv_folder": [],
        "criteria_folder": [],
        "guarantees": [],
        "requirements_folder": [],
        "classifications": [],
        "conditions": [],
        "direct_documents": [],
        "notice_groups": [],
        "modifications": [],
        "status_changes": [],
    }
    defaults.update(overrides)
    return build_parsed_entry(**defaults)


class TestFolderUpsert:
    @pytest.mark.asyncio
    async def test_first_insert_returns_ok(self, repo: PgEntryRepository) -> None:
        result = await repo.process_entry(_entry())
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_newer_update_returns_ok(self, repo: PgEntryRepository) -> None:
        await repo.process_entry(_entry(updated=_NOW))
        result = await repo.process_entry(_entry(updated=_LATER))
        assert result.status == "ok"

    @pytest.mark.asyncio
    async def test_stale_update_returns_stale(self, repo: PgEntryRepository) -> None:
        await repo.process_entry(_entry(updated=_LATER))
        result = await repo.process_entry(_entry(updated=_NOW))
        assert result.status == "stale"

    @pytest.mark.asyncio
    async def test_same_timestamp_returns_stale(self, repo: PgEntryRepository) -> None:
        await repo.process_entry(_entry(updated=_NOW))
        result = await repo.process_entry(_entry(updated=_NOW))
        assert result.status == "stale"

    @pytest.mark.asyncio
    async def test_folder_fields_persisted(self, repo: PgEntryRepository, pool) -> None:
        entry = _entry()
        await repo.process_entry(entry)
        row = await pool.fetchrow(
            "SELECT status_code, feed_type"
            ' FROM contract_folder_status'
            " WHERE entry_id = $1",
            entry.envelope.entry_id,
        )
        assert row["status_code"] == entry.folder.status_code
        assert row["feed_type"] == "outsiders"


class TestContractingParty:
    @pytest.mark.asyncio
    async def test_party_created(self, repo: PgEntryRepository, pool) -> None:
        entry = _entry()
        await repo.process_entry(entry)
        row = await pool.fetchrow(
            'SELECT name, dir3 FROM contracting_party WHERE dir3 = $1',
            entry.contracting_party.dir3,
        )
        assert row is not None
        assert row["name"] == entry.contracting_party.name

    @pytest.mark.asyncio
    async def test_party_linked_to_folder(self, repo: PgEntryRepository, pool) -> None:
        entry = _entry()
        await repo.process_entry(entry)
        row = await pool.fetchrow(
            "SELECT contracting_party_id"
            ' FROM contract_folder_status'
            " WHERE entry_id = $1",
            entry.envelope.entry_id,
        )
        assert row["contracting_party_id"] is not None

    @pytest.mark.asyncio
    async def test_dir3_identity_resolution(
        self, repo: PgEntryRepository, pool
    ) -> None:
        e1 = _entry(entry_id="test://e1", updated=_NOW)
        e2 = _entry(
            entry_id="test://e2",
            updated=_LATER,
            contracting_party=build_contracting_party(
                name="Updated Name",
                dir3="EA0003089",
            ),
        )
        await repo.process_entry(e1)
        await repo.process_entry(e2)
        count = await pool.fetchval(
            'SELECT count(*) FROM contracting_party WHERE dir3 = $1',
            "EA0003089",
        )
        assert count == 1

    @pytest.mark.asyncio
    async def test_platform_id_identity_resolution(
        self, repo: PgEntryRepository, pool
    ) -> None:
        party1 = build_contracting_party(dir3=None, platform_id="PLAT001")
        party2 = build_contracting_party(
            dir3=None,
            platform_id="PLAT001",
            name="New Name",
        )
        await repo.process_entry(
            _entry(
                entry_id="test://p1",
                updated=_NOW,
                contracting_party=party1,
            )
        )
        await repo.process_entry(
            _entry(
                entry_id="test://p2",
                updated=_LATER,
                contracting_party=party2,
            )
        )
        count = await pool.fetchval(
            'SELECT count(*) FROM contracting_party WHERE platform_id = $1',
            "PLAT001",
        )
        assert count == 1

    @pytest.mark.asyncio
    async def test_platform_id_identity_resolution_different_dir3(
        self, repo: PgEntryRepository, pool
    ) -> None:
        """Same platform_id but different dir3 should resolve to one party."""
        party1 = build_contracting_party(
            dir3="EA0000001", platform_id="PLAT002", name="Org A"
        )
        party2 = build_contracting_party(
            dir3="EA0000002", platform_id="PLAT002", name="Org A Renamed"
        )
        await repo.process_entry(
            _entry(
                entry_id="test://pd1",
                updated=_NOW,
                contracting_party=party1,
            )
        )
        await repo.process_entry(
            _entry(
                entry_id="test://pd2",
                updated=_LATER,
                contracting_party=party2,
            )
        )
        count = await pool.fetchval(
            'SELECT count(*) FROM contracting_party WHERE platform_id = $1',
            "PLAT002",
        )
        assert count == 1
        row = await pool.fetchrow(
            'SELECT dir3, name FROM contracting_party WHERE platform_id = $1',
            "PLAT002",
        )
        assert row["dir3"] == "EA0000002"
        assert row["name"] == "Org A Renamed"

    @pytest.mark.asyncio
    async def test_name_fallback_identity(self, repo: PgEntryRepository, pool) -> None:
        party = build_contracting_party(dir3=None, platform_id=None, name="Org Anon")
        await repo.process_entry(
            _entry(
                entry_id="test://n1",
                updated=_NOW,
                contracting_party=party,
            )
        )
        await repo.process_entry(
            _entry(
                entry_id="test://n2",
                updated=_LATER,
                contracting_party=party,
            )
        )
        count = await pool.fetchval(
            'SELECT count(*) FROM contracting_party'
            " WHERE name = $1"
            " AND dir3 IS NULL"
            " AND platform_id IS NULL",
            "Org Anon",
        )
        assert count == 1

    @pytest.mark.asyncio
    async def test_stale_entry_does_not_touch_party(
        self, repo: PgEntryRepository, pool
    ) -> None:
        await repo.process_entry(
            _entry(
                entry_id="test://s1",
                updated=_LATER,
                contracting_party=build_contracting_party(name="Current"),
            )
        )
        await repo.process_entry(
            _entry(
                entry_id="test://s1",
                updated=_NOW,
                contracting_party=build_contracting_party(name="Stale"),
            )
        )
        row = await pool.fetchrow(
            'SELECT name FROM contracting_party WHERE dir3 = $1',
            "EA0003089",
        )
        assert row["name"] == "Current"

    @pytest.mark.asyncio
    async def test_party_merge_on_conflict(self, repo: PgEntryRepository, pool) -> None:
        """dir3-only row + platform_id-only row, then entry with both -> merge to 1."""
        _t2 = _LATER + timedelta(hours=1)
        # Entry 1: party with dir3 only
        await repo.process_entry(
            _entry(
                entry_id="test://m1",
                updated=_NOW,
                contracting_party=build_contracting_party(
                    dir3="EA9999999", platform_id=None, name="Dir3 Only"
                ),
            )
        )
        # Entry 2: party with platform_id only
        await repo.process_entry(
            _entry(
                entry_id="test://m2",
                updated=_LATER,
                contracting_party=build_contracting_party(
                    dir3=None, platform_id="PLAT_MERGE", name="PlatId Only"
                ),
            )
        )
        # Verify 2 distinct rows exist
        pre_count = await pool.fetchval('SELECT count(*) FROM contracting_party')
        assert pre_count == 2

        # Entry 3: party with both identifiers -> triggers merge
        await repo.process_entry(
            _entry(
                entry_id="test://m3",
                updated=_t2,
                contracting_party=build_contracting_party(
                    dir3="EA9999999", platform_id="PLAT_MERGE", name="Merged Org"
                ),
            )
        )
        # Should be a single party now
        post_count = await pool.fetchval('SELECT count(*) FROM contracting_party')
        assert post_count == 1

        merged = await pool.fetchrow(
            'SELECT name, dir3, platform_id FROM contracting_party'
        )
        assert merged["dir3"] == "EA9999999"
        assert merged["platform_id"] == "PLAT_MERGE"
        assert merged["name"] == "Merged Org"

        # All 3 folders should reference the surviving party
        linked = await pool.fetchval(
            "SELECT count(DISTINCT contracting_party_id)"
            ' FROM contract_folder_status'
            " WHERE contracting_party_id IS NOT NULL"
        )
        assert linked == 1

    @pytest.mark.asyncio
    async def test_entry_persisted_when_party_fails(
        self, repo: PgEntryRepository, pool
    ) -> None:
        """Force party failure -> folder + children persisted with NULL party."""

        async def _boom(_self, _conn, _party):
            msg = "Simulated party failure"
            raise RuntimeError(msg)

        with patch.object(PgEntryRepository, "_upsert_party", _boom):
            result = await repo.process_entry(
                _entry(entry_id="test://fail1", updated=_NOW)
            )

        assert result.status == "ok"
        row = await pool.fetchrow(
            'SELECT contracting_party_id FROM contract_folder_status'
            " WHERE entry_id = $1",
            "test://fail1",
        )
        assert row is not None
        assert row["contracting_party_id"] is None

        # StatusChange should still be recorded
        sc = await pool.fetchval(
            'SELECT count(*) FROM status_change sc'
            ' JOIN contract_folder_status cfs ON sc.contract_folder_status_id = cfs.id'
            " WHERE cfs.entry_id = $1",
            "test://fail1",
        )
        assert sc == 1


class TestChildReplacement:
    @pytest.mark.asyncio
    async def test_lots_replaced_on_reupsert(
        self, repo: PgEntryRepository, pool
    ) -> None:
        lot1 = LotGroup(
            lot=ProcurementProjectLotWrite(
                contract_folder_status_id=_PH,
                lot_number="1",
                name="Lot A",
            ),
            cpv_codes=[],
            criteria=[],
            requirements=[],
            locations=[],
        )
        lot2 = LotGroup(
            lot=ProcurementProjectLotWrite(
                contract_folder_status_id=_PH,
                lot_number="2",
                name="Lot B",
            ),
            cpv_codes=[],
            criteria=[],
            requirements=[],
            locations=[],
        )
        await repo.process_entry(
            _entry(
                updated=_NOW,
                lot_groups=[lot1, lot2],
            )
        )
        await repo.process_entry(
            _entry(
                updated=_LATER,
                lot_groups=[lot1],
            )
        )
        count = await pool.fetchval('SELECT count(*) FROM procurement_project_lot')
        assert count == 1

    @pytest.mark.asyncio
    async def test_results_and_parties_replaced(
        self, repo: PgEntryRepository, pool
    ) -> None:
        rg = ResultGroup(
            result=TenderResultWrite(
                contract_folder_status_id=_PH,
                result_code="8",
            ),
            winning_parties=[
                WinningPartyWrite(
                    tender_result_id=_PH,
                    name="WP1",
                )
            ],
        )
        await repo.process_entry(_entry(updated=_NOW, result_groups=[rg]))
        await repo.process_entry(_entry(updated=_LATER, result_groups=[]))
        count = await pool.fetchval('SELECT count(*) FROM tender_result')
        assert count == 0
        wp_count = await pool.fetchval('SELECT count(*) FROM winning_party')
        assert wp_count == 0


class TestDocumentPreservation:
    @pytest.mark.asyncio
    async def test_doc_survives_reupsert(self, repo: PgEntryRepository, pool) -> None:
        doc = DocumentReferenceWrite(
            contract_folder_status_id=_PH,
            source_type="LEGAL",
            filename="pliego.pdf",
            uri="https://example.com/pliego.pdf",
        )
        await repo.process_entry(
            _entry(
                updated=_NOW,
                direct_documents=[doc],
            )
        )
        await pool.execute("UPDATE \"DocumentDownload\" SET status = 'downloaded'")
        await repo.process_entry(
            _entry(
                updated=_LATER,
                direct_documents=[doc],
            )
        )
        row = await pool.fetchrow(
            "SELECT dd.status"
            ' FROM "DocumentDownload" dd'
            ' JOIN document_reference dr'
            " ON dd.document_reference_id = dr.id"
            " WHERE dr.uri = $1",
            "https://example.com/pliego.pdf",
        )
        assert row["status"] == "downloaded"

    @pytest.mark.asyncio
    async def test_doc_hash_change_resets_download(
        self, repo: PgEntryRepository, pool
    ) -> None:
        doc1 = DocumentReferenceWrite(
            contract_folder_status_id=_PH,
            source_type="LEGAL",
            filename="pliego.pdf",
            uri="https://example.com/pliego.pdf",
            document_hash="hash_v1",
        )
        await repo.process_entry(
            _entry(
                updated=_NOW,
                direct_documents=[doc1],
            )
        )
        await pool.execute("UPDATE \"DocumentDownload\" SET status = 'downloaded'")
        doc2 = DocumentReferenceWrite(
            contract_folder_status_id=_PH,
            source_type="LEGAL",
            filename="pliego.pdf",
            uri="https://example.com/pliego.pdf",
            document_hash="hash_v2",
        )
        await repo.process_entry(
            _entry(
                updated=_LATER,
                direct_documents=[doc2],
            )
        )
        row = await pool.fetchrow(
            "SELECT dd.status"
            ' FROM "DocumentDownload" dd'
            ' JOIN document_reference dr'
            " ON dd.document_reference_id = dr.id"
            " WHERE dr.uri = $1",
            "https://example.com/pliego.pdf",
        )
        assert row["status"] == "pending"

    @pytest.mark.asyncio
    async def test_publication_docs_preserved(
        self, repo: PgEntryRepository, pool
    ) -> None:
        pub_doc = DocumentReferenceWrite(
            contract_folder_status_id=_PH,
            publication_status_id=_PH,
            source_type="PUBLICATION",
            filename="anuncio.pdf",
            uri="https://example.com/anuncio.pdf",
        )
        notice = NoticeGroup(
            notice=ValidNoticeInfoWrite(
                contract_folder_status_id=_PH,
                notice_type_code="DOC_CN",
            ),
            statuses=[
                PublicationStatusGroup(
                    status=PublicationStatusWrite(
                        valid_notice_info_id=_PH,
                        publication_media_name="BOE",
                    ),
                    documents=[pub_doc],
                )
            ],
        )
        await repo.process_entry(
            _entry(
                updated=_NOW,
                notice_groups=[notice],
            )
        )
        await pool.execute("UPDATE \"DocumentDownload\" SET status = 'downloaded'")
        await repo.process_entry(
            _entry(
                updated=_LATER,
                notice_groups=[notice],
            )
        )
        row = await pool.fetchrow(
            "SELECT dd.status"
            ' FROM "DocumentDownload" dd'
            ' JOIN document_reference dr'
            " ON dd.document_reference_id = dr.id"
            " WHERE dr.uri = $1",
            "https://example.com/anuncio.pdf",
        )
        assert row["status"] == "downloaded"


class TestStatusChange:
    @pytest.mark.asyncio
    async def test_status_logged(self, repo: PgEntryRepository, pool) -> None:
        await repo.process_entry(_entry())
        count = await pool.fetchval('SELECT count(*) FROM status_change')
        assert count == 1

    @pytest.mark.asyncio
    async def test_status_appended_on_update(
        self, repo: PgEntryRepository, pool
    ) -> None:
        await repo.process_entry(_entry(updated=_NOW))
        await repo.process_entry(_entry(updated=_LATER))
        count = await pool.fetchval('SELECT count(*) FROM status_change')
        assert count == 2


class TestFullParsedEntry:
    @pytest.mark.asyncio
    async def test_full_entry_roundtrip(self, repo: PgEntryRepository, pool) -> None:
        lot_group = LotGroup(
            lot=ProcurementProjectLotWrite(
                contract_folder_status_id=_PH,
                lot_number="1",
                name="Lot 1",
                total_amount=Decimal("50000"),
            ),
            cpv_codes=[
                CpvClassificationWrite(
                    contract_folder_status_id=_PH,
                    item_classification_code="30200000",
                )
            ],
            criteria=[],
            requirements=[],
            locations=[],
        )
        result_group = ResultGroup(
            result=TenderResultWrite(
                contract_folder_status_id=_PH,
                result_code="8",
                awarded_lot_number="1",
            ),
            winning_parties=[
                WinningPartyWrite(
                    tender_result_id=_PH,
                    name="TechCorp",
                    identifier="B12345678",
                )
            ],
        )
        doc = DocumentReferenceWrite(
            contract_folder_status_id=_PH,
            source_type="LEGAL",
            filename="p.pdf",
            uri="https://example.com/p.pdf",
        )
        entry = _entry(
            lot_groups=[lot_group],
            result_groups=[result_group],
            cpv_folder=[
                CpvClassificationWrite(
                    contract_folder_status_id=_PH,
                    item_classification_code="30200000",
                )
            ],
            direct_documents=[doc],
        )
        result = await repo.process_entry(entry)
        assert result.status == "ok"

        lot_count = await pool.fetchval('SELECT count(*) FROM procurement_project_lot')
        assert lot_count == 1

        tr_count = await pool.fetchval('SELECT count(*) FROM tender_result')
        assert tr_count == 1

        tr = await pool.fetchrow('SELECT lot_id FROM tender_result')
        assert tr["lot_id"] is not None

        wp_count = await pool.fetchval('SELECT count(*) FROM winning_party')
        assert wp_count == 1

        doc_count = await pool.fetchval('SELECT count(*) FROM document_reference')
        assert doc_count == 1

        cpv_count = await pool.fetchval('SELECT count(*) FROM cpv_classification')
        assert cpv_count == 2
