"""API request/response schemas for agent-optimized PLACSP API."""
from __future__ import annotations

import base64
import json
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# -- Cursor helpers ----------------------------------------------------------


def encode_cursor(sort_value: Any, row_id: UUID) -> str:
    """Encode sort value + row id into an opaque cursor string."""
    sv = sort_value
    if isinstance(sv, (datetime, date, time)):
        sv = sv.isoformat()
    elif isinstance(sv, (Decimal, UUID)):
        sv = str(sv)
    payload = json.dumps({"s": sv, "i": str(row_id)})
    return base64.b64encode(payload.encode()).decode()


def decode_cursor(cursor: str) -> tuple[str, UUID]:
    """Decode an opaque cursor into (sort_value_str, row_id)."""
    data = json.loads(base64.b64decode(cursor))
    return data["s"], UUID(data["i"])


# -- Request schemas ---------------------------------------------------------


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
        description=(
            "Nombre del organo de contratacion. "
            "Busqueda parcial (ILIKE)."
        ),
        json_schema_extra={"examples": ["Ministerio"]},
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


# -- Response schemas --------------------------------------------------------


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


# -- Detail schemas ----------------------------------------------------------


class Criterio(BaseModel):
    """Criterio de adjudicacion con peso.

    Determina como se evaluan las ofertas. Los pesos suman 100
    (o el total que defina el pliego).
    """

    tipo: str | None = Field(
        description="Tipo de criterio (ej: Juicio de valor, Formula)."
    )
    subtipo: str | None = Field(description="Subtipo del criterio.")
    descripcion: str | None = Field(description="Descripcion del criterio.")
    peso: Decimal | None = Field(description="Puntuacion maxima / peso del criterio.")
    nota: str | None = Field(description="Nota adicional.")


class RequisitoSolvencia(BaseModel):
    """Requisito de solvencia para analisis GO/NO-GO.

    Determina si una empresa cumple los requisitos minimos para presentarse.
    """

    origen: str = Field(
        description="Tipo de solvencia: TECHNICAL, FINANCIAL, o DECLARATION."
    )
    tipo_evaluacion: str | None = Field(description="Tipo de criterio de evaluacion.")
    descripcion: str | None = Field(
        description="Descripcion del requisito tal como aparece en el pliego."
    )
    umbral: Decimal | None = Field(
        description="Importe minimo exigido (ej: volumen de negocios)."
    )
    situacion_personal: str | None = Field(
        description="Requisitos de situacion personal."
    )
    anios_experiencia: int | None = Field(
        description="Anos de experiencia exigidos."
    )
    num_empleados: int | None = Field(
        description="Numero minimo de empleados exigidos."
    )


class Documento(BaseModel):
    """Referencia a documento con URL directa al PDF."""

    tipo: str | None = Field(
        description=(
            "Tipo de documento (ej: Pliego, Anuncio de licitacion, "
            "Informe de valoracion, Acta de mesa)."
        )
    )
    nombre: str | None = Field(description="Nombre del fichero.")
    url: str | None = Field(description="URL directa al documento (normalmente PDF).")


class LoteResumen(BaseModel):
    """Lote dentro de una licitacion dividida en lotes.

    Cada lote puede tener sus propios criterios de adjudicacion,
    requisitos de solvencia y codigos CPV.
    """

    numero: str = Field(description="Numero del lote dentro de la licitacion.")
    titulo: str | None = Field(description="Titulo/objeto del lote.")
    presupuesto_sin_iva: Decimal | None = Field(
        description="Presupuesto del lote sin IVA (euros)."
    )
    cpv: list[str] = Field(description="Codigos CPV asignados al lote.")
    criterios: list[Criterio] = Field(
        description="Criterios de adjudicacion especificos del lote."
    )
    solvencia: list[RequisitoSolvencia] = Field(
        description="Requisitos de solvencia especificos del lote."
    )


class OrganoInfo(BaseModel):
    """Organo de contratacion."""

    id: UUID = Field(description="Identificador unico del organo.")
    nombre: str = Field(description="Nombre del organo de contratacion.")
    nif: str | None = Field(description="NIF del organo.")
    tipo: str | None = Field(
        description=(
            "Tipo de organo (ej: Administracion General del Estado, "
            "Comunidad Autonoma, Entidad Local)."
        )
    )


