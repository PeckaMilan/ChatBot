# Business Requirements

## Status: APPROVED ✅

> This document is created collaboratively by Human + Claude + Gemini

---

## Vision
*What are we building and why?*

Vlastní ChatBase alternativa - chatbot platforma běžící na GCP, kterou lze:
- Embedovat jako widget na vlastní weby
- Prodávat jako SaaS produkt (měsíční předplatné)

## Problem Statement
*What problem does this solve?*

- ChatBase a podobné služby jsou drahé a závislé na třetí straně
- Potřeba vlastní kontroly nad daty a customizací
- Možnost monetizace vlastního řešení

## Target Users
*Who is this for?*

1. **Vlastní použití** - embed na vlastní weby
2. **B2B zákazníci** - firmy chtějící chatbota na svůj web bez technických znalostí

## Success Criteria
*How do we know it works?*

- [ ] Chatbot odpovídá relevantně na základě nahraných dokumentů
- [ ] Widget funguje na libovolném webu (embed script)
- [ ] Admin panel umožňuje správu dokumentů a nastavení
- [ ] Odpovědi v jazyce dotazu (auto-detection)

## Constraints
*Budget, time, technology limitations?*

- **Platform:** Google Cloud Platform (GCP)
- **LLM:** Google Gemini API
- **Architektura:** Single-tenant start, multi-tenant ready (project_id)

## Out of Scope
*What are we explicitly NOT doing?*

- Billing/subscription management (fáze Kolo+)
- Vlastní LLM training
- Voice/audio chatbot
- Mobile app

---

## Technical Decisions

| Rozhodnutí | Volba |
|------------|-------|
| LLM Backend | Google Gemini |
| Hosting | GCP Cloud Run |
| Databáze | Firestore (nebo PostgreSQL) |
| Vector Store | Vertex AI Vector Search / Pinecone |
| Auth | Firebase Auth |
| Storage | Cloud Storage (dokumenty) |

---

## Iterations (Agile Roadmap)

### 🛴 Koloběžka (MVP)
*Minimum viable - fungující chatbot pro vlastní web*

- [ ] Upload dokumentů (PDF, DOCX, TXT)
- [ ] Zpracování dokumentů → vector embeddings
- [ ] Chat API endpoint (Gemini + RAG)
- [ ] Embeddable widget (bublina vpravo dole)
- [ ] Konverzační paměť (kontext v rámci session)
- [ ] Základní admin panel (upload, nastavení)
- [ ] Auto-detekce jazyka odpovědi

### 🚲 Kolo
*Lepší UX, více zdrojů*

- [ ] Web scraping jako zdroj znalostí
- [ ] Manuální FAQ editor
- [ ] Historie konverzací + analytics dashboard
- [ ] Customizace vzhledu widgetu
- [ ] Multi-projekt podpora (více chatbotů)

### 🏍️ Motorka
*Production ready*

- [ ] Multi-tenant architektura (subdomény)
- [ ] Rate limiting a abuse protection
- [ ] Caching pro rychlejší odpovědi
- [ ] Webhook integrace

### 🚗 Auto
*SaaS produkt*

- [ ] Billing integration (Stripe)
- [ ] Pricing tiers
- [ ] Onboarding flow pro zákazníky
- [ ] Self-service registration

### ✈️ Letadlo
*Scale*

- [ ] White-label řešení
- [ ] API pro třetí strany
- [ ] Enterprise features (SSO, audit log)

---

## Sign-off

- [x] Human approved (2026-02-03)
- [x] Ready for technical planning
