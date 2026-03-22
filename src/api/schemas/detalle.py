"""Response schemas for GET /licitacion/{id} detail endpoint."""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


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
    cpv_secundarios: list[str] = Field(description="Codigos CPV secundarios.")

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
