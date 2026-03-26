"""Web page routes: landing, registration, login, dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from api.deps import get_conn
from web.stats import fetch_landing_stats

_TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

router = APIRouter(tags=["Web"], include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
async def landing(
    request: Request,
    conn: asyncpg.Connection = Depends(get_conn),
) -> HTMLResponse:
    """Render the landing page with live stats."""
    stats = await fetch_landing_stats(conn)
    ctx: dict[str, Any] = {"request": request, "stats": stats}
    return templates.TemplateResponse("inicio.html", ctx)


@router.get("/registro", response_class=HTMLResponse)
async def registro(request: Request) -> HTMLResponse:
    """Render the registration page."""
    return templates.TemplateResponse("registro.html", {"request": request})


@router.get("/iniciar-sesion", response_class=HTMLResponse)
async def login(request: Request) -> HTMLResponse:
    """Render the login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/panel", response_class=HTMLResponse)
async def panel(request: Request) -> HTMLResponse:
    """Render the dashboard page."""
    return templates.TemplateResponse("panel.html", {"request": request})
