"""End-to-end content negotiation checks against the running FastAPI app.

Exercises both triggers (``Accept: text/markdown``, ``?format=md``), verifies
JSON stays the default, and confirms 4xx error payloads keep returning JSON.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient


class TestDefaultIsJson:
    def test_empresas_default_json(
        self, auth_client: TestClient, auth_conn: AsyncMock
    ) -> None:
        auth_conn.fetch = AsyncMock(return_value=[])
        resp = auth_client.post("/v1/empresas", json={"q": "foo"})

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")
        assert resp.json() == []


class TestAcceptHeader:
    def test_markdown_via_accept(
        self, auth_client: TestClient, auth_conn: AsyncMock
    ) -> None:
        auth_conn.fetch = AsyncMock(return_value=[])
        resp = auth_client.post(
            "/v1/empresas",
            json={"q": "foo"},
            headers={"Accept": "text/markdown"},
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/markdown")
        assert "# Empresas (0 resultados)" in resp.text

    def test_json_via_accept_header(
        self, auth_client: TestClient, auth_conn: AsyncMock
    ) -> None:
        auth_conn.fetch = AsyncMock(return_value=[])
        resp = auth_client.post(
            "/v1/empresas",
            json={"q": "foo"},
            headers={"Accept": "application/json"},
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")


class TestQueryParam:
    def test_markdown_via_format_md(
        self, auth_client: TestClient, auth_conn: AsyncMock
    ) -> None:
        auth_conn.fetch = AsyncMock(return_value=[])
        resp = auth_client.post("/v1/empresas?format=md", json={"q": "foo"})

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/markdown")
        assert "# Empresas" in resp.text

    def test_format_markdown_long_form(
        self, auth_client: TestClient, auth_conn: AsyncMock
    ) -> None:
        auth_conn.fetch = AsyncMock(return_value=[])
        resp = auth_client.post("/v1/empresas?format=markdown", json={"q": "foo"})

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/markdown")

    def test_query_param_overrides_accept(
        self, auth_client: TestClient, auth_conn: AsyncMock
    ) -> None:
        auth_conn.fetch = AsyncMock(return_value=[])
        resp = auth_client.post(
            "/v1/empresas?format=md",
            json={"q": "foo"},
            headers={"Accept": "application/json"},
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/markdown")


class TestErrorsStayJson:
    def test_404_stays_json_even_with_md_accept(
        self, auth_client: TestClient, auth_conn: AsyncMock
    ) -> None:
        auth_conn.fetchrow = AsyncMock(return_value=None)
        resp = auth_client.get(
            "/v1/empresa/X12345",
            headers={"Accept": "text/markdown"},
        )

        assert resp.status_code == 404
        assert resp.headers["content-type"].startswith("application/json")
        assert resp.json() == {"detail": "Empresa no encontrada"}


class TestOpenApiDeclaresMarkdown:
    def test_text_markdown_declared_on_empresas(self, auth_client: TestClient) -> None:
        schema = auth_client.get("/openapi.json").json()
        responses = schema["paths"]["/v1/empresas"]["post"]["responses"]
        assert "text/markdown" in responses["200"]["content"]

    def test_text_markdown_declared_on_buscar(self, auth_client: TestClient) -> None:
        schema = auth_client.get("/openapi.json").json()
        responses = schema["paths"]["/v1/buscar"]["post"]["responses"]
        assert "text/markdown" in responses["200"]["content"]

    def test_text_markdown_declared_on_licitacion_detail(
        self, auth_client: TestClient
    ) -> None:
        schema = auth_client.get("/openapi.json").json()
        responses = schema["paths"]["/v1/licitacion/{licitacion_id}"]["get"][
            "responses"
        ]
        assert "text/markdown" in responses["200"]["content"]
