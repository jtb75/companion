# 00 - Master Scaffold Plan

> Companion: AI-powered independence assistant for adults with developmental disabilities.

This is the definitive reference for the codebase structure, technology decisions, and build sequence. An engineer joining the project should be able to read this document and know exactly where everything goes and what to build next.

---

## 1. Technology Decisions

| Concern | Choice |
|---|---|
| API Framework | Python / FastAPI |
| Repo layout | Monorepo |
| Web dashboard | React / Vite / Tailwind |
| Mobile | React Native (future, not scaffolded yet) |
| Database | PostgreSQL + Redis |
| Event Bus | Google Cloud Pub/Sub |
| Auth | Firebase Auth |
| Cloud | GCP, Cloud Run for V1 |
| OCR | Google Document AI |
| TTS | Google Cloud TTS |
| STT | Google Cloud Speech-to-Text |
| Wake Word | Picovoice Porcupine |
| LLM | Decision pending (Claude or GPT-4, evaluate during build) |

---

## 2. Repository Structure

```
companion/
├── docs/
│   ├── product/
│   │   └── Companion Design Document v2.1.docx
│   └── architecture/
│       ├── 00-scaffold-plan.md          ← this document
│       ├── 01-system-overview.md
│       ├── 02-data-model.md
│       ├── 03-document-intelligence-pipeline.md
│       ├── 04-api-design.md
│       ├── 05-conversation-and-notification.md
│       ├── 06-caregiver-access-and-privacy.md
│       └── 07-web-dashboard.md
│
├── mockups/
│   └── onboarding-prototype/           ← existing React mockup
│
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   ├── app/
│   │   ├── main.py                     ← FastAPI app, middleware, lifespan
│   │   ├── config.py                   ← pydantic-settings, env-based config
│   │   ├── auth/
│   │   │   ├── firebase.py             ← token verification
│   │   │   ├── dependencies.py         ← get_current_user, get_caregiver, get_admin
│   │   │   └── middleware.py           ← tier enforcement, role enforcement
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── enums.py               ← all PostgreSQL enum types
│   │   │   ├── user.py
│   │   │   ├── document.py
│   │   │   ├── medication.py
│   │   │   ├── appointment.py
│   │   │   ├── bill.py
│   │   │   ├── todo.py
│   │   │   ├── trusted_contact.py
│   │   │   ├── question_tracker.py
│   │   │   ├── functional_memory.py
│   │   │   ├── system_config.py
│   │   │   ├── pipeline_metrics.py
│   │   │   └── admin_user.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── common.py              ← pagination, error envelope, meta
│   │   │   ├── user.py
│   │   │   ├── document.py
│   │   │   ├── medication.py
│   │   │   ├── appointment.py
│   │   │   ├── bill.py
│   │   │   ├── todo.py
│   │   │   ├── contact.py
│   │   │   ├── conversation.py
│   │   │   ├── notification.py
│   │   │   ├── caregiver.py
│   │   │   └── admin.py
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py        ← v1 router aggregation
│   │   │   │   ├── users.py
│   │   │   │   ├── documents.py
│   │   │   │   ├── sections.py
│   │   │   │   ├── medications.py
│   │   │   │   ├── appointments.py
│   │   │   │   ├── bills.py
│   │   │   │   ├── todos.py
│   │   │   │   ├── contacts.py
│   │   │   │   ├── conversation.py
│   │   │   │   ├── notifications.py
│   │   │   │   └── integrations.py
│   │   │   ├── caregiver/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── alerts.py
│   │   │   │   ├── dashboard.py
│   │   │   │   └── collaboration.py
│   │   │   ├── pipeline/
│   │   │   │   ├── __init__.py
│   │   │   │   └── results.py
│   │   │   └── admin/
│   │   │       ├── __init__.py
│   │   │       ├── config.py
│   │   │       ├── pipeline_health.py
│   │   │       ├── escalations.py
│   │   │       ├── metrics.py
│   │   │       └── admin_users.py
│   │   ├── services/
│   │   │   ├── document_service.py
│   │   │   ├── medication_service.py
│   │   │   ├── bill_service.py
│   │   │   ├── notification_service.py
│   │   │   ├── caregiver_service.py
│   │   │   ├── memory_service.py
│   │   │   ├── section_service.py
│   │   │   └── config_service.py
│   │   ├── pipeline/
│   │   │   ├── __init__.py
│   │   │   ├── ingestion.py
│   │   │   ├── classification.py
│   │   │   ├── extraction.py
│   │   │   ├── summarization.py
│   │   │   ├── routing.py
│   │   │   ├── tracker.py
│   │   │   ├── orchestrator.py
│   │   │   └── schemas.py
│   │   ├── conversation/
│   │   │   ├── __init__.py
│   │   │   ├── state_manager.py
│   │   │   ├── prompt_builder.py
│   │   │   ├── persona.py
│   │   │   ├── guided_flows.py
│   │   │   ├── tts.py
│   │   │   ├── stt.py
│   │   │   └── llm.py
│   │   ├── notifications/
│   │   │   ├── __init__.py
│   │   │   ├── priority.py
│   │   │   ├── scheduler.py
│   │   │   ├── morning_checkin.py
│   │   │   ├── escalation.py
│   │   │   └── channels.py
│   │   ├── integrations/
│   │   │   ├── __init__.py
│   │   │   ├── gmail.py
│   │   │   ├── plaid.py
│   │   │   ├── google_ocr.py
│   │   │   └── firebase_push.py
│   │   ├── workers/
│   │   │   ├── __init__.py
│   │   │   ├── retention.py
│   │   │   ├── ttl_purge.py
│   │   │   ├── escalation_check.py
│   │   │   ├── away_monitor.py
│   │   │   └── morning_trigger.py
│   │   ├── events/
│   │   │   ├── __init__.py
│   │   │   ├── publisher.py
│   │   │   ├── subscribers.py
│   │   │   └── schemas.py
│   │   └── db/
│   │       ├── __init__.py
│   │       ├── session.py
│   │       └── redis.py
│   └── tests/
│       ├── conftest.py
│       ├── test_api/
│       ├── test_pipeline/
│       ├── test_conversation/
│       ├── test_notifications/
│       └── test_services/
│
├── web/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.tsx
│   │   ├── shared/
│   │   │   ├── api/
│   │   │   │   ├── client.ts
│   │   │   │   ├── caregiver-api.ts
│   │   │   │   └── admin-api.ts
│   │   │   ├── auth/
│   │   │   │   ├── firebase.ts
│   │   │   │   ├── AuthProvider.tsx
│   │   │   │   └── guards.ts
│   │   │   ├── components/
│   │   │   └── hooks/
│   │   ├── caregiver/
│   │   │   ├── CaregiverLayout.tsx
│   │   │   ├── pages/
│   │   │   │   ├── AlertsPage.tsx
│   │   │   │   ├── DashboardPage.tsx
│   │   │   │   ├── ActivityPage.tsx
│   │   │   │   └── CollaboratePage.tsx
│   │   │   └── components/
│   │   ├── ops/
│   │   │   ├── OpsLayout.tsx
│   │   │   ├── pages/
│   │   │   │   ├── PipelinePage.tsx
│   │   │   │   ├── EscalationsPage.tsx
│   │   │   │   ├── MetricsPage.tsx
│   │   │   │   └── SystemPage.tsx
│   │   │   └── components/
│   │   └── admin/
│   │       ├── AdminLayout.tsx
│   │       ├── pages/
│   │       │   ├── PromptsPage.tsx
│   │       │   ├── ThresholdsPage.tsx
│   │       │   ├── EscalationRulesPage.tsx
│   │       │   ├── VoicesPage.tsx
│   │       │   ├── NotificationsPage.tsx
│   │       │   ├── EmailRulesPage.tsx
│   │       │   └── AuditPage.tsx
│   │       └── components/
│   └── public/
│
├── infrastructure/
│   ├── docker-compose.yml             ← local dev: Postgres, Redis, Pub/Sub emulator
│   ├── Dockerfile.backend
│   ├── Dockerfile.web
│   └── cloud-run/
│       ├── backend-service.yaml
│       └── web-service.yaml
│
├── scripts/
│   ├── seed.py                        ← seed dev DB with "Sam" user + sample data
│   └── run_pipeline.py                ← manual pipeline test runner
│
└── .gitignore
```

