"""Response schemas for search results."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class CambioEstado(BaseModel):
    """Entrada en el historial de estados de una licitacion."""

    estado: str = Field(description="Estado (Publicada, Adjudicada...).")
    fecha: datetime = Field(description="Fecha del cambio de estado.")


class DocumentoResumen(BaseModel):
    """Referencia a documento dentro de un resumen de licitacion."""

    tipo: str | None = Field(description="Tipo de documento (Pliego, Anuncio...).")
    nombre: str | None = Field(description="Nombre del fichero.")
    url: str | None = Field(description="URL directa al documento.")


# Materialized view used by all read-only API routes.
# Switch to "v_licitacion" to bypass the matview if needed.
LICITACION_VIEW = "mv_licitacion"

# SQL columns shared by every route that queries the licitacion view.
# Import and interpolate as f"SELECT {DISPLAY_COLS} FROM {LICITACION_VIEW} v".
DISPLAY_COLS = (
    "v.id, v.expediente, v.titulo, v.organo,"
    " v.tipo_contrato, v.estado, v.presupuesto_sin_iva,"
    " v.importe_adjudicacion, v.fecha_publicacion,"
    " v.fecha_actualizacion, v.fecha_adjudicacion,"
    " v.cpv_principal, v.num_licitadores, v.adjudicatario,"
    " v.lugar_subentidad AS lugar,"
    " v.tiene_documentos, v.num_lotes,"
    " v.historial_estados"
)


class LicitacionResumen(BaseModel):
    """Resumen de licitacion para resultados de busqueda.

    Incluye todos los campos necesarios para triaje rapido
    sin necesidad de llamar al endpoint de detalle.
    """

    id: UUID = Field(description="Identificador unico interno.")
    expediente: str | None = Field(
        description="Numero de expediente (contract_folder_id en CODICE)."
    )
    titulo: str | None = Field(description="Titulo/objeto del contrato.")
    organo: str | None = Field(description="Nombre del organo de contratacion.")
    tipo_contrato: str | None = Field(
        description="Tipo de contrato (Servicios, Obras, Suministros...)."
    )
    estado: str = Field(
        description="Estado actual (Publicada, Adjudicada, Formalizada...)."
    )
    presupuesto_sin_iva: Decimal | None = Field(
        description="Presupuesto base de licitacion sin IVA (euros)."
    )
    importe_adjudicacion: Decimal | None = Field(
        description="Importe de adjudicacion sin IVA. Solo si estado >= Adjudicada."
    )
    fecha_publicacion: datetime = Field(
        description="Fecha de primera publicacion en PLACE."
    )
    fecha_actualizacion: datetime = Field(
        description=(
            "Fecha de ultima actualizacion en PLACE. "
            "Comparar con valor almacenado para detectar cambios."
        )
    )
    fecha_adjudicacion: date | None = Field(
        description="Fecha de adjudicacion. Solo si estado >= Adjudicada."
    )
    cpv_principal: str | None = Field(
        description="Codigo CPV principal (ej: 72212000 para desarrollo software)."
    )
    num_licitadores: int | None = Field(description="Numero de ofertas recibidas.")
    adjudicatario: str | None = Field(description="Nombre de la empresa adjudicataria.")
    lugar: str | None = Field(description="Lugar de ejecucion (provincia/CCAA).")
    tiene_documentos: bool = Field(
        description="Indica si hay documentos (pliegos, resoluciones) disponibles."
    )
    num_lotes: int = Field(description="Numero de lotes. 0 si no esta dividido.")
    historial_estados: list[CambioEstado] = Field(
        description=(
            "Timeline de estados de la licitacion, ordenado "
            "cronologicamente (Publicada, Adjudicada...)."
        )
    )

    @field_validator("historial_estados", mode="before")
    @classmethod
    def _parse_jsonb(cls, v: object) -> object:
        """asyncpg returns JSONB from view columns as str."""
        if isinstance(v, str):
            return json.loads(v)
        return v or []

    documentos: list[DocumentoResumen] | None = Field(
        None,
        description=(
            "Documentos disponibles para descarga. "
            "Presente en /buscar, null en otros endpoints."
        ),
    )
    relevancia: float | None = Field(
        None, description="Puntuacion de relevancia FTS (solo con texto libre)."
    )

    @classmethod
    def from_row(cls, r: object, **extras: object) -> Self:
        """Build from an asyncpg.Record (or any mapping).

        Extra keyword args are forwarded to the constructor, so callers
        can pass ``documentos=...``, ``relevancia=...``, etc.
        """
        return cls(
            id=r["id"],  # type: ignore[index]
            expediente=r["expediente"],  # type: ignore[index]
            titulo=r["titulo"],  # type: ignore[index]
            organo=r["organo"],  # type: ignore[index]
            tipo_contrato=r["tipo_contrato"],  # type: ignore[index]
            estado=r["estado"],  # type: ignore[index]
            presupuesto_sin_iva=r["presupuesto_sin_iva"],  # type: ignore[index]
            importe_adjudicacion=r["importe_adjudicacion"],  # type: ignore[index]
            fecha_publicacion=r["fecha_publicacion"],  # type: ignore[index]
            fecha_actualizacion=r["fecha_actualizacion"],  # type: ignore[index]
            fecha_adjudicacion=r["fecha_adjudicacion"],  # type: ignore[index]
            cpv_principal=r["cpv_principal"],  # type: ignore[index]
            num_licitadores=r["num_licitadores"],  # type: ignore[index]
            adjudicatario=r["adjudicatario"],  # type: ignore[index]
            lugar=r["lugar"],  # type: ignore[index]
            tiene_documentos=r["tiene_documentos"],  # type: ignore[index]
            num_lotes=r["num_lotes"],  # type: ignore[index]
            historial_estados=r["historial_estados"] or [],  # type: ignore[index]
            **extras,
        )


class RespuestaBusqueda(BaseModel):
    """Respuesta de busqueda con paginacion por cursor."""

    total: int = Field(description="Total de resultados que coinciden con la busqueda.")
    resultados: list[LicitacionResumen]
    cursor_siguiente: str | None = Field(
        None,
        description=(
            "Cursor opaco para obtener la siguiente pagina. "
            "null si no hay mas resultados."
        ),
    )