class AdjudicatarioInfo(BaseModel):
    """Empresa adjudicataria."""

    nombre: str = Field(description="Nombre o razon social.")
    nif: str | None = Field(description="NIF/CIF de la empresa.")


class ResultadoInfo(BaseModel):
    """Resultado de adjudicacion."""

    resultado: str | None = Field(
        description="Estado del resultado (ej: Adjudicacion definitiva, Formalizado)."
    )
    fecha_adjudicacion: date | None = Field(description="Fecha de adjudicacion.")
    importe_sin_iva: Decimal | None = Field(
        description="Importe adjudicado sin IVA (euros)."
    )
    num_licitadores: int | None = Field(description="Numero de ofertas recibidas.")
    adjudicatario: AdjudicatarioInfo | None = Field(
        description="Empresa que gano la licitacion."
    )
    fecha_formalizacion: date | None = Field(
        description="Fecha de formalizacion del contrato."
    )


class LicitacionDetalle(BaseModel):
    """Detalle completo de una licitacion.

    Un solo call devuelve toda la informacion estructurada:
    datos generales, criterios de adjudicacion, requisitos de solvencia,
    lotes, y documentos con URL directa al PDF.
    """

    id: UUID = Field(description="Identificador unico interno.")
    expediente: str | None = Field(description="Numero de expediente.")
    titulo: str | None = Field(description="Titulo/objeto del contrato.")
    descripcion: str | None = Field(description="Descripcion detallada del objeto.")
    url_place: str | None = Field(
        description="URL al expediente en la Plataforma de Contratacion."
    )

    tipo_contrato: str | None = Field(
        description="Tipo de contrato (Servicios, Obras, Suministros...)."
    )
    procedimiento: str | None = Field(
        description="Tipo de procedimiento (Abierto, Restringido...)."
    )
    tramitacion: str | None = Field(
        description="Tramitacion (Ordinaria, Urgente, Emergencia)."
    )
    sistema_contratacion: str | None = Field(
        description="Sistema de contratacion (Acuerdo marco, Sistema dinamico)."
    )

    presupuesto_sin_iva: Decimal | None = Field(
        description="Presupuesto base de licitacion sin IVA (euros)."
    )
    presupuesto_con_iva: Decimal | None = Field(
        description="Presupuesto base de licitacion con IVA (euros)."
    )
    valor_estimado: Decimal | None = Field(
        description="Valor estimado total incluyendo prorrogas y modificaciones."
    )

    fecha_publicacion: datetime = Field(description="Fecha de publicacion.")
    fecha_limite: date | None = Field(
        description="Fecha limite de presentacion de ofertas."
    )
    hora_limite: time | None = Field(
        description="Hora limite de presentacion de ofertas."
    )
    duracion: int | None = Field(description="Duracion del contrato.")
    duracion_unidad: str | None = Field(
        description="Unidad de duracion (ej: MON para meses, DAY para dias)."
    )

    estado: str = Field(description="Estado actual de la licitacion.")
    lugar_nuts: str | None = Field(
        description="Lugar de ejecucion (codigo NUTS resuelto a nombre)."
    )
    lugar: str | None = Field(description="Lugar de ejecucion (provincia/CCAA).")

    cpv_principal: str | None = Field(description="Codigo CPV principal.")
    cpv_secundarios: list[str] = Field(
        description="Codigos CPV secundarios."
    )

    tasa_subcontratacion: Decimal | None = Field(
        description="Porcentaje maximo de subcontratacion permitido."
    )
    programa_financiacion: str | None = Field(
        description="Programa de financiacion europea si aplica."
    )

    organo: OrganoInfo | None = Field(description="Organo de contratacion.")
    resultado: ResultadoInfo | None = Field(
        description="Resultado de la adjudicacion (solo si adjudicada/formalizada)."
    )
    criterios: list[Criterio] = Field(
        description="Criterios de adjudicacion a nivel de expediente."
    )
    solvencia: list[RequisitoSolvencia] = Field(
        description="Requisitos de solvencia a nivel de expediente."
    )
    lotes: list[LoteResumen] = Field(
        description="Lotes (vacio si la licitacion no esta dividida en lotes)."
    )
    documentos: list[Documento] = Field(
        description="Documentos disponibles (pliegos, resoluciones, actas)."
    )


# -- Empresa / Organo --------------------------------------------------------


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
