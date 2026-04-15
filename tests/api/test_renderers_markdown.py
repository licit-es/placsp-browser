"""Unit tests for markdown renderers."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time
from decimal import Decimal

from api.renderers.markdown import (
    render_busqueda_md,
    render_empresa_md,
    render_empresas_md,
    render_licitacion_md,
    render_organo_md,
    render_organos_md,
    render_similares_md,
)
from api.schemas import (
    AdjudicatarioInfo,
    Criterio,
    Documento,
    EmpresaDetalle,
    EmpresaResumen,
    EmpresaStats,
    LicitacionDetalle,
    LicitacionResumen,
    LoteResumen,
    OrganoDetalle,
    OrganoInfo,
    OrganoResumen,
    OrganoStats,
    RequisitoSolvencia,
    RespuestaBusqueda,
    ResultadoInfo,
)
from api.schemas.similares import (
    AdjudicatarioFrecuente,
    EstadisticasCompetencia,
    EstadisticasPrecio,
    EstadisticasSimilares,
    LicitacionSimilar,
    RespuestaSimilares,
)

_NOW = datetime(2024, 3, 15, 10, 30, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _licitacion_resumen(
    *,
    titulo: str = "Servicios desarrollo software",
    estado: str = "Adjudicada",
    presupuesto: Decimal | None = Decimal("100000.00"),
    adjudicacion: Decimal | None = Decimal("85000.00"),
) -> LicitacionResumen:
    return LicitacionResumen(
        id=uuid.uuid4(),
        expediente="EXP-2024-001",
        titulo=titulo,
        organo="Ministerio Test",
        tipo_contrato="Servicios",
        estado=estado,
        presupuesto_sin_iva=presupuesto,
        importe_adjudicacion=adjudicacion,
        fecha_publicacion=_NOW,
        fecha_actualizacion=_NOW,
        fecha_adjudicacion=_NOW.date(),
        cpv_principal="72260000",
        num_licitadores=3,
        adjudicatario="Empresa Test S.L.",
        lugar="Madrid",
        tiene_documentos=True,
        num_lotes=0,
        historial_estados=[],
    )


# ---------------------------------------------------------------------------
# Empresas
# ---------------------------------------------------------------------------


class TestRenderEmpresas:
    def test_empty_list(self) -> None:
        out = render_empresas_md([])
        assert "# Empresas (0 resultados)" in out
        assert "_Sin datos._" in out

    def test_populated_list(self) -> None:
        data = [
            EmpresaResumen(
                id="B50014521",
                nombre="HIERROS ALFONSO, S.L.",
                contratos=11,
            ),
            EmpresaResumen(
                id="A02042752",
                nombre="Hierros Buenos, S.A.L.",
                contratos=82,
            ),
        ]
        out = render_empresas_md(data)
        assert "# Empresas (2 resultados)" in out
        assert "| ID | Nombre | Contratos |" in out
        assert "HIERROS ALFONSO, S.L." in out
        assert "Hierros Buenos, S.A.L." in out
        assert "| 82 |" in out

    def test_pipe_in_name_is_escaped(self) -> None:
        data = [EmpresaResumen(id="X", nombre="Foo | Bar", contratos=1)]
        out = render_empresas_md(data)
        assert "Foo \\| Bar" in out


class TestRenderEmpresaDetalle:
    def _empresa(
        self,
        *,
        adjudicaciones: list[LicitacionResumen] | None = None,
        cursor: str | None = None,
    ) -> EmpresaDetalle:
        return EmpresaDetalle(
            id="B50014521",
            nombre="HIERROS ALFONSO, S.L.",
            stats=EmpresaStats(
                contratos_adjudicados=11,
                importe_total=Decimal("949465.88"),
                importe_medio=Decimal("79122.16"),
                cpv_frecuentes=["44000000", "34000000"],
                organos_frecuentes=["Ministerio Defensa"],
                baja_media_pct=Decimal("38.83"),
            ),
            adjudicaciones=adjudicaciones or [],
            cursor_siguiente=cursor,
        )

    def test_headings_and_stats(self) -> None:
        out = render_empresa_md(self._empresa())
        assert "# HIERROS ALFONSO, S.L." in out
        assert "`B50014521`" in out
        assert "## Estadísticas" in out
        assert "Contratos adjudicados: 11" in out
        assert "949,465.88 €" in out
        assert "38.8%" in out
        assert "## CPV frecuentes" in out
        assert "- 44000000" in out
        assert "## Órganos frecuentes" in out

    def test_with_adjudicaciones(self) -> None:
        out = render_empresa_md(self._empresa(adjudicaciones=[_licitacion_resumen()]))
        assert "## Adjudicaciones (1)" in out
        assert "EXP-2024-001" in out
        assert "Servicios desarrollo software" in out

    def test_cursor_footer(self) -> None:
        out = render_empresa_md(self._empresa(cursor="abc123"))
        assert "Siguiente página" in out
        assert "abc123" in out

    def test_none_stats_render_as_dash(self) -> None:
        empresa = EmpresaDetalle(
            id="X",
            nombre="X SL",
            stats=EmpresaStats(
                contratos_adjudicados=0,
                importe_total=None,
                importe_medio=None,
                cpv_frecuentes=[],
                organos_frecuentes=[],
                baja_media_pct=None,
            ),
            adjudicaciones=[],
            cursor_siguiente=None,
        )
        out = render_empresa_md(empresa)
        assert "Importe total: —" in out
        assert "Baja media: —" in out


# ---------------------------------------------------------------------------
# Órganos
# ---------------------------------------------------------------------------


class TestRenderOrganos:
    def test_empty(self) -> None:
        out = render_organos_md([])
        assert "# Órganos (0 resultados)" in out

    def test_populated(self) -> None:
        data = [
            OrganoResumen(
                id=uuid.uuid4(),
                nombre="Ayuntamiento de Madrid",
                nif="P2807900B",
                licitaciones=1234,
            )
        ]
        out = render_organos_md(data)
        assert "# Órganos (1 resultados)" in out
        assert "Ayuntamiento de Madrid" in out
        assert "P2807900B" in out
        assert "| 1,234 |" in out


class TestRenderOrganoDetalle:
    def test_full(self) -> None:
        organo = OrganoDetalle(
            id=uuid.uuid4(),
            nombre="Ministerio Test",
            nif="S1234567A",
            tipo="AGE",
            stats=OrganoStats(
                total_licitaciones=500,
                importe_medio=Decimal("120000.00"),
                cpv_frecuentes=["72000000"],
                plazo_medio_adjudicacion_dias=45,
            ),
            licitaciones=[_licitacion_resumen()],
            cursor_siguiente=None,
        )
        out = render_organo_md(organo)
        assert "# Ministerio Test" in out
        assert "S1234567A" in out
        assert "AGE" in out
        assert "Total licitaciones: 500" in out
        assert "45 días" in out
        assert "## Licitaciones (1)" in out
        assert "EXP-2024-001" in out


# ---------------------------------------------------------------------------
# Búsqueda
# ---------------------------------------------------------------------------


class TestRenderBusqueda:
    def test_with_results(self) -> None:
        data = RespuestaBusqueda(
            total=42,
            resultados=[_licitacion_resumen(), _licitacion_resumen(titulo="Otro")],
            cursor_siguiente="next-cursor",
        )
        out = render_busqueda_md(data)
        assert "# Búsqueda (2 de 42 resultados)" in out
        assert "Servicios desarrollo software" in out
        assert "Otro" in out
        assert "next-cursor" in out

    def test_no_results(self) -> None:
        data = RespuestaBusqueda(total=0, resultados=[], cursor_siguiente=None)
        out = render_busqueda_md(data)
        assert "# Búsqueda (0 de 0 resultados)" in out
        assert "_Sin datos._" in out


# ---------------------------------------------------------------------------
# Licitación detalle
# ---------------------------------------------------------------------------


def _full_licitacion() -> LicitacionDetalle:
    return LicitacionDetalle(
        id=uuid.uuid4(),
        expediente="EXP-2024-001",
        titulo="Servicios desarrollo plataforma",
        descripcion="Mantenimiento y evolución de la plataforma.",
        url_place="https://place.example/exp/001",
        tipo_contrato="Servicios",
        procedimiento="Abierto",
        tramitacion="Ordinaria",
        sistema_contratacion="No aplica",
        presupuesto_sin_iva=Decimal("250000.00"),
        presupuesto_con_iva=Decimal("302500.00"),
        valor_estimado=Decimal("300000.00"),
        fecha_publicacion=_NOW,
        fecha_actualizacion=_NOW,
        fecha_limite=date(2024, 4, 15),
        hora_limite=time(14, 0),
        duracion=12,
        duracion_unidad="MON",
        estado="Publicada",
        lugar_nuts="ES300",
        lugar="Madrid",
        cpv_principal="72260000",
        cpv_secundarios=["72212000"],
        tasa_subcontratacion=Decimal("30.00"),
        programa_financiacion="Next Generation EU",
        organo=OrganoInfo(
            id=uuid.uuid4(),
            nombre="Ministerio Test",
            nif="S1234567A",
            tipo="AGE",
        ),
        resultado=ResultadoInfo(
            resultado="Adjudicada",
            fecha_adjudicacion=date(2024, 5, 1),
            importe_sin_iva=Decimal("220000.00"),
            num_licitadores=4,
            adjudicatario=AdjudicatarioInfo(
                nombre="Indra S.A.",
                nif="A28599033",
            ),
            fecha_formalizacion=date(2024, 5, 15),
        ),
        criterios=[
            Criterio(
                tipo="Formula",
                subtipo="Precio",
                descripcion="Oferta económica",
                peso=Decimal("60"),
                nota=None,
            ),
            Criterio(
                tipo="Juicio de valor",
                subtipo=None,
                descripcion="Memoria técnica",
                peso=Decimal("40"),
                nota=None,
            ),
        ],
        solvencia=[
            RequisitoSolvencia(
                origen="FINANCIAL",
                tipo_evaluacion="Volumen de negocios",
                descripcion="Volumen mínimo",
                umbral=Decimal("500000"),
                situacion_personal=None,
                anios_experiencia=None,
                num_empleados=None,
            )
        ],
        lotes=[
            LoteResumen(
                numero="1",
                titulo="Lote de desarrollo",
                presupuesto_sin_iva=Decimal("150000.00"),
                cpv=["72260000"],
                criterios=[],
                solvencia=[],
            )
        ],
        documentos=[
            Documento(
                tipo="Pliego",
                nombre="PCAP.pdf",
                url="https://example.com/pcap.pdf",
            )
        ],
        historial_estados=[],
    )


class TestRenderLicitacion:
    def test_top_level_fields(self) -> None:
        out = render_licitacion_md(_full_licitacion())
        assert "# Servicios desarrollo plataforma" in out
        assert "**Expediente:** EXP-2024-001" in out
        assert "https://place.example/exp/001" in out
        assert "Mantenimiento y evolución" in out

    def test_presupuesto_section(self) -> None:
        out = render_licitacion_md(_full_licitacion())
        assert "## Presupuesto" in out
        assert "250,000.00 €" in out
        assert "302,500.00 €" in out

    def test_fechas_section(self) -> None:
        out = render_licitacion_md(_full_licitacion())
        assert "## Fechas" in out
        assert "2024-04-15" in out
        assert "14:00" in out
        assert "Duración: 12 MON" in out

    def test_organo_section(self) -> None:
        out = render_licitacion_md(_full_licitacion())
        assert "## Órgano de contratación" in out
        assert "Ministerio Test" in out
        assert "S1234567A" in out

    def test_resultado_section(self) -> None:
        out = render_licitacion_md(_full_licitacion())
        assert "## Resultado" in out
        assert "220,000.00 €" in out
        assert "Indra S.A." in out
        assert "A28599033" in out

    def test_criterios_table(self) -> None:
        out = render_licitacion_md(_full_licitacion())
        assert "## Criterios de adjudicación" in out
        assert "Oferta económica" in out
        assert "60.0%" in out

    def test_lotes_section(self) -> None:
        out = render_licitacion_md(_full_licitacion())
        assert "## Lotes (1)" in out
        assert "### Lote 1: Lote de desarrollo" in out
        assert "150,000.00 €" in out

    def test_documentos_section(self) -> None:
        out = render_licitacion_md(_full_licitacion())
        assert "[PCAP.pdf](https://example.com/pcap.pdf)" in out
        assert "**Pliego:**" in out

    def test_empty_lotes(self) -> None:
        d = _full_licitacion()
        d.lotes = []
        out = render_licitacion_md(d)
        assert "## Lotes (0)" in out
        assert "_Licitación no dividida en lotes._" in out

    def test_no_resultado_no_section(self) -> None:
        d = _full_licitacion()
        d.resultado = None
        out = render_licitacion_md(d)
        assert "## Resultado" not in out


# ---------------------------------------------------------------------------
# Similares
# ---------------------------------------------------------------------------


class TestRenderSimilares:
    def _respuesta(self) -> RespuestaSimilares:
        similar = LicitacionSimilar(
            **_licitacion_resumen().model_dump(),
            similitud=7,
        )
        return RespuestaSimilares(
            resultados=[similar],
            estadisticas=EstadisticasSimilares(
                n=47,
                baja_pct=EstadisticasPrecio(n=35, p25=8.2, mediana=14.5, p75=22.1),
                num_licitadores=EstadisticasCompetencia(media=4.2, mediana=3.0),
                adjudicatarios_frecuentes=[
                    AdjudicatarioFrecuente(
                        nombre="Indra S.A.",
                        n=8,
                        baja_media_pct=18.3,
                    )
                ],
                tasa_desierta=0.12,
                nivel_confianza="alta",
                factor_presupuesto=3,
            ),
        )

    def test_estadisticas(self) -> None:
        out = render_similares_md(self._respuesta())
        assert "# Licitaciones similares (47 en el pool)" in out
        assert "Nivel de confianza:** alta" in out
        assert "Factor presupuesto:** 3" in out
        assert "## Estadísticas de baja" in out
        assert "Mediana: 14.5%" in out

    def test_adjudicatarios_table(self) -> None:
        out = render_similares_md(self._respuesta())
        assert "## Adjudicatarios frecuentes" in out
        assert "Indra S.A." in out
        assert "18.3%" in out

    def test_results_table_includes_similitud(self) -> None:
        out = render_similares_md(self._respuesta())
        assert "## Resultados similares (1)" in out
        assert "| Sim. |" in out
        # The similitud cell should contain the numeric score.
        assert "| 7 |" in out

    def test_empty_pool(self) -> None:
        empty = RespuestaSimilares(
            resultados=[],
            estadisticas=EstadisticasSimilares(
                n=0,
                baja_pct=None,
                num_licitadores=None,
                adjudicatarios_frecuentes=[],
                tasa_desierta=None,
                nivel_confianza="baja",
                factor_presupuesto=10,
            ),
        )
        out = render_similares_md(empty)
        assert "# Licitaciones similares (0 en el pool)" in out
        assert "Datos insuficientes" in out
        assert "_Sin datos._" in out