---

## 3. Dependency Manifest

### Backend (`backend/pyproject.toml`)

| Category | Packages |
|---|---|
| API framework | `fastapi`, `uvicorn[standard]` |
| Database | `sqlalchemy[asyncio]`, `asyncpg`, `alembic` |
| Cache | `redis[hiredis]`, `aioredis` |
| Validation / config | `pydantic`, `pydantic-settings` |
| Auth | `firebase-admin` |
| GCP services | `google-cloud-pubsub`, `google-cloud-storage`, `google-cloud-texttospeech`, `google-cloud-speech`, `google-cloud-documentai` |
| HTTP client | `httpx` |
| LLM clients | `anthropic`, `openai` (both included for evaluation period) |
| Testing | `pytest`, `pytest-asyncio`, `httpx` |

### Web (`web/package.json`)

| Category | Packages |
|---|---|
| Core | `react`, `react-dom`, `react-router-dom` |
| Data fetching | `@tanstack/react-query` |
| Auth | `firebase` |
| Styling | `tailwindcss`, `@tailwindcss/forms`, `@tailwindcss/typography` |
| Charts | `recharts` or `@tremor/react` (evaluate during Phase 8) |
| Build tooling | `vite`, `@vitejs/plugin-react`, `typescript` |

---

## 4. Build Sequence

