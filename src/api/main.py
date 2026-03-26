"""FastAPI application for licit — structured PLACSP procurement API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.catalogs import load as load_catalogs
from api.middleware import AuditMiddleware
from api.routes import (
    admin,
    auth,
    buscar,
    catalogos,
    empresa,
    licitacion,
    organo,
    salud,
    similares,
)
from shared.db import create_pool
from web.routes import router as web_router

_STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage the asyncpg connection pool lifecycle."""
    app.state.pool = await create_pool()
    await load_catalogs(app.state.pool)
    yield
    await app.state.pool.close()


app = FastAPI(
    title="licit",
    description=(
        "API estructurada de licitaciones publicas de Espana. "
        "Datos de la Plataforma de Contratacion del Sector Publico."
    ),
    version="0.3.0",
    lifespan=lifespan,
    docs_url="/docs",
)

app.add_middleware(AuditMiddleware)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

app.include_router(web_router)
app.include_router(salud.router)
app.include_router(auth.router, prefix="/v1")
app.include_router(admin.router, prefix="/v1")
app.include_router(buscar.router, prefix="/v1")
app.include_router(licitacion.router, prefix="/v1")
app.include_router(empresa.router, prefix="/v1")
app.include_router(organo.router, prefix="/v1")
app.include_router(similares.router, prefix="/v1")
app.include_router(catalogos.router, prefix="/v1")
