"""Verify judikat ingestion in Firestore."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.firestore import get_firestore_client


async def main():
    fs = get_firestore_client()
    customer_id = "R2e1hKaEcmQ2GIhThSQU"
    widget_id = "ls0Si9wuw2gbatGla3nW"

    docs_ref = fs.db.collection("documents").where("category", "==", "judikat").where("customer_id", "==", customer_id)
    docs = list(docs_ref.stream())
    print(f"Documents with category=judikat for customer {customer_id}: {len(docs)}")

    widget = await fs.get_widget(widget_id)
    if widget:
        doc_ids = widget.get("document_ids", [])
        print(f"Widget {widget_id} document_ids count: {len(doc_ids)}")
    else:
        print(f"Widget {widget_id} NOT FOUND")

    print("\n--- 3 sample documents ---")
    for i, doc in enumerate(docs[:3]):
        d = doc.to_dict()
        meta = d.get("metadata", {})
        text = d.get("text", "")
        print(f"\n[{i+1}] {d.get('filename', '<no filename>')}")
        print(f"    ECLI: {meta.get('ecli', '?')}")
        print(f"    Soud: {meta.get('soud', '?')}")
        print(f"    Datum: {meta.get('datum_vydani', '?')}")
        print(f"    Predmet: {meta.get('predmet_rizeni', '?')[:120]}")
        print(f"    Klicova slova: {meta.get('klicova_slova', [])[:5]}")
        print(f"    Filter reason: {meta.get('filter_match_reason', '?')}")
        print(f"    Text (200 chars): {text[:200]}")

    chunks_count = 0
    for doc in docs[:50]:
        sub = list(fs.db.collection("documents").document(doc.id).collection("chunks").stream())
        chunks_count += len(sub)
    print(f"\nChunks across first 50 docs: {chunks_count}")


if __name__ == "__main__":
    asyncio.run(main())
