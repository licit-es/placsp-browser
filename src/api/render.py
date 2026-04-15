"""Content negotiation helpers for JSON/Markdown responses.

Routes build their Pydantic payload as usual and return
``negotiate(request, data, md_renderer)``. The client chooses format via
``Accept: text/markdown`` header or ``?format=md`` query parameter;
everything else gets the default JSON.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, PlainTextResponse, Response

MARKDOWN_MEDIA = "text/markdown"
_MARKDOWN_CONTENT_TYPE = f"{MARKDOWN_MEDIA}; charset=utf-8"
_MARKDOWN_FORMATS = frozenset({"md", "markdown"})

# Injected into route decorators via ``responses=MARKDOWN_RESPONSES`` so the
# OpenAPI schema advertises the additional content type. FastAPI merges this
# with the JSON schema derived from ``response_model``.
MARKDOWN_RESPONSES: dict[int | str, dict[str, Any]] = {
    200: {
        "content": {
            MARKDOWN_MEDIA: {
                "schema": {
                    "type": "string",
                    "description": (
                        "Representación markdown del recurso. Solicitar con "
                        "`Accept: text/markdown` o `?format=md`."
                    ),
                }
            }
        }
    }
}


def wants_markdown(request: Request) -> bool:
    """Return True when the caller has asked for markdown.

    Accepts two equivalent triggers:

    - ``?format=md`` (or ``?format=markdown``) query parameter — explicit,
      visible in audit logs, testable from a browser.
    - ``Accept: text/markdown`` header — standard content negotiation. If
      ``application/json`` or ``*/*`` appears before ``text/markdown``
      in the list, JSON wins (first match preference, no q-values parsed).
    """
    fmt = request.query_params.get("format")
    if fmt is not None:
        return fmt.lower() in _MARKDOWN_FORMATS

    accept = request.headers.get("accept", "")
    if not accept:
        return False
    for item in accept.split(","):
        media = item.split(";", 1)[0].strip().lower()
        if media == MARKDOWN_MEDIA:
            return True
        if media in {"application/json", "*/*"}:
            return False
    return False


def negotiate[T](
    request: Request,
    data: T,
    md_renderer: Callable[[T], str],
) -> Response:
    """Serialise ``data`` as markdown or JSON depending on the request.

    The markdown branch calls ``md_renderer(data)`` and returns a
    ``text/markdown; charset=utf-8`` response. The JSON branch runs
    ``data`` through FastAPI's ``jsonable_encoder`` so Pydantic models,
    lists of models, Decimals, datetimes, and UUIDs all serialise
    identically to the default pipeline.
    """
    if wants_markdown(request):
        return PlainTextResponse(
            md_renderer(data),
            media_type=_MARKDOWN_CONTENT_TYPE,
        )
    return JSONResponse(content=jsonable_encoder(data))
