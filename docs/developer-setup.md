# D.D. Companion - Developer Setup Guide

## 1. Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | >= 3.12 (CI uses 3.13) | Backend runtime |
| Node.js | >= 22.11.0 | Mobile app (see `companion-app/package.json` engines) |
| Node.js | 20.x | Web dashboard (Dockerfile uses `node:20-alpine`) |
| Docker & Docker Compose | Latest | Local Postgres, Redis, Pub/Sub emulator |
| Xcode | 15+ | iOS builds; deployment target is iOS 15.1 |
| CocoaPods | Latest | iOS dependency management |
| Terraform | >= 1.5.0 (CI pins 1.9.0) | Infrastructure (only needed for infra work) |
| gcloud CLI | Latest | GCP auth, Pub/Sub emulator (only for cloud features) |
| Ruby | System or rbenv | Required by CocoaPods |

## 2. Repository Structure

```
companion/
  backend/          # FastAPI backend (Python)
  web/              # Caregiver dashboard (React + Vite + Tailwind)
  companion-app/    # Mobile app (React Native 0.84, iOS)
  infrastructure/   # Dockerfiles, docker-compose, Terraform, nginx
  scripts/          # bootstrap-gcp.sh, seed scripts
  docs/             # Documentation
  firestore.rules   # Firebase Firestore security rules
```

## 3. Backend Setup

### 3.1 Start Local Services

From the repo root:

```bash
docker compose -f infrastructure/docker-compose.yml up -d
```

This starts:
- **PostgreSQL 16** on `localhost:5432` (user: `companion`, password: `companion_dev`, db: `companion`)
- **Redis 7** on `localhost:6379`
- **Pub/Sub emulator** on `localhost:8085`

### 3.2 Create Virtual Environment and Install Dependencies

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3.3 (Optional) Install pgvector Extension

The migration `011_document_chunks_pgvector.py` gracefully skips pgvector if the extension is not available. To enable vector search locally:

```bash
# On macOS with Homebrew:
brew install pgvector

# Then inside the running Postgres container:
docker exec -it <postgres-container> psql -U companion -d companion -c "CREATE EXTENSION vector;"
```

### 3.4 Run Database Migrations

```bash
cd backend
alembic upgrade head
```

The connection string defaults to `postgresql+asyncpg://companion:companion_dev@localhost:5432/companion` (configured in `alembic.ini`).

### 3.5 Run the Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8080
```

The API will be available at `http://localhost:8080`. Health check: `GET /health`.

For local development without Firebase auth, set:

```bash
export COMPANION_DEV_AUTH_BYPASS=true
```

**Warning:** Never enable this in production. The app will refuse to start if `dev_auth_bypass=true` and `environment=prod`.

### 3.6 Environment Variables

All backend settings use the `COMPANION_` prefix (defined in `backend/app/config.py`). Set them as environment variables or in your shell profile.

## 4. Web Dashboard Setup

### 4.1 Install Dependencies

```bash
cd web
npm install
```

### 4.2 Configure Environment Variables

Copy the example file and fill in Firebase values:

```bash
cp .env.example .env
```

The `.env` file needs:

| Variable | Description |
|----------|-------------|
| `VITE_FIREBASE_API_KEY` | Firebase Web API key |
| `VITE_FIREBASE_AUTH_DOMAIN` | e.g. `your-project.firebaseapp.com` |
| `VITE_FIREBASE_PROJECT_ID` | Firebase project ID |
| `VITE_FIREBASE_STORAGE_BUCKET` | Firebase storage bucket |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | Firebase Cloud Messaging sender ID |
| `VITE_FIREBASE_APP_ID` | Firebase app ID |
| `VITE_API_BASE_URL` | Leave empty for local dev (Vite serves on `:5173`) |

### 4.3 Run the Web Dashboard

```bash
npm run dev
```

The dashboard starts at `http://localhost:5173`. The backend CORS config allows this origin in development mode.

Other commands:
- `npm run build` -- TypeScript check + production build
- `npm run lint` -- TypeScript type checking (`tsc --noEmit`)

## 5. Mobile App Setup (iOS)

### 5.1 Install JavaScript Dependencies

```bash
cd companion-app
npm install
```

### 5.2 Install CocoaPods

```bash
cd companion-app/ios
bundle exec pod install   # or: pod install
```

