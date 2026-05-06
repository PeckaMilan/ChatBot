# DECISIONS — ChatBot Platform

> Strategic memory for the ChatBot Platform project. Read this at every session start.

## Anti-Patterns

> Things tried and failed. Don't repeat without explicit justification.

- **AP-01** — Filtrovat soudní rozhodnutí pouze přes civilní paragrafy občanského zákoníku § 2894–2971. Chytá veškerou tort liability (nájemní spory, smluvní pokuty, porodní komplikace), false-positive rate >70 %. Civilní paragrafy stačí jen jako booster v kombinaci s keyword/subject signálem. — added 2026-05-04
- **AP-02** — "Bolestné" / "ztížení společenského uplatnění" / "ztráta na výdělku" jako standalone keyword filtr pro "dopravní nehody". Tyto termíny se používají u všech zranění (pracovní úrazy, medical malpractice, asault), nediskriminují dopravu. — added 2026-05-04
- **AP-03** — `predmetRizeni` / `klicovaSlova` obsahuje "vozidla" / "vozidel" jako traffic signal. Chytá vlastnické / registrační spory ("určení vlastnictví silničního vozidla", "vyřazení z provozu"), nejsou to dopravní nehody. — added 2026-05-04
- **AP-04** — Iterativně tweakovat regex/keyword filtr 4× za sebou bez kroku zpět. Lépe je hned po 2-3 false-positive iteracích nasadit LLM-classifier (Gemini Flash) jako post-filter — deterministicky přesný, ~1 sec/dokument, eliminuje šum který regex nedokáže rozlišit. — added 2026-05-04
- **AP-05** — `gcloud run deploy` bez explicitního `--project`. Defaultní gcloud config byl nastaven na `phoenix-staging-ea`, deploy si tiše vytvořil novou Cloud Run instanci v cizím projektu, produkce nebyla aktualizována. **Vždy passuj `--project chatbot-platform-2026` explicitně.** — added 2026-05-05
- **AP-06** — `command 2>&1 | tail -25` v background bash bez `tee`. Tail nepíše do souboru průběžně, log je 0 bytů dokud command neskončí. Pro background úlohy s long output použij `... 2>&1 | tee /tmp/file.log | tail -25`. — added 2026-05-05

## Hard Rules

> Never violate.

- **HR-01** — Při deployi do Cloud Run vždy explicitně specifikovat `--project chatbot-platform-2026`. Nesmí dojít k deployi do jiného GCP projektu. (Důvod: AP-05.)
- **HR-02** — Před commitem vždy ověřit `git status` a stagovat POUZE soubory změněné touto session — nikdy ne `git add .` (codebase obsahuje rozpracovaný echo feature od jiné session).
- **HR-03** — `rozhodnuti.justice.cz/opendata/` API je veřejné, public domain, žádné API klíče. Při dalším využití zachovat max 5 paralelních requestů a respektovat 429 retry logiku.

## Key Decisions

> With status: PERMANENT / ACTIVE / REVOKED

