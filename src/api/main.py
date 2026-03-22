"""FastAPI application for agent-optimized PLACSP procurement search."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.catalogs import load as load_catalogs
from api.routes import (
    buscar,
    catalogos,
    empresa,
    licitacion,
    organo,
    salud,
    similares,
)
from shared.db import create_pool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage the asyncpg connection pool lifecycle."""
    app.state.pool = await create_pool()
    await load_catalogs(app.state.pool)
    yield
    await app.state.pool.close()


app = FastAPI(
    title="PLACSP API",
    description=(
        "API optimizada para agentes: busqueda unificada de licitaciones "
        "de la Plataforma de Contratacion del Sector Publico."
    ),
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(salud.router)
app.include_router(buscar.router, prefix="/api/v1")
app.include_router(licitacion.router, prefix="/api/v1")
app.include_router(empresa.router, prefix="/api/v1")
app.include_router(organo.router, prefix="/api/v1")
app.include_router(similares.router, prefix="/api/v1")
app.include_router(catalogos.router, prefix="/api/v1")
