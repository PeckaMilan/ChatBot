# Technical Plan

## Status: IN PROGRESS 🚧

> This plan is created AFTER business requirements are approved.
> See BUSINESS.md for business context.

---

## Current Iteration: 🛴 Koloběžka (MVP)

**Goal:** Fungující chatbot pro vlastní web s upload dokumentů a RAG

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Cloud Run Service                        │
│  ┌───────────────┐  ┌─────────────────┐  ┌──────────────┐  │
│  │  Admin Panel  │  │    Chat API     │  │ Widget API   │  │
│  │  /admin/*     │  │  /api/chat/*    │  │ /api/widget  │  │
│  └───────┬───────┘  └────────┬────────┘  └──────┬───────┘  │
│          │                   │                   │          │
│          └───────────┬───────┴───────────────────┘          │
│                      ▼                                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Shared Services Layer                   │    │
│  │  • Document Processor (PDF, DOCX, TXT)              │    │
│  │  • Embedding Generator (Gemini)                      │    │
│  │  • RAG Pipeline (retrieval + generation)            │    │
│  │  • Conversation Memory                               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
   ┌──────────┐        ┌───────────┐        ┌───────────┐
   │Firestore │        │  Storage  │        │ Gemini API│
   │(DB+Vec)  │        │  (Docs)   │        │  (LLM)    │
   └──────────┘        └───────────┘        └───────────┘
```

### Architecture Decision Records

| ADR | Decision | Rationale |
|-----|----------|-----------|
| ADR-001 | Firestore + in-memory vectors | Zero infra, MVP fast, migrate to Vertex AI later |
| ADR-002 | Python + FastAPI | Best AI/ML ecosystem, mature Gemini SDK |
| ADR-003 | Single Cloud Run service | Simpler deployment, shared resources |

---

## Tech Stack

| Component | Technology | Version |
|-----------|------------|---------|
| **Runtime** | Python | 3.12 |
| **Framework** | FastAPI | 0.109+ |
| **LLM** | Google Gemini | gemini-2.0-flash |
| **Embeddings** | Gemini text-embedding-004 | 768 dim |
| **Database** | Firestore | - |
| **Storage** | Cloud Storage | - |
| **Auth** | Firebase Auth | - |
| **Hosting** | Cloud Run | 2GB/2CPU |
| **Doc Processing** | PyMuPDF, python-docx | - |

---

## Project Structure

```
chatbot-platform/
├── src/
│   ├── main.py                   # FastAPI entrypoint
│   ├── config.py                 # Environment configuration
│   ├── core/                     # Shared clients
│   │   ├── firebase.py
│   │   ├── firestore.py
│   │   ├── storage.py
│   │   └── gemini.py
│   ├── features/
│   │   ├── auth/                 # Firebase Auth
│   │   ├── documents/            # Upload, processing, embeddings
│   │   ├── chat/                 # RAG pipeline, memory
│   │   ├── widget/               # Embeddable widget config
│   │   └── admin/                # Admin panel API
│   └── utils/
│       ├── language.py           # Auto-detection
│       └── validation.py
├── static/
│   └── widget/
│       ├── chatbot-widget.js     # Embeddable script
│       └── chatbot-widget.css
├── tests/
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Data Models (Firestore)

```
documents/{doc_id}
├── user_id: string
├── filename: string
├── content_type: string
├── storage_path: string
├── status: "pending" | "processing" | "ready" | "failed"
├── chunk_count: number
├── created_at: timestamp
└── chunks/{chunk_id}
    ├── text: string
    ├── embedding: array[768]
    ├── page_number: number
    └── chunk_index: number

conversations/{conv_id}
├── session_id: string
├── document_ids: array
├── created_at: timestamp
└── messages/{msg_id}
    ├── role: "user" | "assistant"
    ├── content: string
    ├── sources: array
    └── created_at: timestamp

settings/{user_id}
├── chatbot_name: string
├── welcome_message: string
├── system_prompt: string
└── widget_color: string
```

---

## Tasks - Koloběžka (MVP)

### Phase 1: Project Setup (Foundation) ✅
- [x] **T1.1** Inicializace Python projektu (pyproject.toml, requirements.txt)
- [x] **T1.2** Struktura složek dle návrhu
- [ ] **T1.3** GCP projekt setup (Firestore, Storage, enable APIs) *[user action]*
- [ ] **T1.4** Firebase Auth konfigurace *[user action]*
- [x] **T1.5** Environment variables (.env.example, config.py)
- [x] **T1.6** FastAPI základní setup (main.py, health endpoint)
- [x] **T1.7** Dockerfile + local docker-compose

### Phase 2: Core Clients ✅
- [x] **T2.1** Firestore client wrapper
- [x] **T2.2** Cloud Storage client wrapper
- [x] **T2.3** Gemini API client (chat + embeddings)
- [ ] **T2.4** Firebase Auth middleware *[later - MVP can work without]*

### Phase 3: Document Processing
- [ ] **T3.1** Document upload endpoint (multipart/form-data)
- [ ] **T3.2** PDF text extraction (PyMuPDF)
- [ ] **T3.3** DOCX text extraction (python-docx)
- [ ] **T3.4** TXT handling
- [ ] **T3.5** Text chunking (RecursiveCharacterTextSplitter)
- [ ] **T3.6** Embedding generation (batch)
- [ ] **T3.7** Store chunks + embeddings in Firestore
- [ ] **T3.8** Document status tracking

### Phase 4: RAG Pipeline
- [ ] **T4.1** Vector similarity search (cosine, in-memory)
- [ ] **T4.2** Retrieval service (top-k chunks)
- [ ] **T4.3** Prompt construction (system + context + query)
- [ ] **T4.4** Gemini chat completion
- [ ] **T4.5** Language auto-detection (langdetect)
- [ ] **T4.6** Response formatting

### Phase 5: Conversation Memory
- [ ] **T5.1** Session ID generation
- [ ] **T5.2** Conversation CRUD (Firestore)
- [ ] **T5.3** Message history retrieval (last N messages)
- [ ] **T5.4** Context window management

### Phase 6: Chat API
- [ ] **T6.1** POST /api/chat endpoint
- [ ] **T6.2** POST /api/widget/{widget_id}/chat endpoint
- [ ] **T6.3** GET /api/conversations/{id} endpoint
- [ ] **T6.4** CORS configuration for widget

### Phase 7: Embeddable Widget
- [ ] **T7.1** Widget JavaScript (vanilla JS, IIFE)
- [ ] **T7.2** Widget CSS (scoped, bubble UI)
- [ ] **T7.3** Widget config endpoint
- [ ] **T7.4** Session persistence (localStorage)
- [ ] **T7.5** Static file serving

### Phase 8: Admin Panel
- [ ] **T8.1** Document list endpoint
- [ ] **T8.2** Document delete endpoint
- [ ] **T8.3** Settings CRUD endpoints
- [ ] **T8.4** Basic HTML admin UI (nebo Jinja2 templates)

### Phase 9: Deployment
- [ ] **T9.1** Cloud Run deployment (gcloud run deploy)
- [ ] **T9.2** Environment secrets (Secret Manager)
- [ ] **T9.3** Custom domain (optional)
- [ ] **T9.4** GitHub Actions CI/CD

### Phase 10: Testing & Polish
- [ ] **T10.1** Unit tests (document processor, embeddings)
- [ ] **T10.2** Integration tests (chat API)
- [ ] **T10.3** Manual E2E test na vlastním webu
- [ ] **T10.4** Error handling + logging

---

## API Contracts

### POST /api/chat
```json
// Request
{
  "message": "Jak funguje produkt X?",
  "session_id": "abc123",
  "document_ids": ["doc1", "doc2"]
}

// Response
{
  "message": "Produkt X funguje tak, že...",
  "sources": [{"chunk_id": "c1", "text": "...", "score": 0.92}],
  "session_id": "abc123",
  "language": "cs"
}
```

### POST /api/documents
```
Content-Type: multipart/form-data
file: <binary>
```

### GET /api/documents
```json
{
  "documents": [
    {"id": "doc1", "filename": "manual.pdf", "status": "ready", "chunks": 42}
  ]
}
```

---

## Cost Estimate (MVP)

| Service | Monthly (low traffic) |
|---------|-----------------------|
| Cloud Run | ~$5-20 |
| Firestore | ~$3-5 |
| Cloud Storage | ~$1 |
| Gemini API | ~$1-5 |
| **Total** | **~$10-30** |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Gemini rate limits | High | Implement retry + exponential backoff |
| Large PDF processing | Medium | Async processing, max file size limit |
| Cold start latency | Medium | Min instances = 1 for production |
| Vector search slow at scale | Medium | Migration path to Vertex AI Vector Search |

---

## Success Criteria (MVP Done When)

- [ ] Upload PDF → zpracuje → odpovídá na dotazy
- [ ] Widget embed script funguje na testovacím webu
- [ ] Konverzace si pamatuje kontext
- [ ] Admin panel umožňuje správu dokumentů
- [ ] Deployed na Cloud Run

---

## Sign-off

- [x] Human approved (2026-02-03)
- [x] Ready for development (/start)
