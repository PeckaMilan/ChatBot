# Pending — ChatBot Platform

> Overwritten by every /finish. Authoritative immediate-action list for next /start.

*Last updated: 2026-05-05*

## P0 — Blockers
*(none)*

## P1 — Active Priorities
- **Phase 4: LLM-generated abstrakty + re-embed pro 322 judikátů** — vyřeší slabou retrieval shodu (laické dotazy ↔ formální rozsudky, score ~0.029). Nový skript `scripts/generate_judikat_abstracts.py`: pro každý judikát vygenerovat 1-2 odstavcový lay-friendly abstract (Gemini Flash) → re-embed → uložit jako alternativní/dodatečný chunk. — delegate: `coder` | needs Board: no
- **Smazat orphan Cloud Run service v `phoenix-staging-ea`** — `gcloud run services delete chatbot-api --region europe-west1 --project phoenix-staging-ea` (vznikla při incident AP-05, nemá přístup k produkčnímu Firestore, je nefunkční). — delegate: CEO direct | needs Board: yes (destruktivní akce)

## P2 — Backlog (next 2–3 sessions)
- **Phase 5: Hybrid search** (BM25 keyword + dense vector) v `chat/retrieval.py` — zejména match na ECLI / jednací číslo když uživatel cituje konkrétní rozsudek.
- **Pravidelný re-ingest justice.cz** — cron / Cloud Scheduler týdně volá `scripts/ingest_judikaty.py --years <current>`, idempotentní (ECLI klíč).
- **Monitoring kvality citací** — log analytics podle widget_id zda model judikáty cituje, nebo ne. Pokud po Phase 4 stále miss-rate >50 %, rozšířit prompt nebo zúžit relevance threshold.
