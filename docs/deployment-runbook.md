# D.D. Companion -- Deployment & Operations Runbook

## 1. Architecture Overview

The D.D. Companion application runs entirely on Google Cloud Platform using serverless and managed services.

### Components

| Component | Service | Purpose |
|-----------|---------|---------|
| Backend API | Cloud Run (`companion-{env}-backend`) | FastAPI application serving the REST API, document pipeline, and worker endpoints |
| Web Dashboard | Cloud Run (`companion-{env}-web`) | Nginx serving the Vite/React SPA |
| Database | Cloud SQL for PostgreSQL 16 | Primary data store with pgvector for RAG embeddings |
| Cache | Memorystore for Redis 7.0 (optional) | Caching layer; currently disabled in both environments (`enable_redis=false`) |
| Object Storage | GCS (`companion-{env}-documents`) | Document storage, encrypted at rest with CMEK (Cloud KMS) |
| Event Bus | Pub/Sub | 22 event topics with dead-letter support; `document-received` uses a push subscription to trigger the document pipeline |
| Scheduled Jobs | Cloud Scheduler | Triggers morning check-in and medication reminder workers every minute |
| Authentication | Firebase Auth (Identity Platform) | Email/password authentication for end users |
| Container Registry | Artifact Registry (`companion-{env}`) | Docker images for backend and web; keeps last 10 images per cleanup policy |
| Networking | VPC + Serverless VPC Access Connector | Private connectivity between Cloud Run and Cloud SQL/Redis |
| Migrations | Cloud Run Jobs (`companion-{env}-migrate`) | Runs Alembic migrations as a one-off job during deploy |
| Monitoring | Cloud Monitoring | Alert policies for error rate, latency, CPU, disk, instance count, and Redis memory |

### Request Flow

```
User -> Firebase Auth -> Cloud Run (web) -> Cloud Run (backend) -> Cloud SQL
                                                |
                                                +-> GCS (documents)
                                                +-> Pub/Sub (events)
                                                +-> LLM APIs (Gemini/Anthropic/OpenAI)
                                                +-> Document AI (OCR)
```

### Document Pipeline Flow

```
Upload -> GCS -> Pub/Sub (document-received) -> Push to /api/pipeline/document-received
  -> Document AI OCR -> LLM extraction -> pgvector embedding -> Pub/Sub (document-processed)
```

---

## 2. Environments

### Staging

| Setting | Value |
|---------|-------|
| GCP Project ID | `companion-staging-491606` |
| Region | `us-central1` |
| DB Tier | `db-f1-micro` |
| DB Disk | 10 GB (SSD, autoresize) |
| Backend Memory | 1Gi |
| Backend CPU | 1 |
| Backend Instances | 0-10 (scales to zero) |
| Web Instances | 0-5 (scales to zero) |
| Redis | Disabled |
| App URL | `https://companion-staging-web-44gbcsdrnq-uc.a.run.app` |
| Deploy Trigger | Automatic on push to `main` |
| DB Availability | ZONAL |
| Deletion Protection | Off |

### Production

| Setting | Value |
|---------|-------|
| GCP Project ID | `companion-prod-491606` |
| Region | `us-central1` |
| DB Tier | `db-f1-micro` |
| DB Disk | 10 GB (SSD, autoresize) |
| Backend Memory | 512Mi |
| Backend CPU | 1 |
| Backend Instances | 0-10 (scales to zero) |
| Web Instances | 0-5 (scales to zero) |
| Redis | Disabled |
| App URL | `https://app.mydailydignity.com` |
| Deploy Trigger | Manual (workflow_dispatch, requires typing "deploy" to confirm) |
| DB Availability | REGIONAL (high availability) |
| Deletion Protection | On |

### Alert Notifications

Both environments send alerts to `dd@mydailydignity.com`.

---

## 3. CI/CD Pipeline

Three GitHub Actions workflows live in `.github/workflows/`:

### CI (`ci.yml`)

