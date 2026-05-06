"""Unit tests for response_guard — deterministic post-processing anti-hallucination guard.

TDD: these tests are written FIRST (RED phase). Implementation follows.
"""

import pytest

from src.features.chat.response_guard import (
    extract_sources_text,
    find_unverified_citations,
    sanitize_response,
)


# ---------------------------------------------------------------------------
# Helpers — dummy source structures
# ---------------------------------------------------------------------------

def _make_dict_source(
    text: str = "generic chunk text",
    filename: str = "doc.pdf",
    soud: str = "",
    jednaci_cislo: str = "",
    ecli: str = "",
) -> dict:
    return {
        "chunk_id": "c1",
        "document_id": "d1",
        "filename": filename,
        "text": text,
        "score": 0.9,
        "page_number": None,
        "metadata": {
            "soud": soud,
            "jednaci_cislo": jednaci_cislo,
            "ecli": ecli,
        },
    }


# ---------------------------------------------------------------------------
# T1 — extract_sources_text concatenates all fields
# ---------------------------------------------------------------------------

class TestExtractSourcesText:
    def test_extract_sources_text_concatenates_all_fields(self):
        """Corpus must contain text, filename, soud, jednaci_cislo, ecli."""
        sources = [
            _make_dict_source(
                text="Žalobkyni náleží náhrada 150 000 Kč.",
                filename="Okresní soud v Sokolově - 7 C 298/2021-45",
                soud="Okresní soud v Sokolově",
                jednaci_cislo="7 C 298/2021",
                ecli="ECLI:CZ:OSSO:2021:7.C.298.2021.2",
            ),
            _make_dict_source(
                text="Obecní vyhláška č. 5/2023.",
                filename="vyhláška.pdf",
                soud="",
                jednaci_cislo="",
                ecli="",
            ),
        ]
        corpus = extract_sources_text(sources)

        assert "Žalobkyni náleží náhrada 150 000 Kč." in corpus
        assert "Okresní soud v Sokolově - 7 C 298/2021-45" in corpus
        assert "Okresní soud v Sokolově" in corpus
        assert "7 C 298/2021" in corpus
        assert "ECLI:CZ:OSSO:2021:7.C.298.2021.2" in corpus
        assert "Obecní vyhláška č. 5/2023." in corpus

    def test_extract_sources_text_handles_missing_metadata(self):
        """Sources without metadata key must not crash."""
        sources = [
            {
                "chunk_id": "c2",
                "document_id": "d2",
                "filename": "bare.pdf",
                "text": "Základní text dokumentu.",
                "score": 0.7,
                "page_number": None,
            }
        ]
        corpus = extract_sources_text(sources)
        assert "Základní text dokumentu." in corpus
        assert "bare.pdf" in corpus

    def test_extract_sources_text_empty_sources(self):
        """Empty sources list returns empty string."""
        assert extract_sources_text([]) == ""


# ---------------------------------------------------------------------------
# T2 — find_unverified_citations detects fabricated jednaci_cislo
# ---------------------------------------------------------------------------

class TestFindUnverifiedCitationsFabricatedJC:
    def test_find_unverified_citations_detects_fabricated_jc(self):
        """Fabricated sp. zn. not in corpus → 1 unverified entry."""
        response = (
            "Pro orientaci – podobný případ řešil Okresní soud v Ostravě "
            "(sp. zn. 32 C 207/2022-106, 21. 11. 2023): soud přiznal náhradu."
        )
        corpus = "real chunk text 9 C 218/2021 something else entirely"

        unverified = find_unverified_citations(response, corpus)

        assert len(unverified) == 1
        assert "32 C 207/2022" in unverified[0][0]


# ---------------------------------------------------------------------------
# T3 — find_unverified_citations passes real jednaci_cislo
# ---------------------------------------------------------------------------

class TestFindUnverifiedCitationsRealJC:
    def test_find_unverified_citations_passes_real_jc(self):
        """sp. zn. present in corpus → 0 unverified."""
        response = "Soud rozhodl ve věci sp. zn. 9 C 218/2021 následovně."
        corpus = "text rozhodnutí 9 C 218/2021 strana 4"

        unverified = find_unverified_citations(response, corpus)

        assert len(unverified) == 0


