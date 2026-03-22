"""Spanish NIF/CIF normalization for CODICE winning-party identifiers."""

from __future__ import annotations

import re

# CIF: letter + 7 digits + check (digit or letter)
# NIF: 8 digits + letter
# NIE: X/Y/Z + 7 digits + letter
_NIF_RE = re.compile(r"^[A-Z]\d{7,8}[A-Z0-9]?$|^\d{8}[A-Z]$")


def normalize_nif(raw: str | None) -> str | None:
    """Normalize a Spanish NIF/CIF.

    Uppercases, strips hyphens/spaces, and validates format.
    Returns None for garbage values (``-``, ``TEMP-*``, empty).
    Compound identifiers (UTEs) are uppercased but otherwise kept.
    """
    if not raw or not raw.strip() or raw.strip() == "-":
        return None

    candidate = raw.strip().upper().replace("-", "").replace(" ", "")

    if _NIF_RE.match(candidate):
        return candidate

    # Not a single valid NIF — keep uppercased original for UTEs etc.
    return raw.strip().upper()


def detect_nif_swap(
    identifier: str | None, name: str | None
) -> tuple[str | None, str | None]:
    """Detect and fix swapped identifier/name fields.

    Some PLACE entries have the NIF in the name field and vice versa.
    Returns (identifier, name), swapped if needed.
    """
    if not identifier or not name:
        return identifier, name

    id_looks_like_nif = _NIF_RE.match(
        identifier.strip().upper().replace("-", "").replace(" ", "")
    )
    name_looks_like_nif = _NIF_RE.match(
        name.strip().upper().replace("-", "").replace(" ", "")
    )

    if not id_looks_like_nif and name_looks_like_nif:
        return name, identifier

    return identifier, name