**Triggers:** Push to `main` or `feature/**` branches, PRs against `main`.

**Jobs:**
1. **lint** -- Runs `ruff check .` on the backend (Python 3.13)
2. **test-backend** -- Spins up Postgres 16 and Redis 7 service containers, runs Alembic migrations, then `pytest -v`
3. **lint-web** -- Runs `npm run lint` on the web frontend (Node 20), if `web/package.json` exists
4. **terraform-validate** -- Runs `terraform fmt -check -recursive` and `terraform validate`

### Deploy to Staging (`deploy-staging.yml`)

**Triggers:** Push to `main` (automatic).

**Path filtering:** Uses `dorny/paths-filter` to detect changes in `backend/`, `web/`, and `infrastructure/terraform/`. Only changed components are built and deployed.

**Jobs (in order):**

1. **changes** -- Detects which paths changed
2. **terraform** (if infra changed) -- `terraform init` / `plan` / `apply` using staging tfvars
3. **build-backend** (if backend changed) -- Builds `infrastructure/Dockerfile.backend`, pushes to Artifact Registry tagged with git SHA and `latest`
4. **migrate** (after build-backend) -- Updates the Cloud Run Job `companion-staging-migrate` with the new image, executes `alembic upgrade head`
5. **deploy-backend** (after migrate) -- Deploys new image to Cloud Run, mounts `firebase-sa-key.json` secret, runs a smoke test (`curl /health`)
6. **build-web** (if web changed) -- Builds `infrastructure/Dockerfile.web` with Firebase and API config injected as build args, pushes to Artifact Registry
7. **deploy-web** (after build-web) -- Deploys to Cloud Run on port 8080, allows unauthenticated access

**Authentication:** Workload Identity Federation (OIDC) -- no service account JSON keys. Uses `STAGING_WIF_PROVIDER` and `STAGING_SA_EMAIL` GitHub secrets.

### Deploy to Production (`deploy-prod.yml`)

**Triggers:** Manual only (`workflow_dispatch`). Requires typing "deploy" in the confirmation input.

**Options:** `skip_terraform` input to deploy application only without Terraform changes.

**Jobs:** Same structure as staging but:
- Uses `PROD_WIF_PROVIDER` and `PROD_SA_EMAIL` secrets
- Has a **validate** job as a safety gate before anything runs
- Builds images fresh from source (does not promote staging images)
- Uses prod Firebase/API variables

### GitHub Secrets Required

| Secret | Purpose |
|--------|---------|
| `STAGING_WIF_PROVIDER` | Workload Identity Federation provider for staging |
| `STAGING_SA_EMAIL` | CI/CD service account email for staging |
| `PROD_WIF_PROVIDER` | Workload Identity Federation provider for production |
| `PROD_SA_EMAIL` | CI/CD service account email for production |

### GitHub Variables Required

| Variable | Purpose |
|----------|---------|
| `STAGING_API_BASE_URL` | Backend API URL for staging web build |
| `STAGING_FIREBASE_API_KEY` | Firebase config for staging web build |
| `STAGING_FIREBASE_AUTH_DOMAIN` | Firebase config for staging web build |
| `STAGING_FIREBASE_PROJECT_ID` | Firebase config for staging web build |
| `STAGING_FIREBASE_STORAGE_BUCKET` | Firebase config for staging web build |
| `STAGING_FIREBASE_MESSAGING_SENDER_ID` | Firebase config for staging web build |
| `STAGING_FIREBASE_APP_ID` | Firebase config for staging web build |
| `PROD_API_BASE_URL` | Backend API URL for prod web build |
| `PROD_FIREBASE_*` | Same set of Firebase config vars for prod |

---

## 4. Terraform Infrastructure

All Terraform lives in `infrastructure/terraform/`. State is stored in GCS buckets (`{project_id}-tf-state`) with versioning enabled, keyed by environment prefix.

### Modules