- **D-01** — Zdroj judikátů pro RAG: `rozhodnuti.justice.cz/opendata/` (REST JSON API, ~600k rozhodnutí 2020-2026, okresní/krajské/vrchní soudy, public domain). NSoud / NALUS / Judikaty.info odloženy jako sekundární. **Status: PERMANENT** (2026-05-04)
- **D-02** — Filter strategie pro výběr "dopravních" judikátů: dvouvrstvá pipeline. (1) Tight regex pre-filter z metadat: criminal statutes § 143/147/148/274 z. č. 40/2009 Sb. + keywords v `klicovaSlova`/`predmetRizeni`. (2) LLM classifier (Gemini Flash 2.0) post-filter na metadata + verdict, vrací ANO/NE/NEJISTE. ANO i NEJISTE keep, NE skip. **Status: ACTIVE** (2026-05-04)
- **D-03** — Judikáty se ukládají jako standardní `documents` (category="judikat") asociované s widget `ls0Si9wuw2gbatGla3nW` (customer `R2e1hKaEcmQ2GIhThSQU`). Idempotency klíč = sanitized ECLI. Žádné nové Firestore kolekce. **Status: PERMANENT** (2026-05-04)
- **D-04** — System prompt widgetu nepřepsat, ale rozšířit. Existující prompt obsahuje doménovou expertízu (lovci nehod, ČKP/ČSSZ, metodika NS, kontakt 703 111 333) — nesmí se ztratit. Nový blok PRACE S JUDIKATUROU se appenduje na konec. **Status: PERMANENT** (2026-05-05)
- **D-05** — `top_k` pro RAG retrieval zvýšen z 5 na 10 (pro `chat/service.py` i `chat/router.py` streaming). Větší pool kandidátů zlepšuje šanci, že se nějaký judikát dostane do kontextu i u laických dotazů. **Status: ACTIVE** (2026-05-05)
- **D-06** — `max_output_tokens` v Gemini chatu zvýšen z 2048 na 4096 (oba volání: blocking + stream). Důvod: odpovědi byly oříznuté uprostřed (např. v telefonním čísle "+420"). **Status: ACTIVE** (2026-05-05)
- **D-07** — Phase 4 abstrakty: pro každý judikát vygenerován 1 lay-friendly abstract (Gemini 2.0 Flash, ~200 slov, 3 pilíře: co se stalo / kolik soud přiznal / klíčový důvod, BEZ právní hantýrky, ECLI/JC citace na konci). Uložen jako další chunk v `documents/{doc_id}/chunks/` s `metadata.is_abstract=True` a `chunk_index=9000`. Embedding identický model jako rozsudkové chunks (Vertex AI 768-dim). Retrieval (`get_all_chunks` → cosine + BM25 RRF) automaticky abstract zahrne. Idempotence: chunk-level check `is_abstract==True`. **Status: ACTIVE** (2026-05-05)
- **D-08** — Phase 4 storage strategie: NEUPDATOVAT `document.chunk_count` po přidání abstract chunku. Důvod: chunk_count byl historicky text-rozsudek count; míchání s abstract by ztěžovalo debugging. Abstract chunk má `chunk_index=9000` jako sentinel hodnotu, aby nekolidoval s 0..N-1 text-chunks. **Status: PERMANENT** (2026-05-05)
- **D-09** — Phase 4 empiricky validována přes `scripts/eval_phase4_retrieval.py` (8 typických laických dotazů, top_k=10, retrieval přes BM25+vector RRF). Výsledky: 8/8 dotazů má abstract chunk v top-3, 0/8 raw judikát-text v top-10. Tj. **bez abstraktů by se judikáty do kontextu vůbec nedostaly** pro laické dotazy. avg RRF score abstract 0.0242 vs web 0.0236 — abstract chunky soutěží s web pages a vyhrávají. Phase 4 = success. **Status: PERMANENT** (2026-05-05)
- **D-10** — Halucinace názvu soudu v RAG odpovědích (2026-05-06, bug). Root cause: (1) `build_context()` posílal Gemini pouze `[Source N]` header bez metadat — LLM hádat název soudu z ECLI prefixu (OSSO→"Ostrava" místo Sokolov). (2) `ingest_judikaty.py` ukládal chunk-level `metadata: {}` prázdné — metadata (soud, ecli, jednaci_cislo) jsou pouze na parent dokumentu, ne v chunk sub-collection. Fix (dvě vrstvy): (a) `firestore.py get_all_chunks()` — propaguje parent doc metadata do každého chunk dict přes `_merge_metadata()`. (b) `retrieval.py build_context()` — nový `_build_source_header()` generuje `[Source N — <soud>, sp. zn. <jednaci_cislo>, <ecli>]` pro judikát chunks (soud+jednaci_cislo non-empty), fallback na `[Source N]` pro web/PDF a chunky s chybějícími metadaty. (c) Widget system prompt doplněn o NAZEV SOUDU klauzuli — zakázat inference soudu z ECLI kódu. Commit: `76a8d99`. 8/8 unit testů v `tests/unit/test_retrieval_build_context.py`. **Status: PERMANENT** (2026-05-06)

## Current State

