"""FastAPI application for browsing PLACSP procurement data."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from api.routes import contratos, documentos, lotes, organos_contratantes, salud
from shared.db import create_pool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage the asyncpg connection pool lifecycle."""
    app.state.pool = await create_pool()
    yield
    await app.state.pool.close()


app = FastAPI(
    title="PLACSP Browser",
    description=(
        "API para explorar datos de licitaciones publicas de la "
        "Plataforma de Contratacion del Sector Publico (PLACSP)."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(salud.router)
app.include_router(contratos.router, prefix="/api/v1")
app.include_router(organos_contratantes.router, prefix="/api/v1")
app.include_router(lotes.router, prefix="/api/v1")
app.include_router(documentos.router, prefix="/api/v1")