| Module | Path | What It Provisions |
|--------|------|--------------------|
| **networking** | `modules/networking/` | VPC, private subnet (10.0.0.0/20), private services IP range for Cloud SQL peering, Serverless VPC Access Connector (2-3 instances), firewall rules (allow internal, deny external ingress) |
| **database** | `modules/database/` | Cloud SQL PostgreSQL 16 instance (SSD, autoresize, PITR, daily backups at 03:00, Sunday maintenance, Query Insights enabled), `companion` database and user, optional Memorystore Redis 7.0 |
| **storage** | `modules/storage/` | Cloud KMS keyring and key (90-day rotation), CMEK-encrypted GCS bucket for documents (versioned, 365-day lifecycle, 3-version limit), Artifact Registry Docker repo (keeps last 10 images) |
| **secrets** | `modules/secrets/` | Auto-populated secrets: database URL, Redis URL. Manually managed secrets: `firebase-credentials`, `anthropic-api-key`, `openai-api-key`, `gmail-oauth-credentials`, `gmail-smtp-password`, `pipeline-api-key` |
| **compute** | `modules/compute/` | Backend Cloud Run v2 service (service account with roles for SQL, GCS, Pub/Sub, Secret Manager, Document AI, AI Platform, Firebase Auth), Web Cloud Run v2 service, IAM bindings for public access |
| **pubsub** | `modules/pubsub/` | 22 event topics, dead-letter topic (7-day retention), pull subscriptions with dead-letter policy (max 5 delivery attempts, 10s-600s exponential backoff), push subscription for `document-received` |
| **scheduler** | `modules/scheduler/` | Cloud Scheduler jobs: `morning-checkin` and `medication-reminders`, both every minute, authenticated via `X-Pipeline-Key` header |
| **cicd** | `modules/cicd/` | Workload Identity Federation pool and provider for GitHub Actions OIDC auth, IAM binding for the CI/CD service account |
| **firebase** | `modules/firebase/` | Firebase project, web app, Identity Platform config (email/password auth), Firebase web config stored in Secret Manager |
| **monitoring** | `modules/monitoring/` | Email notification channel, 6 alert policies: backend error rate >5%, backend P95 latency >2s, Cloud SQL CPU >80%, Cloud SQL disk >80%, backend at max instances, Redis memory >80% |

### Applying Terraform Manually

```bash
cd infrastructure/terraform

# Initialize with the appropriate state bucket
terraform init \
  -backend-config="bucket=companion-staging-491606-tf-state" \
  -backend-config="prefix=staging"

# Plan
terraform plan \
  -var-file="environments/staging.tfvars" \
  -var="project_id=companion-staging-491606" \
  -var="backend_image=us-central1-docker.pkg.dev/companion-staging-491606/companion-staging/companion-backend:latest" \
  -var="web_image=us-central1-docker.pkg.dev/companion-staging-491606/companion-staging/companion-web:latest"

# Apply
terraform apply
```

For production, substitute `prod` for `staging` and use the prod project ID.

### Initial Bootstrap

Run once to create GCP projects, enable APIs, create Terraform state buckets, and create CI/CD service accounts:

```bash
./scripts/bootstrap-gcp.sh <billing-account-id> [org-id]
```

This script (`scripts/bootstrap-gcp.sh`) enables 16 GCP APIs and grants 13 IAM roles to the CI/CD service account.

---

## 5. Database Migrations

Migrations use **Alembic** with async SQLAlchemy. Configuration is in `backend/alembic.ini` and `backend/alembic/env.py`. The database URL is overridden by the `COMPANION_DATABASE_URL` environment variable when set.

### How Migrations Run in CI/CD

During deploy, migrations run as a **Cloud Run Job** (`companion-{env}-migrate`):

1. The job image is updated to the newly built backend image
2. The job executes `alembic upgrade head`
3. The job runs with `--wait` so the deploy pipeline blocks until completion
4. Only after migrations succeed does the backend service deploy

### Current Migrations

Located in `backend/alembic/versions/`, numbered 001 through 019:

- `001_initial_schema.py` through `019_add_related_bill_id_to_todos.py`

