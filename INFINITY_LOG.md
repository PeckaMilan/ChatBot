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

### ChatBot — Orphan staging cleanup (evening session)
- Smazána Cloud Run service `chatbot-api` v projektu `phoenix-staging-ea` (vznikla při AP-05). `gcloud run services delete chatbot-api --region europe-west1 --project phoenix-staging-ea --quiet` → "Deleted service [chatbot-api]".
- Produkce v `chatbot-platform-2026` ověřena: `chatbot-api-00052-rsv` stále aktivní na `chatbot-api-rxun7gaboa-ew.a.run.app`. Žádný impact.
- AP-05 fully resolved. HR-01 (`--project chatbot-platform-2026` při deploy) zůstává aktivní jako prevence.

```json
{
  "eval_block": true,
  "date": "2026-05-06",
  "project": "ChatBot",
  "session_id": "phase4-eval+cleanup",
  "pass_k": null,
  "board_escalations": 1,
  "anti_patterns_repeated": 0,
  "avg_context_needed": null,
  "stale_antipatterns_flagged": 0,
  "reflexion_triggers": 0,
  "notes": "Phase 4 empirically validated (D-09: 100% top-3 abstract coverage on 8 lay queries). Orphan staging service deleted with Board approval. PENDING.md cleared to 0 P1 — only P2 backlog remains. AP-01..AP-06 all <90d old, no decay flagging."
}
```

### ChatBot — Phase 4 empirická validace (evening session)
- Delegováno na `chatbot-dev`: nový read-only eval skript `scripts/eval_phase4_retrieval.py`. Volá produkční `RetrievalService` (cosine + BM25 RRF) lokálně proti Firestore, vrací top-10 chunků pro 8 typických laických dotazů s `is_abstract` flagem.
- 8 dotazů × top_k=10 = 80 retrieved chunks. **66/80 (82.5 %) jsou abstract chunky.** **0/80 jsou raw judikát-text chunky.** Web pages doplňují zbytek.
- Coverage: 8/8 dotazů má aspoň 1 abstract v top-3 (100 %). 8/8 dotazů má aspoň 1 abstract v top-10. **0/8 dotazů má raw judikát-text v top-10.**
- avg RRF score: abstract 0.0242 vs web 0.0236 vs judikat_text 0.0 — abstrakty soutěží s web pages a vyhrávají. Bez Phase 4 by retrieval pro laické dotazy vůbec judikáty do kontextu nepřidal (jen text chunks rozsudku, které mají jiný stylistický registr než dotaz).
- Nález k sledování: `ECLI_CZ_OSTA_2023_9.C.218.2021.1` opakovaně jako web_page kandidát (suspicious — judikát label, ale chová se jako web page) — P2 task.
- D-09 zapsán: Phase 4 = success, empiricky potvrzeno.
- AP-04 compliance: žádná iterace retrieval logic — jen měření, žádný tweak.

```json
{
  "eval_block": true,
  "date": "2026-05-05",
  "project": "ChatBot",
  "session_id": "phase4-eval",
  "pass_k": null,
  "board_escalations": 0,
  "anti_patterns_repeated": 0,
  "avg_context_needed": null,
  "stale_antipatterns_flagged": 0,
  "reflexion_triggers": 0,
  "notes": "Phase 4 empirically validated: 100% top-3 abstract coverage for 8 lay queries, 0% raw judikat_text in top-10 (proves abstracts are the only path for judikat retrieval on lay queries). One suspicious chunk (OSTA_2023_9.C.218.2021.1) flagged for follow-up."
}
```

