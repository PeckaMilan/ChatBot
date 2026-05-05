# Infinity Log — ChatBot Platform

> Append-only chronological record of all sessions and significant events.

## 2026-05-04

### ChatBot — Judikáty pipeline: API ingestion + filter + LLM classifier
- Prozkoumán produkční widget `ls0Si9wuw2gbatGla3nW` na `ponehodovapece.cz` (FastAPI + Gemini + Firestore + GCS, Cloud Run).
- Identifikován zdroj judikátů: `rozhodnuti.justice.cz/opendata/` REST API (D-01) — ~600k rozhodnutí 2020-2026, public domain.
- Vytvořen `scripts/ingest_judikaty.py` — async httpx ingestor s tight regex pre-filter (criminal § 143/147/148/274 + keyword/subject) + LLM classifier post-filter (Gemini Flash 2.0 ANO/NE/NEJISTE) (D-02).
- 4 iterace zužování filtru. Anti-patterny: civilní paragrafy § 2894-2971 chytaly tort liability obecně (AP-01), "bolestné"/"ztížení společenského uplatnění" chytalo všechna zranění (AP-02), "vozidla" v subject hits chytalo vlastnické spory (AP-03). Iterativní tweakování bez kroku zpět = AP-04.

## 2026-05-05

### ChatBot — Production deploy + e2e + retrieval tuning
- Reálný ingest 2021-2026 dokončen: 135 225 processed → 516 regex match → 327 LLM ANO → **322 judikátů uloženo do Firestore** (category="judikat", customer `R2e1hKaEcmQ2GIhThSQU`). 0 errors, ~21 min wall time, 1.59s/dokument.
- System prompt widgetu rozšířen o blok "PRACE S JUDIKATUROU" (D-04) bez ztráty existující doménové expertízy (lovci nehod, ČKP/ČSSZ, kontakt 703 111 333).
- Retrieval tuning: `top_k` 5 → 10 (D-05), `max_output_tokens` 2048 → 4096 (D-06, fix pro oříznuté odpovědi).
- **Incident AP-05**: deploy proběhl nejprve do projektu `phoenix-staging-ea` místo `chatbot-platform-2026` kvůli defaultnímu gcloud config. Re-deploy do správného projektu úspěšný (rev 00052-rsv). Orphan staging instance zůstala — task v PENDING.
- AP-06: background bash s `| tail -25` bez `tee` → log 0 bytů během běhu, nelze monitorovat průběh.
- Známá slabina (Phase 4 candidate): retrieval score ~0.029, laický dotaz neladí sémanticky s formálním rozsudkem. Model dle promptu correctly necituje, ale ztrácí benchmark hodnotu.

```json
{
  "eval_block": true,
  "date": "2026-05-05",
  "project": "ChatBot",
  "session_id": "ea45897",
  "pass_k": null,
  "board_escalations": 0,
  "anti_patterns_repeated": 0,
  "avg_context_needed": null,
  "stale_antipatterns_flagged": 0,
  "reflexion_triggers": 0,
  "notes": "First DECISIONS.md/INFINITY_LOG.md/PENDING.md for this project. Filter-tuning iteration loop (3 false-positive cycles) caught and broken via pivot to LLM classifier (AP-04 lesson)."
}
```
