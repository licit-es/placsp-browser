"""API schemas — re-exports for backward-compatible imports."""

from api.schemas.busqueda import FiltrosBusqueda, PeticionBusqueda
from api.schemas.cursor import decode_cursor, encode_cursor
from api.schemas.detalle import (
    AdjudicatarioInfo,
    Criterio,
    Documento,
    LicitacionDetalle,
    LoteResumen,
    OrganoInfo,
    RequisitoSolvencia,
    ResultadoInfo,
)
from api.schemas.empresa import (
    EmpresaDetalle,
    EmpresaResumen,
    EmpresaStats,
    PeticionBusquedaEmpresas,
)
from api.schemas.organo import OrganoDetalle, OrganoStats
from api.schemas.resumen import (
    CambioEstado,
    DocumentoResumen,
    LicitacionResumen,
    RespuestaBusqueda,
)
from api.schemas.similares import (
    EstadisticasSimilares,
    LicitacionSimilar,
    RespuestaSimilares,
)

__all__ = [
    "AdjudicatarioInfo",
    "CambioEstado",
    "Criterio",
    "Documento",
    "DocumentoResumen",
    "EmpresaDetalle",
    "EmpresaResumen",
    "EmpresaStats",
    "EstadisticasSimilares",
    "FiltrosBusqueda",
    "LicitacionDetalle",
    "LicitacionResumen",
    "LicitacionSimilar",
    "LoteResumen",
    "OrganoDetalle",
    "OrganoInfo",
    "OrganoStats",
    "PeticionBusqueda",
    "PeticionBusquedaEmpresas",
    "RequisitoSolvencia",
    "RespuestaBusqueda",
    "RespuestaSimilares",
    "ResultadoInfo",
    "decode_cursor",
    "encode_cursor",
]
