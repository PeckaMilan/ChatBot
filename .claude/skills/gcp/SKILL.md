---
name: gcp
description: Google Cloud Platform and Firebase authentication and deployment patterns. Use for GCP Cloud Run, Cloud Storage, Firebase Auth, Firestore, and related services.
user-invocable: true
---

# GCP & Firebase Authentication

Autonomous authentication patterns for Google Cloud Platform and Firebase.

## Quick Reference

| Service | Auth Method | Command |
|---------|-------------|---------|
| GCP (local dev) | ADC | `gcloud auth application-default login` |
| GCP (Cloud Run) | Service Account | Automatic |
| Firebase (frontend) | SDK Config | Environment variables |
| Firebase (backend) | Admin SDK | Service account JSON |

---

## GCP Configuration

### Project Details

```bash
PROJECT_ID=glassy-polymer-477908-g9
GCP_REGION=europe-west1
```

### Initial Setup (One-time)

```bash
# Login to GCP
gcloud auth login

# Set default project
gcloud config set project glassy-polymer-477908-g9

# Application Default Credentials (for SDK access)
gcloud auth application-default login

# Verify
gcloud auth list
gcloud config list
```

### WSL Credential Sync

If using WSL and credentials are on Windows:

```bash
mkdir -p ~/.config/gcloud
cp -r /mnt/c/Users/mpeck/AppData/Roaming/gcloud/* ~/.config/gcloud/
gcloud auth list
```

---

## Cloud Run Deployment

### Standard Deployment

```bash
# Build and deploy from source
gcloud run deploy SERVICE_NAME \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated

# With environment variables
gcloud run deploy SERVICE_NAME \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars="VAR1=value1,VAR2=value2"
```

### Production Deployment (Full Config)

```bash
# Build image first
gcloud builds submit \
  --tag europe-west1-docker.pkg.dev/glassy-polymer-477908-g9/cloud-run-source-deploy/SERVICE_NAME:latest

# Deploy with full config
gcloud run deploy SERVICE_NAME \
  --image europe-west1-docker.pkg.dev/glassy-polymer-477908-g9/cloud-run-source-deploy/SERVICE_NAME:latest \
  --region europe-west1 \
  --memory 8Gi \
  --cpu 4 \
  --timeout 600 \
  --concurrency 5 \
  --min-instances 0 \
  --max-instances 10 \
  --no-cpu-throttling \
  --cpu-boost \
  --allow-unauthenticated
```

### Environment Variables for Cloud Run

```bash
# Backend
PROJECT_ID=glassy-polymer-477908-g9
GOOGLE_CLOUD_PROJECT=glassy-polymer-477908-g9
GCP_PROJECT_ID=glassy-polymer-477908-g9
GCP_REGION=europe-west1
```

---

## Cloud Storage

### Bucket Operations

```bash
# Create bucket
gsutil mb -l europe-west1 gs://BUCKET_NAME/

# Upload file
gsutil cp local_file.txt gs://BUCKET_NAME/path/

# List contents
gsutil ls gs://BUCKET_NAME/

# Make public (if needed)
gsutil iam ch allUsers:objectViewer gs://BUCKET_NAME
```

### Python SDK

```python
from google.cloud import storage

# Uses Application Default Credentials automatically
client = storage.Client()
bucket = client.bucket("BUCKET_NAME")

# Upload
blob = bucket.blob("path/to/file.txt")
blob.upload_from_string("content")

# Download
content = blob.download_as_text()
```

---

## Cloud Tasks

### Create Queue

```bash
gcloud tasks queues create QUEUE_NAME \
  --location=europe-west1
```

### Dispatch Task (Python)

```python
from google.cloud import tasks_v2

client = tasks_v2.CloudTasksClient()
parent = client.queue_path(PROJECT_ID, "europe-west1", "QUEUE_NAME")

task = {
    "http_request": {
        "http_method": tasks_v2.HttpMethod.POST,
        "url": "https://SERVICE-URL.run.app/api/task",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload).encode(),
    }
}

client.create_task(parent=parent, task=task)
```

---

## Cloud Scheduler

### Create Scheduled Job

```bash
gcloud scheduler jobs create http JOB_NAME \
  --location=europe-west1 \
  --schedule="0 6 * * *" \
  --time-zone="Europe/Prague" \
  --uri="https://SERVICE-URL.run.app/api/cron" \
  --http-method=POST \
  --oidc-service-account-email=SERVICE@PROJECT_ID.iam.gserviceaccount.com
```

---

## Firebase Configuration

### Firebase Projects

| Project | ID | Purpose |
|---------|-----|---------|
| Phoenix Analytics | `phoenix-analytics-44917` | Electoral analytics |
| LegiMental | `legimental-prod` | Legislative compliance |

### Frontend Environment Variables

