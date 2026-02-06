# ChatBot Platform

Multi-tenant ChatBot SaaS Platform - ChatBase alternative.

## Deployed

- **API**: https://chatbot-api-182382115587.europe-west1.run.app
- **Customer Portal**: https://chatbot-api-182382115587.europe-west1.run.app/static/portal/index.html

## Features

- **Multi-tenant**: Customers, widgets, documents isolated by customer_id
- **RAG**: Upload documents or scrape URLs for knowledge base
- **Gemini Models**: Select from Flash/Pro models per widget
- **Analytics**: Usage trends, widget performance, top questions
- **Embed Widget**: JavaScript snippet for any website
- **Guardrails**: Custom system prompts per widget

## Tech Stack

- Python 3.12 + FastAPI
- Gemini 2.0 (LLM + Embeddings)
- Firestore (database + vectors)
- Cloud Storage (documents)
- Cloud Run (hosting)

## Quick Start

```bash
# Local development
pip install -r requirements.txt
uvicorn src.main:app --reload

# Deploy
gcloud run deploy chatbot-api --source . --region europe-west1
```

## Admin Commands

```bash
# Create customer
curl -X POST "/api/admin/customers" \
  -H "X-Admin-Token: $ADMIN_TOKEN" \
  -d '{"email": "x@y.com", "company_name": "Test", "subscription_tier": "starter"}'

# Create API key
curl -X POST "/api/admin/customers/{id}/create-api-key" \
  -H "X-Admin-Token: $ADMIN_TOKEN"
```

## Documentation

- `.claude/PLAN.md` - Full technical documentation
- `.claude/BUSINESS.md` - Business requirements

## Environment

- Platform: Windows 11
- GCP Project: chatbot-platform-2026
- Region: europe-west1
