"""End-to-end tests for GET /similares/{id}."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.inteligencia.estadisticas import (
    CompetitionStats,
    FrequentWinner,
    PricingStats,
)
from api.inteligencia.similares import IntelligenceResult
from api.inteligencia.similitud import ScoredCandidate

_REF_ID = uuid.uuid4()
_CAND_1 = uuid.uuid4()
_CAND_2 = uuid.uuid4()
_NOW = datetime.now(UTC)


# -------------------------------------------------------------------
# Display row factory
# -------------------------------------------------------------------


def _display_row(uid: uuid.UUID, titulo: str) -> dict:
    """Minimal v_licitacion row for display."""
    return {
        "id": uid,
        "expediente": f"EXP-{uid.hex[:6]}",
        "titulo": titulo,
        "organo": "Organo Test",
        "tipo_contrato": "Servicios",
        "estado": "Adjudicada",
        "presupuesto_sin_iva": Decimal("100000"),
        "importe_adjudicacion": Decimal("85000"),
        "fecha_publicacion": _NOW,
        "fecha_actualizacion": _NOW,
        "fecha_adjudicacion": _NOW.date(),
        "cpv_principal": "72260000",
        "num_licitadores": 3,
        "adjudicatario": "Empresa Test S.L.",
        "lugar": "Madrid",
        "tiene_documentos": True,
        "num_lotes": 0,
        "historial_estados": [{"estado": "Adjudicada", "fecha": _NOW.isoformat()}],
    }


# -------------------------------------------------------------------
# Intelligence fixtures
# -------------------------------------------------------------------


def _full_intel() -> IntelligenceResult:
    return IntelligenceResult(
        candidates=[
            ScoredCandidate(id=_CAND_1, similitud=7),
            ScoredCandidate(id=_CAND_2, similitud=4),
        ],
        pricing=PricingStats(n=35, p25=8.2, mediana=14.5, p75=22.1),
        competition=CompetitionStats(media=4.2, mediana=3.0),
        frequent_winners=[
            FrequentWinner(nombre="Indra S.A.", n=8, baja_media_pct=18.3),
            FrequentWinner(nombre="Everis S.L.", n=5, baja_media_pct=15.1),
        ],
        tasa_desierta=0.12,
        pool_size=47,
        budget_factor=3,
    )


def _empty_intel() -> IntelligenceResult:
    return IntelligenceResult(
        candidates=[],
        pricing=None,
        competition=None,
        frequent_winners=[],
        tasa_desierta=None,
        pool_size=0,
        budget_factor=10,
    )


def _sparse_intel() -> IntelligenceResult:
    return IntelligenceResult(
        candidates=[ScoredCandidate(id=_CAND_1, similitud=5)],
        pricing=None,
        competition=CompetitionStats(media=2.0, mediana=2.0),
        frequent_winners=[],
        tasa_desierta=0.5,
        pool_size=4,
        budget_factor=10,
    )


# -------------------------------------------------------------------
# Fixture: client + conn mock wired together
# -------------------------------------------------------------------


@pytest.fixture
def conn(auth_conn: AsyncMock) -> AsyncMock:
    """Alias for auth_conn — tests configure .fetch before requests."""
    return auth_conn


@pytest.fixture
def client(auth_client: TestClient) -> TestClient:
    """Alias for auth_client with auth overridden."""
    return auth_client


# -------------------------------------------------------------------
# Tests: full response shape
# -------------------------------------------------------------------


class TestFullResponse:
    def test_returns_resultados_and_estadisticas(
        self, client: TestClient, conn: AsyncMock
    ):
        conn.fetch = AsyncMock(
            return_value=[
                _display_row(_CAND_1, "Tender A"),
                _display_row(_CAND_2, "Tender B"),
            ]
        )
        with patch(
            "api.routes.similares.compute_intelligence",
            return_value=_full_intel(),
        ):
            resp = client.get(f"/v1/similares/{_REF_ID}")

        assert resp.status_code == 200
        body = resp.json()

        assert "resultados" in body
        assert "estadisticas" in body
        assert len(body["resultados"]) == 2

        est = body["estadisticas"]
        assert est["n"] == 47
        assert est["nivel_confianza"] == "alta"
        assert est["factor_presupuesto"] == 3
        assert est["tasa_desierta"] == 0.12

        baja = est["baja_pct"]
        assert baja["n"] == 35
        assert baja["p25"] == 8.2
        assert baja["mediana"] == 14.5
        assert baja["p75"] == 22.1

        comp = est["num_licitadores"]
        assert comp["media"] == 4.2
        assert comp["mediana"] == 3.0

        winners = est["adjudicatarios_frecuentes"]
        assert len(winners) == 2
        assert winners[0]["nombre"] == "Indra S.A."
        assert winners[0]["n"] == 8
        assert winners[0]["baja_media_pct"] == 18.3

    def test_resultados_sorted_by_similitud_desc(
        self, client: TestClient, conn: AsyncMock
    ):
        # DB returns them in wrong order
        conn.fetch = AsyncMock(
            return_value=[
                _display_row(_CAND_2, "Low score"),
                _display_row(_CAND_1, "High score"),
            ]
        )
        with patch(
            "api.routes.similares.compute_intelligence",
            return_value=_full_intel(),
        ):
            resp = client.get(f"/v1/similares/{_REF_ID}")

        scores = [r["similitud"] for r in resp.json()["resultados"]]
        assert scores == [7, 4]

    def test_similitud_field_present_on_each_result(
        self, client: TestClient, conn: AsyncMock
    ):
        conn.fetch = AsyncMock(return_value=[_display_row(_CAND_1, "Tender A")])
        with patch(
            "api.routes.similares.compute_intelligence",
            return_value=_full_intel(),
        ):
            resp = client.get(f"/v1/similares/{_REF_ID}?limit=1")

        first = resp.json()["resultados"][0]
        assert "similitud" in first
        assert first["similitud"] == 7

    def test_limit_caps_resultados(self, client: TestClient, conn: AsyncMock):
        # Only _CAND_1 is in the display query (limit=1)
        conn.fetch = AsyncMock(return_value=[_display_row(_CAND_1, "Tender A")])
        with patch(
            "api.routes.similares.compute_intelligence",
            return_value=_full_intel(),
        ):
            resp = client.get(f"/v1/similares/{_REF_ID}?limit=1")

        assert len(resp.json()["resultados"]) == 1
        # But estadisticas still reflect the full pool
        assert resp.json()["estadisticas"]["n"] == 47


# -------------------------------------------------------------------
# Tests: edge cases
# -------------------------------------------------------------------


class TestEdgeCases:
    def test_not_found_returns_404(self, client: TestClient):
        with patch(
            "api.routes.similares.compute_intelligence",
            return_value=None,
        ):
            resp = client.get(f"/v1/similares/{uuid.uuid4()}")

        assert resp.status_code == 404

    def test_empty_pool(self, client: TestClient):
        with patch(
            "api.routes.similares.compute_intelligence",
            return_value=_empty_intel(),
        ):
            resp = client.get(f"/v1/similares/{_REF_ID}")

        assert resp.status_code == 200
        body = resp.json()
        assert body["resultados"] == []
        est = body["estadisticas"]
        assert est["n"] == 0
        assert est["baja_pct"] is None
        assert est["num_licitadores"] is None
        assert est["adjudicatarios_frecuentes"] == []
        assert est["tasa_desierta"] is None
        assert est["nivel_confianza"] == "baja"
        assert est["factor_presupuesto"] == 10

    def test_sparse_data_no_pricing(self, client: TestClient, conn: AsyncMock):
        conn.fetch = AsyncMock(return_value=[_display_row(_CAND_1, "Sparse")])
        with patch(
            "api.routes.similares.compute_intelligence",
            return_value=_sparse_intel(),
        ):
            resp = client.get(f"/v1/similares/{_REF_ID}")

        est = resp.json()["estadisticas"]
        assert est["baja_pct"] is None
        assert est["num_licitadores"] is not None
        assert est["nivel_confianza"] == "baja"
        assert est["factor_presupuesto"] == 10


# -------------------------------------------------------------------
# Tests: intelligence module units
# -------------------------------------------------------------------


class TestSimilitudUnit:
    def test_query_includes_all_scoring_dimensions(self):
        from api.inteligencia.similitud import RefDimensions, _build_query

        ref = RefDimensions(
            type_code="2",
            procedure_code="1",
            budget=100_000.0,
            nuts_code="ES300",
            over_threshold=False,
            auth_type="3",
            cpv_codes=["72260000", "72212000"],
        )
        sql, params = _build_query(ref, _REF_ID, 3)

        assert "cfs.type_code" in sql
        assert "BETWEEN" in sql
        assert "cfs.procedure_code" in sql
        assert "cpv_classification" in sql
        assert "cfs.nuts_code" in sql
        assert "contracting_party_type_code" in sql
        assert "over_threshold_indicator" in sql
        assert _REF_ID in params

    def test_query_handles_missing_dimensions(self):
        from api.inteligencia.similitud import RefDimensions, _build_query

        ref = RefDimensions(
            type_code=None,
            procedure_code=None,
            budget=None,
            nuts_code=None,
            over_threshold=None,
            auth_type=None,
            cpv_codes=[],
        )
        sql, params = _build_query(ref, _REF_ID, 3)

        assert "cfs.id != $1" in sql
        assert len(params) == 1

    def test_adaptive_widening_stops_when_pool_large_enough(self):
        import asyncio

        from api.inteligencia import similitud
        from api.inteligencia.similitud import RefDimensions, find_candidates

        async def _run():
            conn = AsyncMock()
            call_count = 0
            factors_seen = []
            original = similitud._build_query

            def tracking_build(ref, ref_id, factor):
                factors_seen.append(factor)
                return original(ref, ref_id, factor)

            async def mock_fetch(_sql, *_params):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return []
                return [{"id": uuid.uuid4(), "similitud": i} for i in range(15)]

            conn.fetch = mock_fetch
            ref = RefDimensions(
                type_code="2",
                procedure_code="1",
                budget=100_000.0,
                nuts_code="ES300",
                over_threshold=False,
                auth_type="3",
                cpv_codes=["72260000"],
            )

            with patch.object(similitud, "_build_query", side_effect=tracking_build):
                candidates, factor = await find_candidates(conn, ref, _REF_ID)

            assert factor == 5
            assert len(candidates) == 15
            assert factors_seen == [3, 5]

        asyncio.run(_run())


class TestEstadisticasUnit:
    def test_confidence_levels(self):
        from api.inteligencia.estadisticas import confidence

        assert confidence(None) == "baja"
        assert confidence(PricingStats(n=2, p25=0, mediana=0, p75=0)) == "baja"
        assert confidence(PricingStats(n=9, p25=0, mediana=0, p75=0)) == "baja"
        assert confidence(PricingStats(n=15, p25=0, mediana=0, p75=0)) == "media"
        assert confidence(PricingStats(n=30, p25=0, mediana=0, p75=0)) == "alta"
        assert confidence(PricingStats(n=100, p25=0, mediana=0, p75=0)) == "alta"

    def test_pricing_returns_none_below_minimum(self):
        import asyncio

        from api.inteligencia.estadisticas import pricing

        async def _run():
            conn = AsyncMock()
            conn.fetchrow = AsyncMock(return_value={"n": 2, "pcts": [0.1, 0.15, 0.2]})
            result = await pricing(conn, [uuid.uuid4()])
            assert result is None

        asyncio.run(_run())

    def test_pricing_computes_percentages(self):
        import asyncio

        from api.inteligencia.estadisticas import pricing

        async def _run():
            conn = AsyncMock()
            conn.fetchrow = AsyncMock(
                return_value={"n": 50, "pcts": [0.082, 0.145, 0.221]}
            )
            result = await pricing(conn, [uuid.uuid4()])
            assert result is not None
            assert result.n == 50
            assert result.p25 == 8.2
            assert result.mediana == 14.5
            assert result.p75 == 22.1

        asyncio.run(_run())

    def test_desierta_rate_ratio(self):
        import asyncio

        from api.inteligencia.estadisticas import desierta_rate

        async def _run():
            conn = AsyncMock()
            conn.fetchrow = AsyncMock(return_value={"desiertas": 3, "total": 25})
            result = await desierta_rate(conn, [uuid.uuid4()])
            assert result == 0.12

        asyncio.run(_run())

    def test_desierta_rate_none_on_empty(self):
        import asyncio

        from api.inteligencia.estadisticas import desierta_rate

        async def _run():
            conn = AsyncMock()
            conn.fetchrow = AsyncMock(return_value={"desiertas": 0, "total": 0})
            result = await desierta_rate(conn, [uuid.uuid4()])
            assert result is None

        asyncio.run(_run())
