"""Opaque cursor encoding for keyset pagination."""

from __future__ import annotations

import base64
import json
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
from uuid import UUID


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
