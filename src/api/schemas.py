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
    """Structured filters for search."""

    tipo_contrato: list[str] | None = None
    estado: list[str] | None = None
    cpv_prefijo: str | None = None
    importe_min: Decimal | None = None
    importe_max: Decimal | None = None
    fecha_publicacion_desde: date | None = None
    fecha_publicacion_hasta: date | None = None
    procedimiento: list[str] | None = None
    ccaa: str | None = None
    adjudicatario: str | None = None
    organo: str | None = None
    financiacion_ue: bool | None = None


class PeticionBusqueda(BaseModel):
    """Search request body."""

    q: str | None = None
    filtros: FiltrosBusqueda | None = None
    ordenar: Literal["relevancia", "fecha", "importe"] = "fecha"
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = None


# -- Response schemas --------------------------------------------------------


class LicitacionResumen(BaseModel):
    """Summary of a tender for search results (dense, no detail call needed)."""

    id: UUID
    expediente: str | None
    titulo: str | None
    organo: str | None
    tipo_contrato: str | None
    estado: str
    presupuesto_sin_iva: Decimal | None
    importe_adjudicacion: Decimal | None
    fecha_publicacion: datetime
    fecha_adjudicacion: date | None
    cpv_principal: str | None
    num_licitadores: int | None
    adjudicatario: str | None
    lugar: str | None
    tiene_documentos: bool
    num_lotes: int
    relevancia: float | None = None


class RespuestaBusqueda(BaseModel):
    """Search response with cursor pagination."""

    total: int
    resultados: list[LicitacionResumen]
    cursor_siguiente: str | None = None


# -- Detail schemas ----------------------------------------------------------


class Criterio(BaseModel):
    """Awarding criterion."""

    tipo: str | None
    subtipo: str | None
    descripcion: str | None
    peso: Decimal | None
    nota: str | None


class RequisitoSolvencia(BaseModel):
    """Qualification requirement for GO/NO-GO analysis."""

    origen: str
    tipo_evaluacion: str | None
    descripcion: str | None
    umbral: Decimal | None
    situacion_personal: str | None
    anios_experiencia: int | None
    num_empleados: int | None


class Documento(BaseModel):
    """Document reference with direct URL."""

    tipo: str | None
    nombre: str | None
    url: str | None


class LoteResumen(BaseModel):
    """Lot within a tender."""

    numero: str
    titulo: str | None
    presupuesto_sin_iva: Decimal | None
    cpv: list[str]
    criterios: list[Criterio]
    solvencia: list[RequisitoSolvencia]


class OrganoInfo(BaseModel):
    """Contracting body info embedded in detail."""

    id: UUID
    nombre: str
    nif: str | None
    tipo: str | None


class AdjudicatarioInfo(BaseModel):
    """Winning party info."""

    nombre: str
    nif: str | None


class ResultadoInfo(BaseModel):
    """Award result info."""

    resultado: str | None
    fecha_adjudicacion: date | None
    importe_sin_iva: Decimal | None
    num_licitadores: int | None
    adjudicatario: AdjudicatarioInfo | None
    fecha_formalizacion: date | None


class LicitacionDetalle(BaseModel):
    """Full tender detail — one call returns everything."""

    id: UUID
    expediente: str | None
    titulo: str | None
    descripcion: str | None
    url_place: str | None

    tipo_contrato: str | None
    procedimiento: str | None
    tramitacion: str | None
    sistema_contratacion: str | None

    presupuesto_sin_iva: Decimal | None
    presupuesto_con_iva: Decimal | None
    valor_estimado: Decimal | None

    fecha_publicacion: datetime
    fecha_limite: date | None
    hora_limite: time | None
    duracion: int | None
    duracion_unidad: str | None

    estado: str
    lugar_nuts: str | None
    lugar: str | None

    cpv_principal: str | None
    cpv_secundarios: list[str]

    tasa_subcontratacion: Decimal | None
    programa_financiacion: str | None

    organo: OrganoInfo | None
    resultado: ResultadoInfo | None
    criterios: list[Criterio]
    solvencia: list[RequisitoSolvencia]
    lotes: list[LoteResumen]
    documentos: list[Documento]


# -- Empresa / Organo --------------------------------------------------------


class EmpresaStats(BaseModel):
    """Aggregated stats for a company."""

    contratos_adjudicados: int
    importe_total: Decimal | None
    importe_medio: Decimal | None
    cpv_frecuentes: list[str]
    organos_frecuentes: list[str]
    baja_media_pct: Decimal | None


class EmpresaDetalle(BaseModel):
    """Company profile from adjudication history."""

    nif: str
    nombre: str
    stats: EmpresaStats
    adjudicaciones_recientes: list[LicitacionResumen]


class OrganoStats(BaseModel):
    """Aggregated stats for a contracting body."""

    total_licitaciones: int
    importe_medio: Decimal | None
    cpv_frecuentes: list[str]
    plazo_medio_adjudicacion_dias: int | None


class OrganoDetalle(BaseModel):
    """Contracting body profile."""

    id: UUID
    nombre: str
    nif: str | None
    tipo: str | None
    stats: OrganoStats
    licitaciones_recientes: list[LicitacionResumen]