### Phase 1 -- Foundation (runnable empty API)

1. Initialize `pyproject.toml` with all dependencies listed above.
2. `docker-compose.yml`: Postgres 16, Redis 7, Pub/Sub emulator.
3. FastAPI app shell: `main.py`, `config.py`, lifespan handler (DB + Redis connections).
4. Database session setup (SQLAlchemy async engine and session factory).
5. Redis client setup with namespace helpers.
6. Alembic init + first migration (`001_initial_schema.py` derived from `02-data-model.md`).
7. Enum types and SQLAlchemy models for all tables.
8. `.gitignore` updates for Python, Node, IDE files, and secrets.

**Milestone:** `docker compose up` then `uvicorn app.main:app` starts a healthy API. Database tables are created. Health endpoint returns OK.

---

### Phase 2 -- Auth & API Surface (route stubs with real auth)

1. Firebase Auth token verification (`auth/firebase.py`).
2. Auth dependencies: `get_current_user`, `get_caregiver` (with tier check), `get_admin` (with role check).
3. Pydantic schemas: `common.py` first (pagination, error envelope, meta), then per-resource schemas.
4. All App API v1 route stubs (return placeholder data, real auth enforced).
5. All Caregiver API route stubs (tier enforcement verified).
6. All Pipeline API route stubs.
7. All Admin API route stubs (role enforcement verified).

**Milestone:** All 50+ endpoints return shaped responses. Auth works. Tier and role enforcement tested with Firebase tokens.

---

### Phase 3 -- Data Layer (real CRUD)

1. Service layer: `document_service`, `medication_service`, `bill_service`, `notification_service`, `caregiver_service`, `memory_service`, `section_service`, `config_service`.
2. Wire route handlers to services for real database reads and writes.
3. Section aggregation service (cross-section "today" view).
4. Config service: `system_config` CRUD plus `config.updated` event emission.
5. Seed script (`scripts/seed.py`): create "Sam" user with medications, bills, appointments, todos, and sample documents.

**Milestone:** Full CRUD working through the API. Seed data populates all four sections. A GET request returns real rows from the database.

---

### Phase 4 -- Event Bus (async communication)

1. Pub/Sub publisher helper (`events/publisher.py`).
2. Event payload schemas for all 22+ event types (`events/schemas.py`).
3. Subscriber wiring for key flows:
   - `document.processed` triggers section update.
   - `question.threshold_crossed` triggers caregiver alert.
   - `config.updated` triggers service reload.
4. Pipeline metrics recording on each stage event.

**Milestone:** Events flow between services. Config changes propagate to running services without restart. Events visible in Pub/Sub emulator logs.

---

### Phase 5 -- Pipeline Skeleton (document processing)

1. Pipeline orchestrator: chains stages, emits events at each transition, handles errors with retry and dead-letter.
2. Stage 1 -- Ingestion: camera upload to GCS, email attachment normalization.
3. Stage 2 -- Classification: stub LLM call with hardcoded responses for testing.
4. Stage 3 -- Extraction: stub extraction, schema-validated output per document type.
5. Stage 4 -- Summarization: stub LLM call, placeholder plain-language summaries.
6. Stage 5 -- Routing: routing table implemented, section updates written to DB.
7. Stage 6 -- Question tracker: log questions extracted from documents, check thresholds.
8. Pipeline metrics written at each stage completion.

**Milestone:** Upload a document image via the API. See it classified, extracted, routed to the correct section. Pipeline metrics recorded. Question tracker entries created.

---

### Phase 6 -- Conversation Skeleton (Arlo's brain)

