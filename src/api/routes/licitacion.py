"""GET /licitacion/{id} — full tender detail."""
from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_conn
from api.schemas import (
    AdjudicatarioInfo,
    Criterio,
    Documento,
    LicitacionDetalle,
    LoteResumen,
    OrganoInfo,
    RequisitoSolvencia,
    ResultadoInfo,
)

router = APIRouter(tags=["Licitaciones"])


def _parse_criterios(rows: list[asyncpg.Record]) -> list[Criterio]:
    return [
        Criterio(
            tipo=r["criteria_type_code"],
            subtipo=r["criteria_sub_type_code"],
            descripcion=r["description"],
            peso=r["weight_numeric"],
            nota=r["note"],
        )
        for r in rows
    ]


def _parse_solvencia(rows: list[asyncpg.Record]) -> list[RequisitoSolvencia]:
    return [
        RequisitoSolvencia(
            origen=r["origin_type"],
            tipo_evaluacion=r["evaluation_criteria_type_code"],
            descripcion=r["description"],
            umbral=r["threshold_quantity"],
            situacion_personal=r["personal_situation"],
            anios_experiencia=r["operating_years_quantity"],
            num_empleados=r["employee_quantity"],
        )
        for r in rows
    ]


@router.get(
    "/licitacion/{licitacion_id}",
    response_model=LicitacionDetalle,
    summary="Detalle completo de una licitacion",
)
async def get_licitacion(
    licitacion_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),  # type: ignore[assignment]  # noqa: B008
) -> LicitacionDetalle:
    """Return full tender detail with nested criterios, solvencia, lotes, docs."""
    # Main record from view
    row = await conn.fetchrow(
        "SELECT * FROM v_licitacion WHERE id = $1", licitacion_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Licitacion no encontrada")

    # Parallel fetches for nested data
    criterios_rows, solvencia_rows, lotes_rows, docs_rows, cpv_rows = (
        await conn.fetch(
            "SELECT * FROM awarding_criteria"
            " WHERE contract_folder_status_id = $1 AND lot_id IS NULL"
            " ORDER BY weight_numeric DESC NULLS LAST",
            licitacion_id,
        ),
        await conn.fetch(
            "SELECT * FROM qualification_requirement"
            " WHERE contract_folder_status_id = $1 AND lot_id IS NULL",
            licitacion_id,
        ),
        await conn.fetch(
            "SELECT * FROM procurement_project_lot"
            " WHERE contract_folder_status_id = $1 ORDER BY lot_number",
            licitacion_id,
        ),
        await conn.fetch(
            "SELECT document_type_code, filename, uri"
            " FROM document_reference"
            " WHERE contract_folder_status_id = $1",
            licitacion_id,
        ),
        await conn.fetch(
            "SELECT item_classification_code FROM cpv_classification"
            " WHERE contract_folder_status_id = $1 AND lot_id IS NULL",
            licitacion_id,
        ),
    )

    # Build lotes with their own criterios/solvencia/cpvs
    lotes: list[LoteResumen] = []
    for lot_row in lotes_rows:
        lot_id = lot_row["id"]
        lot_criterios = await conn.fetch(
            "SELECT * FROM awarding_criteria WHERE lot_id = $1"
            " ORDER BY weight_numeric DESC NULLS LAST",
            lot_id,
        )
        lot_solvencia = await conn.fetch(
            "SELECT * FROM qualification_requirement WHERE lot_id = $1",
            lot_id,
        )
        lot_cpvs = await conn.fetch(
            "SELECT item_classification_code FROM cpv_classification"
            " WHERE lot_id = $1",
            lot_id,
        )
        lotes.append(
            LoteResumen(
                numero=lot_row["lot_number"],
                titulo=lot_row["name"],
                presupuesto_sin_iva=lot_row["tax_exclusive_amount"],
                cpv=[c["item_classification_code"] for c in lot_cpvs],
                criterios=_parse_criterios(lot_criterios),
                solvencia=_parse_solvencia(lot_solvencia),
            )
        )

    # CPVs
    cpv_codes = [c["item_classification_code"] for c in cpv_rows]
    cpv_principal = cpv_codes[0] if cpv_codes else row["cpv_principal"]
    cpv_secundarios = cpv_codes[1:] if len(cpv_codes) > 1 else []

    # Result
    resultado = None
    if row["result_code"]:
        adj = None
        if row["adjudicatario"]:
            adj = AdjudicatarioInfo(
                nombre=row["adjudicatario"],
                nif=row["adjudicatario_nif"],
            )
        resultado = ResultadoInfo(
            resultado=row["result_code"],
            fecha_adjudicacion=row["fecha_adjudicacion"],
            importe_sin_iva=row["importe_adjudicacion"],
            num_licitadores=row["num_licitadores"],
            adjudicatario=adj,
            fecha_formalizacion=row["fecha_formalizacion"],
        )

    # Organo
    organo = None
    if row["organo_id"]:
        organo = OrganoInfo(
            id=row["organo_id"],
            nombre=row["organo"],
            nif=row["organo_nif"],
            tipo=row["organo_tipo"],
        )

    return LicitacionDetalle(
        id=row["id"],
        expediente=row["expediente"],
        titulo=row["titulo"],
        descripcion=row["descripcion"],
        url_place=None,  # Not stored in schema
        tipo_contrato=row["tipo_contrato"],
        procedimiento=row["procedimiento"],
        tramitacion=row["tramitacion"],
        sistema_contratacion=row["sistema_contratacion"],
        presupuesto_sin_iva=row["presupuesto_sin_iva"],
        presupuesto_con_iva=row["presupuesto_con_iva"],
        valor_estimado=row["valor_estimado"],
        fecha_publicacion=row["fecha_publicacion"],
        fecha_limite=row["fecha_limite"],
        hora_limite=row["hora_limite"],
        duracion=row["duracion"],
        duracion_unidad=row["duracion_unidad"],
        estado=row["estado"],
        lugar_nuts=row["lugar_nuts"],
        lugar=row["lugar_subentidad"],
        cpv_principal=cpv_principal,
        cpv_secundarios=cpv_secundarios,
        tasa_subcontratacion=row["tasa_subcontratacion"],
        programa_financiacion=row["programa_financiacion"],
        organo=organo,
        resultado=resultado,
        criterios=_parse_criterios(criterios_rows),
        solvencia=_parse_solvencia(solvencia_rows),
        lotes=lotes,
        documentos=[
            Documento(
                tipo=d["document_type_code"],
                nombre=d["filename"],
                url=d["uri"],
            )
            for d in docs_rows
        ],
    )
