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

## Current State

**Architektura:** FastAPI + Gemini 2.0/3.0 + Firestore (DB + vectors) + GCS, Cloud Run `chatbot-api-182382115587.europe-west1.run.app` (project `chatbot-platform-2026`, region europe-west1).

**Jediný produkční bot:** widget ID `ls0Si9wuw2gbatGla3nW` ("Virtuální poradce po nehodě"), customer `R2e1hKaEcmQ2GIhThSQU`, embed na `https://www.ponehodovapece.cz/`. Model `gemini-3-flash-preview`.

**RAG knowledge base widgetu (k 2026-05-05):**
- 8 původních dokumentů (web pages — pozůstalostní důchody, etc.)
- 322 nově nasazených soudních judikátů (2021-2026, dopravní nehody / újma na zdraví / bolestné)
- Total `widget.document_ids`: 333

**Production revision:** `chatbot-api-00052-rsv` (2026-05-05) s top_k=10 + max_output_tokens=4096.

**Známá slabina:** Vector retrieval má slabou sémantickou shodu mezi laickými dotazy (např. "kolik dostanu na bolestném") a formálním textem rozsudků (score ~0.029). Model dle promptu correctly necituje judikát když si není jistý relevancí, ale tím se ztrácí benchmark hodnota.

## Next Steps

- [ ] **Phase 4 — LLM-generated abstrakty pro judikáty** (P1): Pro každý ze 322 judikátů vygenerovat 1-2 odstavcový lay-friendly abstrakt ("co se stalo, kolik soud přiznal, klíčový důvod") přes Gemini Flash, re-embed a uložit jako alternativní/dodatečný chunk. Cíl: zlepšit retrieval shodu pro laické dotazy. Delegate: `coder`.
- [ ] **Cleanup orphan staging instance** (P2): Cloud Run service `chatbot-api` v projektu `phoenix-staging-ea` (URL `chatbot-api-383499804038.europe-west1.run.app`) byla omylem vytvořena při AP-05. Smazat: `gcloud run services delete chatbot-api --region europe-west1 --project phoenix-staging-ea`.
- [ ] **Phase 5 — Hybrid search** (P3): Doplnit BM25 keyword search do retrievalu (zejména na ECLI / jednací číslo), kombinovat s vector. Vyžaduje úpravu `chat/retrieval.py`.
- [ ] **Pravidelný re-ingest** (P3): Justice.cz publikuje nová rozhodnutí denně. Zvážit cron / scheduled job, který doplňuje nové judikáty týdně. Skript je idempotentní (ECLI klíč).
- [ ] **Echo feature refactor** (P3, mimo tuto session): rozpracované soubory `src/features/echo/`, `tests/test_echo_*.py`, `static/echo/` patří do jiné rozdělané práce, ne tato session — neřešit zde.
