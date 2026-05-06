"""Deterministický post-processing guard pro eliminaci fabrikovaných citací.

Strippuje sp. zn. a ECLI z LLM response, pokud nejsou doloženy v retrieved sources.
Důvod: Gemini 2.0 Flash generuje "ilustrativní" sp. zn. i přes system prompt zákaz.

Exportuje:
  extract_sources_text  — concatenuje fields ze sources do lookup corpusu
  find_unverified_citations — vrátí list (citation, start, end) pro nenalezené citace
  sanitize_response     — nahradí nenalezené citace placeholder textem
"""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Jednací číslo (sp. zn.) — civilní, trestní, správní soudy
# Formát: <číslo> <typ> <číslo>/<rok>[−<strana>]
# Prefix "sp. zn." nebo "sp.zn." je volitelný — matchujeme i holou citaci
_JC_PATTERN = re.compile(
    r"\b\d{1,5}\s+(?:C|Co|Cdo|Nc|E|T|Tdo|Tz|To|As|Afs|Ads|Aps|Azs|Ans|Na|Nao|Naps|ICm|INs)"
    r"\s+\d{1,5}/\d{2,4}(?:-\d+)?\b",
    re.IGNORECASE,
)

# Ústavní soud — Pl. ÚS nebo I.–X. ÚS
_US_PATTERN = re.compile(
    r"\b(?:Pl|I{1,3}|IV|VI{0,3}|VII|VIII|IX|X|\d+)\.\s*ÚS\s+\d{1,5}/\d{2,4}\b",
)

# ECLI — European Case Law Identifier
_ECLI_PATTERN = re.compile(
    r"\bECLI:CZ:[A-Z]+:\d{4}:[A-Z0-9]+(?:\.[A-Z0-9]+)*\b",
)

_ALL_PATTERNS = [_JC_PATTERN, _US_PATTERN, _ECLI_PATTERN]

# Placeholder text vložený místo fabrikované citace
_PLACEHOLDER = "[citace odstraněna — chybí v podkladech]"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Normalizuj na lowercase a single-space."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _is_in_corpus(citation: str, corpus: str) -> bool:
    """Vrátí True pokud citation (nebo její base bez page-suffix) je v corpus."""
    norm_corpus = _normalize(corpus)
    norm_cite = _normalize(citation)

    if norm_cite in norm_corpus:
        return True

    # Lenient match: odstraň stránkový suffix "-<číslo>" (např. "9 C 218/2021-158" → "9 C 218/2021")
    base = re.sub(r"-\d+$", "", norm_cite).strip()
    if base != norm_cite and base in norm_corpus:
        return True

    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_sources_text(sources: list[Any]) -> str:
    """Concatenuj všechny relevantní fields ze sources do lookup corpusu.

    Zpracovává jak dict sources (streaming endpoint), tak Pydantic SourceReference
    objekty (blocking endpoint). Pro lookup se používá: text, filename,
    a pokud přítomné metadata: soud, jednaci_cislo, ecli.

    Args:
        sources: list[dict] nebo list[SourceReference]

    Returns:
        Jeden velký string se všemi texty oddělený mezerami.
    """
    if not sources:
        return ""

    parts: list[str] = []

    for source in sources:
        # Podpora dict i Pydantic modelu přes hasattr / get
        if isinstance(source, dict):
            _append_str(parts, source.get("text", ""))
            _append_str(parts, source.get("filename", ""))
            meta = source.get("metadata") or {}
            _append_str(parts, meta.get("soud", ""))
            _append_str(parts, meta.get("jednaci_cislo", ""))
            _append_str(parts, meta.get("ecli", ""))
        else:
            # Pydantic SourceReference nebo podobný objekt
            _append_str(parts, getattr(source, "text", ""))
            _append_str(parts, getattr(source, "filename", ""))
            meta = getattr(source, "metadata", None) or {}
            if isinstance(meta, dict):
                _append_str(parts, meta.get("soud", ""))
                _append_str(parts, meta.get("jednaci_cislo", ""))
                _append_str(parts, meta.get("ecli", ""))

    return " ".join(parts)


def _append_str(parts: list[str], value: Any) -> None:
    """Přidej neprázdný string do listu."""
    if value and isinstance(value, str):
        parts.append(value)


def find_unverified_citations(
    response: str, source_corpus: str
) -> list[tuple[str, int, int]]:
    """Najdi citace v response, které NEJSOU v source_corpus.

    Prohledá response pro sp. zn., ÚS a ECLI patterny.
    Pro každý match zkontroluje přítomnost v source_corpus.

    Args:
        response: Text odpovědi LLM.
        source_corpus: Concatenovaný text ze sources (z extract_sources_text).

    Returns:
        list[(citation_string, start_pos, end_pos)] pro každou nenalezenou citaci.
        Seřazeno sestupně podle pozice (pro bezpečný replace zprava doleva).
    """
    unverified: list[tuple[str, int, int]] = []

    for pattern in _ALL_PATTERNS:
        for match in pattern.finditer(response):
            citation = match.group(0)
            if not _is_in_corpus(citation, source_corpus):
                unverified.append((citation, match.start(), match.end()))

    # Deduplikace (stejná citace může matchnout vícekrát — různé patterny ne, ale jistota)
    seen: set[str] = set()
    deduped: list[tuple[str, int, int]] = []
    for item in unverified:
        key = f"{item[1]}:{item[2]}"
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    # Seřad sestupně pro replace zprava doleva (zachovává indexy)
    deduped.sort(key=lambda x: x[1], reverse=True)
    return deduped


def sanitize_response(
    response: str, sources: list[Any]
) -> tuple[str, bool]:
    """Nahraď nenalezené citace placeholderem.

    Args:
        response: Původní text odpovědi od LLM.
        sources: list[dict] nebo list[SourceReference] z RAG retrieval.

    Returns:
        (cleaned_response, was_modified) — cleaned_response má fabrikované citace
        nahrazeny placeholderem; was_modified=True pokud byly provedeny změny.
    """
    corpus = extract_sources_text(sources)
    unverified = find_unverified_citations(response, corpus)

    if not unverified:
        return response, False

    # Replace zprava doleva — zachovává správné indexy
    cleaned = response
    for citation, start, end in unverified:
        cleaned = cleaned[:start] + _PLACEHOLDER + cleaned[end:]
        logger.debug("Stripped fabricated citation: %r", citation)

    return cleaned, True
