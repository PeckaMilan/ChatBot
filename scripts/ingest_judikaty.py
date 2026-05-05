"""
Ingest Czech court decisions (judikáty) on traffic accidents from rozhodnuti.justice.cz/opendata/
into Firestore as documents for RAG pipeline.

Usage:
    python scripts/ingest_judikaty.py --years 2021-2026 --max 500 --dry-run
    python scripts/ingest_judikaty.py --years 2021-2026 --max 500

Required env vars:
    GOOGLE_APPLICATION_CREDENTIALS  - Path to GCP service account JSON
    GOOGLE_API_KEY                   - Gemini API key (for embeddings via Vertex AI)
    GOOGLE_CLOUD_PROJECT             - GCP project ID (e.g. chatbot-platform-2026)

Optional env vars (same as main app):
    Any .env variables recognized by src/config.py

Widget target: ls0Si9wuw2gbatGla3nW (ponehodovapece.cz production widget)
"""

import argparse
import asyncio
import logging
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.firestore import FirestoreClient
from src.core.gemini import GeminiClient
from src.features.documents.processor import DocumentProcessor

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

BASE_URL = "https://rozhodnuti.justice.cz"
DEFAULT_WIDGET_ID = "ls0Si9wuw2gbatGla3nW"
LOG_PROGRESS_EVERY = 50
LLM_CONCURRENCY = 5  # max parallel Gemini Flash calls

# PRIMARY standalone: criminal traffic statutes (unambiguously traffic)
TRAFFIC_STATUTES = {
    "§ 143 z. č. 40/2009 Sb.",   # usmrcení z nedbalosti
    "§ 147 z. č. 40/2009 Sb.",   # těžké ublížení na zdraví z nedbalosti
    "§ 148 z. č. 40/2009 Sb.",   # ublížení na zdraví z nedbalosti
    "§ 274 z. č. 40/2009 Sb.",   # ohrožení pod vlivem návykové látky
}

# SECONDARY path: injury compensation keywords — sent directly to LLM (no text pre-filter)
SECONDARY_KEYWORDS = {
    "škoda na zdraví",
    "újma na zdraví",
    "bolestné",
    "ztížení společenského uplatnění",
    "ztráta na výdělku",
}

# Full-text traffic tokens — available for optional future use, not used in current pipeline
SECONDARY_TEXT_TOKENS = [
    "řidič",
    "řidiče",
    "řidiči",
    "chodec",
    "chodce",
    "chodci",
    "motorové vozidlo",
    "dopravní nehod",
    "silniční provoz",
    "přechod pro chodc",
]

RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRIES = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ingest_judikaty")


# ─────────────────────────────────────────────
# Relevance filter — tight two-tier logic
# ─────────────────────────────────────────────

def is_relevant(item: dict) -> tuple[bool, str]:
    """
    Check if a court decision item should advance to LLM classification.

    PRIMARY (standalone match — unambiguously traffic, straight to LLM):
    - klicovaSlova contains "dopravní nehoda" (case-insensitive substring)
    - predmetRizeni contains "dopravní nehoda"
    - zminenaUstanoveni contains any of §143/§147/§148/§274 z. č. 40/2009 Sb.

    SECONDARY (straight to LLM — no full-text pre-filter):
    - klicovaSlova contains any of: "škoda na zdraví", "újma na zdraví",
      "bolestné", "ztížení společenského uplatnění", "ztráta na výdělku"

    DISCARD (never match):
    - civil statutes §2900-§2971 z. č. 89/2012 Sb.
    - "vozidla"/"vozidel"/"vozidlu" alone in predmetRizeni (vehicle ownership disputes)
    - "havárie"/"kolize" alone in klicovaSlova
    - standalone "ztížení"/"ztráta" NOT in SECONDARY_KEYWORDS → handled by not including them
      in KEYWORD_HITS outside of SECONDARY_KEYWORDS

    Returns (match: bool, reason: str).
    """
    statutes: list[str] = item.get("zminenaUstanoveni") or []
    keywords: list[str] = item.get("klicovaSlova") or []
    subject: str = (item.get("predmetRizeni") or "").lower()
    keywords_lower = [k.lower() for k in keywords]

    # PRIMARY 1 — criminal traffic statutes
    for statute in statutes:
        if statute in TRAFFIC_STATUTES:
            return True, f"primary:criminal_statute:{statute}"

    # PRIMARY 2 — "dopravní nehoda" exact phrase in keywords
    if any("dopravní nehoda" in k for k in keywords_lower):
        return True, "primary:keyword:dopravní_nehoda"

    # PRIMARY 3 — "dopravní nehoda" exact phrase in predmetRizeni
    if "dopravní nehoda" in subject:
        return True, "primary:subject:dopravní_nehoda"

    # SECONDARY — injury compensation keywords (need full-text confirmation)
    for kw in SECONDARY_KEYWORDS:
        if any(kw in k for k in keywords_lower):
            return True, f"secondary:keyword:{kw}"

    return False, ""


