"""
Generate lay-friendly abstracts for Czech court decisions (judikáty) in Firestore.

For each document with category="judikat", generates a 1-2 paragraph abstract via
Gemini 2.0 Flash and stores it as an additional chunk in the document's chunks
sub-collection. Abstracts improve RAG recall for layman queries (e.g., "kolik dostanu
na bolestném") that have low cosine similarity against formal legal text.

Usage:
    python scripts/generate_judikat_abstracts.py --dry-run --max 3 --verbose
    python scripts/generate_judikat_abstracts.py --max 50
    python scripts/generate_judikat_abstracts.py  2>&1 | tee /tmp/abstracts.log | tail -30

Required env vars:
    GOOGLE_APPLICATION_CREDENTIALS  - Path to GCP service account JSON
    GOOGLE_API_KEY                   - Gemini API key
    GOOGLE_CLOUD_PROJECT             - GCP project ID (e.g. chatbot-platform-2026)

Idempotent: documents that already have a chunk with metadata.is_abstract==True are skipped.
"""

import argparse
import asyncio
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from google.genai import types as gtypes

from src.core.firestore import FirestoreClient
from src.core.gemini import GeminiClient

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

DEFAULT_CUSTOMER_ID = "R2e1hKaEcmQ2GIhThSQU"
DEFAULT_WIDGET_ID = "ls0Si9wuw2gbatGla3nW"
ABSTRACT_CHUNK_INDEX = 9000
TEXT_TRUNCATE_CHARS = 15_000
MAX_RETRIES = 5
LLM_CONCURRENCY = 5
FS_CONCURRENCY = 3
LOG_PROGRESS_EVERY = 25

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("generate_judikat_abstracts")


# ─────────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────────

_ABSTRACT_SYSTEM = """\
Jsi český právník-popularizátor. Tvůj úkol: vytvořit krátký, lay-friendly abstract \
českého soudního rozhodnutí, který pochopí běžný občan bez právního vzdělání.

PRAVIDLA:
- 1-2 odstavce (max 200 slov).
- Strukturuj kolem TŘÍ pilířů: (1) co se stalo (typ nehody/újmy, role poškozeného), \
(2) kolik soud přiznal (konkrétní částka, druhy nároků — bolestné, ztížení společenského \
uplatnění, ztráta na výdělku, náklady léčení), (3) klíčový důvod rozhodnutí (proč soud \
přiznal/nepřiznal).
- BEZ právní hantýrky. Místo "promlčení" napiš "lhůta na podání žaloby vypršela". \
Místo "deliktní odpovědnost" napiš "odpovědnost za škodu".
- Pokud rozsudek neobsahuje konkrétní částku (např. zamítavý rozsudek), napiš to explicitně.
- VŽDY uveď ECLI nebo jednací číslo na konci formátem: [ECLI: <ecli>] nebo [JC: <jc>].
- Piš VÝHRADNĚ česky.\
"""

_ABSTRACT_USER_TEMPLATE = """\
Soud: {soud}
Jednací číslo: {jednaci_cislo}
ECLI: {ecli}
Datum vydání: {datum_vydani}
Předmět řízení: {predmet_rizeni}
Klíčová slova: {klicova_slova}
Zmíněná ustanovení: {zminena_ustanoveni}

PLNÝ TEXT ROZHODNUTÍ (zkrácený):
{text_truncated}

Vytvoř lay-friendly abstract dle pravidel.\
"""


# ─────────────────────────────────────────────
# Gemini — abstract generation with retry
# ─────────────────────────────────────────────