**Architektura:** FastAPI + Gemini 2.0/3.0 + Firestore (DB + vectors) + GCS, Cloud Run `chatbot-api-182382115587.europe-west1.run.app` (project `chatbot-platform-2026`, region europe-west1).

**Jediný produkční bot:** widget ID `ls0Si9wuw2gbatGla3nW` ("Virtuální poradce po nehodě"), customer `R2e1hKaEcmQ2GIhThSQU`, embed na `https://www.ponehodovapece.cz/`. Model `gemini-3-flash-preview`.

**RAG knowledge base widgetu (k 2026-05-05 evening):**
- 8 původních dokumentů (web pages — pozůstalostní důchody, etc.)
- 325 soudních judikátů (2021-2026, dopravní nehody / újma na zdraví / bolestné) — pozn. 3 nové od ranního ingestu (322 + 3 admin)
- Každý judikát má **1 lay-friendly abstract chunk** (`is_abstract=True`, `chunk_index=9000`) navíc k text-rozsudkovým chunks
- Total `widget.document_ids`: 333 (8 + 325)
- Total chunks v RAG: ~origin chunks + 325 abstract chunks (každý dotaz teď má dual signál: laický abstract + formální rozsudek)

**Production revision:** `chatbot-api-00054-j68` (2026-05-06) s D-10 fix (build_context metadata header + system prompt NAZEV SOUDU klauzule). Předtím `chatbot-api-00052-rsv` (2026-05-05) s top_k=10 + max_output_tokens=4096.

**Slabina ze 2026-05-05 ranní (vector score ~0.029 pro laické dotazy):** VYŘEŠENA Phase 4 a EMPIRICKY POTVRZENO 2026-05-05 evening (D-09). Abstract chunky vyhrávají vs web pages v RRF retrievalu, pokrytí judikátů v top-3 = 100 % (8/8 dotazů). Bez Phase 4 by se text-rozsudkové chunky do top-10 nedostaly vůbec.

## Next Steps

- [x] ~~**Halucinace názvu soudu — D-10 fix**~~ — DONE 2026-05-06, commit `76a8d99` + `ad1f11f`, deployed rev `chatbot-api-00054-j68`. 3/3 produkčních smoke testů pass, žádná halucinace soudu. Viz D-10 pro full root cause + fix summary.
- [x] ~~**Změřit přínos Phase 4** (P1)~~ — DONE 2026-05-05, viz D-09. Eval skript `scripts/eval_phase4_retrieval.py` zachován pro re-runs.
- [x] ~~**Cleanup orphan staging instance**~~ — DONE 2026-05-05 evening, Board OK obdržen, `gcloud run services delete chatbot-api --project phoenix-staging-ea` úspěšný. Produkce v `chatbot-platform-2026` (rev 00052-rsv) ověřena nedotčená.
- [ ] **Sledovat šum chunk** (P3): `ECLI_CZ_OSTA_2023_9.C.218.2021.1` se opakuje jako web_page kandidát napříč různými laickými dotazy v eval. Layer 1 fix (D-10) nyní propaguje metadata z parent doc do chunku — pokud OSTA má správný název soudu v metadata.soud, header bude korektní a LLM halucinaci neuvidí. Ověřit v prod smoke testech post-D-10 deployi. Pokud stále šum, zvážit re-chunking nebo blacklist.
- [ ] **Phase 5 — Hybrid search refinement** (P3): RetrievalService už BM25 + vector RRF má (`src/features/chat/retrieval.py`). Otázka, zda doplnit ECLI/JC exact-match boost (BM25 sice citaci najde, ale RRF k=60 ji utlumí). Vyžadovalo by speciální handler před RRF.
- [ ] **Pravidelný re-ingest** (P3): Justice.cz publikuje nová rozhodnutí denně. Cron / Cloud Scheduler týdně volá `scripts/ingest_judikaty.py --years <current>` + `scripts/generate_judikat_abstracts.py`. Oba skripty idempotentní.
- [ ] **Echo feature refactor** (P3, mimo tuto session): rozpracované soubory `src/features/echo/`, `tests/test_echo_*.py`, `static/echo/` patří do jiné rozdělané práce, ne tato session — neřešit zde.
