"""Unit tests for the content-negotiation helpers in api.render."""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from starlette.requests import Request

from api.render import MARKDOWN_MEDIA, MARKDOWN_RESPONSES, negotiate, wants_markdown


def _make_request(
    *,
    accept: str | None = None,
    fmt: str | None = None,
) -> Request:
    """Minimal Starlette request without spinning up the whole FastAPI app."""
    headers: list[tuple[bytes, bytes]] = []
    if accept is not None:
        headers.append((b"accept", accept.encode()))
    query_string = f"format={fmt}".encode() if fmt is not None else b""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
        "query_string": query_string,
    }
    return Request(scope)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# wants_markdown
# ---------------------------------------------------------------------------


class TestWantsMarkdown:
    def test_default_is_json(self) -> None:
        assert wants_markdown(_make_request()) is False

    def test_empty_accept_is_json(self) -> None:
        assert wants_markdown(_make_request(accept="")) is False

    @pytest.mark.parametrize("fmt", ["md", "markdown", "MD", "Markdown"])
    def test_format_md_query_param(self, fmt: str) -> None:
        assert wants_markdown(_make_request(fmt=fmt)) is True

    @pytest.mark.parametrize("fmt", ["json", "xml", "html", ""])
    def test_format_non_md_query_param(self, fmt: str) -> None:
        assert wants_markdown(_make_request(fmt=fmt)) is False

    def test_accept_markdown(self) -> None:
        assert wants_markdown(_make_request(accept="text/markdown")) is True

    def test_accept_json_is_false(self) -> None:
        assert wants_markdown(_make_request(accept="application/json")) is False

    def test_accept_wildcard_is_false(self) -> None:
        assert wants_markdown(_make_request(accept="*/*")) is False

    def test_accept_markdown_before_json_wins(self) -> None:
        assert (
            wants_markdown(_make_request(accept="text/markdown, application/json"))
            is True
        )

    def test_accept_json_before_markdown_wins_json(self) -> None:
        assert (
            wants_markdown(_make_request(accept="application/json, text/markdown"))
            is False
        )

    def test_accept_with_q_values_ignored(self) -> None:
        """q-values aren't parsed; first matching media wins."""
        assert (
            wants_markdown(
                _make_request(accept="text/markdown; q=0.9, application/json")
            )
            is True
        )

    def test_query_param_beats_header(self) -> None:
        """format=md overrides Accept: application/json."""
        assert (
            wants_markdown(_make_request(accept="application/json", fmt="md")) is True
        )

    def test_query_param_json_beats_markdown_header(self) -> None:
        """format=json overrides Accept: text/markdown."""
        assert (
            wants_markdown(_make_request(accept="text/markdown", fmt="json")) is False
        )


# ---------------------------------------------------------------------------
# negotiate
# ---------------------------------------------------------------------------


class _Thing(BaseModel):
    name: str
    amount: Decimal


def _render_thing(t: _Thing) -> str:
    return f"# {t.name}\n{t.amount}"


def _render_thing_list(ts: list[_Thing]) -> str:
    return "\n".join(f"- {t.name}" for t in ts)


class TestNegotiate:
    def test_json_default(self) -> None:
        thing = _Thing(name="foo", amount=Decimal("12.34"))
        resp = negotiate(_make_request(), thing, _render_thing)

        assert isinstance(resp, JSONResponse)
        assert resp.media_type == "application/json"
        body = resp.body.decode()
        assert '"name":"foo"' in body
        assert '"amount":"12.34"' in body

    def test_markdown_header(self) -> None:
        thing = _Thing(name="foo", amount=Decimal("12.34"))
        resp = negotiate(
            _make_request(accept="text/markdown"),
            thing,
            _render_thing,
        )

        assert isinstance(resp, PlainTextResponse)
        assert resp.media_type is not None
        assert resp.media_type.startswith(MARKDOWN_MEDIA)
        assert resp.body.decode() == "# foo\n12.34"

    def test_markdown_query_param(self) -> None:
        thing = _Thing(name="foo", amount=Decimal("12.34"))
        resp = negotiate(_make_request(fmt="md"), thing, _render_thing)

        assert isinstance(resp, PlainTextResponse)
        assert resp.body.decode() == "# foo\n12.34"

    def test_list_of_models_json(self) -> None:
        things = [
            _Thing(name="a", amount=Decimal("1")),
            _Thing(name="b", amount=Decimal("2")),
        ]
        resp = negotiate(_make_request(), things, _render_thing_list)

        assert isinstance(resp, JSONResponse)
        body = resp.body.decode()
        assert '"name":"a"' in body
        assert '"name":"b"' in body

    def test_list_of_models_markdown(self) -> None:
        things = [
            _Thing(name="a", amount=Decimal("1")),
            _Thing(name="b", amount=Decimal("2")),
        ]
        resp = negotiate(_make_request(fmt="md"), things, _render_thing_list)

        assert resp.body.decode() == "- a\n- b"


# ---------------------------------------------------------------------------
# MARKDOWN_RESPONSES constant
# ---------------------------------------------------------------------------


def test_markdown_responses_declares_text_markdown() -> None:
    assert MARKDOWN_MEDIA in MARKDOWN_RESPONSES[200]["content"]
    schema = MARKDOWN_RESPONSES[200]["content"][MARKDOWN_MEDIA]["schema"]
    assert schema["type"] == "string"
