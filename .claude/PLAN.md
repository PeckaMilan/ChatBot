# Technical Plan

## Status: DEPLOYED ✅

> Multi-tenant ChatBot SaaS Platform - ChatBase alternative
> Deployed at: https://chatbot-api-182382115587.europe-west1.run.app

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Cloud Run Service                            │
│  ┌───────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
│  │ Admin Portal  │  │ Customer Portal │  │   Widget Chat    │  │
│  │ /api/admin/*  │  │  /api/portal/*  │  │ /api/chat/widget │  │
│  └───────┬───────┘  └────────┬────────┘  └────────┬─────────┘  │
│          │                   │                     │            │
│          └───────────────────┼─────────────────────┘            │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Shared Services Layer                    │   │
│  │  • Document Processor (PDF, DOCX, TXT)                   │   │
│  │  • Web Scraper (single page, sitemap)                    │   │
│  │  • Embedding Generator (Gemini text-embedding-004)       │   │
│  │  • RAG Pipeline (retrieval + generation)                 │   │
│  │  • Conversation Memory                                    │   │
│  │  • Analytics Service                                      │   │
│  │  • Usage & Billing Service                               │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
   ┌──────────┐        ┌───────────┐        ┌───────────┐
   │Firestore │        │  Storage  │        │ Gemini API│
   │(DB+Vec)  │        │  (Docs)   │        │  (LLM)    │
   └──────────┘        └───────────┘        └───────────┘
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Runtime** | Python 3.12 |
| **Framework** | FastAPI |
| **LLM** | Gemini 2.0 Flash / Pro |
| **Embeddings** | text-embedding-004 (768 dim) |
| **Database** | Firestore |
| **Storage** | Cloud Storage |
| **Auth** | API Keys (SHA256 hashed) |
| **Hosting** | Cloud Run |

---

## Multi-Tenant Data Model

```
customers/{customer_id}
├── email, company_name
├── subscription_tier: free | starter | professional | enterprise
├── status: active | suspended
└── monthly limits (messages, documents, scrapes)

customers/{customer_id}/api_keys/{key_id}
├── name, key_hash (SHA256)
├── is_active, created_at

widgets/{widget_id}
├── customer_id
├── name, chatbot_name, welcome_message
├── system_prompt (guardrails)
├── model: gemini-2.0-flash-001 | gemini-2.0-pro-exp-02-05 | ...
├── widget_color, allowed_domains
├── document_ids[]
├── require_jwt, jwt_secret

documents/{doc_id}
├── customer_id
├── filename, storage_path
├── status: pending | processing | ready | failed
├── chunk_count
└── chunks subcollection

analytics_events/{event_id}
├── widget_id, conversation_id, session_id
├── role, message_preview, message_length
├── response_time_ms, language, timestamp

usage/{usage_id}
├── customer_id, widget_id, billing_period
├── usage_type: chat_message | document_upload | web_scrape
├── input_tokens, output_tokens, estimated_cost_usd
```

---

## API Endpoints

### Admin Portal (`/api/admin/*`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /stats | Platform-wide statistics |
| GET | /customers | List customers |
| POST | /customers | Create customer |
| GET | /customers/{id} | Customer details |
| PATCH | /customers/{id} | Update customer |
| POST | /customers/{id}/create-api-key | Create API key |

### Customer Portal (`/api/portal/*`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /dashboard | Dashboard overview |
| GET/POST | /widgets | Widget CRUD |
| GET | /widgets/{id}/embed-code | Get embed code |
| POST | /documents/upload | Upload document (async processing) |
| POST | /documents/upload-batch | Upload multiple documents (max 10) |
| GET | /documents/{id}/status | Check document processing status |
| POST | /documents/scrape | Scrape URL |
| GET | /conversations | List conversations |
| GET | /analytics/overview | All-time stats |
| GET | /analytics/daily-usage | Daily trends |
| GET | /analytics/widgets | Per-widget stats |
| GET | /analytics/top-questions | Popular questions |
| GET | /analytics/export | Export analytics as CSV |

### Chat API (`/api/chat/*`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | / | Direct chat (no widget) |
| POST | /widget/{widget_id} | Widget chat with RAG |
| POST | /widget/{widget_id}/stream | Streaming chat (SSE) |
| POST | /widget/{widget_id}/feedback | Submit feedback (thumbs up/down) |

---

## Customer Portal Features

### UI Design
- **Sidebar navigation** (260px, dark gradient) with SVG icons
- **CSS design system** with `--p-*` custom properties (indigo primary #4f46e5)
- **Toast notifications** replace all alert() calls (success/error/warning/info)
- **Modal animations** with backdrop blur and scale transitions
- **Skeleton loading** states with shimmer animation
- **Responsive** layout (sidebar collapses to hamburger on mobile <768px)

### Dashboard
- Messages used/remaining
- Widget count
- Document count
- Usage bar

### Analytics Tab
- All-time message count
- Monthly message count
- Total conversations
- Average response time
- Usage trend chart (30d/90d/360d/All)
- Widget performance comparison
- Top questions list

### Widgets Tab
- Create/edit/delete widgets
- Configure: name, color, welcome message
- Set guardrails (system prompt)
- Select AI model
- Assign documents

### Knowledge Base Tab
- Upload documents (PDF, DOCX, TXT, MD) - up to 20MB
- Batch upload (up to 10 files at once)
- **Widget selector dropdown** - auto-assign uploaded/scraped docs to a widget
- Async processing with progress indicator
- Scrape URLs (single page or sitemap)
- Document list with chunk count

### Widget Setup Tab
- Embed code generation
- JWT identity verification setup
- Allowed domains configuration

---

## Widget Features

### Streaming Responses
- Real-time text streaming via Server-Sent Events (SSE)
- Chunks appear as they are generated
- Fallback to regular mode if streaming fails

### User Feedback
- Thumbs up/down buttons after each assistant message
- Feedback stored in Firestore `feedback` collection
- Linked to session_id and message_id

### Dark Mode
- Toggle button in widget header
- CSS-only dark theme with `.cb-dark` class
- Auto-detection via `prefers-color-scheme: dark` (default: `'auto'`)
- Can be set explicitly via config: `darkMode: true` / `darkMode: false`

### Remote Config Priority
- Widget fetches config from `/api/chat/widget/{id}/config` on init
- Remote `welcome_message` **overrides** embed code (portal is source of truth)
- Remote `chatbot_name` and `widget_color` apply unless overridden in embed code
- Config is loaded **before** welcome message is displayed

### Branding
- "Powered by DWX" footer with link to https://www.dwx.cz
- Can be hidden per widget via `poweredBy: false` in embed config

### Configuration Options
```javascript
ChatbotWidget.init({
  widgetId: 'your-widget-id',
  apiUrl: 'https://chatbot-api-xxx.run.app',
  primaryColor: '#667eea',  // Gradient header color
  title: 'Chat',
  welcomeMessage: 'Hello!', // Overridden by portal config
  placeholder: 'Type a message...',
  streaming: true,      // Enable streaming (default: true)
  darkMode: 'auto',     // 'auto' | true | false
  autoOpen: false,      // Auto-open chat window
  poweredBy: true,      // Show "Powered by DWX" footer
  userToken: null,      // JWT for identity verification
});
```

### Enterprise Features

#### Rate Limiting
- Per-endpoint limits via slowapi (e.g., 30/min for chat, 10/min for uploads)
- Returns HTTP 429 with user-friendly message in widget

#### PII Detection & Redaction
- Detects emails, phone numbers, Czech birth numbers (rodne cislo), credit cards
- `pii_warning: true` flag in response triggers warning banner in widget
- Redaction available via `redact_pii()` utility

#### Citation Sources
- RAG responses include `sources[]` with title, score, snippet
- Widget renders color-coded source cards: green (>70%), amber (50-70%), red (<50%)
- Expandable snippets with similarity score badges

#### CORS
- Default: `*` (all origins) - required for embeddable widget
- Configurable via `CORS_ORIGINS` environment variable

---

## Subscription Tiers

| Tier | Messages/mo | Documents | Widgets | Scrapes |
|------|-------------|-----------|---------|---------|
| Free | 100 | 5 | 1 | 5 |
| Starter | 1,000 | 25 | 3 | 20 |
| Professional | 10,000 | 100 | 10 | 100 |
| Enterprise | Unlimited | 500 | 50 | 500 |

---

## Gemini Models

| Model | Use Case | Input $/1M | Output $/1M |
|-------|----------|------------|-------------|
| gemini-2.0-flash-001 | Fast, cost-effective | $0.075 | $0.30 |
| gemini-2.0-pro-exp-02-05 | More capable | $1.25 | $5.00 |
| gemini-1.5-pro-002 | Balanced | $1.25 | $5.00 |
| gemini-1.5-flash-002 | Legacy fast | $0.075 | $0.30 |

---

## Deployed Customers

### 1. Vladni Realita (StateOS)
- Widget ID: `Qb9aKBWroHpvYNX1POFz`
- Documents: Government programs (ANO, SPD, Motoriste)
- Deployed on: vladnirealita.cz

### 2. Ponehodova Pece
- Widget ID: `ls0Si9wuw2gbatGla3nW`
- Documents: Traffic laws, insurance info, CSSZ, psychosocial support
- API Key: `cb_live_oMfP9TuH21R2gBTHUoFrLSKPB1qAnLJblQiN7wrMtRk`
- Deployed on: ponehodovapece.cz

---

## URLs

- **API**: https://chatbot-api-182382115587.europe-west1.run.app
- **Customer Portal**: https://chatbot-api-182382115587.europe-west1.run.app/static/portal/index.html
- **Widget JS**: https://chatbot-api-182382115587.europe-west1.run.app/static/widget/chatbot-widget.js

---

## Environment Variables

```
GCP_PROJECT_ID=chatbot-platform-2026
GCP_REGION=europe-west1
GOOGLE_APPLICATION_CREDENTIALS=...
GCS_BUCKET_NAME=chatbot-platform-2026-documents
ADMIN_API_TOKEN=<secret>
PUBLIC_API_URL=https://chatbot-api-182382115587.europe-west1.run.app
```