# ---------------------------------------------------------------------------
# T4 — find_unverified_citations detects fabricated ECLI
# ---------------------------------------------------------------------------

class TestFindUnverifiedCitationsFabricatedECLI:
    def test_find_unverified_citations_detects_fabricated_ecli(self):
        """Fabricated ECLI not in corpus → 1 unverified."""
        response = (
            "Viz ECLI:CZ:OSUL:2023:37.C.143.2023.3 pro srovnatelný případ."
        )
        corpus = "ECLI:CZ:OSSO:2021:7.C.298.2021.2 relevantní rozhodnutí"

        unverified = find_unverified_citations(response, corpus)

        assert len(unverified) == 1
        assert "ECLI:CZ:OSUL:2023:37.C.143.2023.3" in unverified[0][0]


# ---------------------------------------------------------------------------
# T5 — find_unverified_citations detects Ústavní soud pattern
# ---------------------------------------------------------------------------

class TestFindUnverifiedCitationsUSPattern:
    def test_find_unverified_citations_us_pattern(self):
        """IV. ÚS citation not in empty corpus → 1 unverified."""
        response = "Ústavní soud ve věci IV. ÚS 1234/22 rozhodl jinak."
        corpus = ""

        unverified = find_unverified_citations(response, corpus)

        assert len(unverified) == 1
        assert "IV. ÚS 1234/22" in unverified[0][0]


# ---------------------------------------------------------------------------
# T6 — sanitize_response replaces unverified citations
# ---------------------------------------------------------------------------

class TestSanitizeResponseReplacesUnverified:
    def test_sanitize_response_replaces_unverified(self):
        """Fabricated sp. zn. in response must be replaced; was_modified=True."""
        sources = [
            _make_dict_source(
                text="Žalobce obdržel 50 000 Kč.",
                filename="7 C 298/2021.pdf",
                jednaci_cislo="7 C 298/2021",
            )
        ]
        response = (
            "Soud v Ostravě (sp. zn. 32 C 207/2022) přiznal náhradu. "
            "Viz také 7 C 298/2021 pro srovnání."
        )

        cleaned, was_modified = sanitize_response(response, sources)

        assert was_modified is True
        assert "32 C 207/2022" not in cleaned
        assert "[citace odstraněna — chybí v podkladech]" in cleaned
        # Real citation must remain
        assert "7 C 298/2021" in cleaned


# ---------------------------------------------------------------------------
# T7 — sanitize_response no-op for clean response
# ---------------------------------------------------------------------------

class TestSanitizeResponseNoOp:
    def test_sanitize_response_no_op_for_clean_response(self):
        """Response with no citations → unchanged, was_modified=False."""
        sources = [
            _make_dict_source(text="Text bez citací.", filename="doc.pdf")
        ]
        response = "Tento chatbot odpovídá na otázky o úřední desce města."

        cleaned, was_modified = sanitize_response(response, sources)

        assert was_modified is False
        assert cleaned == response


# ---------------------------------------------------------------------------
# T8 — sanitize_response with page suffix (lenient match)
# ---------------------------------------------------------------------------

class TestSanitizeResponseWithSuffixDash:
    def test_sanitize_response_with_suffix_dash(self):
        """sp. zn. '9 C 218/2021-158' with page suffix — base '9 C 218/2021' in corpus → verified, NOT stripped."""
        sources = [
            _make_dict_source(
                text="Rozhodnutí o náhradě škody.",
                filename="9 C 218/2021-158.pdf",
                jednaci_cislo="9 C 218/2021",
                ecli="ECLI:CZ:OSTA:2021:9.C.218.2021.1",
            )
        ]
        # Response references the full citation with page suffix
        response = "Viz rozhodnutí 9 C 218/2021-158 ze dne 15. 6. 2021."

        cleaned, was_modified = sanitize_response(response, sources)

        # Should NOT be stripped — base citation is in corpus
        assert was_modified is False
        assert "9 C 218/2021-158" in cleaned