### Creating a New Migration

```bash
cd backend

# Auto-generate from model changes
alembic revision --autogenerate -m "description_of_change"

# Or create an empty migration for manual SQL
alembic revision -m "description_of_change"
```

The new file will be created in `backend/alembic/versions/`. Follow the existing naming convention: `NNN_description.py`.

### Running Migrations Locally

```bash
cd backend
COMPANION_DATABASE_URL="postgresql+asyncpg://companion:companion_dev@localhost:5432/companion" \
  alembic upgrade head
```

### Rolling Back

```bash
# Downgrade by one revision
alembic downgrade -1

# Downgrade to a specific revision
alembic downgrade <revision_id>
```

Note: Rollback only works if the migration has a `downgrade()` function implemented. Always verify before relying on it in production.

### Running Migrations Manually in Staging/Prod

```bash
# Update the job image first
gcloud run jobs update companion-staging-migrate \
  --image us-central1-docker.pkg.dev/companion-staging-491606/companion-staging/companion-backend:latest \
  --region us-central1 \
  --project companion-staging-491606 \
  --command alembic --args "upgrade,head"

# Execute
gcloud run jobs execute companion-staging-migrate \
  --region us-central1 \
  --project companion-staging-491606 \
  --wait
```

---

## 6. Secret Management

Secrets are stored in **Google Secret Manager** and injected into Cloud Run as environment variables at runtime.

### Auto-Populated Secrets (Managed by Terraform)

| Secret ID | Source |
|-----------|--------|
| `companion-{env}-database-url` | Constructed from Cloud SQL instance connection name, database name, user, and password |
| `companion-{env}-redis-url` | Constructed from Memorystore Redis host/port (or `redis://disabled:6379/0` when Redis is off) |
| `companion-{env}-firebase-web-config` | Auto-generated Firebase web app configuration JSON |

### Manually Managed Secrets (Created Empty by Terraform)

These secrets must have their values set manually via the GCP Console or `gcloud`:

| Secret ID | Environment Variable | Purpose |
|-----------|---------------------|---------|
| `companion-{env}-firebase-credentials` | `COMPANION_FIREBASE_CREDENTIALS` | Firebase service account credentials JSON |
| `companion-{env}-anthropic-api-key` | `COMPANION_ANTHROPIC_API_KEY` | Anthropic API key for Claude |
| `companion-{env}-openai-api-key` | `COMPANION_OPENAI_API_KEY` | OpenAI API key for embeddings |
| `companion-{env}-gmail-oauth-credentials` | -- | Gmail OAuth credentials for email processing |
| `companion-{env}-gmail-smtp-password` | `COMPANION_GMAIL_SMTP_PASSWORD` | Gmail SMTP app password (sender: `dd@mydailydignity.com`) |
| `companion-{env}-pipeline-api-key` | `COMPANION_PIPELINE_API_KEY` | Internal API key for Cloud Scheduler and Pub/Sub push auth |

### Setting a Secret Value

```bash
echo -n "your-secret-value" | gcloud secrets versions add companion-staging-pipeline-api-key \
  --data-file=- \
  --project=companion-staging-491606
```

### Importing a Pre-Existing Secret into Terraform

If a secret was created manually before Terraform managed it:

```bash
terraform import \
  -var-file="environments/staging.tfvars" \
  -var="project_id=companion-staging-491606" \
  -var="backend_image=placeholder" \
  -var="web_image=placeholder" \
  'module.secrets.google_secret_manager_secret.manual["pipeline-api-key"]' \
  "projects/companion-staging-491606/secrets/companion-staging-pipeline-api-key"
```

### Environment Variables (Non-Secret)

Set directly on the Cloud Run service via Terraform (`infrastructure/terraform/modules/compute/main.tf`):

| Variable | Value |
|----------|-------|
| `COMPANION_ENVIRONMENT` | `staging` or `prod` |
| `COMPANION_GCP_PROJECT_ID` | The GCP project ID |
| `COMPANION_GCS_BUCKET_DOCUMENTS` | GCS bucket name for documents |
| `COMPANION_APP_URL` | Frontend URL for email links |

