"""
Eval skript: Phase 4 retrieval — vliv lay-friendly abstraktů na retrieval shodu.

Měří, zda abstract chunky (is_abstract=True, chunk_index=9000) zlepšily cosine/BM25 RRF
skóre pro typické laické dotazy proti widgetu Ponehodová péče.

Usage:
    python scripts/eval_phase4_retrieval.py
    python scripts/eval_phase4_retrieval.py --queries-file queries.txt --top-k 10
    python scripts/eval_phase4_retrieval.py 2>&1 | tee /tmp/eval_phase4.log | tail -50

Required env vars:
    GOOGLE_APPLICATION_CREDENTIALS  - Path to GCP service account JSON
    GOOGLE_CLOUD_PROJECT             - GCP project ID (e.g. chatbot-platform-2026)

Output:
    - Markdown summary → stdout
    - JSON výsledky → eval_phase4_results.json (gitignore-d)

Idempotentní, bez side-effects (jen čtení Firestore + Vertex AI embeddings).
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.firestore import FirestoreClient
from src.core.gemini import GeminiClient
from src.features.chat.retrieval import RetrievalService

# ─────────────────────────────────────────────
# Konstanty
# ─────────────────────────────────────────────

WIDGET_ID = "ls0Si9wuw2gbatGla3nW"
CUSTOMER_ID = "R2e1hKaEcmQ2GIhThSQU"
ABSTRACT_CHUNK_INDEX = 9000

DEFAULT_QUERIES = [
    "Kolik dostanu na bolestném po dopravní nehodě?",
    "Co když mě srazil řidič bez pojištění?",
    "Jak vysoká je náhrada za smrt blízkého při nehodě?",
    "Mám nárok na ušlý zisk když nemůžu pracovat po nehodě?",
    "Kolik mi pojišťovna zaplatí za poškozené auto?",
    "Co dělat když pojišťovna odmítá vyplatit odškodnění?",
    "Mohu žádat odškodnění za psychickou újmu po nehodě?",
    "Jak dlouho trvá vyřízení odškodnění od pojišťovny?",
]

OUTPUT_JSON = Path(__file__).parent.parent / "eval_phase4_results.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("eval_phase4")


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────


def _chunk_type(chunk: dict[str, Any]) -> str:
    """Klasifikuj typ chunku: abstract / judikat_text / web_page."""
    metadata = chunk.get("metadata") or {}
    if metadata.get("is_abstract") is True or chunk.get("chunk_index") == ABSTRACT_CHUNK_INDEX:
        return "abstract"
    category = metadata.get("category", "")
    if category == "judikat":
        return "judikat_text"
    return "web_page"


def _safe_text_preview(text: str | None, length: int = 80) -> str:
    if not text:
        return ""
    single_line = text.replace("\n", " ").replace("\r", " ")
    return single_line[:length]


async def _load_widget_doc_ids(firestore: FirestoreClient) -> list[str]:
    """Načti document_ids widgetu z Firestore."""
    widget = await firestore.get_widget(WIDGET_ID)
    if not widget:
        raise RuntimeError(f"Widget {WIDGET_ID} nenalezen v Firestore")
    doc_ids = widget.get("document_ids", [])
    logger.info(f"Widget má {len(doc_ids)} dokumentů")
    return doc_ids


async def _load_doc_metadata(firestore: FirestoreClient, doc_ids: list[str]) -> dict[str, dict]:
    """Načti metadata dokumentů (filename, category) pro doc_id lookup."""
    meta: dict[str, dict] = {}
    batch_size = 50
    for i in range(0, len(doc_ids), batch_size):
        batch = doc_ids[i : i + batch_size]
        for doc_id in batch:
            doc = await firestore.get_document(doc_id)
            if doc:
                meta[doc_id] = {
                    "filename": doc.get("filename", ""),
                    "category": doc.get("category", ""),
                    "source_url": doc.get("source_url", doc.get("storage_path", "")),
                }
    logger.info(f"Načtena metadata pro {len(meta)} dokumentů")
    return meta


def _run_retrieval_for_query(
    retrieval: RetrievalService,
    query: str,
    doc_ids: list[str],
    top_k: int,
) -> list[dict[str, Any]]:
    """Synchronní wrapper pro asyncio retrieval — spustí se v event loop."""
    return asyncio.get_event_loop().run_until_complete(
        retrieval.search(query=query, document_ids=doc_ids, top_k=top_k, min_score=0.0)
    )


async def run_eval(queries: list[str], top_k: int) -> dict[str, Any]:
    """Hlavní eval pipeline."""
    firestore = FirestoreClient()
    gemini = GeminiClient()
    retrieval = RetrievalService(firestore=firestore, gemini=gemini)

    # Načti widget doc_ids
    doc_ids = await _load_widget_doc_ids(firestore)
    doc_meta = await _load_doc_metadata(firestore, doc_ids)

    results_per_query: list[dict[str, Any]] = []

    for q_idx, query in enumerate(queries):
        logger.info(f"Dotaz {q_idx + 1}/{len(queries)}: {query[:60]}...")

        chunks = await retrieval.search(
            query=query,
            document_ids=doc_ids,
            top_k=top_k,
            min_score=0.0,
        )

        ranked_chunks = []
        for rank, chunk in enumerate(chunks, start=1):
            doc_id = chunk.get("document_id", "")
            meta = doc_meta.get(doc_id, {})
            chunk_type = _chunk_type(chunk)
            ranked_chunks.append({
                "rank": rank,
                "score": round(chunk.get("score", 0.0), 6),
                "doc_id": doc_id,
                "chunk_id": chunk.get("id", ""),
                "chunk_index": chunk.get("chunk_index"),
                "is_abstract": chunk_type == "abstract",
                "chunk_type": chunk_type,
                "filename": meta.get("filename", ""),
                "category": meta.get("category", ""),
                "text_preview": _safe_text_preview(chunk.get("text", ""), 80),
            })

        results_per_query.append({
            "query": query,
            "chunks": ranked_chunks,
        })

    return {
        "eval_timestamp": datetime.now(timezone.utc).isoformat(),
        "widget_id": WIDGET_ID,
        "customer_id": CUSTOMER_ID,
        "top_k": top_k,
        "query_count": len(queries),
        "results": results_per_query,
    }


def _aggregate(eval_data: dict[str, Any]) -> dict[str, Any]:
    """Agreguj výsledky: avg skóre per typ, judikát coverage v top-k/top-3."""
    scores_abstract: list[float] = []
    scores_judikat_text: list[float] = []
    scores_web_page: list[float] = []

    queries_with_judikat_in_top_k = 0
    queries_with_judikat_in_top_3 = 0
    queries_with_abstract_in_top_k = 0
    queries_with_abstract_in_top_3 = 0

    top_k = eval_data["top_k"]

    for result in eval_data["results"]:
        chunks = result["chunks"]
        has_judikat_top_k = False
        has_judikat_top_3 = False
        has_abstract_top_k = False
        has_abstract_top_3 = False

        for chunk in chunks:
            score = chunk["score"]
            ctype = chunk["chunk_type"]
            rank = chunk["rank"]

            if ctype == "abstract":
                scores_abstract.append(score)
                has_abstract_top_k = True
                if rank <= 3:
                    has_abstract_top_3 = True
            elif ctype == "judikat_text":
                scores_judikat_text.append(score)
                has_judikat_top_k = True
                if rank <= 3:
                    has_judikat_top_3 = True
            elif ctype == "web_page":
                scores_web_page.append(score)

        if has_judikat_top_k:
            queries_with_judikat_in_top_k += 1
        if has_judikat_top_3:
            queries_with_judikat_in_top_3 += 1
        if has_abstract_top_k:
            queries_with_abstract_in_top_k += 1
        if has_abstract_top_3:
            queries_with_abstract_in_top_3 += 1

    def _avg(lst: list[float]) -> float:
        return round(sum(lst) / len(lst), 6) if lst else 0.0

    query_count = eval_data["query_count"]
    return {
        "avg_score_abstract": _avg(scores_abstract),
        "avg_score_judikat_text": _avg(scores_judikat_text),
        "avg_score_web_page": _avg(scores_web_page),
        "total_abstract_chunks_in_results": len(scores_abstract),
        "total_judikat_text_chunks_in_results": len(scores_judikat_text),
        "total_web_page_chunks_in_results": len(scores_web_page),
        "queries_with_any_judikat_in_top_k": queries_with_judikat_in_top_k,
        "queries_with_judikat_in_top_3": queries_with_judikat_in_top_3,
        "queries_with_abstract_in_top_k": queries_with_abstract_in_top_k,
        "queries_with_abstract_in_top_3": queries_with_abstract_in_top_3,
        "pct_queries_judikat_top_k": round(queries_with_judikat_in_top_k / query_count * 100, 1),
        "pct_queries_judikat_top_3": round(queries_with_judikat_in_top_3 / query_count * 100, 1),
        "pct_queries_abstract_top_k": round(queries_with_abstract_in_top_k / query_count * 100, 1),
        "pct_queries_abstract_top_3": round(queries_with_abstract_in_top_3 / query_count * 100, 1),
    }


def _print_markdown_summary(eval_data: dict[str, Any], agg: dict[str, Any]) -> None:
    """Vytiskni markdown summary na stdout."""
    top_k = eval_data["top_k"]
    ts = eval_data["eval_timestamp"]

    print(f"\n## Phase 4 Retrieval Eval — {ts}")
    print(f"Widget: `{eval_data['widget_id']}` | top_k={top_k} | dotazů={eval_data['query_count']}\n")

    # Per-query tabulka
    print("### Per-query top-10 retrieval\n")
    for result in eval_data["results"]:
        print(f"**Dotaz:** {result['query']}")
        print(f"{'rank':>4} | {'score':>8} | {'typ':>12} | {'is_abstr':>8} | {'doc_id':>24} | text[:80]")
        print("-" * 100)
        for c in result["chunks"]:
            abstr_flag = "ANO" if c["is_abstract"] else "ne"
            print(
                f"{c['rank']:>4} | {c['score']:>8.5f} | {c['chunk_type']:>12} | {abstr_flag:>8} | "
                f"{c['doc_id']:>24} | {c['text_preview']}"
            )
        print()

    # Agregovaná čísla
    print("### Agregovaná čísla\n")
    print(f"| Metrika | Hodnota |")
    print(f"|---|---|")
    print(f"| avg score abstract chunky | {agg['avg_score_abstract']} |")
    print(f"| avg score judikat_text chunky | {agg['avg_score_judikat_text']} |")
    print(f"| avg score web_page chunky | {agg['avg_score_web_page']} |")
    print(f"| abstract v top-{top_k} (počet chunků celkem) | {agg['total_abstract_chunks_in_results']} |")
    print(f"| judikat_text v top-{top_k} (počet chunků celkem) | {agg['total_judikat_text_chunks_in_results']} |")
    print(f"| web_page v top-{top_k} (počet chunků celkem) | {agg['total_web_page_chunks_in_results']} |")
    print(f"| dotazů s aspoň 1 judikát (text nebo abstract) v top-{top_k} | {agg['queries_with_any_judikat_in_top_k']}/{eval_data['query_count']} ({agg['pct_queries_judikat_top_k']}%) |")
    print(f"| dotazů s aspoň 1 judikát v top-3 | {agg['queries_with_judikat_in_top_3']}/{eval_data['query_count']} ({agg['pct_queries_judikat_top_3']}%) |")
    print(f"| dotazů s aspoň 1 ABSTRACT v top-{top_k} | {agg['queries_with_abstract_in_top_k']}/{eval_data['query_count']} ({agg['pct_queries_abstract_top_k']}%) |")
    print(f"| dotazů s aspoň 1 ABSTRACT v top-3 | {agg['queries_with_abstract_in_top_3']}/{eval_data['query_count']} ({agg['pct_queries_abstract_top_3']}%) |")

    # Verdikt
    print("\n### Verdikt\n")
    abs_score = agg["avg_score_abstract"]
    jt_score = agg["avg_score_judikat_text"]
    wp_score = agg["avg_score_web_page"]
    abs_top3_pct = agg["pct_queries_abstract_top_3"]
    abs_topk_pct = agg["pct_queries_abstract_top_k"]

    if abs_score > jt_score and abs_top3_pct >= 50:
        verdict = "ANO — abstrakty zlepšily retrieval"
        reason = (
            f"avg score abstract ({abs_score}) > judikat_text ({jt_score}), "
            f"abstract v top-3 u {abs_top3_pct}% dotazů."
        )
    elif abs_score > jt_score and abs_topk_pct >= 50:
        verdict = "PRAVDEPODOBNE ANO — abstrakty v top-k, slabší signal v top-3"
        reason = (
            f"avg score abstract ({abs_score}) > judikat_text ({jt_score}), "
            f"ale abstract v top-3 jen u {abs_top3_pct}% dotazů (top-{top_k}: {abs_topk_pct}%)."
        )
    elif agg["total_abstract_chunks_in_results"] == 0:
        verdict = "NE — abstrakty se vůbec nedostaly do výsledků"
        reason = f"0 abstract chunků v top-{top_k} pro všech {eval_data['query_count']} dotazů. Zkontroluj, zda jsou indexovány s is_abstract=True."
    else:
        verdict = "NEJISTE — abstrakty přítomny, ale skóre nepřevyšuje text-chunky"
        reason = (
            f"avg score abstract ({abs_score}) vs judikat_text ({jt_score}) vs web_page ({wp_score}). "
            f"Abstract v top-{top_k} u {abs_topk_pct}% dotazů, v top-3 u {abs_top3_pct}%."
        )

    print(f"**{verdict}**")
    print(f"\nDůkaz: {reason}")
    print(f"\nJSON výsledky uloženy: `{OUTPUT_JSON}`")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Eval Phase 4 retrieval — abstract chunky vs laické dotazy"
    )
    parser.add_argument(
        "--queries-file",
        type=Path,
        default=None,
        help="Textový soubor s dotazy (1 dotaz na řádek). Default: hardcoded 8 dotazů.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Počet výsledků na dotaz (default: 10)",
    )
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()

    if args.queries_file:
        queries_path = Path(args.queries_file)
        if not queries_path.exists():
            logger.error(f"Soubor s dotazy nenalezen: {queries_path}")
            sys.exit(1)
        queries = [
            line.strip()
            for line in queries_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        logger.info(f"Načteno {len(queries)} dotazů ze souboru {queries_path}")
    else:
        queries = DEFAULT_QUERIES
        logger.info(f"Používám {len(queries)} hardcoded dotazů")

    logger.info(f"Spouštím eval: top_k={args.top_k}, dotazů={len(queries)}")

    eval_data = await run_eval(queries=queries, top_k=args.top_k)
    agg = _aggregate(eval_data)
    eval_data["aggregated"] = agg

    # Ulož JSON
    OUTPUT_JSON.write_text(
        json.dumps(eval_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(f"JSON uložen: {OUTPUT_JSON}")

    # Markdown summary na stdout
    _print_markdown_summary(eval_data, agg)


if __name__ == "__main__":
    asyncio.run(main())
