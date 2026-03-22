"""Tests for shared.codice.nif — NIF/CIF normalization."""

import pytest

from shared.codice.nif import detect_nif_swap, normalize_nif


class TestNormalizeNif:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("B88018098", "B88018098"),
            ("b88018098", "B88018098"),
            ("B-88018098", "B88018098"),
            ("A-28599033", "A28599033"),
            ("A28599033", "A28599033"),
            (" B88018098 ", "B88018098"),
            ("12345678A", "12345678A"),
            ("X1234567A", "X1234567A"),
        ],
    )
    def test_valid_nifs(self, raw: str, expected: str) -> None:
        assert normalize_nif(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [None, "", " ", "-"],
    )
    def test_garbage_returns_none(self, raw: str | None) -> None:
        assert normalize_nif(raw) is None

    def test_compound_ute_kept(self) -> None:
        raw = "A28855260-B88018098-B63130074"
        result = normalize_nif(raw)
        assert result == "A28855260-B88018098-B63130074"

    def test_ute_identifier_uppercased(self) -> None:
        assert normalize_nif("u87895405") == "U87895405"

    def test_temp_identifiers_kept(self) -> None:
        result = normalize_nif("TEMP-00078")
        assert result == "TEMP-00078"


class TestDetectNifSwap:
    def test_swapped_fields(self) -> None:
        identifier, name = detect_nif_swap("INDRA SISTEMAS, S.A.", "A28599033")
        assert identifier == "A28599033"
        assert name == "INDRA SISTEMAS, S.A."

    def test_normal_order_unchanged(self) -> None:
        identifier, name = detect_nif_swap("B88018098", "Indra Soluciones")
        assert identifier == "B88018098"
        assert name == "Indra Soluciones"

    def test_both_none(self) -> None:
        assert detect_nif_swap(None, None) == (None, None)

    def test_identifier_none(self) -> None:
        assert detect_nif_swap(None, "Empresa") == (None, "Empresa")

    def test_both_nifs_no_swap(self) -> None:
        identifier, name = detect_nif_swap("B88018098", "A28599033")
        assert identifier == "B88018098"
        assert name == "A28599033"
