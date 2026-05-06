"""Unit tests for build_context() — metadata-enriched headers for judikat chunks."""

import pytest

from src.features.chat.retrieval import RetrievalService


def _make_service() -> RetrievalService:
    """Create RetrievalService with stub dependencies."""

    class _StubFirestore:
        pass

    class _StubGemini:
        pass

    return RetrievalService(firestore=_StubFirestore(), gemini=_StubGemini())


class TestBuildContextJudikatHeader:
    """Test A — judikat chunk with full metadata produces enriched header."""

    def test_judikat_chunk_header_contains_court_name(self):
        service = _make_service()
        chunks = [
            {
                "id": "chunk_1",
                "document_id": "ECLI_CZ_OSSO_2021_7.C.298.2021.2",
                "text": "Žalobkyni náleží náhrada škody ve výši 150 000 Kč.",
                "chunk_index": 0,
                "page_number": 1,
                "score": 0.85,
                "metadata": {
                    "soud": "Okresní soud v Sokolově",
                    "jednaci_cislo": "7 C 298/2021",
                    "ecli": "ECLI:CZ:OSSO:2021:7.C.298.2021.2",
                },
            }
        ]

        context = service.build_context(chunks)

        assert "Okresní soud v Sokolově" in context
        assert "7 C 298/2021" in context
        assert "ECLI:CZ:OSSO:2021:7.C.298.2021.2" in context
        # Must NOT hallucinate Ostrava instead of Sokolov
        assert "Ostrava" not in context

    def test_judikat_chunk_header_format(self):
        """Header must follow [Source N — <soud>, sp. zn. <jednaci_cislo>, <ecli>] format."""
        service = _make_service()
        chunks = [
            {
                "id": "chunk_1",
                "document_id": "ECLI_CZ_OSSO_2021_7.C.298.2021.2",
                "text": "Věc rozhodnutá.",
                "chunk_index": 0,
                "page_number": 1,
                "score": 0.90,
                "metadata": {
                    "soud": "Okresní soud v Sokolově",
                    "jednaci_cislo": "7 C 298/2021",
                    "ecli": "ECLI:CZ:OSSO:2021:7.C.298.2021.2",
                },
            }
        ]

        context = service.build_context(chunks)

        assert "[Source 1 — Okresní soud v Sokolově, sp. zn. 7 C 298/2021" in context


class TestBuildContextWebPageHeader:
    """Test B — web page chunk (no judikat metadata) keeps plain [Source N] header."""

    def test_web_chunk_plain_header_no_regression(self):
        service = _make_service()
        chunks = [
            {
                "id": "chunk_web_1",
                "document_id": "web_muhb_cz_123",
                "text": "Úřední deska — zveřejnění záměru.",
                "chunk_index": 2,
                "page_number": None,
                "score": 0.75,
                "metadata": {},
            }
        ]

        context = service.build_context(chunks)

        assert "[Source 1]" in context
        assert "sp. zn." not in context
        assert "ECLI" not in context

    def test_chunk_without_metadata_key_plain_header(self):
        """Chunk dict that has no 'metadata' key at all falls back to plain header."""
        service = _make_service()
        chunks = [
            {
                "id": "chunk_legacy_1",
                "document_id": "legacy_doc",
                "text": "Starý dokument bez metadata.",
                "chunk_index": 0,
                "page_number": None,
                "score": 0.65,
                # no 'metadata' key
            }
        ]

        context = service.build_context(chunks)

        assert "[Source 1]" in context
        assert "sp. zn." not in context


class TestBuildContextEmptyMetadataFallback:
    """Test C — chunk with metadata dict but empty fields falls back to [Source N]."""

    def test_empty_soud_falls_back_to_plain_header(self):
        service = _make_service()
        chunks = [
            {
                "id": "chunk_partial_1",
                "document_id": "ECLI_CZ_OSSO_2021_7.C.298.2021.2",
                "text": "Text rozhodnutí.",
                "chunk_index": 0,
                "page_number": 1,
                "score": 0.80,
                "metadata": {
                    "soud": "",
                    "jednaci_cislo": "",
                    "ecli": "",
                },
            }
        ]

        context = service.build_context(chunks)

        assert "[Source 1]" in context
        assert "sp. zn." not in context

    def test_ecli_prefix_in_document_id_but_empty_metadata_falls_back(self):
        """document_id starts with ECLI_ but metadata fields are empty — plain header."""
        service = _make_service()
        chunks = [
            {
                "id": "chunk_2",
                "document_id": "ECLI_CZ_OSTA_2023_9.C.218.2021.1",
                "text": "Rozhodnutí soudu.",
                "chunk_index": 9000,
                "page_number": None,
                "score": 0.77,
                "metadata": {
                    "soud": "",
                    "jednaci_cislo": "9 C 218/2021",
                    "ecli": "",
                },
            }
        ]

        context = service.build_context(chunks)

        # Only jednaci_cislo is non-empty but soud is empty — falls back to plain
        assert "[Source 1]" in context

    def test_partial_metadata_soud_only_falls_back(self):
        """Only soud filled, jednaci_cislo empty — not enough for enriched header, fallback."""
        service = _make_service()
        chunks = [
            {
                "id": "chunk_3",
                "document_id": "ECLI_CZ_OSSO_2021_7.C.298.2021.2",
                "text": "Rozhodnutí.",
                "chunk_index": 0,
                "page_number": 1,
                "score": 0.70,
                "metadata": {
                    "soud": "Okresní soud v Sokolově",
                    "jednaci_cislo": "",
                    "ecli": "ECLI:CZ:OSSO:2021:7.C.298.2021.2",
                },
            }
        ]

        context = service.build_context(chunks)

        # jednaci_cislo is required for enriched header
        assert "[Source 1]" in context
        # soud must not appear as partial header
        # (we check: either full enriched header or plain)
        lines = context.splitlines()
        source_line = next(
            (ln for ln in lines if ln.startswith("[Source")), ""
        )
        assert source_line == "[Source 1]"


class TestBuildContextMultipleChunks:
    """Test D — mixed judikat + web chunks produce correct headers for each."""

    def test_mixed_chunks_correct_headers(self):
        service = _make_service()
        chunks = [
            {
                "id": "chunk_web",
                "document_id": "web_page_abc",
                "text": "Informace z webu.",
                "chunk_index": 0,
                "page_number": None,
                "score": 0.88,
                "metadata": {},
            },
            {
                "id": "chunk_judikat",
                "document_id": "ECLI_CZ_OSSO_2021_7.C.298.2021.2",
                "text": "Soud přiznal žalobci bolestné 80 000 Kč.",
                "chunk_index": 0,
                "page_number": 2,
                "score": 0.82,
                "metadata": {
                    "soud": "Okresní soud v Sokolově",
                    "jednaci_cislo": "7 C 298/2021",
                    "ecli": "ECLI:CZ:OSSO:2021:7.C.298.2021.2",
                },
            },
        ]

        context = service.build_context(chunks)

        assert "[Source 1]" in context
        assert "[Source 2 — Okresní soud v Sokolově" in context
        assert "sp. zn. 7 C 298/2021" in context
