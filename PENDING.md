# Pending — ChatBot Platform

> Overwritten by every /finish. Authoritative immediate-action list for next /start.

*Last updated: 2026-05-06 (D-10 court hallucination fix deployed rev 00054-j68, 0 P1)*

## P0 — Blockers
*(none)*

## P1 — Active Priorities
*(none)*

## P2 — Backlog (next 2–3 sessions)
- **Verify šum chunk OSTA post-D-10** — `ECLI_CZ_OSTA_2023_9.C.218.2021.1` se opakovaně objevoval jako web_page kandidát před D-10. Layer 1 fix nyní propaguje `metadata.soud` z parent doc do chunků; pokud OSTA má korektní metadata, header je správný a halucinace nehrozí. Akce: smoke testovat 5 dotazů typu "soud v Táboře" + ověřit, zda OSTA chunk vrací správnou hlavičku. Pokud ne, debug parent doc metadata. — delegate: `chatbot-dev`
- **Phase 5: ECLI/JC exact-match boost** v `chat/retrieval.py` — RetrievalService už má BM25 + vector RRF, ale RRF (k=60) utlumí přesné citace ECLI/jednacího čísla. Doplnit special handler před RRF: pokud query obsahuje `ECLI:CZ:...` nebo `<číslo> Cdo <číslo>/<rok>`, force-include ten chunk do top_k. — delegate: `chatbot-dev`
- **Pravidelný re-ingest justice.cz + abstrakty** — cron / Cloud Scheduler týdně volá:
  1. `scripts/ingest_judikaty.py --years <current>`
  2. `scripts/generate_judikat_abstracts.py`
  Oba idempotentní (ECLI klíč / `is_abstract` flag). — delegate: `chatbot-dev` (skript) + CEO (Cloud Scheduler setup)
- **Monitoring kvality citací** — log analytics podle widget_id zda model judikáty cituje. Po Phase 4 by miss-rate měl klesnout — ověřit z produkčních logů po 1-2 týdnech provozu. — delegate: `chatbot-dev` nebo CEO direct
