"""Response schemas for GET /organo/{id}."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from api.schemas.resumen import LicitacionResumen


class OrganoStats(BaseModel):
    """Estadisticas agregadas de un organo de contratacion."""

    total_licitaciones: int = Field(
        description="Numero total de licitaciones publicadas."
    )
    importe_medio: Decimal | None = Field(
        description="Presupuesto medio de sus licitaciones (euros)."
    )
    cpv_frecuentes: list[str] = Field(
        description="Top 5 codigos CPV mas frecuentes."
    )
    plazo_medio_adjudicacion_dias: int | None = Field(
        description="Dias promedio entre publicacion y adjudicacion."
    )


class OrganoDetalle(BaseModel):
    """Perfil de organo de contratacion."""

    id: UUID = Field(description="Identificador unico del organo.")
    nombre: str = Field(description="Nombre del organo.")
    nif: str | None = Field(description="NIF del organo.")
    tipo: str | None = Field(description="Tipo de organo (AGE, CCAA, Local...).")
    stats: OrganoStats = Field(description="Estadisticas agregadas.")
    licitaciones_recientes: list[LicitacionResumen] = Field(
        description="Ultimas 20 licitaciones publicadas."
    )