### ChatBot — Phase 4: Lay-friendly abstrakty pro 325 judikátů (afternoon session)
- Delegováno na `chatbot-dev`: nový skript `scripts/generate_judikat_abstracts.py` (Gemini 2.0 Flash, idempotentní, dry-run capable, statistiky).
- Pre-flight `--dry-run --max 3`: 3 abstracts vygenerované, 0 writes, kvalita potvrzená (česky, konkrétní částky, ECLI citace, žádná hantýrka).
- Full run (background, `tee` log): 325 judikátů zpracováno, 325 abstracts vygenerováno, **0 errors** (LLM/embed/write), avg 3.11s/doc, ~17 min wall time.
- Idempotence ověřena (re-run --max 10 → all 10 already_had_abstract=10, generated=0).
- Storage strategie (D-07/D-08): abstract jako další chunk v `documents/{doc_id}/chunks/`, `metadata.is_abstract=True`, `chunk_index=9000`. **NEUPDATUJE** `document.chunk_count`. Retrieval (`get_all_chunks` → cosine + BM25 RRF) abstrakty automaticky zahrne — žádná změna v `chat/retrieval.py` ani redeploy.
- Compliance s anti-patterns: AP-04 (write-first prompt design, žádná iterace) ✓, AP-06 (`tee` v background) ✓.
- **Nezměřeno empiricky.** Hypotéza, že abstracts zvedne retrieval shodu pro laické dotazy z ~0.029 na user-relevant level, je zatím neověřená. Next step: A/B test nebo ad-hoc dotazy proti produkčnímu widgetu.

```json
{
  "eval_block": true,
  "date": "2026-05-05",
  "project": "ChatBot",
  "session_id": "phase4-abstracts",
  "pass_k": null,
  "board_escalations": 0,
  "anti_patterns_repeated": 0,
  "avg_context_needed": null,
  "stale_antipatterns_flagged": 0,
  "reflexion_triggers": 0,
  "notes": "Phase 4 done autonomously: chatbot-dev delegation → dry-run validation → full run 325/325 0 errors → idempotency verified → KB updated. Empirical retrieval-improvement measurement still pending."
}
```

## 2026-05-06

### ChatBot — D-10 Court name hallucination fix
- Smoke test produkčního widgetu odhalil halucinaci: model tvrdil "Okresní soud v Ostravě" pro source z `ECLI_CZ_OSSO_2021_...` (= Sokolov). Root cause: `build_context()` posílal Gemini pouze chunk text + `[Source N]` header, žádné metadata; abstract chunky končí jen `[ECLI: ...]`; LLM neumí ECLI location codes (OSSO, OSTA, OSOS, OSPH) → tipoval city.
- CEO investigace identifikovala 2 vrstvy: (a) `firestore.get_all_chunks()` nepropaguje parent doc metadata do chunků; (b) `retrieval.build_context()` nemá metadata header.
- Delegováno `chatbot-dev`: TDD workflow (3+ unit testy first), dual-layer fix, deploy + 3 smoke testy. Výsledek: 8/8 unit testů zelených, deploy rev `chatbot-api-00054-j68` (project `chatbot-platform-2026`, HR-01 dodrženo), 3/3 produkčních smoke testů bez halucinace.
- Změny: `src/features/chat/retrieval.py` (`_build_source_header()` helper), Firestore client (metadata propagation z parent doc), widget `ls0Si9wuw2gbatGla3nW` system prompt (+289 znaků klauzule NAZEV SOUDU), `tests/unit/test_retrieval_build_context.py` (NEW).
- Compliance s anti-patterns: AP-04 (žádná regex/prompt iterace, root cause-first diagnostika), HR-01 (deploy s explicitním `--project chatbot-platform-2026`), HR-02 (jen explicit files, echo session netknutá).
- D-10 zapsán: PERMANENT.

```json
{
  "eval_block": true,
  "date": "2026-05-06",
  "project": "ChatBot",
  "session_id": "ad1f11f",
  "pass_k": null,
  "board_escalations": 0,
  "anti_patterns_repeated": 0,
  "avg_context_needed": null,
  "stale_antipatterns_flagged": 0,
  "reflexion_triggers": 0,
  "notes": "Court name hallucination fix delivered same-session: smoke detect → root cause → dual-layer fix (data + prompt) → TDD → deploy → smoke verify. PENDING P2 \"OSTA šum\" task downgraded to verify-post-D-10."
}
```