### All Backend Config Variables

Defined in `backend/app/config.py` using `pydantic_settings.BaseSettings` with the `COMPANION_` prefix. Key variables:

| Variable | Default | Notes |
|----------|---------|-------|
| `COMPANION_DATABASE_URL` | `postgresql+asyncpg://companion:companion_dev@localhost:5432/companion` | Overridden by Secret Manager in cloud |
| `COMPANION_REDIS_URL` | `redis://localhost:6379/0` | |
| `COMPANION_LLM_PROVIDER` | `gemini` | Options: `gemini`, `anthropic`, `openai` |
| `COMPANION_GEMINI_MODEL` | `gemini-2.5-flash` | |
| `COMPANION_EMBEDDING_MODEL` | `text-embedding-005` | |
| `COMPANION_DEV_AUTH_BYPASS` | `false` | Must never be true in production |
| `COMPANION_DOCUMENTAI_PROCESSOR_ID` | `6785df08989fd9a6` | |
| `COMPANION_DOCUMENTAI_LOCATION` | `us` | |

---

## 7. Monitoring and Logging

### Alert Policies

Defined in `infrastructure/terraform/modules/monitoring/main.tf`. All alerts notify `dd@mydailydignity.com` and auto-close after 30 minutes.

| Alert | Condition | Duration |
|-------|-----------|----------|
| Backend Error Rate | 5xx rate > 5 requests/sec | 5 minutes |
| Backend P95 Latency | P95 response time > 2 seconds | 5 minutes |
| Cloud SQL CPU | CPU utilization > 80% | 10 minutes |
| Cloud SQL Disk | Disk utilization > 80% | 5 minutes |
| Backend Max Instances | Instance count > 8 (staging) or > 45 (prod) | 5 minutes |
| Redis Memory | Memory usage > 80% | 5 minutes |

### Where to Find Logs

**Cloud Run logs (backend):**
```bash
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="companion-staging-backend"' \
  --project=companion-staging-491606 \
  --limit=50 \
  --format="table(timestamp,severity,textPayload)"
```

Or in the GCP Console: Cloud Run > companion-{env}-backend > Logs

**Cloud Run Job logs (migrations):**
```bash
gcloud logging read \
  'resource.type="cloud_run_job" AND resource.labels.job_name="companion-staging-migrate"' \
  --project=companion-staging-491606 \
  --limit=50
```

**Pub/Sub dead-letter messages:**
```bash
gcloud pubsub subscriptions pull companion-staging-dead-letter-sub \
  --project=companion-staging-491606 \
  --limit=10 \
  --auto-ack
```

**Cloud SQL Query Insights:**
GCP Console > SQL > companion-{env}-db > Query Insights (enabled via Terraform with query plans and application tags).

**Cloud Scheduler job history:**
```bash
gcloud scheduler jobs describe companion-staging-morning-checkin \
  --project=companion-staging-491606 \
  --location=us-central1
```

Or in the GCP Console: Cloud Scheduler > job name > Logs.

### Health Check Endpoint

The backend exposes `GET /health` which is used by:
- Cloud Run startup and liveness probes (defined in `infrastructure/terraform/modules/compute/main.tf`)
- Post-deploy smoke tests in the CI/CD pipeline
- Docker container health checks

---

## 8. Manual Operations

### Force Restart a Cloud Run Service

```bash
# Redeploy with the same image (forces new revision)
gcloud run services update companion-staging-backend \
  --region us-central1 \
  --project companion-staging-491606 \
  --update-labels="force-restart=$(date +%s)"
```

### View Running Revisions

```bash
gcloud run revisions list \
  --service companion-staging-backend \
  --region us-central1 \
  --project companion-staging-491606
```

### Roll Back to a Previous Revision

