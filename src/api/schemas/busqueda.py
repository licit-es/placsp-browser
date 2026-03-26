"""Request schemas for POST /buscar."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class FiltrosBusqueda(BaseModel):
    """Filtros estructurados para busqueda de licitaciones.

    Todos los filtros son opcionales y se combinan con AND.
    Los valores de texto aceptan tanto etiquetas legibles como codigos CODICE.
    Consultar GET /catalogos/{tipo} para ver valores validos.
    """

    tipo_contrato: list[str] | None = Field(
        None,
        description=(
            "Tipo de contrato. Valores: Suministros, Servicios, Obras, "
            "Concesion de Obras, Concesion de Servicios, "
            "Colaboracion entre sector publico y privado, "
            "Administrativo especial, Privado. "
            "Ver GET /catalogos/tipo_contrato"
        ),
        json_schema_extra={"examples": [["Servicios", "Suministros"]]},
    )
    estado: list[str] | None = Field(
        None,
        description=(
            "Estado de la licitacion. Valores tipicos: "
            "Anuncio previo, Publicada, En plazo, Pendiente de adjudicacion, "
            "Adjudicada, Formalizada, Anulada, Resuelta. "
            "Ver GET /catalogos/estado"
        ),
        json_schema_extra={"examples": [["Adjudicada", "Formalizada"]]},
    )
    cpv_prefijo: str | None = Field(
        None,
        description=(
            "Prefijo de codigo CPV (Common Procurement Vocabulary). "
            "Ej: '72' para IT, '722' para desarrollo software, "
            "'45' para construccion. Ver GET /catalogos/cpv"
        ),
        json_schema_extra={"examples": ["722"]},
    )
    importe_min: Decimal | None = Field(
        None,
        description="Presupuesto base sin IVA minimo (euros).",
        json_schema_extra={"examples": [50000]},
    )
    importe_max: Decimal | None = Field(
        None,
        description="Presupuesto base sin IVA maximo (euros).",
        json_schema_extra={"examples": [500000]},
    )
    fecha_publicacion_desde: date | None = Field(
        None,
        description="Fecha de publicacion minima (ISO 8601).",
        json_schema_extra={"examples": ["2024-01-01"]},
    )
    fecha_publicacion_hasta: date | None = Field(
        None,
        description="Fecha de publicacion maxima (ISO 8601).",
        json_schema_extra={"examples": ["2025-12-31"]},
    )
    procedimiento: list[str] | None = Field(
        None,
        description=(
            "Tipo de procedimiento. Valores: Abierto, Restringido, "
            "Negociado con publicidad, Negociado sin publicidad, "
            "Dialogo competitivo, Asociacion para la innovacion, "
            "Basado en Acuerdo Marco, Otros. "
            "Ver GET /catalogos/procedimiento"
        ),
        json_schema_extra={"examples": [["Abierto"]]},
    )
    ccaa: str | None = Field(
        None,
        description=(
            "Comunidad autonoma / provincia. "
            "Busqueda parcial (ILIKE) en lugar de ejecucion."
        ),
        json_schema_extra={"examples": ["Madrid"]},
    )
    adjudicatario: str | None = Field(
        None,
        description=(
            "Nombre de la empresa adjudicataria. "
            "Busqueda parcial (ILIKE) en todas las adjudicaciones."
        ),
        json_schema_extra={"examples": ["Indra"]},
    )
    organo: str | None = Field(
        None,
        description="Nombre del organo de contratacion. Busqueda parcial (ILIKE).",
        json_schema_extra={"examples": ["Ministerio"]},
    )
    organo_id: UUID | None = Field(
        None,
        description=(
            "Identificador UUID del organo de contratacion. "
            "Filtro exacto; tiene prioridad sobre 'organo' textual."
        ),
    )
    financiacion_ue: bool | None = Field(
        None,
        description="Filtrar por financiacion europea (FEDER, Next Gen, etc.).",
    )


class PeticionBusqueda(BaseModel):
    """Peticion de busqueda unificada.

    Combina texto libre con filtros estructurados opcionales.
    Paginacion basada en cursor opaco.
    """

    q: str | None = Field(
        None,
        description=(
            "Texto libre. Busca en titulo y descripcion de la licitacion "
            "usando busqueda full-text en espanol."
        ),
        json_schema_extra={
            "examples": ["mantenimiento plataforma contratacion electronica"]
        },
    )
    filtros: FiltrosBusqueda | None = Field(
        None, description="Filtros estructurados opcionales (combinados con AND)."
    )
    ordenar: Literal["relevancia", "fecha", "importe"] = Field(
        "fecha",
        description=(
            "Criterio de ordenacion. "
            "'relevancia' solo tiene efecto con texto libre (q)."
        ),
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Numero maximo de resultados por pagina.",
    )
    cursor: str | None = Field(
        None,
        description=(
            "Cursor opaco para paginacion. "
            "Usar el valor de cursor_siguiente de la respuesta anterior."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "q": "servicios desarrollo software",
                    "filtros": {
                        "tipo_contrato": ["Servicios"],
                        "estado": ["Adjudicada", "Formalizada"],
                        "cpv_prefijo": "722",
                        "importe_min": 50000,
                        "importe_max": 500000,
                        "procedimiento": ["Abierto"],
                    },
                    "ordenar": "fecha",
                    "limit": 20,
                }
            ]
        }
    }