```bash
# React (Create React App)
REACT_APP_FIREBASE_API_KEY=xxx
REACT_APP_FIREBASE_AUTH_DOMAIN=PROJECT_ID.firebaseapp.com
REACT_APP_FIREBASE_PROJECT_ID=PROJECT_ID
REACT_APP_FIREBASE_STORAGE_BUCKET=PROJECT_ID.appspot.com
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=xxx
REACT_APP_FIREBASE_APP_ID=xxx

# Next.js
NEXT_PUBLIC_FIREBASE_API_KEY=xxx
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=PROJECT_ID.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=PROJECT_ID
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=PROJECT_ID.firebasestorage.app
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=xxx
NEXT_PUBLIC_FIREBASE_APP_ID=xxx
```

### Firebase SDK Setup (Frontend)

```typescript
// lib/firebase.ts
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const db = getFirestore(app);
```

### Firebase Admin SDK (Backend)

```python
# Python backend
import firebase_admin
from firebase_admin import credentials, firestore, auth

# Uses Application Default Credentials
firebase_admin.initialize_app()

# Or with service account JSON
cred = credentials.Certificate("path/to/service-account.json")
firebase_admin.initialize_app(cred)

# Firestore
db = firestore.client()

# Verify user token
decoded_token = auth.verify_id_token(id_token)
uid = decoded_token['uid']
```

### Firebase Hosting

```bash
# firebase.json
{
  "hosting": {
    "site": "PROJECT_ID",
    "public": "out",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [{"source": "**", "destination": "/index.html"}],
    "headers": [
      {
        "source": "**/*.@(js|css)",
        "headers": [{"key": "Cache-Control", "value": "max-age=31536000"}]
      }
    ]
  }
}

# Deploy
firebase deploy --only hosting --project PROJECT_ID
```

---

## Gemini AI Integration

### SDK Setup

```python
# Use google-genai (NOT google-generativeai - deprecated)
from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Your prompt here",
    config=types.GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=2048
    )
)
```

### Model Fallback Chain

```python
MODELS = [
    "gemini-2.5-pro",      # Primary
    "gemini-2.5-flash",    # Fallback 1
    "gemini-2.0-flash",    # Fallback 2
    "gemini-1.5-flash",    # Fallback 3
]

for model in MODELS:
    try:
        response = client.models.generate_content(model=model, ...)
        break
    except Exception:
        continue
```

---

## Authentication Patterns

### Pattern 1: Public API (No Auth)

```bash
gcloud run deploy --allow-unauthenticated
```

Use for: Public dashboards, APIs with own auth layer

### Pattern 2: Firebase Auth (Frontend)

```typescript
// Login
import { signInWithEmailAndPassword } from 'firebase/auth';
await signInWithEmailAndPassword(auth, email, password);

// Get token for backend
const token = await auth.currentUser.getIdToken();

// Send to backend
fetch('/api/endpoint', {
  headers: { Authorization: `Bearer ${token}` }
});
```

### Pattern 3: Token Verification (Backend)

```python
from firebase_admin import auth

def verify_token(request):
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    try:
        decoded = auth.verify_id_token(token)
        return decoded['uid']
    except:
        raise HTTPException(401, "Invalid token")
```

### Pattern 4: Service Account (Server-to-Server)

```bash
# Cloud Scheduler → Cloud Run
--oidc-service-account-email=SERVICE@PROJECT.iam.gserviceaccount.com
```

---

## Common Issues & Fixes

### "No credentialed accounts"

```bash
gcloud auth login
gcloud auth application-default login
```

### "Container import error" on Cloud Run

Use two-step deployment:
```bash
gcloud builds submit --tag IMAGE_URL
gcloud run deploy --image IMAGE_URL
```

### Firebase "From" email mismatch

SMTP sender email MUST match Firebase Auth template "From" address.

### Czech encoding (Windows-1250)

```javascript
// For PSP.cz and Czech government sites
const decoder = new TextDecoder('windows-1250');
const text = decoder.decode(buffer);
```

---

## Secrets in .env

```bash
# GCP
GOOGLE_API_KEY=xxx

# Firebase (get from Firebase Console → Project Settings)
FIREBASE_API_KEY=xxx
FIREBASE_AUTH_DOMAIN=xxx
FIREBASE_PROJECT_ID=xxx

# Admin (for backend)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

---

## Autonomous Deployment Checklist

Before deploying to GCP:

1. [ ] `gcloud auth application-default login` done
2. [ ] Environment variables set in Cloud Run
3. [ ] Firebase config in frontend .env
4. [ ] Service account has required permissions
5. [ ] Consult Gemini: "Deploying [service]. Config: [summary]. Approve?"

After deployment:

1. [ ] Verify service is running: `gcloud run services list`
2. [ ] Test endpoint manually
3. [ ] Check logs: `gcloud run logs read SERVICE_NAME`