```bash
# List revisions
gcloud run revisions list --service companion-staging-backend \
  --region us-central1 --project companion-staging-491606

# Route 100% traffic to a previous revision
gcloud run services update-traffic companion-staging-backend \
  --to-revisions=REVISION_NAME=100 \
  --region us-central1 \
  --project companion-staging-491606
```

### Trigger Workers Manually

Workers are authenticated via the `X-Pipeline-Key` header. Get the key from Secret Manager first:

```bash
# Get the pipeline API key
KEY=$(gcloud secrets versions access latest \
  --secret=companion-staging-pipeline-api-key \
  --project=companion-staging-491606)

# Get the backend URL
URL=$(gcloud run services describe companion-staging-backend \
  --region us-central1 \
  --project companion-staging-491606 \
  --format='value(status.url)')

# Trigger morning check-in
curl -X POST "$URL/api/internal/workers/morning-checkin" \
  -H "X-Pipeline-Key: $KEY" \
  -H "Content-Type: application/json"

# Trigger medication reminders
curl -X POST "$URL/api/internal/workers/medication-reminders" \
  -H "X-Pipeline-Key: $KEY" \
  -H "Content-Type: application/json"
```

### Reprocess a Document

Publish a message to the `document-received` Pub/Sub topic to retrigger the pipeline:

```bash
gcloud pubsub topics publish companion-staging-document-received \
  --project=companion-staging-491606 \
  --message='{"document_id": "YOUR_DOCUMENT_UUID", "user_id": "USER_UUID"}'
```

The push subscription will deliver it to `/api/pipeline/document-received`.

### Pause/Resume Cloud Scheduler Jobs

```bash
# Pause
gcloud scheduler jobs pause companion-staging-morning-checkin \
  --project=companion-staging-491606 \
  --location=us-central1

# Resume
gcloud scheduler jobs resume companion-staging-morning-checkin \
  --project=companion-staging-491606 \
  --location=us-central1
```

### Seed Staging Data

The backend image includes `seed_staging.py` (copied in `infrastructure/Dockerfile.backend`). Run it as a Cloud Run Job or locally against the staging database.

### Connect to Cloud SQL Directly

```bash
# Using Cloud SQL Auth Proxy
gcloud sql connect companion-staging-db \
  --user=companion \
  --project=companion-staging-491606
```

---

## 9. Incident Response

### Common Failure Modes

#### Backend returns 503 / does not start

**Symptoms:** Health check failures, smoke test fails in CI.

**Diagnosis:**
```bash
# Check recent logs for startup errors
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="companion-staging-backend" AND severity>=ERROR' \
  --project=companion-staging-491606 \
  --limit=20 \
  --format="table(timestamp,textPayload)"
```

**Common causes:**
- Missing or invalid secret (Secret Manager version not set) -- check that all manual secrets have values
- Database unreachable (VPC connector issue) -- verify VPC connector is healthy
- Bad migration left database in broken state -- check migration job logs

#### Migration job fails

**Symptoms:** `companion-{env}-migrate` job fails, backend deploy is blocked.

**Diagnosis:**
```bash
gcloud run jobs executions list --job=companion-staging-migrate \
  --region=us-central1 --project=companion-staging-491606

# Check logs for the failed execution
gcloud logging read \
  'resource.type="cloud_run_job" AND resource.labels.job_name="companion-staging-migrate"' \
  --project=companion-staging-491606 --limit=30
```

**Fix:** Fix the migration code, push to main (staging), or manually run a corrective migration.

#### Document pipeline not processing

**Symptoms:** Documents uploaded but never processed.

**Diagnosis:**
1. Check if messages are accumulating in the Pub/Sub subscription:
   ```bash
   gcloud pubsub subscriptions describe companion-staging-document-received-push \
     --project=companion-staging-491606
   ```
2. Check dead-letter topic for failed messages:
   ```bash
   gcloud pubsub subscriptions pull companion-staging-dead-letter-sub \
     --project=companion-staging-491606 --limit=10
   ```