def text_has_secondary_signal(full_text: str) -> tuple[bool, str]:
    """
    Confirm SECONDARY matches by verifying the full text contains a traffic token.
    Required before sending SECONDARY candidates to the LLM classifier.

    Returns (passed: bool, matched_token: str).
    """
    text_lower = full_text.lower()
    for token in SECONDARY_TEXT_TOKENS:
        if token in text_lower:
            return True, token
    return False, ""


# ─────────────────────────────────────────────
# LLM classifier
# ─────────────────────────────────────────────

_LLM_SYSTEM = (
    "Jsi právní klasifikátor. Rozhoduješ, zda soudní rozhodnutí je relevantní "
    "pro poradnu zaměřenou na odškodnění po dopravních nehodách v České republice. "
    "Odpovídáš VÝHRADNĚ jedním slovem: ANO, NE nebo NEJISTE."
)

_LLM_TEMPLATE = """\
Soud: {soud}
Číslo jednací: {jc}
Předmět řízení: {predmet}
Klíčová slova: {kw}
Zmíněná ustanovení: {statutes}
Výrok (prvních 800 znaků): {verdict}

Je toto rozhodnutí relevantní pro odškodnění po dopravní nehodě?
Odpovedz VÝHRADNĚ: ANO, NE nebo NEJISTE."""


async def classify_with_llm(
    item: dict,
    full_text: str,
    gemini: GeminiClient,
    llm_semaphore: asyncio.Semaphore,
) -> str:
    """
    Classify a court decision using Gemini Flash 2.0.

    Returns "ANO", "NE", or "NEJISTE".
    On any error returns "NE" (safe default — skip).
    """
    verdict_preview = full_text[:800] if full_text else ""
    prompt = _LLM_TEMPLATE.format(
        soud=item.get("soud", ""),
        jc=item.get("jednaciCislo", ""),
        predmet=(item.get("predmetRizeni") or "")[:200],
        kw=", ".join((item.get("klicovaSlova") or [])[:8]),
        statutes=", ".join((item.get("zminenaUstanoveni") or [])[:6]),
        verdict=verdict_preview,
    )

    async with llm_semaphore:
        try:
            from google.genai import types as gtypes

            response = gemini.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[gtypes.Content(
                    role="user",
                    parts=[gtypes.Part.from_text(text=prompt)],
                )],
                config=gtypes.GenerateContentConfig(
                    system_instruction=_LLM_SYSTEM,
                    temperature=0.0,
                    max_output_tokens=8,
                ),
            )
            raw = (response.text or "").strip().upper()
            if raw.startswith("ANO"):
                return "ANO"
            if raw.startswith("NE"):
                return "NE"
            return "NEJISTE"
        except Exception as exc:
            logger.error("LLM classification failed: %s", exc)
            return "NE"


# ─────────────────────────────────────────────
# Justice.cz API client
# ─────────────────────────────────────────────

def _extract_uuid(odkaz: str) -> str | None:
    """Extract UUID from finaldoc URL."""
    match = re.search(r"/api/finaldoc/([a-f0-9-]{36})", odkaz or "")
    return match.group(1) if match else None


