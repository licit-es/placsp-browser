"""Response schemas for GET /empresa/{nif}."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from api.schemas.resumen import LicitacionResumen


class EmpresaResumen(BaseModel):
    """Resultado de busqueda de empresa adjudicataria."""

    nif: str = Field(description="NIF/CIF de la empresa.")
    nombre: str = Field(description="Nombre o razon social.")
    contratos: int = Field(description="Numero de contratos adjudicados.")


class EmpresaStats(BaseModel):
    """Estadisticas agregadas de una empresa adjudicataria."""

    contratos_adjudicados: int = Field(
        description="Numero total de contratos adjudicados."
    )
    importe_total: Decimal | None = Field(
        description="Suma de todos los importes adjudicados (euros)."
    )
    importe_medio: Decimal | None = Field(
        description="Importe medio por adjudicacion (euros)."
    )
    cpv_frecuentes: list[str] = Field(
        description="Top 5 codigos CPV mas frecuentes en sus adjudicaciones."
    )
    organos_frecuentes: list[str] = Field(
        description="Top 5 organos de contratacion que mas le adjudican."
    )
    baja_media_pct: Decimal | None = Field(
        description=(
            "Porcentaje medio de baja sobre el presupuesto base. "
            "Ej: 15.3 significa que oferta un 15.3% menos que el presupuesto."
        )
    )


class EmpresaDetalle(BaseModel):
    """Perfil de empresa a partir de su historial de adjudicaciones."""

    nif: str = Field(description="NIF/CIF de la empresa.")
    nombre: str = Field(description="Nombre o razon social.")
    stats: EmpresaStats = Field(description="Estadisticas agregadas.")
    adjudicaciones_recientes: list[LicitacionResumen] = Field(
        description="Ultimas 20 adjudicaciones."
    )
