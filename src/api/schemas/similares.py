"""Response schemas for similar tenders with competitive intelligence."""

from __future__ import annotations

from pydantic import BaseModel, Field

from api.schemas.resumen import LicitacionResumen


class AdjudicatarioFrecuente(BaseModel):
    """Empresa que gana con frecuencia en licitaciones similares."""

    nombre: str = Field(description="Nombre del adjudicatario.")
    n: int = Field(description="Adjudicaciones en el pool de similares.")
    baja_media_pct: float | None = Field(
        description="Baja media ofertada (% sobre presupuesto)."
    )


class EstadisticasPrecio(BaseModel):
    """Distribucion de baja en licitaciones similares resueltas."""

    n: int = Field(description="Adjudicaciones con datos de precio.")
    p25: float = Field(description="Percentil 25 de baja (%).")
    mediana: float = Field(description="Mediana de baja (%).")
    p75: float = Field(description="Percentil 75 de baja (%).")


class EstadisticasCompetencia(BaseModel):
    """Distribucion de numero de licitadores."""

    media: float = Field(description="Media de licitadores.")
    mediana: float = Field(description="Mediana de licitadores.")


class EstadisticasSimilares(BaseModel):
    """Inteligencia competitiva agregada del pool de similares."""

    n: int = Field(description="Total de licitaciones similares encontradas.")
    baja_pct: EstadisticasPrecio | None = Field(
        None,
        description=("Distribucion de baja. null si < 3 adjudicaciones con datos."),
    )
    num_licitadores: EstadisticasCompetencia | None = Field(
        None,
        description="Distribucion de competidores. null si insuficiente.",
    )
    adjudicatarios_frecuentes: list[AdjudicatarioFrecuente] = Field(
        description="Top 5 empresas ganadoras en licitaciones similares."
    )
    tasa_desierta: float | None = Field(
        None,
        description=(
            "Proporcion de licitaciones terminales que quedaron desiertas (0.0-1.0)."
        ),
    )
    nivel_confianza: str = Field(description="alta (>=30), media (10-29), baja (<10).")
    factor_presupuesto: int = Field(
        description=(
            "Factor de amplitud presupuestaria usado (3=default, 5 o 10 si adaptativo)."
        ),
    )


class LicitacionSimilar(LicitacionResumen):
    """Licitacion con puntuacion de similitud."""

    similitud: int = Field(description="Puntuacion de similitud (0-9).")


class RespuestaSimilares(BaseModel):
    """Licitaciones similares con inteligencia competitiva."""

    resultados: list[LicitacionSimilar]
    estadisticas: EstadisticasSimilares