def _walk_texts(obj, key: str = "text") -> list[str]:
    """Recursively collect all string values under a given key from nested dicts/lists."""
    results: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, str):
                results.append(v)
            else:
                results.extend(_walk_texts(v, key))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(_walk_texts(item, key))
    return results


async def _fetch_with_retry(
    client: httpx.AsyncClient, url: str, semaphore: asyncio.Semaphore
) -> dict | list | None:
    """Fetch JSON from URL with exponential backoff on transient errors."""
    async with semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                resp = await client.get(url, timeout=30.0)
                if resp.status_code in RETRY_STATUSES:
                    wait = min(2 ** attempt, 60)
                    logger.warning(
                        "HTTP %s for %s — retry %d/%d in %ds",
                        resp.status_code, url, attempt + 1, MAX_RETRIES, wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException:
                wait = min(2 ** attempt, 60)
                logger.warning("Timeout for %s — retry %d/%d in %ds", url, attempt + 1, MAX_RETRIES, wait)
                await asyncio.sleep(wait)
            except httpx.HTTPStatusError as exc:
                logger.error("HTTP error %s for %s: %s", exc.response.status_code, url, exc)
                return None
            except Exception as exc:
                logger.error("Unexpected error fetching %s: %s", url, exc)
                return None
        logger.error("All retries exhausted for %s", url)
        return None


async def fetch_year_months(
    client: httpx.AsyncClient, year: int, semaphore: asyncio.Semaphore
) -> list[dict]:
    """Fetch list of month entries for a year."""
    data = await _fetch_with_retry(client, f"{BASE_URL}/api/opendata/{year}", semaphore)
    return data if isinstance(data, list) else []


async def fetch_month_days(
    client: httpx.AsyncClient, year: int, month: int, semaphore: asyncio.Semaphore
) -> list[dict]:
    """Fetch list of day entries for a month."""
    data = await _fetch_with_retry(
        client, f"{BASE_URL}/api/opendata/{year}/{month}", semaphore
    )
    return data if isinstance(data, list) else []


async def fetch_day_items(
    client: httpx.AsyncClient, year: int, month: int, day: int, semaphore: asyncio.Semaphore
) -> list[dict]:
    """Fetch all court decision items for a specific day."""
    data = await _fetch_with_retry(
        client, f"{BASE_URL}/api/opendata/{year}/{month}/{day}", semaphore
    )
    if isinstance(data, dict):
        return data.get("items") or []
    return []


async def fetch_full_text(
    client: httpx.AsyncClient, uuid: str, semaphore: asyncio.Semaphore
) -> str:
    """Download and concatenate full text of a court decision."""
    data = await _fetch_with_retry(
        client, f"{BASE_URL}/api/finaldoc/{uuid}", semaphore
    )
    if not data:
        return ""
    parts: list[str] = []
    for section_key in ("header", "verdict", "body"):
        section = data.get(section_key) or []
        parts.extend(_walk_texts(section))
    return "\n\n".join(t for t in parts if t.strip())


# ─────────────────────────────────────────────
# Idempotency helpers
# ─────────────────────────────────────────────

def sanitize_ecli(ecli: str) -> str:
    """Convert ECLI to a valid Firestore document ID."""
    return re.sub(r"[/\s]+", "_", ecli).replace(":", "_")


async def document_exists(fs: FirestoreClient, doc_id: str) -> bool:
    """Check if a document already exists in Firestore."""
    doc = await fs.get_document(doc_id)
    return doc is not None


# ─────────────────────────────────────────────
# Ingest pipeline
# ─────────────────────────────────────────────

async def ingest_item(
    item: dict,
    match_reason: str,
    customer_id: str,
    widget_id: str,
    fs: FirestoreClient,
    gemini: GeminiClient,
    processor: DocumentProcessor,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    verbose: bool,
) -> str:
    """
    Process and store a single court decision.

    Returns: 'inserted' | 'skipped' | 'error'
    """
    ecli: str = item.get("ecli") or ""
    odkaz: str = item.get("odkaz") or ""
    uuid = _extract_uuid(odkaz)

    if not ecli and not uuid:
        logger.warning("Item has neither ECLI nor UUID, skipping: %s", item.get("jednaciCislo"))
        return "error"

    doc_id = sanitize_ecli(ecli) if ecli else f"uuid_{uuid}"

    if verbose:
        logger.info("Processing: %s (%s)", ecli or uuid, match_reason)

    # Idempotency check
    if await document_exists(fs, doc_id):
        if verbose:
            logger.info("SKIP (exists): %s", doc_id)
        return "skipped"

    # Fetch full text
    if not uuid:
        logger.warning("No UUID for %s, skipping full text", ecli)
        return "error"

    full_text = await fetch_full_text(client, uuid, semaphore)
    if not full_text.strip():
        logger.warning("Empty full text for %s", ecli or uuid)
        return "error"

    # Chunk text
    chunks = processor.chunk_text(full_text)
    if not chunks:
        logger.warning("No chunks for %s", ecli or uuid)
        return "error"

    # Generate embeddings
    try:
        chunk_texts = [c["text"] for c in chunks]
        embeddings = await gemini.generate_embeddings_batch(chunk_texts)
    except Exception as exc:
        logger.error("Embedding failed for %s: %s", ecli or uuid, exc)
        return "error"

    if len(embeddings) != len(chunks):
        logger.error(
            "Embedding count mismatch for %s: %d vs %d",
            ecli or uuid, len(embeddings), len(chunks),
        )
        return "error"

    # Build document record
    now = datetime.now(timezone.utc)
    doc_data = {
        "id": doc_id,
        "customer_id": customer_id,
        "user_id": customer_id,
        "filename": f"{item.get('soud', '')} - {item.get('jednaciCislo', '')}",
        "content_type": "judikat",
        "category": "judikat",
        "text": full_text,
        "status": "ready",
        "chunk_count": len(chunks),
        "storage_path": "",
        "widget_ids": [widget_id],
        "metadata": {
            "ecli": ecli,
            "uuid": uuid,
            "soud": item.get("soud", ""),
            "jednaci_cislo": item.get("jednaciCislo", ""),
            "datum_vydani": item.get("datumVydani", ""),
            "datum_zverejneni": item.get("datumZverejneni", ""),
            "predmet_rizeni": item.get("predmetRizeni", ""),
            "klicova_slova": item.get("klicovaSlova") or [],
            "zminena_ustanoveni": item.get("zminenaUstanoveni") or [],
            "odkaz": odkaz,
            "filter_match_reason": match_reason,
        },
        "created_at": now,
        "updated_at": now,
    }

    # Write document to Firestore with explicit ID
    doc_ref = fs.db.collection("documents").document(doc_id)
    doc_ref.set(doc_data)

    # Write chunks sub-collection
    chunks_with_embeddings = [
        {
            "text": chunks[i]["text"],
            "embedding": embeddings[i],
            "chunk_index": chunks[i]["chunk_index"],
            "page_number": chunks[i].get("page_number"),
            "metadata": {},
        }
        for i in range(len(chunks))
    ]
    await fs.create_chunks(doc_id, chunks_with_embeddings)

    # Add document to widget's document_ids list
    await _add_doc_to_widget(fs, widget_id, doc_id)

    if verbose:
        logger.info("INSERTED: %s (%d chunks)", doc_id, len(chunks))

    return "inserted"


async def _add_doc_to_widget(fs: FirestoreClient, widget_id: str, doc_id: str) -> None:
    """Append doc_id to widget.document_ids (deduplicated)."""
    widget = await fs.get_widget(widget_id)
    if not widget:
        logger.warning("Widget %s not found — skipping document_ids update", widget_id)
        return
    existing: list[str] = widget.get("document_ids") or []
    if doc_id not in existing:
        await fs.update_widget(widget_id, {"document_ids": existing + [doc_id]})


# ─────────────────────────────────────────────
# Year range parser
# ─────────────────────────────────────────────

def parse_years(years_str: str) -> list[int]:
    """Parse '2021-2026' or '2024' into a list of years."""
    if "-" in years_str:
        parts = years_str.split("-")
        if len(parts) == 2:
            start, end = int(parts[0]), int(parts[1])
            return list(range(start, end + 1))
    return [int(years_str)]


# ─────────────────────────────────────────────
# Main orchestration
# ─────────────────────────────────────────────

async def run(
    years: list[int],
    max_docs: int,
    concurrency: int,
    dry_run: bool,
    widget_id: str,
    verbose: bool,
) -> None:
    fs = FirestoreClient()
    gemini = GeminiClient()
    processor = DocumentProcessor()

    # Resolve customer_id from widget
    widget = await fs.get_widget(widget_id)
    if not widget:
        logger.error("Widget %s not found in Firestore", widget_id)
        sys.exit(1)
    customer_id: str = widget["customer_id"]
    logger.info("Widget %s → customer_id=%s", widget_id, customer_id)

    semaphore = asyncio.Semaphore(concurrency)
    llm_semaphore = asyncio.Semaphore(LLM_CONCURRENCY)
    stats = {
        "processed": 0,
        "regex_match": 0,
        "llm_ano": 0,
        "llm_nejiste": 0,
        "llm_no": 0,
        "inserted": 0,
        "skipped": 0,
        "error": 0,
    }
    samples: list[dict] = []
    total_time = 0.0

    async with httpx.AsyncClient(
        headers={"Accept": "application/json"},
        follow_redirects=True,
    ) as client:
        for year in years:
            if max_docs and stats["inserted"] >= max_docs:
                break

            logger.info("=== Year %d ===", year)
            months = await fetch_year_months(client, year, semaphore)

            for month_entry in months:
                if max_docs and stats["inserted"] >= max_docs:
                    break

                month: int = month_entry.get("mesic") or month_entry.get("month") or 0
                if not month:
                    continue

                days = await fetch_month_days(client, year, month, semaphore)

                for day_entry in days:
                    if max_docs and stats["inserted"] >= max_docs:
                        break

                    day_str: str = day_entry.get("datum") or ""
                    try:
                        day_val = int(day_str.split("-")[2]) if day_str else 0
                    except (IndexError, ValueError):
                        continue
                    if not day_val:
                        continue

                    items = await fetch_day_items(client, year, month, day_val, semaphore)

                    for item in items:
                        stats["processed"] += 1

                        match, reason = is_relevant(item)
                        if not match:
                            continue

                        stats["regex_match"] += 1

                        # Fetch full text for SECONDARY candidates and dry-run samples
                        odkaz: str = item.get("odkaz") or ""
                        uuid = _extract_uuid(odkaz)

                        if not uuid:
                            if verbose:
                                logger.info("SKIP (no_uuid): %s", item.get("ecli"))
                            stats["error"] += 1
                            continue

                        full_text = await fetch_full_text(client, uuid, semaphore)

                        # LLM classification — all regex matches go straight to LLM
                        verdict = await classify_with_llm(item, full_text, gemini, llm_semaphore)

                        if verbose:
                            logger.info(
                                "LLM=%s | %s | %s | reason=%s",
                                verdict, item.get("ecli"), item.get("soud"), reason,
                            )

                        if verdict == "ANO":
                            stats["llm_ano"] += 1
                        elif verdict == "NEJISTE":
                            stats["llm_nejiste"] += 1
                        else:
                            stats["llm_no"] += 1

                        if verdict not in ("ANO", "NEJISTE"):
                            continue

                        # Collect dry-run samples
                        if dry_run:
                            if len(samples) < 5 and verdict == "ANO":
                                samples.append({
                                    "ecli": item.get("ecli"),
                                    "soud": item.get("soud"),
                                    "jednaciCislo": item.get("jednaciCislo"),
                                    "datumVydani": item.get("datumVydani"),
                                    "predmetRizeni": (item.get("predmetRizeni") or "")[:120],
                                    "klicovaSlova": (item.get("klicovaSlova") or [])[:5],
                                    "zminenaUstanoveni": (item.get("zminenaUstanoveni") or [])[:5],
                                    "reason": reason,
                                    "llm": verdict,
                                    "text_preview": full_text[:200],
                                })
                            continue

                        # Real ingest
                        if max_docs and stats["inserted"] >= max_docs:
                            break

                        t0 = time.monotonic()
                        result = await ingest_item(
                            item=item,
                            match_reason=f"{reason}|llm:{verdict}",
                            customer_id=customer_id,
                            widget_id=widget_id,
                            fs=fs,
                            gemini=gemini,
                            processor=processor,
                            client=client,
                            semaphore=semaphore,
                            verbose=verbose,
                        )
                        elapsed = time.monotonic() - t0
                        total_time += elapsed

                        if result == "inserted":
                            stats["inserted"] += 1
                        elif result == "skipped":
                            stats["skipped"] += 1
                        else:
                            stats["error"] += 1

                        total_ingested = stats["inserted"] + stats["skipped"] + stats["error"]
                        if total_ingested % LOG_PROGRESS_EVERY == 0:
                            avg = total_time / max(stats["inserted"], 1)
                            logger.info(
                                "Progress: processed=%d regex=%d "
                                "llm_ano=%d llm_nejiste=%d llm_no=%d "
                                "inserted=%d skipped=%d errors=%d avg=%.1fs",
                                stats["processed"], stats["regex_match"],
                                stats["llm_ano"], stats["llm_nejiste"], stats["llm_no"],
                                stats["inserted"], stats["skipped"], stats["error"], avg,
                            )

    # Final report
    logger.info("─" * 60)
    logger.info(
        "DONE  processed=%d  regex_match=%d  "
        "llm_ano=%d  llm_nejiste=%d  llm_no=%d  "
        "inserted=%d  skipped=%d  errors=%d",
        stats["processed"], stats["regex_match"],
        stats["llm_ano"], stats["llm_nejiste"], stats["llm_no"],
        stats["inserted"], stats["skipped"], stats["error"],
    )
    if not dry_run and stats["inserted"]:
        avg_time = total_time / stats["inserted"]
        logger.info("Avg time per document: %.2fs", avg_time)

    if dry_run:
        logger.info("DRY RUN — no data written to Firestore")
        logger.info(
            "Filter funnel: regex=%d → llm_ano=%d / llm_nejiste=%d / llm_no=%d",
            stats["regex_match"],
            stats["llm_ano"], stats["llm_nejiste"], stats["llm_no"],
        )
        logger.info("Sample ANO decisions (up to 5):")
        for i, s in enumerate(samples, 1):
            logger.info(
                "  [%d] ECLI=%s | %s | %s | reason=%s | llm=%s",
                i, s.get("ecli"), s.get("soud"), s.get("jednaciCislo"),
                s.get("reason"), s.get("llm"),
            )
            logger.info("       predmět: %s", s.get("predmetRizeni"))
            if s.get("klicovaSlova"):
                logger.info("       klíčová slova: %s", s.get("klicovaSlova"))
            logger.info("       text (200 chars): %s", s.get("text_preview", "")[:200])


# ─────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ingest Czech traffic accident court decisions into Firestore RAG pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--years",
        default="2021-2026",
        help='Year range "2021-2026" or single year "2024" (default: 2021-2026)',
    )
    parser.add_argument(
        "--max",
        type=int,
        default=500,
        dest="max_docs",
        help="Max documents to ingest after filter; 0 = unlimited (default: 500)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Parallel HTTP requests (default: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print stats and samples without writing to Firestore",
    )
    parser.add_argument(
        "--widget-id",
        default=DEFAULT_WIDGET_ID,
        help=f"Widget ID to associate documents with (default: {DEFAULT_WIDGET_ID})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-document log lines",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    years = parse_years(args.years)
    logger.info(
        "Starting ingest: years=%s max=%d concurrency=%d dry_run=%s widget=%s",
        years, args.max_docs, args.concurrency, args.dry_run, args.widget_id,
    )

    asyncio.run(
        run(
            years=years,
            max_docs=args.max_docs,
            concurrency=args.concurrency,
            dry_run=args.dry_run,
            widget_id=args.widget_id,
            verbose=args.verbose,
        )
    )


if __name__ == "__main__":
    main()
