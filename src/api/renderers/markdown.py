"""Markdown renderers for API responses.

Each ``render_*`` function is a pure transform from a Pydantic schema (or a
list of one) into a markdown document. Renderers never emit YAML frontmatter:
the KB ingest layer is responsible for adding its own frontmatter when saving
responses to ``_raw/md/``.

Conventions:
- Lists → markdown tables with stable column order.
- Nested resources → ``#`` title + ``##`` sections per field group.
- Missing values render as em-dash (``—``) for visual alignment.
- Cursors and totals surface as italic footer lines.
- Money formats as ``1,234,567.89 €``; percentages with one decimal.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from api.schemas import (
    EmpresaDetalle,
    EmpresaResumen,
    LicitacionDetalle,
    LicitacionResumen,
    OrganoDetalle,
    OrganoResumen,
    RespuestaBusqueda,
    RespuestaSimilares,
)

DASH = "—"


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _fmt_money(d: Decimal | None) -> str:
    if d is None:
        return DASH
    return f"{d:,.2f} €"


def _fmt_pct(d: Decimal | float | None, precision: int = 1) -> str:
    if d is None:
        return DASH
    return f"{float(d):.{precision}f}%"


def _fmt_int(n: int | None) -> str:
    if n is None:
        return DASH
    return f"{n:,}"


def _fmt_date(d: date | datetime | None) -> str:
    if d is None:
        return DASH
    if isinstance(d, datetime):
        return d.strftime("%Y-%m-%d %H:%M")
    return d.strftime("%Y-%m-%d")


def _fmt_time(t: time | None) -> str:
    if t is None:
        return DASH
    return t.strftime("%H:%M")


def _cell(v: Any) -> str:
    """Normalise a value for inclusion in a markdown table cell."""
    if v is None or v == "":
        return DASH
    return str(v).replace("|", "\\|").replace("\n", " ")


def _md_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    """Render a markdown table. Empty ``rows`` → single ``_Sin datos._`` line."""
    if not rows:
        return ["_Sin datos._"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def _bullets(items: Sequence[str]) -> list[str]:
    if not items:
        return ["_Sin datos._"]
    return [f"- {item}" for item in items]


def _licitaciones_table(
    rows: Sequence[LicitacionResumen],
    *,
    similitud: bool = False,
) -> list[str]:
    """Common table layout for any list of LicitacionResumen (or subclass)."""
    headers: list[str] = []
    if similitud:
        headers.append("Sim.")
    headers.extend(
        [
            "Expediente",
            "Título",
            "Órgano",
            "Estado",
            "Presupuesto",
            "Adjudicación",
            "Fecha pub.",
        ]
    )
    table_rows: list[list[str]] = []
    for r in rows:
        row: list[str] = []
        if similitud:
            row.append(_cell(getattr(r, "similitud", None)))
        row.extend(
            [
                _cell(r.expediente),
                _cell(r.titulo),
                _cell(r.organo),
                _cell(r.estado),
                _fmt_money(r.presupuesto_sin_iva),
                _fmt_money(r.importe_adjudicacion),
                _fmt_date(r.fecha_publicacion),
            ]
        )
        table_rows.append(row)
    return _md_table(headers, table_rows)


def _cursor_footer(cursor: str | None) -> list[str]:
    if cursor is None:
        return []
    return ["", f"_Siguiente página: `{cursor}`_"]


# ---------------------------------------------------------------------------
# Empresas
# ---------------------------------------------------------------------------


def render_empresas_md(data: list[EmpresaResumen]) -> str:
    """Render a list of empresas as a markdown table."""
    lines = [f"# Empresas ({len(data)} resultados)", ""]
    rows = [[_cell(e.id), _cell(e.nombre), _fmt_int(e.contratos)] for e in data]
    lines.extend(_md_table(["ID", "Nombre", "Contratos"], rows))
    lines.append("")
    return "\n".join(lines)


def render_empresa_md(data: EmpresaDetalle) -> str:
    """Render an empresa profile with stats and paginated adjudications."""
    s = data.stats
    lines: list[str] = [
        f"# {data.nombre}",
        "",
        f"**ID:** `{data.id}`",
        "",
        "## Estadísticas",
        "",
        f"- Contratos adjudicados: {_fmt_int(s.contratos_adjudicados)}",
        f"- Importe total: {_fmt_money(s.importe_total)}",
        f"- Importe medio: {_fmt_money(s.importe_medio)}",
        f"- Baja media: {_fmt_pct(s.baja_media_pct)}",
        "",
        "## CPV frecuentes",
        "",
    ]
    lines.extend(_bullets(s.cpv_frecuentes))
    lines.extend(["", "## Órganos frecuentes", ""])
    lines.extend(_bullets(s.organos_frecuentes))
    lines.extend(
        [
            "",
            f"## Adjudicaciones ({len(data.adjudicaciones)})",
            "",
        ]
    )
    lines.extend(_licitaciones_table(data.adjudicaciones))
    lines.extend(_cursor_footer(data.cursor_siguiente))
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Órganos
# ---------------------------------------------------------------------------


def render_organos_md(data: list[OrganoResumen]) -> str:
    """Render a list of órganos as a markdown table."""
    lines = [f"# Órganos ({len(data)} resultados)", ""]
    rows = [
        [
            _cell(o.id),
            _cell(o.nombre),
            _cell(o.nif),
            _fmt_int(o.licitaciones),
        ]
        for o in data
    ]
    lines.extend(_md_table(["ID", "Nombre", "NIF", "Licitaciones"], rows))
    lines.append("")
    return "\n".join(lines)


def render_organo_md(data: OrganoDetalle) -> str:
    """Render an órgano profile with stats and paginated licitaciones."""
    s = data.stats
    lines: list[str] = [
        f"# {data.nombre}",
        "",
        f"**ID:** `{data.id}`",
        f"**NIF:** {_cell(data.nif)}",
        f"**Tipo:** {_cell(data.tipo)}",
        "",
        "## Estadísticas",
        "",
        f"- Total licitaciones: {_fmt_int(s.total_licitaciones)}",
        f"- Importe medio: {_fmt_money(s.importe_medio)}",
        (
            "- Plazo medio de adjudicación: "
            f"{_fmt_int(s.plazo_medio_adjudicacion_dias)} días"
        ),
        "",
        "## CPV frecuentes",
        "",
    ]
    lines.extend(_bullets(s.cpv_frecuentes))
    lines.extend(
        [
            "",
            f"## Licitaciones ({len(data.licitaciones)})",
            "",
        ]
    )
    lines.extend(_licitaciones_table(data.licitaciones))
    lines.extend(_cursor_footer(data.cursor_siguiente))
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Búsqueda
# ---------------------------------------------------------------------------


def render_busqueda_md(data: RespuestaBusqueda) -> str:
    """Render a /buscar response with total, results table and cursor."""
    header = f"# Búsqueda ({len(data.resultados)} de {_fmt_int(data.total)} resultados)"
    lines: list[str] = [header, ""]
    lines.extend(_licitaciones_table(data.resultados))
    lines.extend(_cursor_footer(data.cursor_siguiente))
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Licitación detalle
# ---------------------------------------------------------------------------


def _render_criterios(items: Sequence[Any]) -> list[str]:
    rows = [
        [
            _cell(c.tipo),
            _cell(c.subtipo),
            _cell(c.descripcion),
            _fmt_pct(c.peso),
            _cell(c.nota),
        ]
        for c in items
    ]
    return _md_table(["Tipo", "Subtipo", "Descripción", "Peso", "Nota"], rows)


def _render_solvencia(items: Sequence[Any]) -> list[str]:
    rows = [
        [
            _cell(r.origen),
            _cell(r.tipo_evaluacion),
            _cell(r.descripcion),
            _fmt_money(r.umbral),
            _cell(r.situacion_personal),
            _cell(r.anios_experiencia),
            _cell(r.num_empleados),
        ]
        for r in items
    ]
    return _md_table(
        [
            "Origen",
            "Tipo eval.",
            "Descripción",
            "Umbral",
            "Sit. personal",
            "Años exp.",
            "Nº empleados",
        ],
        rows,
    )


def _render_lote(lote: Any) -> list[str]:
    lines = [
        f"### Lote {lote.numero}: {lote.titulo or DASH}",
        "",
        f"- Presupuesto sin IVA: {_fmt_money(lote.presupuesto_sin_iva)}",
        f"- CPV: {', '.join(lote.cpv) if lote.cpv else DASH}",
        "",
        "**Criterios:**",
        "",
    ]
    lines.extend(_render_criterios(lote.criterios))
    lines.extend(["", "**Solvencia:**", ""])
    lines.extend(_render_solvencia(lote.solvencia))
    return lines


def _render_licitacion_header(data: LicitacionDetalle) -> list[str]:
    lines = [
        f"# {data.titulo or DASH}",
        "",
        f"**ID:** `{data.id}`",
        f"**Expediente:** {_cell(data.expediente)}",
        f"**Estado:** {_cell(data.estado)}",
    ]
    if data.url_place:
        lines.append(f"**URL PLACE:** {data.url_place}")
    if data.descripcion:
        lines.extend(["", "## Descripción", "", data.descripcion])
    return lines


def _render_licitacion_datos(data: LicitacionDetalle) -> list[str]:
    return [
        "",
        "## Datos generales",
        "",
        f"- Tipo de contrato: {_cell(data.tipo_contrato)}",
        f"- Procedimiento: {_cell(data.procedimiento)}",
        f"- Tramitación: {_cell(data.tramitacion)}",
        f"- Sistema de contratación: {_cell(data.sistema_contratacion)}",
        f"- Lugar: {_cell(data.lugar)}",
        f"- Lugar NUTS: {_cell(data.lugar_nuts)}",
        f"- Tasa de subcontratación: {_fmt_pct(data.tasa_subcontratacion)}",
        f"- Programa de financiación: {_cell(data.programa_financiacion)}",
        "",
        "## Presupuesto",
        "",
        f"- Sin IVA: {_fmt_money(data.presupuesto_sin_iva)}",
        f"- Con IVA: {_fmt_money(data.presupuesto_con_iva)}",
        f"- Valor estimado: {_fmt_money(data.valor_estimado)}",
        "",
        "## Fechas",
        "",
        f"- Publicación: {_fmt_date(data.fecha_publicacion)}",
        f"- Última actualización: {_fmt_date(data.fecha_actualizacion)}",
        f"- Límite presentación: {_fmt_date(data.fecha_limite)}",
        f"- Hora límite: {_fmt_time(data.hora_limite)}",
        (
            f"- Duración: {_fmt_int(data.duracion)} {data.duracion_unidad or ''}"
        ).rstrip(),
    ]


def _render_organo_section(organo: Any | None) -> list[str]:
    if not organo:
        return []
    return [
        "",
        "## Órgano de contratación",
        "",
        f"- Nombre: {_cell(organo.nombre)}",
        f"- NIF: {_cell(organo.nif)}",
        f"- Tipo: {_cell(organo.tipo)}",
        f"- ID: `{organo.id}`",
    ]


def _render_resultado_section(resultado: Any | None) -> list[str]:
    if not resultado:
        return []
    lines = [
        "",
        "## Resultado",
        "",
        f"- Resultado: {_cell(resultado.resultado)}",
        f"- Fecha adjudicación: {_fmt_date(resultado.fecha_adjudicacion)}",
        f"- Importe sin IVA: {_fmt_money(resultado.importe_sin_iva)}",
        f"- Nº licitadores: {_fmt_int(resultado.num_licitadores)}",
        f"- Fecha formalización: {_fmt_date(resultado.fecha_formalizacion)}",
    ]
    if resultado.adjudicatario:
        lines.append(
            f"- Adjudicatario: {_cell(resultado.adjudicatario.nombre)} "
            f"(NIF: {_cell(resultado.adjudicatario.nif)})"
        )
    return lines


def _render_cpv_section(principal: str | None, secundarios: Sequence[str]) -> list[str]:
    lines = ["", "## CPV", "", f"- Principal: {_cell(principal)}"]
    if secundarios:
        lines.append(f"- Secundarios: {', '.join(secundarios)}")
    return lines


def _render_lotes_section(lotes: Sequence[Any]) -> list[str]:
    lines = ["", f"## Lotes ({len(lotes)})", ""]
    if not lotes:
        lines.append("_Licitación no dividida en lotes._")
        return lines
    for lote in lotes:
        lines.extend(_render_lote(lote))
        lines.append("")
    return lines


def _render_documentos_section(documentos: Sequence[Any]) -> list[str]:
    lines = ["", "## Documentos", ""]
    if not documentos:
        lines.append("_Sin documentos._")
        return lines
    lines.extend(
        f"- **{d.tipo or 'Documento'}:** "
        + (f"[{d.nombre or d.url or DASH}]({d.url})" if d.url else (d.nombre or DASH))
        for d in documentos
    )
    return lines


def _render_historial_section(historial: Sequence[Any]) -> list[str]:
    lines = ["", "## Historial de estados", ""]
    if not historial:
        lines.append("_Sin historial._")
        return lines
    lines.extend(f"- {_fmt_date(h.fecha)}: {h.estado}" for h in historial)
    return lines


def render_licitacion_md(data: LicitacionDetalle) -> str:
    """Render the full detail of a licitación."""
    lines = _render_licitacion_header(data)
    lines.extend(_render_licitacion_datos(data))
    lines.extend(_render_organo_section(data.organo))
    lines.extend(_render_resultado_section(data.resultado))
    lines.extend(_render_cpv_section(data.cpv_principal, data.cpv_secundarios))
    lines.extend(["", "## Criterios de adjudicación", ""])
    lines.extend(_render_criterios(data.criterios))
    lines.extend(["", "## Solvencia", ""])
    lines.extend(_render_solvencia(data.solvencia))
    lines.extend(_render_lotes_section(data.lotes))
    lines.extend(_render_documentos_section(data.documentos))
    lines.extend(_render_historial_section(data.historial_estados))
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Similares
# ---------------------------------------------------------------------------


def render_similares_md(data: RespuestaSimilares) -> str:
    """Render similares with market intelligence stats."""
    est = data.estadisticas
    tasa_desierta = (
        _fmt_pct(est.tasa_desierta * 100) if est.tasa_desierta is not None else DASH
    )
    lines: list[str] = [
        f"# Licitaciones similares ({_fmt_int(est.n)} en el pool)",
        "",
        f"**Nivel de confianza:** {est.nivel_confianza}",
        f"**Factor presupuesto:** {est.factor_presupuesto}",
        f"**Tasa desierta:** {tasa_desierta}",
        "",
        "## Estadísticas de baja",
        "",
    ]
    if est.baja_pct:
        b = est.baja_pct
        lines.extend(
            [
                f"- n: {_fmt_int(b.n)}",
                f"- P25: {_fmt_pct(b.p25)}",
                f"- Mediana: {_fmt_pct(b.mediana)}",
                f"- P75: {_fmt_pct(b.p75)}",
            ]
        )
    else:
        lines.append("_Datos insuficientes._")

    lines.extend(["", "## Competencia", ""])
    if est.num_licitadores:
        c = est.num_licitadores
        lines.extend(
            [
                f"- Media de licitadores: {c.media:.1f}",
                f"- Mediana de licitadores: {c.mediana:.1f}",
            ]
        )
    else:
        lines.append("_Datos insuficientes._")

    lines.extend(["", "## Adjudicatarios frecuentes", ""])
    if est.adjudicatarios_frecuentes:
        rows = [
            [
                _cell(w.nombre),
                _fmt_int(w.n),
                _fmt_pct(w.baja_media_pct),
            ]
            for w in est.adjudicatarios_frecuentes
        ]
        lines.extend(_md_table(["Nombre", "N", "Baja media"], rows))
    else:
        lines.append("_Sin datos._")

    lines.extend(
        [
            "",
            f"## Resultados similares ({len(data.resultados)})",
            "",
        ]
    )
    lines.extend(_licitaciones_table(data.resultados, similitud=True))
    lines.append("")
    return "\n".join(lines)