async def generate_abstract(
    doc: dict,
    gemini: GeminiClient,
    llm_semaphore: asyncio.Semaphore,
) -> str:
    """
    Generate a lay-friendly abstract for a judikát document.

    Returns the abstract text string.
    Raises RuntimeError after MAX_RETRIES exhausted.
    """
    metadata = doc.get("metadata") or {}
    full_text: str = doc.get("text") or ""
    text_truncated = full_text[:TEXT_TRUNCATE_CHARS]

    user_prompt = _ABSTRACT_USER_TEMPLATE.format(
        soud=metadata.get("soud", ""),
        jednaci_cislo=metadata.get("jednaci_cislo", ""),
        ecli=metadata.get("ecli", ""),
        datum_vydani=metadata.get("datum_vydani", ""),
        predmet_rizeni=metadata.get("predmet_rizeni", ""),
        klicova_slova=", ".join(metadata.get("klicova_slova") or []),
        zminena_ustanoveni=", ".join(metadata.get("zminena_ustanoveni") or []),
        text_truncated=text_truncated,
    )

    async with llm_semaphore:
        for attempt in range(MAX_RETRIES):
            try:
                response = gemini.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[
                        gtypes.Content(
                            role="user",
                            parts=[gtypes.Part.from_text(text=user_prompt)],
                        )
                    ],
                    config=gtypes.GenerateContentConfig(
                        system_instruction=_ABSTRACT_SYSTEM,
                        temperature=0.3,
                        max_output_tokens=600,
                    ),
                )
                text = (response.text or "").strip()
                if text:
                    return text
                raise ValueError("Empty response from Gemini")

            except Exception as exc:
                err_str = str(exc)
                is_rate_limit = "429" in err_str or "quota" in err_str.lower()
                if attempt < MAX_RETRIES - 1:
                    wait = min(2 ** attempt * (4 if is_rate_limit else 1), 60)
                    logger.warning(
                        "Gemini error (attempt %d/%d), retry in %ds: %s",
                        attempt + 1, MAX_RETRIES, wait, exc,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise RuntimeError(
                        f"Abstract generation failed after {MAX_RETRIES} attempts: {exc}"
                    ) from exc

    raise RuntimeError("Unreachable")


# ─────────────────────────────────────────────
# Firestore helpers
# ─────────────────────────────────────────────

def has_existing_abstract(fs: FirestoreClient, doc_id: str) -> bool:
    """Return True if the document already has an abstract chunk."""
    doc_ref = fs.db.collection("documents").document(doc_id)
    existing = list(
        doc_ref.collection("chunks")
        .where("metadata.is_abstract", "==", True)
        .limit(1)
        .stream()
    )
    return len(existing) > 0


def load_judikat_docs(
    fs: FirestoreClient,
    customer_id: str,
    max_docs: int,
) -> list[dict]:
    """
    Load judikát documents from Firestore filtered by customer_id and category.

    Returns list of document dicts (with 'id' field).
    """
    query = (
        fs.db.collection("documents")
        .where("customer_id", "==", customer_id)
        .where("category", "==", "judikat")
    )
    docs = list(query.stream())
    result = [d.to_dict() for d in docs]
    if max_docs:
        result = result[:max_docs]
    return result


# ─────────────────────────────────────────────
# Per-document processing
# ─────────────────────────────────────────────

async def process_document(
    doc: dict,
    fs: FirestoreClient,
    gemini: GeminiClient,
    llm_semaphore: asyncio.Semaphore,
    fs_semaphore: asyncio.Semaphore,
    dry_run: bool,
    verbose: bool,
) -> str:
    """
    Process a single judikát document: check idempotency, generate abstract,
    embed it, and write the abstract chunk.

    Returns: 'generated' | 'skipped' | 'llm_error' | 'embed_error' | 'write_error'
    """
    doc_id: str = doc.get("id") or ""
    metadata = doc.get("metadata") or {}
    ecli = metadata.get("ecli", "")
    soud = metadata.get("soud", "")
    jc = metadata.get("jednaci_cislo", "")

    if verbose:
        logger.info("Processing: %s | %s | %s", ecli or doc_id, soud, jc)

    # Idempotency check (sync Firestore call, guarded by fs semaphore)
    async with fs_semaphore:
        already_done = has_existing_abstract(fs, doc_id)

    if already_done:
        if verbose:
            logger.info("SKIP (abstract exists): %s", doc_id)
        return "skipped"

    # Generate abstract text
    try:
        abstract_text = await generate_abstract(doc, gemini, llm_semaphore)
    except RuntimeError as exc:
        logger.error("LLM error for %s: %s", doc_id, exc)
        return "llm_error"

    if dry_run:
        return "generated"

    # Generate embedding for abstract
    try:
        abstract_embedding = await gemini.generate_embedding(abstract_text)
    except Exception as exc:
        logger.error("Embed error for %s: %s", doc_id, exc)
        return "embed_error"

    # Write abstract chunk
    now_iso = datetime.now(timezone.utc).isoformat()
    abstract_chunk = {
        "text": abstract_text,
        "embedding": abstract_embedding,
        "chunk_index": ABSTRACT_CHUNK_INDEX,
        "page_number": None,
        "metadata": {
            "is_abstract": True,
            "abstract_version": 1,
            "generated_at": now_iso,
            "model": "gemini-2.0-flash",
        },
    }

    try:
        async with fs_semaphore:
            await fs.create_chunks(doc_id, [abstract_chunk])
    except Exception as exc:
        logger.error("Write error for %s: %s", doc_id, exc)
        return "write_error"

    if verbose:
        logger.info(
            "DONE: %s | abstract=%d chars",
            doc_id, len(abstract_text),
        )

    return "generated"


# ─────────────────────────────────────────────
# Main orchestration
# ─────────────────────────────────────────────

async def run(
    customer_id: str,
    widget_id: str,
    max_docs: int,
    dry_run: bool,
    verbose: bool,
) -> None:
    fs = FirestoreClient()
    gemini = GeminiClient()

    logger.info(
        "Loading judikáty: customer_id=%s widget_id=%s max=%d dry_run=%s",
        customer_id, widget_id, max_docs, dry_run,
    )

    docs = load_judikat_docs(fs, customer_id, max_docs)
    total = len(docs)
    logger.info("Found %d judikát documents to process", total)

    if total == 0:
        logger.warning(
            "No documents found for customer_id=%s category=judikat", customer_id
        )
        return

    llm_semaphore = asyncio.Semaphore(LLM_CONCURRENCY)
    fs_semaphore = asyncio.Semaphore(FS_CONCURRENCY)

    stats = {
        "generated": 0,
        "skipped": 0,
        "llm_error": 0,
        "embed_error": 0,
        "write_error": 0,
    }
    samples: list[dict] = []
    total_time = 0.0
    processed = 0

    async def process_with_stats(doc: dict) -> None:
        nonlocal total_time, processed

        t0 = time.monotonic()
        result = await process_document(
            doc=doc,
            fs=fs,
            gemini=gemini,
            llm_semaphore=llm_semaphore,
            fs_semaphore=fs_semaphore,
            dry_run=dry_run,
            verbose=verbose,
        )
        elapsed = time.monotonic() - t0

        stats[result] = stats.get(result, 0) + 1
        if result == "generated":
            total_time += elapsed

        processed += 1
        if processed % LOG_PROGRESS_EVERY == 0:
            avg = total_time / max(stats["generated"], 1)
            logger.info(
                "Progress %d/%d: generated=%d skipped=%d "
                "llm_err=%d embed_err=%d write_err=%d avg=%.1fs",
                processed, total,
                stats["generated"], stats["skipped"],
                stats["llm_error"], stats["embed_error"], stats["write_error"],
                avg,
            )

        # Collect dry-run samples (first 5 new abstracts)
        if dry_run and result == "generated" and len(samples) < 5:
            metadata = doc.get("metadata") or {}
            # Re-generate abstract for sample display (semaphore already released)
            try:
                abstract_text = await generate_abstract(doc, gemini, llm_semaphore)
            except RuntimeError:
                abstract_text = "(generation failed for sample)"
            samples.append({
                "index": processed,
                "total": total,
                "ecli": metadata.get("ecli", ""),
                "soud": metadata.get("soud", ""),
                "jc": metadata.get("jednaci_cislo", ""),
                "abstract": abstract_text,
            })

    # Process all documents concurrently (semaphores control actual parallelism)
    tasks = [process_with_stats(doc) for doc in docs]
    await asyncio.gather(*tasks)

    # Final report
    avg_time = total_time / max(stats["generated"], 1)
    logger.info("─" * 60)
    logger.info(
        "DONE  total_judikats=%d  already_had_abstract=%d  generated=%d  "
        "llm_errors=%d  embed_errors=%d  write_errors=%d  avg_time=%.2fs",
        total,
        stats["skipped"],
        stats["generated"],
        stats["llm_error"],
        stats["embed_error"],
        stats["write_error"],
        avg_time,
    )

    if dry_run:
        logger.info("DRY RUN — no data written to Firestore")
        logger.info("Sample abstracts (up to 5):")
        for s in samples:
            abstract = s["abstract"]
            logger.info(
                "\n[%d/%d] ECLI=%s | soud=%s | jc=%s\n"
                "  ABSTRACT (%d chars):\n  %s",
                s["index"], s["total"],
                s["ecli"], s["soud"], s["jc"],
                len(abstract),
                abstract.replace("\n", "\n  "),
            )


# ─────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate lay-friendly abstracts for judikát documents in Firestore.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--customer-id",
        default=DEFAULT_CUSTOMER_ID,
        dest="customer_id",
        help=f"Customer ID to scope document query (default: {DEFAULT_CUSTOMER_ID})",
    )
    parser.add_argument(
        "--widget-id",
        default=DEFAULT_WIDGET_ID,
        dest="widget_id",
        help=f"Widget ID (informational only, default: {DEFAULT_WIDGET_ID})",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=0,
        dest="max_docs",
        help="Max documents to process; 0 = unlimited (default: 0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and display sample abstracts without writing to Firestore",
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

    logger.info(
        "Starting generate_judikat_abstracts: customer_id=%s max=%d dry_run=%s",
        args.customer_id, args.max_docs, args.dry_run,
    )

    asyncio.run(
        run(
            customer_id=args.customer_id,
            widget_id=args.widget_id,
            max_docs=args.max_docs,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    )


if __name__ == "__main__":
    main()
