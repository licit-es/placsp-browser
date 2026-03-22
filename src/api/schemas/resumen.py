"""Response schemas for search results."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


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
    fecha_publicacion: datetime = Field(description="Fecha de publicacion en PLACE.")
    fecha_adjudicacion: date | None = Field(
        description="Fecha de adjudicacion. Solo si estado >= Adjudicada."
    )
    cpv_principal: str | None = Field(
        description="Codigo CPV principal (ej: 72212000 para desarrollo software)."
    )
    num_licitadores: int | None = Field(
        description="Numero de ofertas recibidas."
    )
    adjudicatario: str | None = Field(
        description="Nombre de la empresa adjudicataria."
    )
    lugar: str | None = Field(description="Lugar de ejecucion (provincia/CCAA).")
    tiene_documentos: bool = Field(
        description="Indica si hay documentos (pliegos, resoluciones) disponibles."
    )
    num_lotes: int = Field(description="Numero de lotes. 0 si no esta dividido.")
    relevancia: float | None = Field(
        None, description="Puntuacion de relevancia FTS (solo con texto libre)."
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
