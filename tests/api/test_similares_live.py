"""Live integration tests against api.licit.es — no mocks.

Run with:  uv run pytest tests/api/test_similares_live.py -m network -v
"""

from __future__ import annotations

import httpx
import pytest

BASE = "https://api.licit.es/v1"

# A real tender from production (Soporte Microsoft, Ayto Málaga).
REF_ID = "c1d8e9b3-2adb-41d9-8285-173fdb42439a"

pytestmark = pytest.mark.network


@pytest.fixture(scope="module")
def api() -> httpx.Client:
    with httpx.Client(base_url=BASE, timeout=30) as c:
        yield c


# -------------------------------------------------------------------
# Smoke: current similares endpoint works and returns data
# -------------------------------------------------------------------


class TestSimilaresSmoke:
    def test_returns_200(self, api: httpx.Client):
        r = api.get(f"/similares/{REF_ID}")
        assert r.status_code == 200

    def test_returns_list_of_tenders(self, api: httpx.Client):
        r = api.get(f"/similares/{REF_ID}")
        body = r.json()
        # Current format: flat list. After deploy: {resultados, estadisticas}
        if isinstance(body, list):
            tenders = body
        else:
            assert "resultados" in body
            assert "estadisticas" in body
            tenders = body["resultados"]

        assert len(tenders) > 0

    def test_each_result_has_required_fields(self, api: httpx.Client):
        r = api.get(f"/similares/{REF_ID}")
        body = r.json()
        tenders = body if isinstance(body, list) else body["resultados"]

        required = {
            "id",
            "expediente",
            "titulo",
            "organo",
            "tipo_contrato",
            "estado",
            "presupuesto_sin_iva",
        }
        for t in tenders:
            assert required.issubset(t.keys()), f"Missing: {required - t.keys()}"

    def test_404_on_unknown_id(self, api: httpx.Client):
        r = api.get("/similares/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404


# -------------------------------------------------------------------
# Data quality: verify the data my intelligence layer consumes
# -------------------------------------------------------------------


class TestDataQuality:
    """Verify real tenders have the fields needed for intelligence."""

    def test_reference_tender_has_cpv_and_budget(self, api: httpx.Client):
        r = api.get(f"/licitacion/{REF_ID}")
        assert r.status_code == 200
        detail = r.json()
        assert detail["presupuesto_sin_iva"] is not None
        assert float(detail["presupuesto_sin_iva"]) > 0
        assert detail["tipo_contrato"] is not None

    def test_similar_tenders_share_contract_type(self, api: httpx.Client):
        ref = api.get(f"/licitacion/{REF_ID}").json()
        ref_tipo = ref["tipo_contrato"]

        similares = api.get(f"/similares/{REF_ID}").json()
        tenders = similares if isinstance(similares, list) else similares["resultados"]

        for t in tenders:
            assert t["tipo_contrato"] == ref_tipo, (
                f"{t['expediente']}: {t['tipo_contrato']} != {ref_tipo}"
            )

    def test_resolved_tenders_have_pricing_data(self, api: httpx.Client):
        """At least some similar tenders should have award amounts."""
        similares = api.get(f"/similares/{REF_ID}").json()
        tenders = similares if isinstance(similares, list) else similares["resultados"]

        resolved = [
            t
            for t in tenders
            if t["estado"] in ("Adjudicada", "Resuelta", "Formalizada")
        ]
        with_price = [t for t in resolved if t["importe_adjudicacion"] is not None]

        # At least one resolved tender with pricing data
        assert len(with_price) > 0, "No resolved tenders with pricing data"

    def test_budgets_in_similar_order_of_magnitude(self, api: httpx.Client):
        """Similar tenders should have budgets within ~10x of reference."""
        ref = api.get(f"/licitacion/{REF_ID}").json()
        ref_budget = float(ref["presupuesto_sin_iva"])

        similares = api.get(f"/similares/{REF_ID}").json()
        tenders = similares if isinstance(similares, list) else similares["resultados"]

        for t in tenders:
            if t["presupuesto_sin_iva"] is None:
                continue
            budget = float(t["presupuesto_sin_iva"])
            ratio = budget / ref_budget
            assert 0.05 < ratio < 20, (
                f"{t['expediente']}: budget {budget} is {ratio:.1f}x ref {ref_budget}"
            )


# -------------------------------------------------------------------
# After deploy: new response format
# -------------------------------------------------------------------


class TestNewFormat:
    """Tests that only pass after the new code is deployed."""

    def test_response_has_estadisticas(self, api: httpx.Client):
        r = api.get(f"/similares/{REF_ID}")
        body = r.json()
        if isinstance(body, list):
            pytest.skip("Old format still deployed")

        assert "estadisticas" in body
        est = body["estadisticas"]
        assert "n" in est
        assert "baja_pct" in est
        assert "num_licitadores" in est
        assert "adjudicatarios_frecuentes" in est
        assert "tasa_desierta" in est
        assert "nivel_confianza" in est
        assert "factor_presupuesto" in est

    def test_similitud_field_on_results(self, api: httpx.Client):
        r = api.get(f"/similares/{REF_ID}")
        body = r.json()
        if isinstance(body, list):
            pytest.skip("Old format still deployed")

        for t in body["resultados"]:
            assert "similitud" in t
            assert isinstance(t["similitud"], int)
            assert 0 <= t["similitud"] <= 9

    def test_results_sorted_by_similitud(self, api: httpx.Client):
        r = api.get(f"/similares/{REF_ID}")
        body = r.json()
        if isinstance(body, list):
            pytest.skip("Old format still deployed")

        scores = [t["similitud"] for t in body["resultados"]]
        assert scores == sorted(scores, reverse=True)

    def test_pricing_percentiles_make_sense(self, api: httpx.Client):
        r = api.get(f"/similares/{REF_ID}")
        body = r.json()
        if isinstance(body, list):
            pytest.skip("Old format still deployed")

        baja = body["estadisticas"]["baja_pct"]
        if baja is None:
            pytest.skip("Insufficient pricing data")

        assert baja["n"] >= 3
        assert 0 <= baja["p25"] <= baja["mediana"] <= baja["p75"] <= 100
        # Typical public procurement discounts are 0-40%
        assert baja["mediana"] < 50, f"Median baja {baja['mediana']}% seems too high"

    def test_competition_stats_reasonable(self, api: httpx.Client):
        r = api.get(f"/similares/{REF_ID}")
        body = r.json()
        if isinstance(body, list):
            pytest.skip("Old format still deployed")

        comp = body["estadisticas"]["num_licitadores"]
        if comp is None:
            pytest.skip("No competition data")

        assert comp["media"] > 0
        assert comp["mediana"] > 0
        # Typical range: 1-20 bidders
        assert comp["media"] < 50

    def test_confidence_is_valid_label(self, api: httpx.Client):
        r = api.get(f"/similares/{REF_ID}")
        body = r.json()
        if isinstance(body, list):
            pytest.skip("Old format still deployed")

        assert body["estadisticas"]["nivel_confianza"] in ("alta", "media", "baja")

    def test_desierta_rate_is_proportion(self, api: httpx.Client):
        r = api.get(f"/similares/{REF_ID}")
        body = r.json()
        if isinstance(body, list):
            pytest.skip("Old format still deployed")

        tasa = body["estadisticas"]["tasa_desierta"]
        if tasa is not None:
            assert 0.0 <= tasa <= 1.0