3. Check backend logs for pipeline errors (look for `pipeline` or `document_handler` in logs)

**Common causes:**
- Pipeline API key mismatch between Pub/Sub push config and backend secret
- LLM API key expired or quota exceeded (Anthropic, OpenAI, or Gemini)
- Document AI processor issue

#### Cloud Scheduler jobs not firing

**Symptoms:** No morning check-ins or medication reminders being sent.

**Diagnosis:**
```bash
gcloud scheduler jobs describe companion-staging-morning-checkin \
  --project=companion-staging-491606 --location=us-central1
```

Check the `state` field (should be `ENABLED`) and `lastAttemptTime` / `status`.

**Common causes:**
- Job is paused
- Pipeline API key mismatch
- Backend is scaled to zero and cold start exceeds the scheduler timeout

#### Cloud SQL connection failures

**Symptoms:** Backend logs show database connection errors.

**Diagnosis:**
- Verify VPC connector status in GCP Console
- Check Cloud SQL instance status: `gcloud sql instances describe companion-staging-db --project=companion-staging-491606`
- Check max_connections (set to 100 via Terraform)

**Fix:** If connections are exhausted, restart the backend to drop idle connections. If the VPC connector is unhealthy, it may need to be recreated via Terraform.

---

## 10. Scaling Considerations

### Current Configuration

| Resource | Staging | Production |
|----------|---------|------------|
| Backend instances | 0-10 | 0-10 |
| Backend CPU | 1 | 1 |
| Backend memory | 1Gi | 512Mi |
| Backend concurrency | 80 requests/instance | 80 requests/instance |
| Backend timeout | 300s | 300s |
| Web instances | 0-5 | 0-5 |
| Web CPU | 1 | 1 |
| Web memory | 256Mi | 256Mi |
| Cloud SQL tier | db-f1-micro | db-f1-micro |
| Cloud SQL max connections | 100 | 100 |
| Cloud SQL disk | 10GB (autoresize) | 10GB (autoresize) |
| VPC connector instances | 2-3 | 2-3 |
| Redis | Disabled | Disabled |

### Scaling Levers

**To handle more traffic:**
- Increase `backend_max_instances` in the environment tfvars file
- Increase `backend_cpu` and `backend_memory` for heavier workloads
- Set `backend_min_instances` > 0 to eliminate cold starts (increases cost)

**To handle more data:**
- Upgrade `db_tier` (e.g., `db-custom-2-7680` for 2 vCPU / 7.5GB RAM)
- Cloud SQL disk autoresizes automatically
- Increase `max_connections` database flag if connection pooling is insufficient

**To enable caching:**
- Set `enable_redis = true` in the environment tfvars
- The backend already reads `COMPANION_REDIS_URL` from secrets; the app handles the disabled case gracefully

**To reduce cost (low traffic):**
- Keep `backend_min_instances = 0` and `web_min_instances = 0` (current setting)
- CPU idle is automatically enabled when min instances is 0 (`cpu_idle = true`)
- Startup CPU boost is enabled to mitigate cold start latency

### Bottlenecks to Watch

- **Cloud SQL db-f1-micro** is shared-core with limited CPU and memory. Monitor Query Insights and the CPU/disk alerts. Upgrade the tier before sustained high load.
- **VPC connector** is limited to 2-3 instances. If throughput to Cloud SQL becomes a bottleneck, increase `max_instances`.
- **Document pipeline** has a 300-second Pub/Sub ack deadline. Very large documents with slow LLM processing could time out and be retried (up to 5 times before dead-lettering).
- **100 max_connections** on Cloud SQL could be exhausted if backend scales to many instances with concurrent database access. Each Cloud Run instance runs 2 uvicorn workers.

### Local Development

Use the docker-compose setup in `infrastructure/docker-compose.yml`:

```bash
docker compose -f infrastructure/docker-compose.yml up -d
```

This starts Postgres 16, Redis 7, and a Pub/Sub emulator. The backend connects using the defaults in `backend/app/config.py`.