1. Prompt builder with five-component assembly (persona + context + section data + conversation history + user message).
2. Arlo persona definition loaded from `system_config`, not hardcoded.
3. LLM client abstraction supporting both Claude and GPT-4 for evaluation.
4. Conversation state manager backed by Redis (session state, turn history, TTL).
5. TTS client: Google Cloud TTS with four voice profiles loaded from `system_config`.
6. STT client: Google Cloud STT with confidence scoring and fallback handling.
7. Conversation API endpoints wired to real services.

**Milestone:** `POST /conversation/message` with a text prompt returns an Arlo response in character. TTS audio returned as a streaming response. Conversation history persists across turns.

---

### Phase 7 -- Notification Engine

1. Priority assignment logic (four levels as defined in the design spec).
2. Morning check-in assembly: cross-section aggregation into a prompt, LLM generates a natural-language briefing.
3. Delivery scheduler: quiet hours enforcement, batching, context-sensitive timing.
4. Escalation evaluation: question tracker thresholds trigger caregiver alerts at the appropriate level.
5. Push notification delivery via Firebase Cloud Messaging.
6. In-app notification cards for the conversation interface.

**Milestone:** Morning check-in fires on schedule with real section data. Bills due tomorrow trigger a Level 2 notification. Missed medication acknowledgments escalate to the caregiver.

---

### Phase 8 -- Web Dashboard

1. Vite + React + Tailwind project initialization.
2. Shared layer: Firebase auth integration, API client with token injection, layout components.
3. Caregiver dashboard: alerts page, dashboard overview, activity feed, collaboration tools.
4. Ops dashboard: pipeline health monitor, escalation queue, pilot metrics.
5. Config admin: prompt editor with preview, threshold sliders, voice profile manager, notification rule editor, escalation rule editor, audit log viewer.

**Milestone:** A caregiver can log in and see Sam's summarized status across all sections. An admin can edit Arlo's persona prompt and see the change take effect in the next conversation turn.

---

### Phase 9 -- Integration & Polish

1. Gmail OAuth integration for email ingestion.
2. Background workers: retention enforcement, TTL purge, away mode monitor, escalation checker, morning trigger.
3. Seed script expanded with realistic document processing scenarios (medical bill, prescription label, appointment letter, insurance EOB).
4. End-to-end test: email arrives with a document attachment, pipeline processes it, section updates, morning check-in mentions it the next day, caregiver sees it in the dashboard.

**Milestone:** Full vertical slice working end to end. Ready for internal testing with real Firebase accounts.

---

## 5. Local Development Setup

```bash
# Clone and enter the repo
cd companion

# Start infrastructure (Postgres 16, Redis 7, Pub/Sub emulator)
docker compose up -d

# Install backend dependencies
cd backend
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Seed development data (creates "Sam" user + sample data across all sections)
python ../scripts/seed.py

# Start the backend API server
uvicorn app.main:app --reload --port 8000

# In a separate terminal, start the web dashboard
cd web
npm install
npm run dev
```

The API will be available at `http://localhost:8000`. The web dashboard will be available at `http://localhost:5173`. API docs are served at `http://localhost:8000/docs`.

---

## 6. What Is NOT Scaffolded

These items are explicitly deferred. Do not create directories or stubs for them.

| Item | Target |
|---|---|
| React Native mobile app | Built when mobile work begins, after the API surface is stable |
| Mail Station hardware integration | V2 |
| Outlook email integration | V2 |
| Agency account model (multi-org) | V2 |
| Paratransit API integration | V2 |
| Multi-language support | V2 |

---

## 7. Cross-References

Each architecture document covers a specific subsystem in depth:

- **01-system-overview.md** -- High-level architecture, service boundaries, deployment topology.
- **02-data-model.md** -- PostgreSQL schema, Redis key design, enum definitions. Source of truth for `001_initial_schema.py`.
- **03-document-intelligence-pipeline.md** -- Six-stage pipeline detail, LLM prompt templates, error handling, metrics.
- **04-api-design.md** -- All endpoints, request/response shapes, auth requirements, rate limits.
- **05-conversation-and-notification.md** -- Arlo persona, prompt assembly, notification priority, morning check-in, escalation rules.
- **06-caregiver-access-and-privacy.md** -- Tier model, data visibility rules, audit logging, collaboration features.
- **07-web-dashboard.md** -- Page inventory, component hierarchy, real-time update strategy.
