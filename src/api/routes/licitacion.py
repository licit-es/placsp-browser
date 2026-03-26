"""GET /licitacion/{id} — full tender detail."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_conn
from api.schemas import (
    LICITACION_VIEW,
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


@router.get(
    "/licitacion/{licitacion_id}",
    response_model=LicitacionDetalle,
    summary="Detalle completo de una licitacion",
)
async def get_licitacion(
    licitacion_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
) -> LicitacionDetalle:
    """Return full tender detail with nested criterios, solvencia, lotes, docs."""
    row = await conn.fetchrow(
        f"SELECT * FROM {LICITACION_VIEW} WHERE id = $1", licitacion_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Licitacion no encontrada")

    # Nested data from presentation views
    criterios_rows, solvencia_rows, docs_rows, cpv_rows, lotes_rows = (
        await conn.fetch(
            "SELECT tipo, subtipo, descripcion, peso, nota"
            " FROM v_criterio WHERE licitacion_id = $1 AND lote_id IS NULL"
            " ORDER BY peso DESC NULLS LAST",
            licitacion_id,
        ),
        await conn.fetch(
            "SELECT origen, tipo_evaluacion, descripcion,"
            "  umbral, situacion_personal, anios_experiencia, num_empleados"
            " FROM v_solvencia WHERE licitacion_id = $1 AND lote_id IS NULL",
            licitacion_id,
        ),
        await conn.fetch(
            "SELECT tipo, nombre, url FROM v_documento WHERE licitacion_id = $1",
            licitacion_id,
        ),
        await conn.fetch(
            "SELECT codigo, descripcion"
            " FROM v_cpv WHERE licitacion_id = $1 AND lote_id IS NULL",
            licitacion_id,
        ),
        await conn.fetch(
            "SELECT * FROM v_lote WHERE licitacion_id = $1 ORDER BY numero",
            licitacion_id,
        ),
    )

    # Lotes with per-lot criterios, solvencia, CPVs (batch to avoid N+1)
    lot_ids = [lr["id"] for lr in lotes_rows]
    if lot_ids:
        all_lot_criterios, all_lot_solvencia, all_lot_cpvs = (
            await conn.fetch(
                "SELECT lote_id, tipo, subtipo, descripcion, peso, nota"
                " FROM v_criterio WHERE lote_id = ANY($1)"
                " ORDER BY peso DESC NULLS LAST",
                lot_ids,
            ),
            await conn.fetch(
                "SELECT lote_id, origen, tipo_evaluacion, descripcion,"
                "  umbral, situacion_personal, anios_experiencia,"
                "  num_empleados"
                " FROM v_solvencia WHERE lote_id = ANY($1)",
                lot_ids,
            ),
            await conn.fetch(
                "SELECT lote_id, codigo FROM v_cpv WHERE lote_id = ANY($1)",
                lot_ids,
            ),
        )
    else:
        all_lot_criterios = all_lot_solvencia = all_lot_cpvs = []

    # Group by lot_id
    crit_by_lot: dict[UUID, list[asyncpg.Record]] = defaultdict(list)
    solv_by_lot: dict[UUID, list[asyncpg.Record]] = defaultdict(list)
    cpv_by_lot: dict[UUID, list[asyncpg.Record]] = defaultdict(list)
    for r in all_lot_criterios:
        crit_by_lot[r["lote_id"]].append(r)
    for r in all_lot_solvencia:
        solv_by_lot[r["lote_id"]].append(r)
    for r in all_lot_cpvs:
        cpv_by_lot[r["lote_id"]].append(r)

    lotes: list[LoteResumen] = []
    for lr in lotes_rows:
        lot_id = lr["id"]
        lotes.append(
            LoteResumen(
                numero=lr["numero"],
                titulo=lr["titulo"],
                presupuesto_sin_iva=lr["presupuesto_sin_iva"],
                cpv=[c["codigo"] for c in cpv_by_lot[lot_id]],
                criterios=[Criterio(**dict(r)) for r in crit_by_lot[lot_id]],
                solvencia=[RequisitoSolvencia(**dict(r)) for r in solv_by_lot[lot_id]],
            )
        )

    # CPVs
    cpv_codes = [c["codigo"] for c in cpv_rows]
    cpv_principal = cpv_codes[0] if cpv_codes else row["cpv_principal"]
    cpv_secundarios = cpv_codes[1:] if len(cpv_codes) > 1 else []

    # Result
    resultado = None
    if row["resultado"]:
        adj = None
        if row["adjudicatario"]:
            adj = AdjudicatarioInfo(
                nombre=row["adjudicatario"], nif=row["adjudicatario_nif"]
            )
        resultado = ResultadoInfo(
            resultado=row["resultado"],
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
        url_place=row["url_place"],
        tipo_contrato=row["tipo_contrato"],
        procedimiento=row["procedimiento"],
        tramitacion=row["tramitacion"],
        sistema_contratacion=row["sistema_contratacion"],
        presupuesto_sin_iva=row["presupuesto_sin_iva"],
        presupuesto_con_iva=row["presupuesto_con_iva"],
        valor_estimado=row["valor_estimado"],
        fecha_publicacion=row["fecha_publicacion"],
        fecha_actualizacion=row["fecha_actualizacion"],
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
        criterios=[Criterio(**dict(r)) for r in criterios_rows],
        solvencia=[RequisitoSolvencia(**dict(r)) for r in solvencia_rows],
        lotes=lotes,
        documentos=[Documento(**dict(r)) for r in docs_rows],
        historial_estados=row["historial_estados"] or [],
    )