The Podfile uses static frameworks (`use_frameworks! :linkage => :static`) and sets `$RNFirebaseAsStaticFramework = true` for Firebase compatibility.

### 5.3 Firebase Configuration

The iOS app requires a `GoogleService-Info.plist` file at `companion-app/ios/CompanionApp/GoogleService-Info.plist`. Download this from the Firebase Console (Project Settings > iOS app).

### 5.4 Open in Xcode

Open the `.xcodeproj` (not a workspace, since CocoaPods generates one):

```bash
open companion-app/ios/CompanionApp.xcodeproj
```

Or after `pod install`, use the generated workspace if present.

Key build settings:
- iOS deployment target: **15.1**
- React Native version: **0.84.1**
- The app includes a native `DocumentScannerModule` (Swift + Objective-C bridge)

### 5.5 Run on Simulator

```bash
cd companion-app
npm run ios
```

Or build from Xcode by selecting a simulator target and pressing Cmd+R.

### 5.6 Run Metro Bundler

In a separate terminal:

```bash
cd companion-app
npm start
```

## 6. GCP / Firebase Configuration

### 6.1 Firebase Project

The project uses Firebase for:
- **Authentication** (Google Sign-In) -- both mobile and web
- **Cloud Messaging** -- push notifications to the mobile app
- **Firestore** -- real-time pipeline event streaming (see `firestore.rules`)

You need a Firebase project. The staging project ID is `companion-staging-491606`.

### 6.2 Service Account for Backend

The backend uses `firebase-admin` SDK, which requires a service account credential. For local development:

1. Go to Firebase Console > Project Settings > Service Accounts
2. Generate a new private key (JSON)
3. Set `GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json`

This same credential provides access to all Google Cloud services (Pub/Sub, Cloud Storage, Text-to-Speech, Speech-to-Text, Document AI, Vertex AI, KMS, Vision).

### 6.3 GCP Bootstrap (New Projects Only)

For creating new GCP projects from scratch:

```bash
./scripts/bootstrap-gcp.sh <billing-account-id> [org-id]
```

This creates staging and prod projects, enables all required APIs, and sets up CI/CD service accounts.

### 6.4 Terraform (Infrastructure Only)

```bash
cd infrastructure/terraform
terraform init -backend-config="bucket=companion-terraform-state" -backend-config="prefix=staging"
terraform plan -var-file=staging.tfvars
```

Required Terraform version: `>= 1.5.0`. CI validates with `1.9.0`.

## 7. Environment Variables Reference

All variables use the `COMPANION_` prefix. Source: `backend/app/config.py`.

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPANION_DATABASE_URL` | `postgresql+asyncpg://companion:companion_dev@localhost:5432/companion` | Async PostgreSQL connection string |
| `COMPANION_DATABASE_ECHO` | `false` | Log all SQL queries (for debugging) |
| `COMPANION_REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `COMPANION_GCP_PROJECT_ID` | `companion-dev` | Google Cloud project ID |
| `COMPANION_PUBSUB_EMULATOR_HOST` | (none) | Set to `localhost:8085` to use local Pub/Sub emulator |
| `COMPANION_GCS_BUCKET_DOCUMENTS` | `companion-docs-dev` | GCS bucket for document storage |
| `COMPANION_KMS_KEY_ID` | (empty) | Google Cloud KMS key for encryption |
| `COMPANION_FIREBASE_PROJECT_ID` | `companion-dev` | Firebase project ID for auth verification |
| `COMPANION_ANTHROPIC_API_KEY` | (empty) | Anthropic API key (for Claude LLM) |
| `COMPANION_OPENAI_API_KEY` | (empty) | OpenAI API key |
| `COMPANION_LLM_PROVIDER` | `gemini` | LLM provider: `gemini`, `anthropic`, or `openai` |
| `COMPANION_GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `COMPANION_GEMINI_LOCATION` | `us-central1` | Vertex AI region for Gemini |
| `COMPANION_EMBEDDING_MODEL` | `text-embedding-005` | Embedding model for RAG |
| `COMPANION_RAG_CHUNK_SIZE` | `800` | Document chunk size for RAG |
| `COMPANION_RAG_CHUNK_OVERLAP` | `100` | Overlap between chunks |
| `COMPANION_RAG_TOP_K` | `5` | Number of chunks to retrieve |
| `COMPANION_PIPELINE_API_KEY` | (empty) | Service-to-service auth key (required in production) |
| `COMPANION_DEV_AUTH_BYPASS` | `false` | Skip Firebase auth (local dev only, never in prod) |
| `COMPANION_GMAIL_SMTP_USER` | `dd@mydailydignity.com` | Gmail SMTP sender address |
| `COMPANION_GMAIL_SMTP_PASSWORD` | (empty) | Gmail app password for SMTP |
| `COMPANION_DOCUMENTAI_PROCESSOR_ID` | `6785df08989fd9a6` | Google Document AI processor ID |
| `COMPANION_DOCUMENTAI_LOCATION` | `us` | Document AI processor region |
| `COMPANION_APP_URL` | `http://localhost:5173` | Frontend URL (used in email links) |
| `COMPANION_ENVIRONMENT` | `development` | Environment name: `development`, `staging`, `prod`, or `test` |
| `COMPANION_DEBUG` | `false` | Debug mode |
| `COMPANION_API_V1_PREFIX` | `/api/v1` | API version prefix |

