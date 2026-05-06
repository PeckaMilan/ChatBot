# Pending — ChatBot Platform

> Overwritten by every /finish. Authoritative immediate-action list for next /start.

*Last updated: 2026-05-06 (D-11 multi-layer defense deployed rev 00058-lhz, 5/5 smoke PASS)*

## P0 — Blockers
*(none)*

## P1 — Active Priorities
- **Phase 5: ECLI/JC exact-match boost** — planner design hotov, prerekvizita (D-11(c) metadata propagation) splněna. Implementace per plán: prepend-bypass strategie v `retrieval.py:search()`, 10 unit + 1 integration test (TDD RED-first), +~45 řádků v `retrieval.py`, nový `tests/unit/test_retrieval_exact_match_boost.py` (~200 řádků). Žádný API change. Plán k dispozici v session transcript (planner output) — pro pohodlí zopakovat: detection regex (ECLI + JC C/Co/Cdo/T/Tdo/As/Afs/ÚS), partial-bez-roku ignore, force-include abstract+raw oba pokud sdílí ECLI. — delegate: `chatbot-dev`

## P2 — Backlog (next 2–3 sessions)
- **Frontend update pro `replace_message` SSE event** — D-11(b) guard ve streaming endpointu emituje `replace_message` event po EOS pokud `was_sanitized=True`. Frontend (`static/widget/chatbot-widget.js`) tento event zatím neumí — pokud guard zasáhne během streamingu, uživatel uvidí původní halucinaci v chatu. Update widget JS aby zpracoval `replace_message` payload a override displayed text. — delegate: `fullstack-dev` nebo `frontend-designer`
- **Monitoring "Response sanitized" warningů** — log analytics: kolik guard sanitizací za týden? Pokud >5/týden, znamená to že LLM hodně fabrikuje (anti-fab klauzule v promptu nestačí) — zvážit prompt rewrite nebo post-guard alerting. — delegate: `chatbot-dev` nebo CEO direct
- **Pravidelný re-ingest justice.cz + abstrakty** — cron / Cloud Scheduler týdně volá `scripts/ingest_judikaty.py --years <current>` + `scripts/generate_judikat_abstracts.py`. Oba idempotentní. — delegate: `chatbot-dev` (skript) + CEO (Cloud Scheduler setup)
- **Monitoring kvality citací** — log analytics podle widget_id zda model judikáty cituje. Po Phase 4+5 by miss-rate měl klesnout. Ověřit z produkčních logů po 1-2 týdnech provozu. — delegate: `chatbot-dev` nebo CEO direct
