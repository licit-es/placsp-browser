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
from api.schemas.empresa import EmpresaDetalle, EmpresaResumen, EmpresaStats
from api.schemas.organo import OrganoDetalle, OrganoStats
from api.schemas.resumen import CambioEstado, LicitacionResumen, RespuestaBusqueda

__all__ = [
    "AdjudicatarioInfo",
    "CambioEstado",
    "Criterio",
    "Documento",
    "EmpresaDetalle",
    "EmpresaResumen",
    "EmpresaStats",
    "FiltrosBusqueda",
    "LicitacionDetalle",
    "LicitacionResumen",
    "LoteResumen",
    "OrganoDetalle",
    "OrganoInfo",
    "OrganoStats",
    "PeticionBusqueda",
    "RequisitoSolvencia",
    "RespuestaBusqueda",
    "ResultadoInfo",
    "decode_cursor",
    "encode_cursor",
]