## 8. Running Tests

### Backend Tests

Start local services first (Postgres + Redis are required):

```bash
docker compose -f infrastructure/docker-compose.yml up -d
```

Create and migrate the test database:

```bash
PGPASSWORD=companion_dev psql -h localhost -U companion -d postgres -c "CREATE DATABASE companion_test;"

cd backend
COMPANION_DATABASE_URL=postgresql+asyncpg://companion:companion_dev@localhost:5432/companion_test \
  alembic upgrade head
```

Run tests:

```bash
cd backend
COMPANION_DATABASE_URL=postgresql+asyncpg://companion:companion_dev@localhost:5432/companion_test \
COMPANION_REDIS_URL=redis://localhost:6379/0 \
COMPANION_ENVIRONMENT=test \
COMPANION_DEV_AUTH_BYPASS=true \
  pytest -v
```

The test suite uses `pytest-asyncio` in auto mode. The `conftest.py` automatically creates a test user and replaces the DB engine with a NullPool variant to avoid async event loop conflicts.

### Backend Linting

```bash
cd backend
ruff check .
```

Ruff is configured in `pyproject.toml` targeting Python 3.12, line length 100.

### Web Linting

```bash
cd web
npm run lint
```

### Mobile App Tests

```bash
cd companion-app
npm test
```

### Terraform Validation

```bash
cd infrastructure/terraform
terraform fmt -check -recursive
terraform init -backend=false
terraform validate
```

## 9. Common Issues and Solutions

### "Connection refused" on port 5432 or 6379

The Docker services are not running. Start them:

```bash
docker compose -f infrastructure/docker-compose.yml up -d
```

Check service health:

```bash
docker compose -f infrastructure/docker-compose.yml ps
```

### `COMPANION_DEV_AUTH_BYPASS` not taking effect

Ensure you export the variable (not just set it). All settings use the `COMPANION_` prefix:

```bash
export COMPANION_DEV_AUTH_BYPASS=true
```

### `RuntimeError: FATAL: dev_auth_bypass is enabled in production`

The app refuses to start if `dev_auth_bypass=true` and `environment=prod`. Unset the bypass or change the environment.

### CocoaPods install fails with Firebase / React Native errors

The Podfile includes workarounds for non-modular header includes. Make sure you are using the correct Ruby/CocoaPods version. Try:

```bash
cd companion-app/ios
pod deintegrate
pod install --repo-update
```

### pgvector migration warning

Migration `011` gracefully skips pgvector if the extension is not installed. This is fine for basic development. Vector search features will be unavailable.

### Alembic "Target database is not up to date"

Run pending migrations:

```bash
cd backend
alembic upgrade head
```

### CORS errors in browser

The backend only allows specific origins per environment. For local dev (`development` environment), `http://localhost:5173` and `http://localhost:3000` are allowed. Make sure `COMPANION_ENVIRONMENT` is set to `development` (the default).

### CI uses Python 3.13 but `pyproject.toml` says >= 3.12

Both versions work. The CI workflow pins 3.13 and the Dockerfile uses `python:3.13-slim`. Local development with 3.12 or 3.13 is fine.

### Firebase auth not working in mobile app

Ensure `GoogleService-Info.plist` is present at `companion-app/ios/CompanionApp/GoogleService-Info.plist` and was downloaded from the correct Firebase project.
