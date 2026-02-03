# GCP & Firebase Operations

Quick commands for Google Cloud Platform and Firebase.

## Authentication

```bash
# Login to GCP
gcloud auth login

# Application Default Credentials (for SDK)
gcloud auth application-default login

# Verify
gcloud auth list
gcloud config list

# Set project
gcloud config set project glassy-polymer-477908-g9
```

## Cloud Run

### Deploy from Source

```bash
gcloud run deploy SERVICE_NAME \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated
```

### Deploy with Env Vars

```bash
gcloud run deploy SERVICE_NAME \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars="KEY1=value1,KEY2=value2"
```

### Check Logs

```bash
gcloud run logs read SERVICE_NAME --region europe-west1
```

### List Services

```bash
gcloud run services list --region europe-west1
```

## Firebase

### Deploy Hosting

```bash
firebase deploy --only hosting --project PROJECT_ID
```

### Deploy Functions

```bash
firebase deploy --only functions --project PROJECT_ID
```

### View Console

```bash
# Opens browser
firebase open hosting --project PROJECT_ID
```

## Cloud Storage

```bash
# List buckets
gsutil ls

# List bucket contents
gsutil ls gs://BUCKET_NAME/

# Upload
gsutil cp file.txt gs://BUCKET_NAME/

# Download
gsutil cp gs://BUCKET_NAME/file.txt .
```

## Quick Troubleshooting

### No credentials

```bash
gcloud auth application-default login
```

### WSL credential sync

```bash
cp -r /mnt/c/Users/mpeck/AppData/Roaming/gcloud/* ~/.config/gcloud/
```

### Check current project

```bash
gcloud config get-value project
```

## Integration with Workflow

Before any GCP deployment, consult Gemini:

```bash
python scripts/gemini_consult.py "Deploying [SERVICE] to Cloud Run. Config: [SUMMARY]. Approve?"
```

Gemini responses:
- `APPROVED` → proceed with deployment
- `REVISE` → adjust configuration
- `ESCALATE` → ask human (production deployments, new services)
