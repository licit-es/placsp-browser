"""API response schemas."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class RespuestaPaginada(BaseModel, Generic[T]):
    """Respuesta paginada generica."""

    elementos: list[T]
    total: int
    offset: int
    limite: int
